"""
XGBoost e LightGBM para o TDS (plano_projeto_TDS.md secao 3.c/3.e).

GPU: testado nesta maquina (RTX 4060 Ti, driver CUDA 13.3) —
  - XGBoost: `tree_method='hist', device='cuda'` funciona nativamente, usado aqui.
  - LightGBM: o pacote `lightgbm` instalado via pip NAO vem com suporte a GPU
    compilado (erro "GPU Tree Learner was not enabled in this build" ao tentar
    device='gpu') — exigiria recompilar com CMake -DUSE_GPU=1 (fora do escopo
    desta sessao). Roda em CPU, exatamente como o plano ja previa como
    fallback aceitavel — nao quebra o pipeline.

Reaproveita a engenharia de features e a serie de TDS do script_03 (mesmas
features de tempo/sazonalidade/lags), para nao duplicar logica. Mesma nota de
desenho dos scripts 01-03: univariado em TDS, independe do tratamento de ND
do BOD.

Diferente do script_03 (RF), aqui o IC90% vem de regressao quantilica de
verdade (objetivo quantile em cada biblioteca, alpha=0.05 e 0.95) treinada
com os mesmos hiperparametros do modelo pontual (escolhidos por
GridSearchCV), em vez da dispersao entre arvores — mais correto
estatisticamente. A previsao de longo prazo tambem e recursiva (mesma
limitacao de saturacao esperada para modelos baseados em arvore, ja
documentada no script_03).
"""

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
import xgboost as xgb
import lightgbm as lgb

from script_03_random_forest_gridsearch import carregar_serie_tds, construir_features, FEATURES
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/xgboost-lightgbm-tds.png"
SEED = 42

XGBOOST_GPU_OK = None  # descoberto em tempo de execucao


def checar_gpu_xgboost() -> bool:
    global XGBOOST_GPU_OK
    if XGBOOST_GPU_OK is not None:
        return XGBOOST_GPU_OK
    try:
        m = xgb.XGBRegressor(tree_method="hist", device="cuda", n_estimators=5)
        m.fit(np.random.rand(20, 2), np.random.rand(20))
        XGBOOST_GPU_OK = True
    except Exception as e:
        print(f"  Aviso: XGBoost CUDA indisponivel ({e}); caindo para CPU.")
        XGBOOST_GPU_OK = False
    return XGBOOST_GPU_OK


def grid_search_xgb(X_train, y_train):
    usa_gpu = checar_gpu_xgboost()
    base_kwargs = dict(tree_method="hist", device="cuda" if usa_gpu else "cpu", random_state=SEED)
    grade = {
        "n_estimators": [100, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.03, 0.1],
    }
    tscv = TimeSeriesSplit(n_splits=5)
    busca = GridSearchCV(
        xgb.XGBRegressor(**base_kwargs), grade, cv=tscv,
        scoring="neg_root_mean_squared_error", n_jobs=1 if usa_gpu else -1,
    )
    busca.fit(X_train, y_train)
    print(f"  XGBoost — melhores hiperparametros ({'GPU/CUDA' if usa_gpu else 'CPU'}): {busca.best_params_}")
    return busca.best_estimator_, busca.best_params_, usa_gpu


def grid_search_lgbm(X_train, y_train):
    grade = {
        "n_estimators": [100, 300],
        "max_depth": [3, 5, -1],
        "learning_rate": [0.03, 0.1],
    }
    tscv = TimeSeriesSplit(n_splits=5)
    busca = GridSearchCV(
        lgb.LGBMRegressor(random_state=SEED, verbose=-1), grade, cv=tscv,
        scoring="neg_root_mean_squared_error", n_jobs=-1,
    )
    busca.fit(X_train, y_train)
    print(f"  LightGBM — melhores hiperparametros (CPU): {busca.best_params_}")
    return busca.best_estimator_, busca.best_params_


def treinar_quantis_xgb(X, y, params, usa_gpu):
    modelos = {}
    for q, nome in [(0.05, "baixo"), (0.95, "alto")]:
        m = xgb.XGBRegressor(
            tree_method="hist", device="cuda" if usa_gpu else "cpu", random_state=SEED,
            objective="reg:quantileerror", quantile_alpha=q, **params,
        )
        m.fit(X, y)
        modelos[nome] = m
    return modelos


