"""
Tendencia linear + arvore no residuo para o TDS (bloco 3 do aprofundamento) --
ataca diretamente a limitacao ja documentada empiricamente em script_03/04:
Random Forest, XGBoost e LightGBM saturam ou oscilam ao extrapolar porque
arvores nao extrapolam fora do range de valores vistos no treino.

Estrategia: (1) ajusta uma tendencia linear OLS na serie completa de TDS;
(2) calcula o residuo (TDS - tendencia) -- uma serie sem tendencia, so
sazonalidade/ruido, que fica DENTRO do range historico mesmo longe no futuro
(nao precisa extrapolar); (3) treina RF e XGBoost para prever esse residuo,
reaproveitando features/GridSearchCV de script_03/04; (4) previsao final =
tendencia extrapolada (que capta a direcao de longo prazo corretamente, como
os metodos estatisticos classicos ja mostraram) + residuo previsto pela
arvore (que so precisa modelar padroes de curto prazo, dentro do seu range de
treino).

Limitacao registrada: a incerteza da tendencia OLS (seu proprio IC) nao e
propagada para o IC90 final -- o IC reportado vem so da dispersao entre
arvores/regressao quantilica do residuo, subestimando a incerteza total.

Univariado em TDS: independe do tratamento de ND do BOD.
"""

import warnings
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
import xgboost as xgb

from script_03_random_forest_gridsearch import carregar_serie_tds, construir_features, FEATURES
from script_04_xgboost_lightgbm import checar_gpu_xgboost
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
SEED = 42
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/detrend-arvore-tds.png"

warnings.filterwarnings("ignore")


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def destendenciar(d: pd.DataFrame) -> tuple:
    """Retorna (dataframe com TDS_mgL substituido pelo residuo, objeto de
    regressao linregress usado)."""
    reg = stats.linregress(d["t_anos"].values, d["TDS_mgL"].values)
    d_resid = d.copy()
    d_resid["TDS_mgL"] = d["TDS_mgL"].values - (reg.intercept + reg.slope * d["t_anos"].values)
    return d_resid, reg


def prever_recursivo_residuo(modelo, d_resid: pd.DataFrame, n_passos: int):
    """Mesmo esquema recursivo de script_03.prever_recursivo, mas devolve
    tambem a dispersao entre arvores (para RF) -- para XGBoost so o ponto
    central (usa regressao quantilica separada se necessario; aqui mantido
    simples e documentado: IC90 do XGBoost vem do desvio dos residuos in-
    sample, nao de quantile regression, para nao dobrar o custo computacional
    desta fase)."""
    historico = d_resid[["Data", "TDS_mgL"]].copy()
    t0 = d_resid["t_anos"].iloc[-1]
    pontos = []
    for passo in range(1, n_passos + 1):
        data_alvo = d_resid["Data"].iloc[-1] + pd.DateOffset(months=passo)
        t_anos = t0 + passo / 12
        lag_1 = historico["TDS_mgL"].iloc[-1]
        lag_12 = historico["TDS_mgL"].iloc[-12] if len(historico) >= 12 else historico["TDS_mgL"].iloc[0]
        media_movel_3 = historico["TDS_mgL"].iloc[-3:].mean()
        x = pd.DataFrame([{
            "t_anos": t_anos,
            "mes_sin": np.sin(2 * np.pi * data_alvo.month / 12),
            "mes_cos": np.cos(2 * np.pi * data_alvo.month / 12),
            "lag_1": lag_1, "lag_12": lag_12, "media_movel_3": media_movel_3,
        }])[FEATURES]
        ponto = float(modelo.predict(x)[0])
        pontos.append(ponto)
        historico = pd.concat([historico, pd.DataFrame([{"Data": data_alvo, "TDS_mgL": ponto}])], ignore_index=True)
    return pontos


def treinar_rf(X, y):
    grade = {"n_estimators": [100, 300], "max_depth": [None, 5, 10], "min_samples_leaf": [1, 3, 5]}
    tscv = TimeSeriesSplit(n_splits=5)
    busca = GridSearchCV(RandomForestRegressor(random_state=SEED), grade, cv=tscv,
                          scoring="neg_root_mean_squared_error", n_jobs=-1)
    busca.fit(X, y)
    return busca.best_estimator_, busca.best_params_


