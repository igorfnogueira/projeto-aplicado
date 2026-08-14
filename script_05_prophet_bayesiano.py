"""
Prophet e regressao bayesiana para o TDS (plano_projeto_TDS.md secao 3.d) —
os dois metodos escolhidos por exporem explicitamente a incerteza crescente
com o horizonte, mais honestos para extrapolar ~15 anos de historico para
+20 anos (ao contrario dos metodos baseados em arvore dos scripts 03/04, que
saturam ou oscilam sem sinalizar a propria fragilidade).

GPU: nao aplicavel. Prophet usa Stan/CmdStan (sem backend CUDA); a regressao
bayesiana aqui usa PyMC/NUTS via CPU puro (sem g++ nesta maquina, PyTensor
cai para o fallback Python — mais lento, mas funcional para um dataset deste
tamanho). A variante JAX/CUDA mencionada no plano nao foi configurada nesta
sessao (exigiria jax[cuda12] + driver compativel, fora do escopo atual).

Mesma nota de desenho dos scripts 01-04: univariado em TDS, independe do
tratamento de ND do BOD.
"""

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/prophet-bayes-tds.png"
SEED = 42


def carregar_serie_tds() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    return d


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


# --------------------------------------------------------------------------
# 3.d.1 Prophet
# --------------------------------------------------------------------------

def rodar_prophet(d: pd.DataFrame) -> dict:
    from prophet import Prophet

    treino, holdout = d.iloc[:-HOLDOUT_MESES], d.iloc[-HOLDOUT_MESES:]
    df_treino = treino[["Data", "TDS_mgL"]].rename(columns={"Data": "ds", "TDS_mgL": "y"})

    modelo_treino = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True,
                             weekly_seasonality=False, daily_seasonality=False)
    modelo_treino.fit(df_treino)
    futuro_holdout = modelo_treino.make_future_dataframe(periods=HOLDOUT_MESES, freq="MS")
    prev_holdout = modelo_treino.predict(futuro_holdout).tail(HOLDOUT_MESES)
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, prev_holdout["yhat"].values)

    df_full = d[["Data", "TDS_mgL"]].rename(columns={"Data": "ds", "TDS_mgL": "y"})
    modelo_full = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True,
                           weekly_seasonality=False, daily_seasonality=False)
    modelo_full.fit(df_full)

    max_passos = max(HORIZONTES_ANOS) * 12
    futuro = modelo_full.make_future_dataframe(periods=max_passos, freq="MS")
    prev_full = modelo_full.predict(futuro)

    # tendencia: regressao OLS sobre a componente "trend" do proprio Prophet, no periodo observado
    hist = prev_full.iloc[: len(d)]
    reg = stats.linregress(d["t_anos"].values, hist["trend"].values)

    linha = {
        "metodo": "prophet",
        "tendencia_mgL_ano": reg.slope,
        "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"),
        "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
    }
    prev_full_indexada = prev_full.set_index("ds")
    for h in HORIZONTES_ANOS:
        data_alvo = d["Data"].iloc[-1] + pd.DateOffset(months=h * 12)
        linha_h = prev_full_indexada.iloc[prev_full_indexada.index.get_indexer([data_alvo], method="nearest")[0]]
        linha[f"forecast_{h}y"] = float(linha_h["yhat"])
        linha[f"ci90_low_{h}y"] = float(linha_h["yhat_lower"])
        linha[f"ci90_high_{h}y"] = float(linha_h["yhat_upper"])

    return linha, prev_full


# --------------------------------------------------------------------------
# 3.d.2 Regressao bayesiana (PyMC/NUTS)
# --------------------------------------------------------------------------

def ajustar_bayes(t: np.ndarray, y: np.ndarray, draws=800, tune=800):
    import pymc as pm

    t_centro = t.mean()
    tc = t - t_centro
    with pm.Model():
        a = pm.Normal("a", mu=float(y.mean()), sigma=float(y.std() * 3 + 50))
        b = pm.Normal("b", mu=0, sigma=50)
        sigma = pm.HalfNormal("sigma", sigma=float(y.std() * 2 + 10))
        mu = a + b * tc
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)
        idata = pm.sample(draws, tune=tune, chains=2, cores=1, progressbar=False,
                           random_seed=SEED, target_accept=0.9)
    return idata, t_centro