def treinar_quantis_lgbm(X, y, params):
    modelos = {}
    for q, nome in [(0.05, "baixo"), (0.95, "alto")]:
        m = lgb.LGBMRegressor(random_state=SEED, verbose=-1, objective="quantile", alpha=q, **params)
        m.fit(X, y)
        modelos[nome] = m
    return modelos


def prever_recursivo(modelo_ponto, modelos_quantil, d: pd.DataFrame, n_passos: int):
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

        ponto = float(modelo_ponto.predict(x)[0])
        lo = float(modelos_quantil["baixo"].predict(x)[0])
        hi = float(modelos_quantil["alto"].predict(x)[0])
        # modelos de quantil sao treinados separadamente do modelo pontual e
        # podem "cruzar" (quantile crossing) — garante que o IC sempre contem
        # o ponto central
        lo, hi = min(lo, hi, ponto), max(lo, hi, ponto)

        pontos.append(ponto)
        baixos.append(lo)
        altos.append(hi)
        historico = pd.concat(
            [historico, pd.DataFrame([{"Data": data_alvo, "TDS_mgL": ponto}])], ignore_index=True
        )

    return pontos, baixos, altos


def _fit_predict_arvore_generico(treino: pd.Series, n_passos: int, treinar_modelo_fn):
    """Reconstroi features a partir de um treino (pd.Series indexado por
    data), treina um unico modelo pontual (hiperparametros FIXOS, ja
    escolhidos por GridSearchCV em main() -- mesma decisao de escopo do
    script_03: repetir a busca em grade em ~25 folds/origens seria caro
    demais) e roda a previsao recursiva ja existente. Os modelos de quantil
    nao sao retreinados aqui -- validar_metodo so usa a previsao pontual."""
    d_treino = pd.DataFrame({"Data": treino.index, "TDS_mgL": treino.values})
    d_treino["t_anos"] = (d_treino["Data"] - d_treino["Data"].iloc[0]).dt.days / 365.25
    f_treino = construir_features(d_treino)
    modelo = treinar_modelo_fn(f_treino[FEATURES], f_treino["TDS_mgL"])
    pontos, _, _ = prever_recursivo(modelo, {"baixo": modelo, "alto": modelo}, d_treino, n_passos)
    return np.array(pontos)


def construir_fit_predict_xgb(params: dict, usa_gpu: bool):
    def treinar(X, y):
        m = xgb.XGBRegressor(tree_method="hist", device="cuda" if usa_gpu else "cpu",
                              random_state=SEED, **params)
        m.fit(X, y)
        return m
    return lambda treino, n_passos: _fit_predict_arvore_generico(treino, n_passos, treinar)


def construir_fit_predict_lgbm(params: dict):
    def treinar(X, y):
        m = lgb.LGBMRegressor(random_state=SEED, verbose=-1, **params)
        m.fit(X, y)
        return m
    return lambda treino, n_passos: _fit_predict_arvore_generico(treino, n_passos, treinar)


def montar_linha(nome_metodo, rmse, mae, r2, pontos, params_extra=None):
    passos_10a = 10 * 12
    reg = stats.linregress(np.arange(passos_10a), pontos[0][:passos_10a])  # pontos[0] = lista de pontos
    linha = {
        "metodo": nome_metodo,
        "tendencia_mgL_ano": reg.slope * 12,
        "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"),
        "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
    }
    if params_extra:
        linha["hiperparametros"] = str(params_extra)
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = pontos[0][passo]
        linha[f"ci90_low_{h}y"] = pontos[1][passo]
        linha[f"ci90_high_{h}y"] = pontos[2][passo]
    return linha