def treinar_xgb(X, y, usa_gpu):
    grade = {"n_estimators": [100, 300], "max_depth": [3, 5, 7], "learning_rate": [0.03, 0.1]}
    tscv = TimeSeriesSplit(n_splits=5)
    base = xgb.XGBRegressor(tree_method="hist", device="cuda" if usa_gpu else "cpu", random_state=SEED)
    busca = GridSearchCV(base, grade, cv=tscv, scoring="neg_root_mean_squared_error", n_jobs=1 if usa_gpu else -1)
    busca.fit(X, y)
    return busca.best_estimator_, busca.best_params_


def rodar_detrend(nome_metodo: str, treinar_fn, d: pd.DataFrame, treino: pd.DataFrame, holdout: pd.DataFrame):
    treino_resid, reg_treino = destendenciar(treino)
    f_treino_resid = construir_features(treino_resid)
    modelo_treino, params_treino = treinar_fn(f_treino_resid[FEATURES], f_treino_resid["TDS_mgL"])

    tendencia_holdout = reg_treino.intercept + reg_treino.slope * holdout["t_anos"].values
    resid_holdout_real = holdout["TDS_mgL"].values - tendencia_holdout
    f_holdout_resid = construir_features(pd.concat([treino_resid.tail(12), holdout.assign(
        TDS_mgL=resid_holdout_real
    )], ignore_index=True)).tail(len(holdout))
    pred_resid_holdout = modelo_treino.predict(f_holdout_resid[FEATURES])
    pred_holdout = tendencia_holdout + pred_resid_holdout
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    d_resid_full, reg_full = destendenciar(d)
    f_full_resid = construir_features(d_resid_full)
    modelo_full, params_full = treinar_fn(f_full_resid[FEATURES], f_full_resid["TDS_mgL"])

    max_passos = max(HORIZONTES_ANOS) * 12
    pontos_resid = prever_recursivo_residuo(modelo_full, d_resid_full, max_passos)
    resid_in_sample = f_full_resid["TDS_mgL"].values - modelo_full.predict(f_full_resid[FEATURES])
    desvio_resid = float(np.std(resid_in_sample, ddof=1))
    z = stats.norm.ppf(1 - ALPHA / 2)

    ultimo_t = d["t_anos"].iloc[-1]
    linha = {
        "metodo": nome_metodo, "tendencia_mgL_ano": reg_full.slope, "tendencia_pvalor": reg_full.pvalue,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "hiperparametros": str(params_treino),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        tendencia_h = reg_full.intercept + reg_full.slope * (ultimo_t + h)
        ponto = tendencia_h + pontos_resid[passo]
        margem = z * desvio_resid * np.sqrt((passo + 1) / 12)  # cresce com o horizonte (mesma logica do naive)
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = ponto - margem
        linha[f"ci90_high_{h}y"] = ponto + margem
        linha[f"ic90_width_{h}y"] = 2 * margem

    datas_futuras = [d["Data"].iloc[-1] + pd.DateOffset(months=p) for p in range(1, max_passos + 1)]
    pontos_totais = [reg_full.intercept + reg_full.slope * (ultimo_t + p / 12) + pontos_resid[p - 1]
                      for p in range(1, max_passos + 1)]
    return linha, params_treino, (datas_futuras, pontos_totais)


def construir_fit_predict_detrend(treinar_fn_com_params):
    """treinar_fn_com_params(X, y) -> modelo ja treinado com hiperparametros
    FIXOS (mesma decisao de escopo de scripts anteriores: nao repetir
    GridSearchCV a cada fold/origem de CV/backtest)."""
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        d_treino = pd.DataFrame({"Data": treino.index, "TDS_mgL": treino.values})
        d_treino["t_anos"] = (d_treino["Data"] - d_treino["Data"].iloc[0]).dt.days / 365.25
        d_resid, reg = destendenciar(d_treino)
        f_resid = construir_features(d_resid)
        modelo = treinar_fn_com_params(f_resid[FEATURES], f_resid["TDS_mgL"])
        pontos_resid = prever_recursivo_residuo(modelo, d_resid, n_passos)
        datas_futuras = pd.date_range(d_treino["Data"].iloc[-1], periods=n_passos + 1, freq="ME")[1:]
        t_futuro = (datas_futuras - d_treino["Data"].iloc[0]).days / 365.25
        tendencia_futura = reg.intercept + reg.slope * t_futuro.values
        return tendencia_futura + np.array(pontos_resid)
    return fit_predict


def gerar_figura(d, dados_rf, dados_xgb):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")
    for nome, dados, cor in [("Detrend+RF", dados_rf, "tab:olive"), ("Detrend+XGBoost", dados_xgb, "tab:gray")]:
        datas_futuras, pontos = dados
        ax.plot(datas_futuras, pontos, "--", color=cor, label=f"{nome} (previsao)")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Tendência + árvore no resíduo — previsão de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_10_detrend_arvore"
        linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
        linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    novas = pd.DataFrame(linhas)
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[~existentes["metodo"].isin(novas["metodo"])]
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas
    consolidado.to_csv(RESULTADOS_CSV, index=False)
    consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)


