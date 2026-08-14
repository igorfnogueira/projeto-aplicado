"""
Random Forest para o TDS (plano_projeto_TDS.md secao 3.c), construido do zero
(notebook antigo nao reaproveitado). CPU apenas — RF so ganha GPU com cuML/
RAPIDS (nao disponivel nesta maquina Windows), entao roda via scikit-learn.

Mesma nota de desenho dos scripts 01/02: univariado em TDS, independe do
tratamento de ND do BOD.

Diferenca importante em relacao aos scripts 01/02: arvores nao tem uma nocao
nativa de "reta de tendencia" nem extrapolam linearmente — preve um valor a
partir de features. Para conseguir prever meses futuros, e preciso:
  1. Construir features (tempo, mes do ano, lags, media movel);
  2. Fazer busca de hiperparametros com GridSearchCV + TimeSeriesSplit
     (nunca embaralhar dados temporais);
  3. Prever o holdout em modo "one-step" (lags reais conhecidos);
  4. Prever os horizontes de +10/+15/+20 anos em modo RECURSIVO (a previsao
     de um mes vira o lag do mes seguinte), unico jeito de chegar tao longe.

Limitacao conhecida e esperada (ja registrada no plano, secao 3.c): arvores
nao extrapolam fora do range de valores vistos no treino — a previsao tende a
SATURAR (achatar) em vez de continuar subindo, especialmente em +15/+20 anos.
Isso e reportado explicitamente nos resultados, nao escondido.
"""

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/random-forest-tds.png"
SEED = 42


def carregar_serie_tds() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    return d


def construir_features(d: pd.DataFrame) -> pd.DataFrame:
    f = d.copy()
    f["mes_sin"] = np.sin(2 * np.pi * f["Data"].dt.month / 12)
    f["mes_cos"] = np.cos(2 * np.pi * f["Data"].dt.month / 12)
    f["lag_1"] = f["TDS_mgL"].shift(1)
    f["lag_12"] = f["TDS_mgL"].shift(12)
    f["media_movel_3"] = f["TDS_mgL"].shift(1).rolling(3).mean()
    return f.dropna().reset_index(drop=True)


FEATURES = ["t_anos", "mes_sin", "mes_cos", "lag_1", "lag_12", "media_movel_3"]


def treinar_grid_search(X_train, y_train) -> RandomForestRegressor:
    grade = {
        "n_estimators": [100, 300],
        "max_depth": [None, 5, 10],
        "min_samples_leaf": [1, 3, 5],
    }
    tscv = TimeSeriesSplit(n_splits=5)
    busca = GridSearchCV(
        RandomForestRegressor(random_state=SEED),
        grade, cv=tscv, scoring="neg_root_mean_squared_error", n_jobs=-1,
    )
    busca.fit(X_train, y_train)
    print(f"  Melhores hiperparametros (CV temporal, RMSE): {busca.best_params_}")
    return busca.best_estimator_, busca.best_params_


def prever_recursivo(modelo: RandomForestRegressor, d: pd.DataFrame, n_passos: int):
    """Previsao passo-a-passo: a previsao de um mes vira o lag do mes seguinte
    (unico jeito de projetar uma arvore muitos meses a frente). Tambem retorna,
    a cada passo, o intervalo empirico [5%,95%] das previsoes das arvores
    individuais da floresta (aproximacao de incerteza — nao inclui a
    incerteza composta de erros anteriores realimentados na recursao)."""
    historico = d[["Data", "TDS_mgL"]].copy()
    t0 = d["t_anos"].iloc[-1]
    pontos, baixos, altos = [], [], []

    for passo in range(1, n_passos + 1):
        data_alvo = d["Data"].iloc[-1] + pd.DateOffset(months=passo)
        t_anos = t0 + passo / 12
        lag_1 = historico["TDS_mgL"].iloc[-1]
        lag_12 = historico["TDS_mgL"].iloc[-12] if len(historico) >= 12 else historico["TDS_mgL"].iloc[0]
        media_movel_3 = historico["TDS_mgL"].iloc[-3:].mean()
        x = pd.DataFrame([{
            "t_anos": t_anos,
            "mes_sin": np.sin(2 * np.pi * data_alvo.month / 12),
            "mes_cos": np.cos(2 * np.pi * data_alvo.month / 12),
            "lag_1": lag_1,
            "lag_12": lag_12,
            "media_movel_3": media_movel_3,
        }])[FEATURES]

        preds_arvores = np.array([arv.predict(x.values)[0] for arv in modelo.estimators_])
        ponto = float(preds_arvores.mean())
        lo, hi = np.percentile(preds_arvores, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])

        pontos.append(ponto)
        baixos.append(float(lo))
        altos.append(float(hi))
        historico = pd.concat(
            [historico, pd.DataFrame([{"Data": data_alvo, "TDS_mgL": ponto}])], ignore_index=True
        )

    return pontos, baixos, altos