def gerar_figura(d, datas_futuras, resultados_por_metodo):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")
    cores = {"xgboost": "tab:orange", "lightgbm": "tab:cyan"}
    for nome, (pontos, baixos, altos) in resultados_por_metodo.items():
        cor = cores.get(nome, "gray")
        ax.plot(datas_futuras, pontos, "--", color=cor, label=f"{nome} (previsao)")
        ax.fill_between(datas_futuras, baixos, altos, color=cor, alpha=0.15)
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("XGBoost e LightGBM — previsao recursiva de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_04_xgboost_lightgbm"
        linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
        linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame(linhas)
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
    treino, holdout = f.iloc[:-HOLDOUT_MESES], f.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(d)} meses | apos features: {len(f)} | Treino: {len(treino)} | Holdout: {len(holdout)}")
    print()

    max_passos = max(HORIZONTES_ANOS) * 12
    linhas = []
    resultados_por_metodo = {}

    print("--- XGBoost ---")
    modelo_xgb, params_xgb, usa_gpu = grid_search_xgb(treino[FEATURES], treino["TDS_mgL"])
    pred_holdout = modelo_xgb.predict(holdout[FEATURES])
    rmse = float(np.sqrt(mean_squared_error(holdout["TDS_mgL"], pred_holdout)))
    mae = float(mean_absolute_error(holdout["TDS_mgL"], pred_holdout))
    r2 = float(r2_score(holdout["TDS_mgL"], pred_holdout))
    print(f"  Holdout: RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.3f}")

    modelo_xgb_full, params_xgb_full, usa_gpu = grid_search_xgb(f[FEATURES], f["TDS_mgL"])
    quantis_xgb = treinar_quantis_xgb(f[FEATURES], f["TDS_mgL"], params_xgb_full, usa_gpu)
    pontos, baixos, altos = prever_recursivo(modelo_xgb_full, quantis_xgb, d, max_passos)
    resultados_por_metodo["xgboost"] = (pontos, baixos, altos)
    params_xgb_full["device"] = "cuda" if usa_gpu else "cpu"
    linha_xgb = montar_linha("xgboost", rmse, mae, r2, (pontos, baixos, altos), params_xgb_full)
    linhas.append(linha_xgb)
    print()

    print("--- LightGBM ---")
    modelo_lgb, params_lgb = grid_search_lgbm(treino[FEATURES], treino["TDS_mgL"])
    pred_holdout = modelo_lgb.predict(holdout[FEATURES])
    rmse = float(np.sqrt(mean_squared_error(holdout["TDS_mgL"], pred_holdout)))
    mae = float(mean_absolute_error(holdout["TDS_mgL"], pred_holdout))
    r2 = float(r2_score(holdout["TDS_mgL"], pred_holdout))
    print(f"  Holdout: RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.3f}")

    modelo_lgb_full, params_lgb_full = grid_search_lgbm(f[FEATURES], f["TDS_mgL"])
    quantis_lgb = treinar_quantis_lgbm(f[FEATURES], f["TDS_mgL"], params_lgb_full)
    pontos, baixos, altos = prever_recursivo(modelo_lgb_full, quantis_lgb, d, max_passos)
    resultados_por_metodo["lightgbm"] = (pontos, baixos, altos)
    params_lgb_full["device"] = "cpu"
    linha_lgb = montar_linha("lightgbm", rmse, mae, r2, (pontos, baixos, altos), params_lgb_full)
    linhas.append(linha_lgb)
    print()

    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]
    fit_predicts = {
        "xgboost": construir_fit_predict_xgb(params_xgb, usa_gpu),
        "lightgbm": construir_fit_predict_lgbm(params_lgb),
    }

    for linha in linhas:
        linha.update(validar_metodo(fit_predicts[linha["metodo"]], serie, treino_serie, holdout_serie))
        for h in HORIZONTES_ANOS:
            baixo, alto = linha[f"ci90_low_{h}y"], linha[f"ci90_high_{h}y"]
            if not (np.isnan(baixo) or np.isnan(alto)):
                linha[f"ic90_width_{h}y"] = alto - baixo

        print(f"--- {linha['metodo']} (resumo) ---")
        print(f"  Tendencia implicita (1os 10a): {linha['tendencia_mgL_ano']:.3f} mg/L/ano (p={linha['tendencia_pvalor']:.4f})")
        print(f"  Holdout: MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
        print(f"  CV (5 folds expansivos): RMSE={linha['cv_rmse_media']:.2f}±{linha['cv_rmse_desvio']:.2f}  "
              f"MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}")
        print(f"  Backtest origem movel: MAE(+3a)={linha.get('backtest_mae_36m', float('nan')):.2f}  "
              f"MAE(+5a)={linha.get('backtest_mae_60m', float('nan')):.2f}")
        for h in HORIZONTES_ANOS:
            print(f"  +{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]")

    gravar_resultados(linhas)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

    datas_futuras = [d["Data"].iloc[-1] + pd.DateOffset(months=p) for p in range(1, max_passos + 1)]
    gerar_figura(d, datas_futuras, resultados_por_metodo)

    for linha in linhas:
        with iniciar_run(
            linha["metodo"], "script_04_xgboost_lightgbm",
            params={"device": "cuda" if (linha["metodo"] == "xgboost" and usa_gpu) else "cpu"},
            seed=SEED,
            janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
        ):
            logar_linha_resultado(linha)
            logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
