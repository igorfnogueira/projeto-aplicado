"""
Diagnostico isolado (issue #1/#8): hiperparametro FIXO (escolhido uma unica
vez fora da validacao cruzada, decisao de escopo ja registrada em script_03/
04/09) vs. CV ANINHADA (hiperparametro reotimizado a cada fold/origem de
expanding_window_cv/backtest_origem_movel) para RF, XGBoost, LightGBM e SVR.

NAO roda junto do pipeline principal (nao e chamado por nenhum outro
script) -- e caro (cada fold reaplica um GridSearchCV inteiro) e serve so
para responder uma pergunta pontual: a simplificacao de hiperparametro fixo
muda materialmente o erro de CV/backtest reportado? Se a diferenca entre
"fixo" e "aninhado" for pequena, a simplificacao atual fica justificada e
nao precisa ser revisitada.

GP (script_09) fica de fora -- GaussianProcessRegressor ja reajusta o
kernel via MLE a cada fold (sem GridSearchCV externo), nao ha nada a mudar.

TimeSeriesSplit interno reduzido para n_splits=3 (em vez de 5): com
min_treino=60 e series de ~150-180 meses, um fold de CV pode ter so ~10-20
meses de treino -- 5 splits internos deixaria folds internos minusculos
demais para os grids de RF/XGB/LightGBM/SVR.

Saida propria: results/cv_aninhada_resultados.csv (nao toca em
resultados_comparacao.csv).
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.paths import bootstrap_sys_path, result, RESULTADOS_COMPARACAO_CSV
bootstrap_sys_path()


import time
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from script_03_random_forest_gridsearch import carregar_serie_tds, construir_features, FEATURES, prever_recursivo
from script_04_xgboost_lightgbm import checar_gpu_xgboost, _fit_predict_arvore_generico
from script_09_svr_gp import prever_recursivo_svr
from utils.validacao_utils import expanding_window_cv, resumir_cv, backtest_origem_movel, resumir_backtest

warnings.filterwarnings("ignore")

HOLDOUT_MESES = 24
SEED = 42
N_SPLITS_ANINHADO = 3
RESULTADOS_CSV = result("cv_aninhada_resultados.csv")


def carregar_serie() -> pd.Series:
    d = carregar_serie_tds()
    return pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))


def _d_treino_de_serie(treino: pd.Series) -> pd.DataFrame:
    d_treino = pd.DataFrame({"Data": treino.index, "TDS_mgL": treino.values})
    d_treino["t_anos"] = (d_treino["Data"] - d_treino["Data"].iloc[0]).dt.days / 365.25
    return d_treino


# --------------------------------------------------------------------------
# Random Forest
# --------------------------------------------------------------------------

def _treinar_rf_aninhado(X, y):
    grade = {"n_estimators": [100, 300], "max_depth": [None, 5, 10], "min_samples_leaf": [1, 3, 5]}
    tscv = TimeSeriesSplit(n_splits=N_SPLITS_ANINHADO)
    busca = GridSearchCV(RandomForestRegressor(random_state=SEED), grade, cv=tscv,
                          scoring="neg_root_mean_squared_error", n_jobs=-1)
    busca.fit(X, y)
    return busca.best_estimator_


def fit_predict_rf_aninhado(treino: pd.Series, n_passos: int) -> np.ndarray:
    d_treino = _d_treino_de_serie(treino)
    f_treino = construir_features(d_treino)
    modelo = _treinar_rf_aninhado(f_treino[FEATURES], f_treino["TDS_mgL"])
    pontos, _, _ = prever_recursivo(modelo, d_treino, n_passos)
    return np.array(pontos)


# --------------------------------------------------------------------------
# XGBoost / LightGBM (reaproveita _fit_predict_arvore_generico de script_04)
# --------------------------------------------------------------------------

def _treinar_xgb_aninhado(X, y):
    usa_gpu = checar_gpu_xgboost()
    grade = {"n_estimators": [100, 300], "max_depth": [3, 5, 7], "learning_rate": [0.03, 0.1]}
    tscv = TimeSeriesSplit(n_splits=N_SPLITS_ANINHADO)
    base = xgb.XGBRegressor(tree_method="hist", device="cuda" if usa_gpu else "cpu", random_state=SEED)
    busca = GridSearchCV(base, grade, cv=tscv, scoring="neg_root_mean_squared_error",
                          n_jobs=1 if usa_gpu else -1)
    busca.fit(X, y)
    return busca.best_estimator_


def fit_predict_xgb_aninhado(treino: pd.Series, n_passos: int) -> np.ndarray:
    return _fit_predict_arvore_generico(treino, n_passos, _treinar_xgb_aninhado)


def _treinar_lgbm_aninhado(X, y):
    grade = {"n_estimators": [100, 300], "max_depth": [3, 5, -1], "learning_rate": [0.03, 0.1]}
    tscv = TimeSeriesSplit(n_splits=N_SPLITS_ANINHADO)
    busca = GridSearchCV(lgb.LGBMRegressor(random_state=SEED, verbose=-1), grade, cv=tscv,
                          scoring="neg_root_mean_squared_error", n_jobs=-1)
    busca.fit(X, y)
    return busca.best_estimator_


def fit_predict_lgbm_aninhado(treino: pd.Series, n_passos: int) -> np.ndarray:
    return _fit_predict_arvore_generico(treino, n_passos, _treinar_lgbm_aninhado)


# --------------------------------------------------------------------------
# SVR
# --------------------------------------------------------------------------

def fit_predict_svr_aninhado(treino: pd.Series, n_passos: int) -> np.ndarray:
    d_treino = _d_treino_de_serie(treino)
    f_treino = construir_features(d_treino)
    grade = {"svr__C": [1, 10, 100], "svr__epsilon": [0.5, 1.0, 5.0], "svr__gamma": ["scale", "auto"]}
    pipe = make_pipeline(StandardScaler(), SVR(kernel="rbf"))
    tscv = TimeSeriesSplit(n_splits=N_SPLITS_ANINHADO)
    busca = GridSearchCV(pipe, grade, cv=tscv, scoring="neg_root_mean_squared_error", n_jobs=-1)
    busca.fit(f_treino[FEATURES], f_treino["TDS_mgL"])
    pontos, _, _ = prever_recursivo_svr(busca.best_estimator_, d_treino, n_passos)
    return np.array(pontos)


FIT_PREDICTS_ANINHADOS = {
    "random_forest": fit_predict_rf_aninhado,
    "xgboost": fit_predict_xgb_aninhado,
    "lightgbm": fit_predict_lgbm_aninhado,
    "svr": fit_predict_svr_aninhado,
}


def ler_versao_fixa(metodo: str) -> dict:
    tabela = pd.read_csv(RESULTADOS_COMPARACAO_CSV).set_index("metodo")
    if metodo not in tabela.index:
        return {"cv_mase_media": float("nan"), "cv_mase_desvio": float("nan"), "backtest_mae_36m": float("nan")}
    linha = tabela.loc[metodo]
    return {
        "cv_mase_media": float(linha.get("cv_mase_media", float("nan"))),
        "cv_mase_desvio": float(linha.get("cv_mase_desvio", float("nan"))),
        "backtest_mae_36m": float(linha.get("backtest_mae_36m", float("nan"))),
    }


def rodar_diagnostico_metodo(metodo: str, fit_predict_fn, serie: pd.Series) -> list:
    print(f"--- {metodo} (aninhado, TimeSeriesSplit(n_splits={N_SPLITS_ANINHADO}) por fold) ---")
    t0 = time.time()

    cv = expanding_window_cv(serie, fit_predict_fn, n_folds=5, horizonte=12, min_treino=60)
    resumo_cv = resumir_cv(cv)
    bt = backtest_origem_movel(serie, fit_predict_fn, min_treino=60)
    resumo_bt = resumir_backtest(bt)

    tempo_execucao_s = time.time() - t0
    fixo = ler_versao_fixa(metodo)

    linhas = [
        {
            "metodo": metodo, "variante": "fixo",
            "cv_mase_media": fixo["cv_mase_media"], "cv_mase_desvio": fixo["cv_mase_desvio"],
            "backtest_mae_36m": fixo["backtest_mae_36m"], "tempo_execucao_s": float("nan"),
        },
        {
            "metodo": metodo, "variante": "aninhado",
            "cv_mase_media": resumo_cv["cv_mase_media"], "cv_mase_desvio": resumo_cv["cv_mase_desvio"],
            "backtest_mae_36m": resumo_bt.get("backtest_mae_36m", float("nan")),
            "tempo_execucao_s": tempo_execucao_s,
        },
    ]
    print(f"  fixo:     cv_mase_media={fixo['cv_mase_media']:.3f}  backtest_mae_36m={fixo['backtest_mae_36m']:.2f}")
    print(f"  aninhado: cv_mase_media={resumo_cv['cv_mase_media']:.3f}  "
          f"backtest_mae_36m={resumo_bt.get('backtest_mae_36m', float('nan')):.2f}  "
          f"(tempo={tempo_execucao_s:.1f}s)")
    print()
    return linhas


def gravar_resultados(linhas: list):
    df = pd.DataFrame(linhas)
    df["script"] = "script_32_cv_aninhada_diagnostico"
    df["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    df.to_csv(RESULTADOS_CSV, index=False)
    return df


def main():
    print("Diagnostico de CV aninhada -- isolado do pipeline principal, pode ser lento")
    print("(cada fold de CV/backtest reaplica um GridSearchCV inteiro por metodo).\n")

    serie = carregar_serie()
    print(f"Serie TDS: {len(serie)} meses\n")

    todas_linhas = []
    tempo_total_0 = time.time()
    for metodo, fit_predict_fn in FIT_PREDICTS_ANINHADOS.items():
        todas_linhas.extend(rodar_diagnostico_metodo(metodo, fit_predict_fn, serie))
    tempo_total = time.time() - tempo_total_0

    df = gravar_resultados(todas_linhas)
    print(f"Tempo total: {tempo_total:.1f}s")
    print(f"Resultados gravados em {RESULTADOS_CSV}")

    for metodo in FIT_PREDICTS_ANINHADOS:
        sub = df[df["metodo"] == metodo].set_index("variante")
        if sub.loc["fixo", "cv_mase_media"] == 0 or pd.isna(sub.loc["fixo", "cv_mase_media"]):
            continue
        diff_pct = abs(sub.loc["aninhado", "cv_mase_media"] - sub.loc["fixo", "cv_mase_media"]) / sub.loc["fixo", "cv_mase_media"] * 100
        veredito = "diferenca pequena (<10%), simplificacao de hiperparametro fixo parece segura" if diff_pct < 10 else "diferenca relevante (>=10%), vale revisitar a simplificacao"
        print(f"  {metodo}: diferenca de cv_mase_media = {diff_pct:.1f}% -- {veredito}")


if __name__ == "__main__":
    main()