def rodar_bayesiano(d: pd.DataFrame) -> dict:
    treino, holdout = d.iloc[:-HOLDOUT_MESES], d.iloc[-HOLDOUT_MESES:]

    print("  Ajustando regressao bayesiana (treino, NUTS)...")
    idata_tr, t_centro_tr = ajustar_bayes(treino["t_anos"].values, treino["TDS_mgL"].values)
    a_tr = float(idata_tr.posterior["a"].mean())
    b_tr = float(idata_tr.posterior["b"].mean())
    pred_holdout = a_tr + b_tr * (holdout["t_anos"].values - t_centro_tr)
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    print("  Ajustando regressao bayesiana (serie completa, NUTS)...")
    idata_full, t_centro_full = ajustar_bayes(d["t_anos"].values, d["TDS_mgL"].values)
    a_s = idata_full.posterior["a"].values.flatten()
    b_s = idata_full.posterior["b"].values.flatten()
    sigma_s = idata_full.posterior["sigma"].values.flatten()

    b_mean = float(b_s.mean())
    prob_b_positivo = float((b_s > 0).mean())
    p_valor_bayes = 2 * min(prob_b_positivo, 1 - prob_b_positivo)
    slope_lo, slope_hi = np.percentile(b_s, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])

    linha = {
        "metodo": "regressao_bayesiana",
        "tendencia_mgL_ano": b_mean,
        "tendencia_pvalor": p_valor_bayes,
        "tendencia_ic90_baixo": float(slope_lo),
        "tendencia_ic90_alto": float(slope_hi),
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
        "prob_tendencia_positiva": prob_b_positivo,
    }

    rng = np.random.default_rng(SEED)
    for h in HORIZONTES_ANOS:
        t_h = d["t_anos"].iloc[-1] + h
        mu_draws = a_s + b_s * (t_h - t_centro_full)
        pred_draws = rng.normal(mu_draws, sigma_s)
        ponto = float(np.mean(pred_draws))
        lo, hi = np.percentile(pred_draws, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = float(lo)
        linha[f"ci90_high_{h}y"] = float(hi)

    return linha, (a_s, b_s, sigma_s, t_centro_full)


# --------------------------------------------------------------------------
# Adaptadores fit_predict (validacao_utils.validar_metodo: CV expansiva + backtest)
# --------------------------------------------------------------------------

def construir_fit_predict_prophet():
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        from prophet import Prophet
        df_treino = pd.DataFrame({"ds": treino.index, "y": treino.values})
        m = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True,
                    weekly_seasonality=False, daily_seasonality=False)
        m.fit(df_treino)
        futuro = m.make_future_dataframe(periods=n_passos, freq="MS")
        return m.predict(futuro).tail(n_passos)["yhat"].values
    return fit_predict


def construir_fit_predict_bayes_rapido():
    """Aproximacao rapida para CV/backtest: usa o estimador de minimos
    quadrados (a media da posterior de um modelo linear-gaussiano com priors
    fracos converge para a OLS) em vez de reamostrar NUTS a cada um dos ~25
    folds/origens -- a amostragem completa (800+800 iteracoes, ~225s por
    ajuste so na serie inteira) tornaria a validacao inviavel em tempo
    habil. A previsao final (+10/+15/+20 anos, reportada em
    resultados_comparacao.csv) continua usando NUTS completo com incerteza
    posterior real -- so a validacao de fold usa este atalho, documentado
    aqui explicitamente para nao ser confundido com o metodo final."""
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        data0 = treino.index[0]
        t = (treino.index - data0).days / 365.25
        reg = stats.linregress(t.values, treino.values)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_futuro = (datas_futuras - data0).days / 365.25
        return reg.intercept + reg.slope * t_futuro
    return fit_predict


