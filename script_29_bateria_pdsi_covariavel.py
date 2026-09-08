"""
Segunda rodada da bateria original com o PDSI como covariavel climatica
(Artigo/DECISOES.md D-56): re-treina os 10 metodos da bateria de
script_01-script_15 que aceitam regressor exogeno, agora com o PDSI
(defasagem de 4 meses, mesmo lag de D-37/D-41) como covariavel adicional,
para comparar diretamente -- metodo a metodo -- o quanto cada um muda em
relacao a versao original (sem PDSI) ja gravada em resultados_comparacao.csv.

NAO substitui nem sobrescreve as linhas originais -- cada metodo entra aqui
com o sufixo "_com_pdsi" (ex. sarima_com_pdsi, xgboost_com_pdsi).

Escopo (D-56): SARIMAX, Random Forest, XGBoost, LightGBM, Prophet (regressor
externo), regressao bayesiana, SVR, Detrend+RF, hibrido SARIMA+Prophet, GAM,
regressao quantilica (Q50) e espaco de estados (PDSI como exog do
UnobservedComponents). Excluidos (D-56): os 4 baselines, os testes de
tendencia estatistica de script_01 (nao sao modelos treinaveis com
covariavel), e o LSTM (ja abaixo dos baselines mesmo sem covariavel).

PDSI futuro (para os horizontes +10/+15/+20a, alem do que ja e conhecido):
trajetoria DETERMINISTICA de reversao a media do mesmo AR(1) ajustado em
script_21 (mu, phi do cenario "normal"), sem ruido -- ou seja, o valor
esperado E[PDSI_t] sob o cenario normal, nao uma simulacao Monte Carlo. Essa
e a mesma limitacao declarada do Cloreto extrapolado em script_11: a
incerteza de qual cenario climatico de fato ocorrera NAO e propagada ao IC90
final de cada metodo aqui.
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.gaussian_process import GaussianProcessRegressor  # noqa: F401  (nao usado nesta rodada, GP fica fora do escopo D-56)
from statsmodels.regression.quantile_regression import QuantReg
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.statespace.structural import UnobservedComponents
import xgboost as xgb
import lightgbm as lgb
from pygam import LinearGAM, s

from script_00_preprocessamento import construir_datasets
from script_02_arima_sarima import buscar_melhor_sarima
from script_03_random_forest_gridsearch import construir_features, FEATURES
from script_04_xgboost_lightgbm import checar_gpu_xgboost
from script_21_cenarios import ajustar_ar1, carregar_lag_otimo, carregar_pdsi_historico
from script_23_gam import construir_termo_sazonal, LAM_FLOOR_TENDENCIA
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

warnings.filterwarnings("ignore")

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
SEED = 42
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
COMPARACAO_ANTES_DEPOIS_CSV = "comparacao_pdsi_antes_depois.csv"
FIGURA_PATH = "Artigo/images/bateria-pdsi-covariavel-comparacao.png"

FEATURES_PDSI = FEATURES + ["pdsi_lag"]

METODOS_NESTA_RODADA = [
    "sarima", "random_forest", "xgboost", "lightgbm", "prophet",
    "regressao_bayesiana", "svr", "detrend_rf", "hibrido_arima_prophet",
    "gam", "regressao_quantilica_q50", "espaco_estados_dlm",
]


# --------------------------------------------------------------------------
# Covariavel PDSI: historico real + extensao deterministica (cenario normal)
# --------------------------------------------------------------------------

def construir_pdsi_estendido(pdsi_hist: pd.Series, ar1: dict, ultima_data_necessaria: pd.Timestamp) -> pd.Series:
    """Concatena o PDSI historico real com uma extensao deterministica (sem
    ruido) do MESMO AR(1) de script_21, ate cobrir qualquer data usada como
    PDSI(lag) por esta rodada -- inclusive as datas de treino/holdout mais
    recentes que ja estejam alem do ultimo PDSI historico baixado."""
    pdsi_hist = pdsi_hist.copy()
    ultima_data_hist = pdsi_hist.index[-1]
    if ultima_data_necessaria <= ultima_data_hist:
        return pdsi_hist
    datas_futuras = pd.date_range(ultima_data_hist, ultima_data_necessaria, freq="ME")[1:]
    valores = np.empty(len(datas_futuras))
    anterior = float(pdsi_hist.iloc[-1])
    for i in range(len(datas_futuras)):
        anterior = ar1["mu"] + ar1["phi"] * (anterior - ar1["mu"])
        valores[i] = anterior
    extensao = pd.Series(valores, index=datas_futuras)
    return pd.concat([pdsi_hist, extensao])


def pdsi_lag_em(pdsi_estendido: pd.Series, datas: pd.DatetimeIndex, lag: int) -> np.ndarray:
    """PDSI(data - lag meses) para cada data pedida, usando o PDSI histórico
    real quando disponível e a extensão determinística (normal) além dele.

    `pd.DateOffset(months=lag)` preserva o dia-do-mês (ex.: 30/abr - 4 meses =
    30/dez, não 31/dez) em vez de "fim de mês" -- por isso a defasagem é
    renormalizada para o fim do mês antes do reindex. Sem isso, uma chamada
    com uma única data (como nas funções de previsão recursiva) não tem
    vizinhos para o ffill/bfill usar e vira NaN sempre que o offset bruto cai
    num dia que não é o último do mês alvo."""
    datas_defasadas = (pd.DatetimeIndex(datas) - pd.DateOffset(months=lag)) + pd.offsets.MonthEnd(0)
    return pdsi_estendido.reindex(datas_defasadas).ffill().bfill().values


def carregar_tudo():
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["Data"] = pd.to_datetime(d["Data"]) + pd.offsets.MonthEnd(0)
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25

    lag = carregar_lag_otimo()
    pdsi_hist = carregar_pdsi_historico()
    ar1 = ajustar_ar1(pdsi_hist)

    max_passos = max(HORIZONTES_ANOS) * 12
    ultima_data_necessaria = d["Data"].iloc[-1] + pd.DateOffset(months=max_passos)
    pdsi_estendido = construir_pdsi_estendido(pdsi_hist, ar1, ultima_data_necessaria)

    d["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(d["Data"]), lag)
    return d, lag, pdsi_estendido, ar1


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan")
    return rmse, mae, r2


def montar_linha_base(nome_metodo, pontos, ic_low=None, ic_high=None):
    passos_10a = 10 * 12
    reg = stats.linregress(np.arange(passos_10a), pontos[:passos_10a])
    linha = {
        "metodo": f"{nome_metodo}_com_pdsi",
        "tendencia_mgL_ano": reg.slope * 12,
        "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"),
        "tendencia_ic90_alto": float("nan"),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = float(pontos[passo])
        if ic_low is not None and ic_high is not None:
            linha[f"ci90_low_{h}y"] = float(ic_low[passo])
            linha[f"ci90_high_{h}y"] = float(ic_high[passo])
            linha[f"ic90_width_{h}y"] = float(ic_high[passo] - ic_low[passo])
        else:
            linha[f"ci90_low_{h}y"] = float("nan")
            linha[f"ci90_high_{h}y"] = float("nan")
    return linha


# --------------------------------------------------------------------------
# 1. SARIMAX(TDS, exog=PDSI_lag)  -- mesma ordem de script_02
# --------------------------------------------------------------------------

def rodar_sarimax_pdsi(d, pdsi_estendido, lag, ordem, ordem_sazonal, trend):
    s = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    exog = pd.Series(d["pdsi_lag"].values, index=s.index)
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    exog_treino, exog_holdout = exog.iloc[:-HOLDOUT_MESES], exog.iloc[-HOLDOUT_MESES:]

    modelo_treino = SARIMAX(treino, exog=exog_treino.values.reshape(-1, 1), order=ordem,
                             seasonal_order=ordem_sazonal, trend=trend,
                             enforce_stationarity=False, enforce_invertibility=False)
    res_treino = modelo_treino.fit(disp=False)
    pred_holdout = res_treino.get_forecast(steps=len(holdout), exog=exog_holdout.values.reshape(-1, 1)).predicted_mean.values
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    modelo_full = SARIMAX(s, exog=exog.values.reshape(-1, 1), order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                           enforce_stationarity=False, enforce_invertibility=False)
    res_full = modelo_full.fit(disp=False)
    coef_pdsi = float(res_full.params.get("x1", float("nan")))
    coef_pdsi_p = float(res_full.pvalues.get("x1", float("nan")))

    max_passos = max(HORIZONTES_ANOS) * 12
    datas_futuras = pd.date_range(s.index[-1], periods=max_passos + 1, freq="ME")[1:]
    exog_futuro = pdsi_lag_em(pdsi_estendido, datas_futuras, lag)
    prev = res_full.get_forecast(steps=max_passos, exog=exog_futuro.reshape(-1, 1))
    media = prev.predicted_mean.values
    ic = prev.conf_int(alpha=ALPHA)

    linha = montar_linha_base("sarima", media, ic.iloc[:, 0].values, ic.iloc[:, 1].values)
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, r2
    linha["ordem_sarima"] = f"order={ordem} seasonal_order={ordem_sazonal} trend={trend}"
    linha["hiperparametros"] = str({"coef_pdsi": round(coef_pdsi, 4), "coef_pdsi_p": round(coef_pdsi_p, 4)})

    def fit_predict(treino_s, n_passos):
        exog_tr = exog.reindex(treino_s.index).values.reshape(-1, 1)
        m = SARIMAX(treino_s, exog=exog_tr, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                    enforce_stationarity=False, enforce_invertibility=False)
        r = m.fit(disp=False)
        datas_fut = pd.date_range(treino_s.index[-1], periods=n_passos + 1, freq="ME")[1:]
        exog_fut = pdsi_lag_em(pdsi_estendido, datas_fut, lag)
        return r.get_forecast(steps=n_passos, exog=exog_fut.reshape(-1, 1)).predicted_mean.values

    return linha, fit_predict, (s, treino, holdout)


# --------------------------------------------------------------------------
# 2-4. Random Forest / XGBoost / LightGBM com pdsi_lag como feature extra
# --------------------------------------------------------------------------

def construir_features_pdsi(d: pd.DataFrame) -> pd.DataFrame:
    f = construir_features(d)
    return f


def prever_recursivo_arvore_pdsi(modelo, d: pd.DataFrame, pdsi_estendido: pd.Series, lag: int, n_passos: int):
    historico = d[["Data", "TDS_mgL"]].copy()
    t0 = d["t_anos"].iloc[-1]
    pontos = []
    for passo in range(1, n_passos + 1):
        data_alvo = d["Data"].iloc[-1] + pd.DateOffset(months=passo)
        t_anos = t0 + passo / 12
        lag_1 = historico["TDS_mgL"].iloc[-1]
        lag_12 = historico["TDS_mgL"].iloc[-12] if len(historico) >= 12 else historico["TDS_mgL"].iloc[0]
        media_movel_3 = historico["TDS_mgL"].iloc[-3:].mean()
        pdsi_val = float(pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex([data_alvo]), lag)[0])
        x = pd.DataFrame([{
            "t_anos": t_anos, "mes_sin": np.sin(2 * np.pi * data_alvo.month / 12),
            "mes_cos": np.cos(2 * np.pi * data_alvo.month / 12),
            "lag_1": lag_1, "lag_12": lag_12, "media_movel_3": media_movel_3, "pdsi_lag": pdsi_val,
        }])[FEATURES_PDSI]
        ponto = float(modelo.predict(x)[0])
        pontos.append(ponto)
        historico = pd.concat([historico, pd.DataFrame([{"Data": data_alvo, "TDS_mgL": ponto}])], ignore_index=True)
    return pontos


def _grid_search(modelo_base, grade, X, y):
    tscv = TimeSeriesSplit(n_splits=5)
    busca = GridSearchCV(modelo_base, grade, cv=tscv, scoring="neg_root_mean_squared_error", n_jobs=-1)
    busca.fit(X, y)
    return busca.best_estimator_, busca.best_params_


def rodar_arvore_pdsi(nome_metodo, treinar_fn, d, pdsi_estendido, lag):
    f = construir_features_pdsi(d)
    f["pdsi_lag"] = d.set_index("Data").reindex(f["Data"])["pdsi_lag"].values
    treino, holdout = f.iloc[:-HOLDOUT_MESES], f.iloc[-HOLDOUT_MESES:]

    modelo_treino, params_treino = treinar_fn(treino[FEATURES_PDSI], treino["TDS_mgL"])
    pred_holdout = modelo_treino.predict(holdout[FEATURES_PDSI])
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    modelo_full, params_full = treinar_fn(f[FEATURES_PDSI], f["TDS_mgL"])
    max_passos = max(HORIZONTES_ANOS) * 12
    d_para_recursao = d[["Data", "TDS_mgL", "t_anos"]]
    pontos = prever_recursivo_arvore_pdsi(modelo_full, d_para_recursao, pdsi_estendido, lag, max_passos)

    linha = montar_linha_base(nome_metodo, np.array(pontos))
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, r2
    linha["hiperparametros"] = str(params_full)

    def fit_predict(treino_s, n_passos):
        d_tr = pd.DataFrame({"Data": treino_s.index, "TDS_mgL": treino_s.values})
        d_tr["t_anos"] = (d_tr["Data"] - d_tr["Data"].iloc[0]).dt.days / 365.25
        f_tr = construir_features_pdsi(d_tr)
        f_tr["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(f_tr["Data"]), lag)
        m, _ = treinar_fn(f_tr[FEATURES_PDSI], f_tr["TDS_mgL"])
        return np.array(prever_recursivo_arvore_pdsi(m, d_tr[["Data", "TDS_mgL", "t_anos"]], pdsi_estendido, lag, n_passos))

    return linha, fit_predict


def treinar_rf_pdsi(X, y):
    grade = {"n_estimators": [100, 300], "max_depth": [None, 5, 10], "min_samples_leaf": [1, 3, 5]}
    return _grid_search(RandomForestRegressor(random_state=SEED), grade, X, y)


def treinar_xgb_pdsi(X, y, usa_gpu):
    grade = {"n_estimators": [100, 300], "max_depth": [3, 5, 7], "learning_rate": [0.03, 0.1]}
    base = xgb.XGBRegressor(tree_method="hist", device="cuda" if usa_gpu else "cpu", random_state=SEED)
    return _grid_search(base, grade, X, y)


def treinar_lgbm_pdsi(X, y):
    grade = {"n_estimators": [100, 300], "max_depth": [3, 5, -1], "learning_rate": [0.03, 0.1]}
    return _grid_search(lgb.LGBMRegressor(random_state=SEED, verbose=-1), grade, X, y)


# --------------------------------------------------------------------------
# 5. Prophet com PDSI(lag) como regressor externo
# --------------------------------------------------------------------------

def rodar_prophet_pdsi(d):
    from prophet import Prophet

    treino, holdout = d.iloc[:-HOLDOUT_MESES], d.iloc[-HOLDOUT_MESES:]
    df_treino = treino[["Data", "TDS_mgL", "pdsi_lag"]].rename(columns={"Data": "ds", "TDS_mgL": "y"})
    m_treino = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m_treino.add_regressor("pdsi_lag")
    m_treino.fit(df_treino)
    futuro_holdout = holdout[["Data", "pdsi_lag"]].rename(columns={"Data": "ds"})
    prev_holdout = m_treino.predict(futuro_holdout)
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, prev_holdout["yhat"].values)

    df_full = d[["Data", "TDS_mgL", "pdsi_lag"]].rename(columns={"Data": "ds", "TDS_mgL": "y"})
    m_full = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m_full.add_regressor("pdsi_lag")
    m_full.fit(df_full)

    return m_full, treino, holdout, rmse, mae, r2


def construir_fit_predict_prophet_pdsi(pdsi_estendido, lag):
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        from prophet import Prophet
        datas_treino = pd.DatetimeIndex(treino.index)
        df_treino = pd.DataFrame({
            "ds": datas_treino, "y": treino.values,
            "pdsi_lag": pdsi_lag_em(pdsi_estendido, datas_treino, lag),
        })
        m = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m.add_regressor("pdsi_lag")
        m.fit(df_treino)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        futuro = pd.DataFrame({"ds": datas_futuras, "pdsi_lag": pdsi_lag_em(pdsi_estendido, datas_futuras, lag)})
        return m.predict(futuro)["yhat"].values
    return fit_predict


# --------------------------------------------------------------------------
# 6. Regressao bayesiana: TDS ~ tempo + PDSI(lag)  (PyMC/NUTS)
# --------------------------------------------------------------------------

def ajustar_bayes_pdsi(t: np.ndarray, pdsi: np.ndarray, y: np.ndarray, draws=800, tune=800):
    import pymc as pm

    t_centro, pdsi_centro = t.mean(), pdsi.mean()
    tc, pc = t - t_centro, pdsi - pdsi_centro
    with pm.Model():
        a = pm.Normal("a", mu=float(y.mean()), sigma=float(y.std() * 3 + 50))
        b_t = pm.Normal("b_t", mu=0, sigma=50)
        b_pdsi = pm.Normal("b_pdsi", mu=0, sigma=50)
        sigma = pm.HalfNormal("sigma", sigma=float(y.std() * 2 + 10))
        mu = a + b_t * tc + b_pdsi * pc
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)
        idata = pm.sample(draws, tune=tune, chains=2, cores=1, progressbar=False,
                           random_seed=SEED, target_accept=0.9)
    return idata, t_centro, pdsi_centro


def rodar_bayes_pdsi(d, pdsi_estendido, lag):
    treino, holdout = d.iloc[:-HOLDOUT_MESES], d.iloc[-HOLDOUT_MESES:]

    idata_tr, t_c_tr, p_c_tr = ajustar_bayes_pdsi(treino["t_anos"].values, treino["pdsi_lag"].values, treino["TDS_mgL"].values)
    a_tr, bt_tr, bp_tr = (float(idata_tr.posterior[v].mean()) for v in ("a", "b_t", "b_pdsi"))
    pred_holdout = a_tr + bt_tr * (holdout["t_anos"].values - t_c_tr) + bp_tr * (holdout["pdsi_lag"].values - p_c_tr)
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    idata_full, t_c, p_c = ajustar_bayes_pdsi(d["t_anos"].values, d["pdsi_lag"].values, d["TDS_mgL"].values)
    a_s = idata_full.posterior["a"].values.flatten()
    bt_s = idata_full.posterior["b_t"].values.flatten()
    bp_s = idata_full.posterior["b_pdsi"].values.flatten()
    sigma_s = idata_full.posterior["sigma"].values.flatten()

    b_t_mean = float(bt_s.mean())
    prob_pos = float((bt_s > 0).mean())
    p_valor = 2 * min(prob_pos, 1 - prob_pos)

    rng = np.random.default_rng(SEED)
    max_passos = max(HORIZONTES_ANOS) * 12
    datas_futuras = pd.date_range(d["Data"].iloc[-1], periods=max_passos + 1, freq="ME")[1:]
    pdsi_futuro = pdsi_lag_em(pdsi_estendido, datas_futuras, lag)
    t_ultimo = d["t_anos"].iloc[-1]

    linha = {
        "metodo": "regressao_bayesiana_com_pdsi",
        "tendencia_mgL_ano": b_t_mean, "tendencia_pvalor": p_valor,
        "tendencia_ic90_baixo": float(np.percentile(bt_s, 100 * ALPHA / 2)),
        "tendencia_ic90_alto": float(np.percentile(bt_s, 100 * (1 - ALPHA / 2))),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "prob_tendencia_positiva": prob_pos,
        "hiperparametros": str({"coef_pdsi": round(float(bp_s.mean()), 4)}),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        t_h = t_ultimo + h
        mu_draws = a_s + bt_s * (t_h - t_c) + bp_s * (pdsi_futuro[passo] - p_c)
        pred_draws = rng.normal(mu_draws, sigma_s)
        linha[f"forecast_{h}y"] = float(np.mean(pred_draws))
        lo, hi = np.percentile(pred_draws, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
        linha[f"ci90_low_{h}y"] = float(lo)
        linha[f"ci90_high_{h}y"] = float(hi)
        linha[f"ic90_width_{h}y"] = float(hi - lo)

    def fit_predict(treino_s, n_passos):
        """Aproximacao OLS (mesma razao de script_05: NUTS a cada fold seria caro demais)."""
        data0 = treino_s.index[0]
        t = (treino_s.index - data0).days / 365.25
        pdsi_tr = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(treino_s.index), lag)
        X = sm.add_constant(np.column_stack([t, pdsi_tr]))
        modelo = sm.OLS(treino_s.values, X).fit()
        datas_fut = pd.date_range(treino_s.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_fut = (datas_fut - data0).days / 365.25
        pdsi_fut = pdsi_lag_em(pdsi_estendido, datas_fut, lag)
        X_fut = sm.add_constant(np.column_stack([t_fut, pdsi_fut]), has_constant="add")
        return modelo.predict(X_fut)

    return linha, fit_predict


# --------------------------------------------------------------------------
# 7. SVR com pdsi_lag como feature extra (mesmo esquema de script_09)
# --------------------------------------------------------------------------

def prever_recursivo_svr_pdsi(modelo, d, pdsi_estendido, lag, n_passos, residuos_boot=None, n_boot=0, rng=None):
    def caminho(injetar_residuo):
        historico = d[["Data", "TDS_mgL"]].copy()
        t0 = d["t_anos"].iloc[-1]
        pontos = []
        for passo in range(1, n_passos + 1):
            data_alvo = d["Data"].iloc[-1] + pd.DateOffset(months=passo)
            t_anos = t0 + passo / 12
            lag_1 = historico["TDS_mgL"].iloc[-1]
            lag_12 = historico["TDS_mgL"].iloc[-12] if len(historico) >= 12 else historico["TDS_mgL"].iloc[0]
            media_movel_3 = historico["TDS_mgL"].iloc[-3:].mean()
            pdsi_val = float(pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex([data_alvo]), lag)[0])
            x = pd.DataFrame([{
                "t_anos": t_anos, "mes_sin": np.sin(2 * np.pi * data_alvo.month / 12),
                "mes_cos": np.cos(2 * np.pi * data_alvo.month / 12),
                "lag_1": lag_1, "lag_12": lag_12, "media_movel_3": media_movel_3, "pdsi_lag": pdsi_val,
            }])[FEATURES_PDSI]
            ponto = float(modelo.predict(x)[0])
            if injetar_residuo:
                ponto = ponto + rng.choice(residuos_boot)
            pontos.append(ponto)
            historico = pd.concat([historico, pd.DataFrame([{"Data": data_alvo, "TDS_mgL": ponto}])], ignore_index=True)
        return pontos

    ponto_central = caminho(False)
    if n_boot == 0:
        return ponto_central, ponto_central, ponto_central
    replicas = np.array([caminho(True) for _ in range(n_boot)])
    baixos = np.percentile(replicas, 100 * ALPHA / 2, axis=0)
    altos = np.percentile(replicas, 100 * (1 - ALPHA / 2), axis=0)
    return ponto_central, baixos.tolist(), altos.tolist()


def rodar_svr_pdsi(d, pdsi_estendido, lag):
    rng = np.random.default_rng(SEED)
    f = construir_features_pdsi(d)
    f["pdsi_lag"] = d.set_index("Data").reindex(f["Data"])["pdsi_lag"].values
    treino, holdout = f.iloc[:-HOLDOUT_MESES], f.iloc[-HOLDOUT_MESES:]

    grade = {"svr__C": [1, 10, 100], "svr__epsilon": [0.5, 1.0, 5.0], "svr__gamma": ["scale", "auto"]}
    pipe = make_pipeline(StandardScaler(), SVR(kernel="rbf"))
    modelo, params = _grid_search(pipe, grade, treino[FEATURES_PDSI], treino["TDS_mgL"])
    pred_holdout = modelo.predict(holdout[FEATURES_PDSI])
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    modelo_full, params_full = _grid_search(pipe, grade, f[FEATURES_PDSI], f["TDS_mgL"])
    residuos = f["TDS_mgL"].values - modelo_full.predict(f[FEATURES_PDSI])

    max_passos = max(HORIZONTES_ANOS) * 12
    d_rec = d[["Data", "TDS_mgL", "t_anos"]]
    pontos, baixos, altos = prever_recursivo_svr_pdsi(modelo_full, d_rec, pdsi_estendido, lag, max_passos, residuos, 200, rng)

    linha = montar_linha_base("svr", np.array(pontos), baixos, altos)
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, r2
    linha["hiperparametros"] = str(params_full)

    def fit_predict(treino_s, n_passos):
        d_tr = pd.DataFrame({"Data": treino_s.index, "TDS_mgL": treino_s.values})
        d_tr["t_anos"] = (d_tr["Data"] - d_tr["Data"].iloc[0]).dt.days / 365.25
        f_tr = construir_features_pdsi(d_tr)
        f_tr["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(f_tr["Data"]), lag)
        p = make_pipeline(StandardScaler(), SVR(kernel="rbf", **{k.replace("svr__", ""): v for k, v in params.items()}))
        p.fit(f_tr[FEATURES_PDSI], f_tr["TDS_mgL"])
        pontos_, _, _ = prever_recursivo_svr_pdsi(p, d_tr[["Data", "TDS_mgL", "t_anos"]], pdsi_estendido, lag, n_passos)
        return np.array(pontos_)

    return linha, fit_predict


# --------------------------------------------------------------------------
# 8. Detrend + RF, com pdsi_lag como feature extra no residuo
# --------------------------------------------------------------------------

def destendenciar(d):
    reg = stats.linregress(d["t_anos"].values, d["TDS_mgL"].values)
    d_resid = d.copy()
    d_resid["TDS_mgL"] = d["TDS_mgL"].values - (reg.intercept + reg.slope * d["t_anos"].values)
    return d_resid, reg


def rodar_detrend_rf_pdsi(d, pdsi_estendido, lag):
    treino, holdout = d.iloc[:-HOLDOUT_MESES].reset_index(drop=True), d.iloc[-HOLDOUT_MESES:].reset_index(drop=True)

    treino_resid, reg_treino = destendenciar(treino)
    f_treino_resid = construir_features_pdsi(treino_resid)
    f_treino_resid["pdsi_lag"] = treino_resid.set_index("Data").reindex(f_treino_resid["Data"])["pdsi_lag"].values
    modelo_treino, _ = treinar_rf_pdsi(f_treino_resid[FEATURES_PDSI], f_treino_resid["TDS_mgL"])

    tendencia_holdout = reg_treino.intercept + reg_treino.slope * holdout["t_anos"].values
    resid_holdout_real = holdout["TDS_mgL"].values - tendencia_holdout
    holdout_resid = holdout.assign(TDS_mgL=resid_holdout_real)
    f_holdout_resid = construir_features_pdsi(pd.concat([treino_resid.tail(12), holdout_resid], ignore_index=True)).tail(len(holdout))
    f_holdout_resid["pdsi_lag"] = holdout_resid.set_index("Data").reindex(f_holdout_resid["Data"])["pdsi_lag"].values
    pred_resid_holdout = modelo_treino.predict(f_holdout_resid[FEATURES_PDSI])
    pred_holdout = tendencia_holdout + pred_resid_holdout
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    d_resid_full, reg_full = destendenciar(d)
    f_full_resid = construir_features_pdsi(d_resid_full)
    f_full_resid["pdsi_lag"] = d_resid_full.set_index("Data").reindex(f_full_resid["Data"])["pdsi_lag"].values
    modelo_full, params_full = treinar_rf_pdsi(f_full_resid[FEATURES_PDSI], f_full_resid["TDS_mgL"])

    max_passos = max(HORIZONTES_ANOS) * 12
    d_resid_rec = d_resid_full[["Data", "TDS_mgL", "t_anos"]]
    pontos_resid = prever_recursivo_arvore_pdsi(modelo_full, d_resid_rec, pdsi_estendido, lag, max_passos)
    resid_in_sample = f_full_resid["TDS_mgL"].values - modelo_full.predict(f_full_resid[FEATURES_PDSI])
    desvio_resid = float(np.std(resid_in_sample, ddof=1))
    z = stats.norm.ppf(1 - ALPHA / 2)

    ultimo_t = d["t_anos"].iloc[-1]
    linha = {
        "metodo": "detrend_rf_com_pdsi", "tendencia_mgL_ano": reg_full.slope, "tendencia_pvalor": reg_full.pvalue,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2, "hiperparametros": str(params_full),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        tendencia_h = reg_full.intercept + reg_full.slope * (ultimo_t + h)
        ponto = tendencia_h + pontos_resid[passo]
        margem = z * desvio_resid * np.sqrt((passo + 1) / 12)
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = ponto - margem
        linha[f"ci90_high_{h}y"] = ponto + margem
        linha[f"ic90_width_{h}y"] = 2 * margem

    def fit_predict(treino_s, n_passos):
        d_tr = pd.DataFrame({"Data": treino_s.index, "TDS_mgL": treino_s.values})
        d_tr["t_anos"] = (d_tr["Data"] - d_tr["Data"].iloc[0]).dt.days / 365.25
        d_resid, reg = destendenciar(d_tr)
        f_resid = construir_features_pdsi(d_resid)
        f_resid["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(f_resid["Data"]), lag)
        m, _ = treinar_rf_pdsi(f_resid[FEATURES_PDSI], f_resid["TDS_mgL"])
        pontos_resid_ = prever_recursivo_arvore_pdsi(m, d_resid[["Data", "TDS_mgL", "t_anos"]], pdsi_estendido, lag, n_passos)
        datas_fut = pd.date_range(d_tr["Data"].iloc[-1], periods=n_passos + 1, freq="ME")[1:]
        t_fut = (datas_fut - d_tr["Data"].iloc[0]).days / 365.25
        tendencia_futura = reg.intercept + reg.slope * t_fut.values
        return tendencia_futura + np.array(pontos_resid_)

    return linha, fit_predict


# --------------------------------------------------------------------------
# 9. Hibrido SARIMA+Prophet, ambos com PDSI(lag)
# --------------------------------------------------------------------------

def rodar_hibrido_pdsi(d, pdsi_estendido, lag, ordem, ordem_sazonal, trend):
    s = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    exog = pd.Series(d["pdsi_lag"].values, index=s.index)

    def prever_sarima(treino_s, n_passos):
        exog_tr = exog.reindex(treino_s.index).values.reshape(-1, 1)
        m = SARIMAX(treino_s, exog=exog_tr, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                    enforce_stationarity=False, enforce_invertibility=False)
        r = m.fit(disp=False)
        datas_fut = pd.date_range(treino_s.index[-1], periods=n_passos + 1, freq="ME")[1:]
        exog_fut = pdsi_lag_em(pdsi_estendido, datas_fut, lag)
        prev = r.get_forecast(steps=n_passos, exog=exog_fut.reshape(-1, 1))
        ic = prev.conf_int(alpha=ALPHA)
        return prev.predicted_mean.values, ic.iloc[:, 0].values, ic.iloc[:, 1].values

    fit_predict_prophet = construir_fit_predict_prophet_pdsi(pdsi_estendido, lag)

    def prever_prophet(treino_s, n_passos):
        pontos = fit_predict_prophet(treino_s, n_passos)
        return pontos, pontos, pontos  # IC do Prophet nao exposto aqui de forma simples; envoltoria usa so o SARIMA

    def prever_hibrido(treino_s, n_passos):
        p_s, lo_s, hi_s = prever_sarima(treino_s, n_passos)
        p_p = fit_predict_prophet(treino_s, n_passos)
        ponto = (p_s + p_p) / 2
        baixo = np.minimum(lo_s, p_p)
        alto = np.maximum(hi_s, p_p)
        return ponto, baixo, alto

    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    pred_holdout, _, _ = prever_hibrido(treino, len(holdout))
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    max_passos = max(HORIZONTES_ANOS) * 12
    pontos, baixos, altos = prever_hibrido(s, max_passos)

    linha = montar_linha_base("hibrido_arima_prophet", pontos, baixos, altos)
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, r2
    linha["ordem_sarima"] = f"order={ordem} seasonal_order={ordem_sazonal} trend={trend}"

    return linha, (lambda treino_s, n_passos: prever_hibrido(treino_s, n_passos)[0])


# --------------------------------------------------------------------------
# 10. GAM: s(tempo) + s(mes) + PDSI(lag) linear
# --------------------------------------------------------------------------

def rodar_gam_pdsi(d, pdsi_estendido, lag, termo_sazonal):
    d = d.copy()
    d["mes"] = d["Data"].dt.month
    treino = d.iloc[:-HOLDOUT_MESES].reset_index(drop=True)
    holdout = d.iloc[-HOLDOUT_MESES:].reset_index(drop=True)

    def montar_X(df):
        return np.column_stack([df["t_anos"].values, df["mes"].values, df["pdsi_lag"].values])

    termos = s(0, n_splines=8) + termo_sazonal + s(2, n_splines=6)
    lams_tendencia = np.logspace(np.log10(LAM_FLOOR_TENDENCIA), 3, 6)
    lams_sazonal = np.logspace(-3, 3, 6)
    lams_pdsi = np.logspace(-3, 3, 6)

    gam_treino = LinearGAM(termos)
    gam_treino.gridsearch(montar_X(treino), treino["TDS_mgL"].values, lam=[lams_tendencia, lams_sazonal, lams_pdsi], progress=False)
    pred_holdout = gam_treino.predict(montar_X(holdout))
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    gam_full = LinearGAM(termos)
    gam_full.gridsearch(montar_X(d), d["TDS_mgL"].values, lam=[lams_tendencia, lams_sazonal, lams_pdsi], progress=False)

    max_passos = max(HORIZONTES_ANOS) * 12
    datas_futuras = pd.date_range(d["Data"].iloc[-1], periods=max_passos + 1, freq="ME")[1:]
    t0 = d["Data"].iloc[0]
    t_fut = (datas_futuras - t0).days / 365.25
    pdsi_fut = pdsi_lag_em(pdsi_estendido, datas_futuras, lag)
    X_fut = np.column_stack([t_fut.values, datas_futuras.month, pdsi_fut])
    pontos = gam_full.predict(X_fut)
    ic = gam_full.prediction_intervals(X_fut, width=0.90)

    linha = montar_linha_base("gam", pontos, ic[:, 0], ic[:, 1])
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, r2
    linha["hiperparametros"] = f"lam={list(gam_full.lam)}"

    def fit_predict(treino_s, n_passos):
        d_tr = pd.DataFrame({"Data": treino_s.index, "TDS_mgL": treino_s.values})
        data0 = d_tr["Data"].iloc[0]
        d_tr["t_anos"] = (d_tr["Data"] - data0).dt.days / 365.25
        d_tr["mes"] = d_tr["Data"].dt.month
        d_tr["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(d_tr["Data"]), lag)
        g = LinearGAM(termos)
        g.gridsearch(montar_X(d_tr), d_tr["TDS_mgL"].values, lam=[lams_tendencia, lams_sazonal, lams_pdsi], progress=False)
        datas_fut = pd.date_range(treino_s.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_f = (datas_fut - data0).days / 365.25
        pdsi_f = pdsi_lag_em(pdsi_estendido, datas_fut, lag)
        return g.predict(np.column_stack([t_f.values, datas_fut.month, pdsi_f]))

    return linha, fit_predict


# --------------------------------------------------------------------------
# 11. Regressao quantilica (Q50) ~ tempo + PDSI(lag)
# --------------------------------------------------------------------------

def rodar_quantilica_pdsi(d, pdsi_estendido, lag):
    treino, holdout = d.iloc[:-HOLDOUT_MESES], d.iloc[-HOLDOUT_MESES:]

    def ajustar(df):
        X = sm.add_constant(np.column_stack([df["t_anos"].values, df["pdsi_lag"].values]))
        return QuantReg(df["TDS_mgL"].values, X).fit(q=0.5)

    res_treino = ajustar(treino)
    X_holdout = sm.add_constant(np.column_stack([holdout["t_anos"].values, holdout["pdsi_lag"].values]), has_constant="add")
    pred_holdout = res_treino.predict(X_holdout)
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    res_full = ajustar(d)
    t_ultimo = d["t_anos"].iloc[-1]
    max_passos = max(HORIZONTES_ANOS) * 12
    datas_futuras = pd.date_range(d["Data"].iloc[-1], periods=max_passos + 1, freq="ME")[1:]
    t_fut = t_ultimo + np.arange(1, max_passos + 1) / 12
    pdsi_fut = pdsi_lag_em(pdsi_estendido, datas_futuras, lag)
    X_fut = sm.add_constant(np.column_stack([t_fut, pdsi_fut]), has_constant="add")
    pontos = res_full.predict(X_fut)

    rng = np.random.default_rng(SEED)
    n = len(d)
    n_boot = 300
    previsoes_boot = np.zeros((n_boot, max_passos))
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        try:
            X_b = sm.add_constant(np.column_stack([d["t_anos"].values[idx], d["pdsi_lag"].values[idx]]))
            r_b = QuantReg(d["TDS_mgL"].values[idx], X_b).fit(q=0.5)
            previsoes_boot[b] = r_b.params[0] + r_b.params[1] * t_fut + r_b.params[2] * pdsi_fut
        except Exception:
            previsoes_boot[b] = np.nan
    ic_low = np.nanpercentile(previsoes_boot, 100 * ALPHA / 2, axis=0)
    ic_high = np.nanpercentile(previsoes_boot, 100 * (1 - ALPHA / 2), axis=0)

    linha = montar_linha_base("regressao_quantilica_q50", pontos, ic_low, ic_high)
    linha["tendencia_mgL_ano"] = float(res_full.params[1])
    linha["tendencia_pvalor"] = float(res_full.pvalues[1])
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, float("nan")
    linha["hiperparametros"] = f"quantil=0.5, coef_pdsi={res_full.params[2]:.4f}, bootstrap_n={n_boot}"

    def fit_predict(treino_s, n_passos):
        d_tr = pd.DataFrame({"Data": treino_s.index, "TDS_mgL": treino_s.values})
        data0 = d_tr["Data"].iloc[0]
        d_tr["t_anos"] = (d_tr["Data"] - data0).dt.days / 365.25
        d_tr["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(d_tr["Data"]), lag)
        r = ajustar(d_tr)
        datas_fut = pd.date_range(treino_s.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_f = (datas_fut - data0).days / 365.25
        pdsi_f = pdsi_lag_em(pdsi_estendido, datas_fut, lag)
        X_f = sm.add_constant(np.column_stack([t_f.values, pdsi_f]), has_constant="add")
        return r.predict(X_f)

    return linha, fit_predict


# --------------------------------------------------------------------------
# 12. Espaco de estados / DLM com PDSI(lag) como exog
# --------------------------------------------------------------------------

def rodar_espaco_estados_pdsi(d, pdsi_estendido, lag):
    s = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME")).asfreq("ME")
    exog = pd.Series(d["pdsi_lag"].values, index=s.index)
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    exog_treino, exog_holdout = exog.iloc[:-HOLDOUT_MESES], exog.iloc[-HOLDOUT_MESES:]

    def ajustar(serie, ex, espec):
        m = UnobservedComponents(serie, level=espec, seasonal=12, stochastic_seasonal=True, exog=ex.values.reshape(-1, 1))
        return m.fit(disp=False)

    candidatos = {}
    for espec in ["local level", "local linear trend"]:
        try:
            candidatos[espec] = ajustar(s, exog, espec)
        except Exception:
            continue
    melhor = min(candidatos, key=lambda k: candidatos[k].aic)
    res_full = candidatos[melhor]
    coef_pdsi = float(res_full.params[res_full.param_names.index("beta.x1")]) if "beta.x1" in res_full.param_names else float("nan")

    res_treino = ajustar(treino, exog_treino, melhor)
    fc_holdout = res_treino.get_forecast(steps=HOLDOUT_MESES, exog=exog_holdout.values.reshape(-1, 1))
    pred_holdout = fc_holdout.predicted_mean.values
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    max_passos = max(HORIZONTES_ANOS) * 12
    datas_futuras = pd.date_range(s.index[-1], periods=max_passos + 1, freq="ME")[1:]
    exog_futuro = pdsi_lag_em(pdsi_estendido, datas_futuras, lag)
    fc_full = res_full.get_forecast(steps=max_passos, exog=exog_futuro.reshape(-1, 1))
    ic = fc_full.conf_int(alpha=ALPHA)

    linha = montar_linha_base("espaco_estados_dlm", fc_full.predicted_mean.values, ic.iloc[:, 0].values, ic.iloc[:, 1].values)
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, r2
    linha["tendencia_pvalor"] = float("nan")
    linha["ordem_sarima"] = melhor
    linha["hiperparametros"] = f"level={melhor}, seasonal=12, coef_pdsi={coef_pdsi:.4f}"

    def fit_predict(treino_s, n_passos):
        exog_tr = exog.reindex(treino_s.index).values.reshape(-1, 1)
        r = UnobservedComponents(treino_s, level=melhor, seasonal=12, stochastic_seasonal=True, exog=exog_tr).fit(disp=False)
        datas_fut = pd.date_range(treino_s.index[-1], periods=n_passos + 1, freq="ME")[1:]
        exog_fut = pdsi_lag_em(pdsi_estendido, datas_fut, lag)
        return r.get_forecast(steps=n_passos, exog=exog_fut.reshape(-1, 1)).predicted_mean.values

    return linha, fit_predict, (s, treino, holdout)


# --------------------------------------------------------------------------
# Comparacao antes/depois + gravacao
# --------------------------------------------------------------------------

def montar_comparacao_antes_depois(linhas_novas: list) -> pd.DataFrame:
    existentes = pd.read_csv(RESULTADOS_CSV)
    linhas_cmp = []
    for linha in linhas_novas:
        nome_depois = linha["metodo"]
        nome_antes = nome_depois.replace("_com_pdsi", "")
        antes = existentes[existentes["metodo"] == nome_antes]
        if antes.empty:
            continue
        antes = antes.iloc[0]
        cmp = {"metodo": nome_antes}
        for col in ["rmse_holdout", "mae_holdout", "r2_holdout", "tendencia_mgL_ano"] + [f"forecast_{h}y" for h in HORIZONTES_ANOS]:
            v_antes, v_depois = antes.get(col, np.nan), linha.get(col, np.nan)
            cmp[f"{col}_antes"] = v_antes
            cmp[f"{col}_depois"] = v_depois
            if pd.notna(v_antes) and v_antes != 0 and pd.notna(v_depois):
                cmp[f"{col}_variacao_pct"] = 100 * (v_depois - v_antes) / abs(v_antes)
            else:
                cmp[f"{col}_variacao_pct"] = np.nan
        linhas_cmp.append(cmp)
    return pd.DataFrame(linhas_cmp)


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_29_bateria_pdsi_covariavel"
        linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
        linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    novas = pd.DataFrame(linhas)
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[~existentes["metodo"].isin(novas["metodo"])]
        for col in novas.columns:
            if col not in existentes.columns:
                existentes[col] = np.nan
        for col in existentes.columns:
            if col not in novas.columns:
                novas[col] = np.nan
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas
    consolidado.to_csv(RESULTADOS_CSV, index=False)
    consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)


def gerar_figura(comparacao: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 5))
    y_pos = np.arange(len(comparacao))
    ax.barh(y_pos - 0.2, comparacao["rmse_holdout_antes"], height=0.4, color="tab:gray", label="RMSE antes (sem PDSI)")
    ax.barh(y_pos + 0.2, comparacao["rmse_holdout_depois"], height=0.4, color="tab:blue", label="RMSE depois (com PDSI)")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(comparacao["metodo"], fontsize=8)
    ax.set_xlabel("RMSE no holdout (mg/L)")
    ax.set_title("Bateria original vs. com PDSI como covariável — RMSE de holdout")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def main():
    print("=== Bateria original re-treinada com PDSI como covariável (D-56) ===")
    d, lag, pdsi_estendido, ar1 = carregar_tudo()
    print(f"Série TDS: {len(d)} meses | PDSI lag={lag} meses (D-37) | AR(1) normal: mu={ar1['mu']:.2f}, phi={ar1['phi']:.3f}")
    print()

    linhas = []
    fit_predicts = {}
    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]

    print("--- Reaproveitando ordem SARIMA de script_02 ---")
    aic, ordem, ordem_sazonal, trend, _ = buscar_melhor_sarima(treino_serie)
    print(f"  order={ordem} seasonal_order={ordem_sazonal} trend={trend}")
    print()

    print("--- 1. SARIMAX(TDS, exog=PDSI_lag) ---")
    linha, fp, _ = rodar_sarimax_pdsi(d, pdsi_estendido, lag, ordem, ordem_sazonal, trend)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 2. Random Forest + PDSI ---")
    linha, fp = rodar_arvore_pdsi("random_forest", treinar_rf_pdsi, d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 3. XGBoost + PDSI ---")
    usa_gpu = checar_gpu_xgboost()
    linha, fp = rodar_arvore_pdsi("xgboost", lambda X, y: treinar_xgb_pdsi(X, y, usa_gpu), d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 4. LightGBM + PDSI ---")
    linha, fp = rodar_arvore_pdsi("lightgbm", treinar_lgbm_pdsi, d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 5. Prophet + PDSI (regressor externo) ---")
    m_full, treino_p, holdout_p, rmse_p, mae_p, r2_p = rodar_prophet_pdsi(d)
    max_passos = max(HORIZONTES_ANOS) * 12
    futuro = pd.DataFrame({
        "ds": pd.date_range(d["Data"].iloc[-1], periods=max_passos + 1, freq="ME")[1:],
    })
    futuro["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(futuro["ds"]), lag)
    prev_full = m_full.predict(futuro)
    linha = montar_linha_base("prophet", prev_full["yhat"].values, prev_full["yhat_lower"].values, prev_full["yhat_upper"].values)
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse_p, mae_p, r2_p
    linhas.append(linha); fit_predicts[linha["metodo"]] = construir_fit_predict_prophet_pdsi(pdsi_estendido, lag)

    print("--- 6. Regressão bayesiana + PDSI (PyMC/NUTS) ---")
    linha, fp = rodar_bayes_pdsi(d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 7. SVR + PDSI ---")
    linha, fp = rodar_svr_pdsi(d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 8. Detrend + RF, com PDSI no resíduo ---")
    linha, fp = rodar_detrend_rf_pdsi(d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 9. Híbrido SARIMA+Prophet, ambos com PDSI ---")
    linha, fp = rodar_hibrido_pdsi(d, pdsi_estendido, lag, ordem, ordem_sazonal, trend)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 10. GAM: s(tempo) + s(mês) + PDSI linear ---")
    termo_sazonal, _ = construir_termo_sazonal()
    linha, fp = rodar_gam_pdsi(d, pdsi_estendido, lag, termo_sazonal)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 11. Regressão quantílica (Q50) + PDSI ---")
    linha, fp = rodar_quantilica_pdsi(d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 12. Espaço de estados / DLM + PDSI (exog) ---")
    linha, fp, _ = rodar_espaco_estados_pdsi(d, pdsi_estendido, lag)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print()
    print("--- Validação honesta (CV expansiva + backtest) de cada método ---")
    for linha in linhas:
        try:
            linha.update(validar_metodo(fit_predicts[linha["metodo"]], serie, treino_serie, holdout_serie))
        except Exception as e:
            print(f"  Aviso: validação honesta falhou para {linha['metodo']} ({e}) -- holdout simples já gravado.")
        print(f"  {linha['metodo']}: RMSE={linha['rmse_holdout']:.2f}  R2={linha['r2_holdout']:.3f}  "
              f"tendência={linha['tendencia_mgL_ano']:.3f} mg/L/ano")

    gravar_resultados(linhas)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

    print()
    print("--- Comparação antes (sem PDSI) vs. depois (com PDSI) ---")
    comparacao = montar_comparacao_antes_depois(linhas)
    comparacao.to_csv(COMPARACAO_ANTES_DEPOIS_CSV, index=False)
    for _, row in comparacao.iterrows():
        print(f"  {row['metodo']}: RMSE {row['rmse_holdout_antes']:.2f} -> {row['rmse_holdout_depois']:.2f} "
              f"({row['rmse_holdout_variacao_pct']:+.1f}%)  |  "
              f"tendência {row['tendencia_mgL_ano_antes']:.3f} -> {row['tendencia_mgL_ano_depois']:.3f} mg/L/ano")
    print(f"\nComparação gravada em {COMPARACAO_ANTES_DEPOIS_CSV}")

    gerar_figura(comparacao)

    with iniciar_run(
        "bateria_pdsi_covariavel", "script_29_bateria_pdsi_covariavel",
        params={"lag_pdsi_meses": lag, "n_metodos": len(linhas)}, seed=SEED,
        janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
    ):
        for linha in linhas:
            logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH, COMPARACAO_ANTES_DEPOIS_CSV])


if __name__ == "__main__":
    main()