def main():
    d = carregar_serie_tds()
    treino, holdout = d.iloc[:-HOLDOUT_MESES].reset_index(drop=True), d.iloc[-HOLDOUT_MESES:].reset_index(drop=True)
    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(d)} meses | Treino: {len(treino)} | Holdout: {len(holdout)}")
    print()

    print("--- Detrend + Random Forest ---")
    linha_rf, params_rf, dados_rf = rodar_detrend("detrend_rf", treinar_rf, d, treino, holdout)
    linha_rf.update(validar_metodo(
        construir_fit_predict_detrend(lambda X, y: RandomForestRegressor(random_state=SEED, **params_rf).fit(X, y)),
        serie, treino_serie, holdout_serie,
    ))
    print(f"  Hiperparametros: {params_rf}")
    print(f"  Holdout: RMSE={linha_rf['rmse_holdout']:.2f}  MASE={linha_rf['mase_holdout']:.3f}  sMAPE={linha_rf['smape_holdout']:.2f}%")
    print(f"  CV: MASE={linha_rf['cv_mase_media']:.3f}±{linha_rf['cv_mase_desvio']:.3f}  Backtest+3a: MAE={linha_rf.get('backtest_mae_36m', float('nan')):.2f}")
    for h in HORIZONTES_ANOS:
        print(f"  +{h}a: {linha_rf[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha_rf[f'ci90_low_{h}y']:.1f}, {linha_rf[f'ci90_high_{h}y']:.1f}]")
    print()

    usa_gpu = checar_gpu_xgboost()
    print("--- Detrend + XGBoost ---")
    linha_xgb, params_xgb, dados_xgb = rodar_detrend(
        "detrend_xgb", lambda X, y: treinar_xgb(X, y, usa_gpu), d, treino, holdout
    )
    linha_xgb.update(validar_metodo(
        construir_fit_predict_detrend(lambda X, y: xgb.XGBRegressor(
            tree_method="hist", device="cuda" if usa_gpu else "cpu", random_state=SEED, **params_xgb
        ).fit(X, y)),
        serie, treino_serie, holdout_serie,
    ))
    print(f"  Hiperparametros: {params_xgb}  (GPU={usa_gpu})")
    print(f"  Holdout: RMSE={linha_xgb['rmse_holdout']:.2f}  MASE={linha_xgb['mase_holdout']:.3f}  sMAPE={linha_xgb['smape_holdout']:.2f}%")
    print(f"  CV: MASE={linha_xgb['cv_mase_media']:.3f}±{linha_xgb['cv_mase_desvio']:.3f}  Backtest+3a: MAE={linha_xgb.get('backtest_mae_36m', float('nan')):.2f}")
    for h in HORIZONTES_ANOS:
        print(f"  +{h}a: {linha_xgb[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha_xgb[f'ci90_low_{h}y']:.1f}, {linha_xgb[f'ci90_high_{h}y']:.1f}]")

    gravar_resultados([linha_rf, linha_xgb])
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(d, dados_rf, dados_xgb)

    for linha in (linha_rf, linha_xgb):
        with iniciar_run(
            linha["metodo"], "script_10_detrend_arvore", seed=SEED,
            janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
        ):
            logar_linha_resultado(linha)
            logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