def gerar_figura(d, linha_prophet, prev_full_prophet, linha_bayes):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")

    ultima_data = d["Data"].iloc[-1]
    prev_futuro = prev_full_prophet[prev_full_prophet["ds"] > ultima_data]
    ax.plot(prev_futuro["ds"], prev_futuro["yhat"], "--", color="tab:green", label="Prophet (previsao)")
    ax.fill_between(prev_futuro["ds"], prev_futuro["yhat_lower"], prev_futuro["yhat_upper"],
                     color="tab:green", alpha=0.12)

    anos_futuros = [0] + HORIZONTES_ANOS
    datas_futuras = [ultima_data + pd.DateOffset(months=int(a * 12)) for a in anos_futuros]
    pontos = [linha_bayes[f"forecast_{h}y"] if h > 0 else d["TDS_mgL"].iloc[-1] for h in anos_futuros]
    baixos = [linha_bayes[f"ci90_low_{h}y"] if h > 0 else d["TDS_mgL"].iloc[-1] for h in anos_futuros]
    altos = [linha_bayes[f"ci90_high_{h}y"] if h > 0 else d["TDS_mgL"].iloc[-1] for h in anos_futuros]
    ax.plot(datas_futuras, pontos, "--", color="tab:pink", label="Regressao bayesiana (previsao)")
    ax.fill_between(datas_futuras, baixos, altos, color="tab:pink", alpha=0.15)

    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Prophet e regressao bayesiana — previsao de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_05_prophet_bayesiano"
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
    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(d)} meses ({d['Data'].iloc[0].date()} a {d['Data'].iloc[-1].date()})")
    print(f"Treino: {len(d) - HOLDOUT_MESES} meses | Holdout: {HOLDOUT_MESES} meses")
    print()

    print("--- Prophet ---")
    linha_prophet, prev_full_prophet = rodar_prophet(d)
    linha_prophet.update(validar_metodo(construir_fit_predict_prophet(), serie, treino_serie, holdout_serie))
    print(f"  Tendencia: {linha_prophet['tendencia_mgL_ano']:.3f} mg/L/ano (p={linha_prophet['tendencia_pvalor']:.4f})")
    print(f"  Holdout: RMSE={linha_prophet['rmse_holdout']:.2f}  MAE={linha_prophet['mae_holdout']:.2f}  R2={linha_prophet['r2_holdout']:.3f}  "
          f"MASE={linha_prophet['mase_holdout']:.3f}  sMAPE={linha_prophet['smape_holdout']:.2f}%")
    print(f"  CV (5 folds expansivos): RMSE={linha_prophet['cv_rmse_media']:.2f}±{linha_prophet['cv_rmse_desvio']:.2f}  "
          f"MASE={linha_prophet['cv_mase_media']:.3f}±{linha_prophet['cv_mase_desvio']:.3f}")
    for h in HORIZONTES_ANOS:
        baixo, alto = linha_prophet[f"ci90_low_{h}y"], linha_prophet[f"ci90_high_{h}y"]
        if not (np.isnan(baixo) or np.isnan(alto)):
            linha_prophet[f"ic90_width_{h}y"] = alto - baixo
        print(f"  +{h}a: {linha_prophet[f'forecast_{h}y']:.1f} mg/L  IC90% [{baixo:.1f}, {alto:.1f}]")
    print()

    print("--- Regressao bayesiana (PyMC/NUTS) ---")
    linha_bayes, _ = rodar_bayesiano(d)
    linha_bayes.update(validar_metodo(construir_fit_predict_bayes_rapido(), serie, treino_serie, holdout_serie))
    print(f"  Tendencia: {linha_bayes['tendencia_mgL_ano']:.3f} mg/L/ano "
          f"(p~{linha_bayes['tendencia_pvalor']:.4f}, P(tendencia>0)={linha_bayes['prob_tendencia_positiva']:.4f}, "
          f"IC90% [{linha_bayes['tendencia_ic90_baixo']:.3f}, {linha_bayes['tendencia_ic90_alto']:.3f}])")
    print(f"  Holdout: RMSE={linha_bayes['rmse_holdout']:.2f}  MAE={linha_bayes['mae_holdout']:.2f}  R2={linha_bayes['r2_holdout']:.3f}  "
          f"MASE={linha_bayes['mase_holdout']:.3f}  sMAPE={linha_bayes['smape_holdout']:.2f}%")
    print(f"  CV (5 folds expansivos, aproximacao OLS): RMSE={linha_bayes['cv_rmse_media']:.2f}±{linha_bayes['cv_rmse_desvio']:.2f}  "
          f"MASE={linha_bayes['cv_mase_media']:.3f}±{linha_bayes['cv_mase_desvio']:.3f}")
    for h in HORIZONTES_ANOS:
        baixo, alto = linha_bayes[f"ci90_low_{h}y"], linha_bayes[f"ci90_high_{h}y"]
        if not (np.isnan(baixo) or np.isnan(alto)):
            linha_bayes[f"ic90_width_{h}y"] = alto - baixo
        print(f"  +{h}a: {linha_bayes[f'forecast_{h}y']:.1f} mg/L  IC90% [{baixo:.1f}, {alto:.1f}]")

    gravar_resultados([linha_prophet, linha_bayes])
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(d, linha_prophet, prev_full_prophet, linha_bayes)

    for linha in (linha_prophet, linha_bayes):
        with iniciar_run(
            linha["metodo"], "script_05_prophet_bayesiano", seed=SEED,
            janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
        ):
            logar_linha_resultado(linha)
            logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