def construir_fit_predict_rf(params: dict):
    """Adaptador para validacao_utils.validar_metodo. Hiperparametros FIXOS
    (os ja escolhidos uma unica vez por GridSearchCV em treino/main()) --
    repetir a busca em grade dentro de cada um dos ~25 folds/origens de CV+
    backtest multiplicaria o custo computacional sem ganho proporcional
    (mesma decisao de escopo do SARIMA em script_02). treino chega como
    pd.Series indexado por data; reconstroi features e roda a previsao
    recursiva ja existente (prever_recursivo)."""
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        d_treino = pd.DataFrame({"Data": treino.index, "TDS_mgL": treino.values})
        d_treino["t_anos"] = (d_treino["Data"] - d_treino["Data"].iloc[0]).dt.days / 365.25
        f_treino = construir_features(d_treino)
        modelo = RandomForestRegressor(random_state=SEED, **params)
        modelo.fit(f_treino[FEATURES], f_treino["TDS_mgL"])
        pontos, _, _ = prever_recursivo(modelo, d_treino, n_passos)
        return np.array(pontos)
    return fit_predict


def gerar_figura(d: pd.DataFrame, datas_futuras, pontos, baixos, altos):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")
    ax.plot(datas_futuras, pontos, "--", color="tab:brown", label="Random Forest (previsao recursiva)")
    ax.fill_between(datas_futuras, baixos, altos, color="tab:brown", alpha=0.15, label="IC90% (dispersao entre arvores)")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Random Forest — previsao recursiva de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linha: dict):
    linha["script"] = "script_03_random_forest_gridsearch"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[~existentes["metodo"].isin(novas["metodo"])]
        for col in novas.columns:
            if col not in existentes.columns:
                existentes[col] = np.nan
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas

    consolidado.to_csv(RESULTADOS_CSV, index=False)
    consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)


def main():
    d = carregar_serie_tds()
    f = construir_features(d)
    print(f"Serie TDS: {len(d)} meses | apos engenharia de features (lags): {len(f)} meses")

    treino, holdout = f.iloc[:-HOLDOUT_MESES], f.iloc[-HOLDOUT_MESES:]
    print(f"Treino: {len(treino)} meses | Holdout: {len(holdout)} meses (ultimos {HOLDOUT_MESES})")
    print()

    modelo, melhores_params = treinar_grid_search(treino[FEATURES], treino["TDS_mgL"])

    # holdout em modo one-step (lags reais, ja conhecidos)
    pred_holdout = modelo.predict(holdout[FEATURES])
    rmse = float(np.sqrt(mean_squared_error(holdout["TDS_mgL"], pred_holdout)))
    mae = float(mean_absolute_error(holdout["TDS_mgL"], pred_holdout))
    r2 = float(r2_score(holdout["TDS_mgL"], pred_holdout))
    print(f"Holdout (one-step, lags reais): RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.3f}")

    # refit na serie completa (features), para a previsao recursiva final
    modelo_full, _ = treinar_grid_search(f[FEATURES], f["TDS_mgL"])

    max_passos = max(HORIZONTES_ANOS) * 12
    pontos, baixos, altos = prever_recursivo(modelo_full, d, max_passos)
    datas_futuras = [d["Data"].iloc[-1] + pd.DateOffset(months=p) for p in range(1, max_passos + 1)]

    # tendencia implicita: OLS sobre os primeiros 10 anos do caminho recursivo
    passos_10a = 10 * 12
    reg = stats.linregress(np.arange(passos_10a), pontos[:passos_10a])

    linha = {
        "metodo": "random_forest",
        "tendencia_mgL_ano": reg.slope * 12,
        "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"),
        "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
        "hiperparametros": str(melhores_params),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = pontos[passo]
        linha[f"ci90_low_{h}y"] = baixos[passo]
        linha[f"ci90_high_{h}y"] = altos[passo]

    print()
    print(f"Tendencia implicita (OLS sobre previsao recursiva, 1os 10 anos): {linha['tendencia_mgL_ano']:.3f} mg/L/ano (p={linha['tendencia_pvalor']:.4f})")
    for h in HORIZONTES_ANOS:
        print(f"  +{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]")

    incremento_10_15 = abs(linha["forecast_15y"] - linha["forecast_10y"])
    incremento_15_20 = abs(linha["forecast_20y"] - linha["forecast_15y"])
    saturou = incremento_15_20 <= incremento_10_15 * 0.5 + 1e-6
    if saturou:
        print("\n  AVISO: a previsao mostra sinal de saturacao entre +15 e +20 anos"
              " (incremento visivelmente menor que entre +10 e +15) — limitacao"
              " esperada de arvores extrapolando fora do range de treino (ver plano, secao 3.c).")

    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]
    linha.update(validar_metodo(construir_fit_predict_rf(melhores_params), serie, treino_serie, holdout_serie))
    for h in HORIZONTES_ANOS:
        baixo, alto = linha[f"ci90_low_{h}y"], linha[f"ci90_high_{h}y"]
        if not (np.isnan(baixo) or np.isnan(alto)):
            linha[f"ic90_width_{h}y"] = alto - baixo
    print(f"\nHoldout: MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
    print(f"CV (5 folds expansivos): RMSE={linha['cv_rmse_media']:.2f}±{linha['cv_rmse_desvio']:.2f}  "
          f"MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}")
    print(f"Backtest origem movel: MAE(+3a)={linha.get('backtest_mae_36m', float('nan')):.2f}  "
          f"MAE(+5a)={linha.get('backtest_mae_60m', float('nan')):.2f}")

    gravar_resultados(linha)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(d, datas_futuras, pontos, baixos, altos)

    with iniciar_run(
        "random_forest", "script_03_random_forest_gridsearch",
        params=melhores_params, seed=SEED,
        janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
    ):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
