"""
SVR e Gaussian Process para o TDS (bloco 3 do aprofundamento -- metodos
adicionais alem da bateria original, escolhidos do material de apoio):

- SVR (Support Vector Regression, kernel RBF): mesmas features de tempo/
  sazonalidade/lags de script_03 (reaproveitadas via construir_features),
  hiperparametros (C, epsilon, gamma) por GridSearchCV+TimeSeriesSplit,
  previsao recursiva multi-passo (mesmo esquema de script_03/04). IC90 por
  BOOTSTRAP de residuos: a cada passo da previsao recursiva, soma-se um
  residuo do treino (com reposicao) ao ponto previsto, em N replicas
  independentes -- o IC90 empirico vem dos percentis 5/95% dessas replicas
  em cada horizonte (mais correto que assumir um desvio-padrao fixo, pois
  incorpora a propagacao de incerteza da recursao).

- Gaussian Process com kernel COMPOSTO: RBF (tendencia suave de longo prazo)
  + ExpSineSquared periodo=12 (sazonalidade, mesmo se fraca -- o proprio
  ajuste de hiperparametros decide o peso) + WhiteKernel (ruido). Ajustado
  diretamente sobre t_anos (nao sobre as features de arvore -- GP com kernel
  de tempo e a forma padrao de usar este metodo para series temporais). IC90
  analitico via desvio-padrao posterior do GP.

Univariado em TDS (mesma nota de desenho dos scripts 01-05/07/08): independe
do tratamento de ND do BOD.
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ExpSineSquared, ConstantKernel as C
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from script_03_random_forest_gridsearch import carregar_serie_tds, construir_features, FEATURES
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
PERIODO_SAZONAL = 12
N_BOOTSTRAP = 200
SEED = 42
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/svr-gp-tds.png"

warnings.filterwarnings("ignore")
rng = np.random.default_rng(SEED)


def construir_serie_indexada(d: pd.DataFrame) -> pd.Series:
    return pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


# --------------------------------------------------------------------------
# SVR
# --------------------------------------------------------------------------

def treinar_svr(X_train, y_train) -> SVR:
    grade = {"svr__C": [1, 10, 100], "svr__epsilon": [0.5, 1.0, 5.0], "svr__gamma": ["scale", "auto"]}
    pipe = make_pipeline(StandardScaler(), SVR(kernel="rbf"))
    tscv = TimeSeriesSplit(n_splits=5)
    busca = GridSearchCV(pipe, grade, cv=tscv, scoring="neg_root_mean_squared_error", n_jobs=-1)
    busca.fit(X_train, y_train)
    return busca.best_estimator_, busca.best_params_


def prever_recursivo_svr(modelo, d: pd.DataFrame, n_passos: int, residuos_boot: np.ndarray = None, n_boot: int = 0):
    """Previsao recursiva (mesmo esquema de script_03/04). Se residuos_boot e
    n_boot>0, retorna tambem N replicas bootstrap (residuo do treino somado a
    cada passo) para o IC90 empirico; caso contrario so o ponto central."""
    def caminho(injetar_residuo: bool):
        historico = d[["Data", "TDS_mgL"]].copy()
        t0 = d["t_anos"].iloc[-1]
        pontos = []
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
                "lag_1": lag_1, "lag_12": lag_12, "media_movel_3": media_movel_3,
            }])[FEATURES]
            ponto = float(modelo.predict(x)[0])
            if injetar_residuo:
                ponto = ponto + rng.choice(residuos_boot)
            pontos.append(ponto)
            historico = pd.concat([historico, pd.DataFrame([{"Data": data_alvo, "TDS_mgL": ponto}])], ignore_index=True)
        return pontos

    ponto_central = caminho(injetar_residuo=False)
    if n_boot == 0:
        return ponto_central, ponto_central, ponto_central

    replicas = np.array([caminho(injetar_residuo=True) for _ in range(n_boot)])
    baixos = np.percentile(replicas, 100 * ALPHA / 2, axis=0)
    altos = np.percentile(replicas, 100 * (1 - ALPHA / 2), axis=0)
    return ponto_central, baixos.tolist(), altos.tolist()


def construir_fit_predict_svr(params: dict):
    """Adaptador para validacao_utils.validar_metodo -- hiperparametros
    FIXOS (mesma decisao de escopo de script_03/04: nao repetir GridSearchCV
    a cada fold/origem de CV/backtest)."""
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        d_treino = pd.DataFrame({"Data": treino.index, "TDS_mgL": treino.values})
        d_treino["t_anos"] = (d_treino["Data"] - d_treino["Data"].iloc[0]).dt.days / 365.25
        f_treino = construir_features(d_treino)
        pipe = make_pipeline(StandardScaler(), SVR(kernel="rbf", **{k.replace("svr__", ""): v for k, v in params.items()}))
        pipe.fit(f_treino[FEATURES], f_treino["TDS_mgL"])
        pontos, _, _ = prever_recursivo_svr(pipe, d_treino, n_passos)
        return np.array(pontos)
    return fit_predict


def rodar_svr(d: pd.DataFrame, f: pd.DataFrame, treino: pd.DataFrame, holdout: pd.DataFrame):
    modelo, params = treinar_svr(treino[FEATURES], treino["TDS_mgL"])
    pred_holdout = modelo.predict(holdout[FEATURES])
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    modelo_full, params_full = treinar_svr(f[FEATURES], f["TDS_mgL"])
    residuos = f["TDS_mgL"].values - modelo_full.predict(f[FEATURES])

    max_passos = max(HORIZONTES_ANOS) * 12
    pontos, baixos, altos = prever_recursivo_svr(modelo_full, d, max_passos, residuos, N_BOOTSTRAP)

    passos_10a = 10 * 12
    reg = stats.linregress(np.arange(passos_10a), pontos[:passos_10a])

    linha = {
        "metodo": "svr", "tendencia_mgL_ano": reg.slope * 12, "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "hiperparametros": str(params),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = pontos[passo]
        linha[f"ci90_low_{h}y"] = baixos[passo]
        linha[f"ci90_high_{h}y"] = altos[passo]
        linha[f"ic90_width_{h}y"] = altos[passo] - baixos[passo]

    datas_futuras = [d["Data"].iloc[-1] + pd.DateOffset(months=p) for p in range(1, max_passos + 1)]
    return linha, params, (datas_futuras, pontos, baixos, altos)


# --------------------------------------------------------------------------
# Gaussian Process (kernel composto)
# --------------------------------------------------------------------------

def construir_kernel_composto():
    tendencia = C(500.0, (10, 5000)) * RBF(length_scale=8.0, length_scale_bounds=(2, 40))
    sazonal = C(50.0, (1, 500)) * ExpSineSquared(length_scale=1.0, periodicity=1.0, periodicity_bounds="fixed")
    ruido = WhiteKernel(noise_level=100.0, noise_level_bounds=(1, 1e4))
    return tendencia + sazonal + ruido


def ajustar_gp(t: np.ndarray, y: np.ndarray) -> GaussianProcessRegressor:
    gp = GaussianProcessRegressor(kernel=construir_kernel_composto(), normalize_y=True,
                                   n_restarts_optimizer=3, random_state=SEED)
    gp.fit(t.reshape(-1, 1), y)
    return gp


def rodar_gp(d: pd.DataFrame, treino: pd.DataFrame, holdout: pd.DataFrame):
    gp_treino = ajustar_gp(treino["t_anos"].values, treino["TDS_mgL"].values)
    pred_holdout, _ = gp_treino.predict(holdout["t_anos"].values.reshape(-1, 1), return_std=True)
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    gp_full = ajustar_gp(d["t_anos"].values, d["TDS_mgL"].values)
    z = stats.norm.ppf(1 - ALPHA / 2)
    t_full = d["t_anos"].values

    reg = stats.linregress(t_full, d["TDS_mgL"].values)  # tendencia global de referencia (linear, so para reportar)

    linha = {
        "metodo": "gaussian_process", "tendencia_mgL_ano": reg.slope, "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "hiperparametros": str(gp_full.kernel_),
    }
    ultimo_t = t_full[-1]
    for h in HORIZONTES_ANOS:
        t_h = np.array([[ultimo_t + h]])
        media, std = gp_full.predict(t_h, return_std=True)
        ponto, s = float(media[0]), float(std[0])
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = ponto - z * s
        linha[f"ci90_high_{h}y"] = ponto + z * s
        linha[f"ic90_width_{h}y"] = 2 * z * s
    return linha, gp_full


def construir_fit_predict_gp():
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        data0 = treino.index[0]
        t = (treino.index - data0).days / 365.25
        gp = ajustar_gp(t.values, treino.values)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_futuro = (datas_futuras - data0).days / 365.25
        media, _ = gp.predict(t_futuro.values.reshape(-1, 1), return_std=True)
        return media
    return fit_predict


# --------------------------------------------------------------------------

def gerar_figura(d, svr_dados, gp_full, treino_gp):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")

    datas_futuras, pontos, baixos, altos = svr_dados
    ax.plot(datas_futuras, pontos, "--", color="tab:cyan", label="SVR (previsao)")
    ax.fill_between(datas_futuras, baixos, altos, color="tab:cyan", alpha=0.15)

    max_passos = len(datas_futuras)
    t0 = d["t_anos"].iloc[-1]
    t_futuro = np.array([t0 + p / 12 for p in range(1, max_passos + 1)])
    media, std = gp_full.predict(t_futuro.reshape(-1, 1), return_std=True)
    z = stats.norm.ppf(1 - ALPHA / 2)
    ax.plot(datas_futuras, media, "--", color="tab:pink", label="Gaussian Process (previsao)")
    ax.fill_between(datas_futuras, media - z * std, media + z * std, color="tab:pink", alpha=0.15)

    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("SVR e Gaussian Process — previsao de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_09_svr_gp"
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
    f = construir_features(d)
    treino, holdout = f.iloc[:-HOLDOUT_MESES], f.iloc[-HOLDOUT_MESES:]
    serie = construir_serie_indexada(d)
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]

    print(f"Serie TDS: {len(d)} meses | Treino: {len(treino)} | Holdout: {len(holdout)}")
    print()

    print("--- SVR ---")
    linha_svr, params_svr, svr_dados = rodar_svr(d, f, treino, holdout)
    linha_svr.update(validar_metodo(construir_fit_predict_svr(params_svr), serie, treino_serie, holdout_serie))
    print(f"  Hiperparametros: {params_svr}")
    print(f"  Holdout: RMSE={linha_svr['rmse_holdout']:.2f}  MASE={linha_svr['mase_holdout']:.3f}  sMAPE={linha_svr['smape_holdout']:.2f}%")
    print(f"  CV: MASE={linha_svr['cv_mase_media']:.3f}±{linha_svr['cv_mase_desvio']:.3f}  Backtest+3a: MAE={linha_svr.get('backtest_mae_36m', float('nan')):.2f}")
    for h in HORIZONTES_ANOS:
        print(f"  +{h}a: {linha_svr[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha_svr[f'ci90_low_{h}y']:.1f}, {linha_svr[f'ci90_high_{h}y']:.1f}]")
    print()

    print("--- Gaussian Process (kernel composto) ---")
    linha_gp, gp_full = rodar_gp(d, treino, holdout)
    linha_gp.update(validar_metodo(construir_fit_predict_gp(), serie, treino_serie, holdout_serie))
    print(f"  Kernel ajustado: {linha_gp['hiperparametros']}")
    print(f"  Holdout: RMSE={linha_gp['rmse_holdout']:.2f}  MASE={linha_gp['mase_holdout']:.3f}  sMAPE={linha_gp['smape_holdout']:.2f}%")
    print(f"  CV: MASE={linha_gp['cv_mase_media']:.3f}±{linha_gp['cv_mase_desvio']:.3f}  Backtest+3a: MAE={linha_gp.get('backtest_mae_36m', float('nan')):.2f}")
    for h in HORIZONTES_ANOS:
        print(f"  +{h}a: {linha_gp[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha_gp[f'ci90_low_{h}y']:.1f}, {linha_gp[f'ci90_high_{h}y']:.1f}]")

    gravar_resultados([linha_svr, linha_gp])
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(d, svr_dados, gp_full, treino)

    for linha in (linha_svr, linha_gp):
        with iniciar_run(
            linha["metodo"], "script_09_svr_gp", seed=SEED,
            janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
        ):
            logar_linha_resultado(linha)
            logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
