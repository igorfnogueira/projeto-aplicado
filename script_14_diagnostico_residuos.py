"""
Diagnostico de residuos dos candidatos mais fortes da bateria (bloco final do
aprofundamento): Ljung-Box (autocorrelacao residual), Shapiro-Wilk
(normalidade) e ARCH (heterocedasticidade condicional) sobre os residuos
IN-SAMPLE de cada candidato, ajustado na serie completa.

Candidatos escolhidos por equilibrarem MASE baixo + captacao real de
tendencia de longo prazo sem saturar/oscilar (baselines ficam de fora --
nao captam tendencia por construcao):
  - OLS (script_01): referencia classica.
  - Regressao bayesiana (script_05): residuos IN-SAMPLE tratados como
    equivalentes aos da OLS -- e o mesmo modelo linear-gaussiano, a media da
    posterior converge para a estimativa de maxima verossimilhanca (OLS) com
    priors fracos, entao o valor ajustado (e o residuo) e praticamente
    identico; reamostrar NUTS (~230s) so para obter residuos quase iguais
    nao se justifica computacionalmente. Decisao de escopo registrada aqui.
  - Detrend+RF (script_10): melhor MASE entre os metodos que captam
    tendencia sem saturar.
  - SARIMA (script_02): representante da familia estocastica/diferenciada.
  - Hibrido SARIMA+Prophet (script_12): representante do ensemble.

Saida: diagnostico_residuos_resultados.csv/json (mesmo padrao de
diagnostico_serie_resultados.csv do script_07) + figura em painel (residuo x
tempo, histograma, QQ-plot) por candidato. Rastreado em runs MLflow.
"""

import json
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch

from script_00_preprocessamento import construir_datasets
from script_02_arima_sarima import carregar_serie_tds as carregar_serie_02, buscar_melhor_sarima
from script_03_random_forest_gridsearch import carregar_serie_tds as carregar_serie_03, construir_features, FEATURES
from script_10_detrend_arvore import destendenciar
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

RESULTADOS_CSV = "diagnostico_residuos_resultados.csv"
RESULTADOS_JSON = "diagnostico_residuos_resultados.json"
FIGURA_PATH = "Artigo/images/diagnostico-residuos-finalistas.png"
SEED = 42
LAG_LJUNG_BOX = 12

warnings.filterwarnings("ignore")


def residuos_ols():
    d = carregar_serie_03()
    reg = stats.linregress(d["t_anos"].values, d["TDS_mgL"].values)
    resid = d["TDS_mgL"].values - (reg.intercept + reg.slope * d["t_anos"].values)
    return "ols", d["Data"].values, resid


def residuos_detrend_rf():
    d = carregar_serie_03()
    d_resid, reg = destendenciar(d)
    f_resid = construir_features(d_resid)
    modelo = RandomForestRegressor(random_state=SEED, n_estimators=300, min_samples_leaf=1, max_depth=10)
    modelo.fit(f_resid[FEATURES], f_resid["TDS_mgL"])
    resid_arvore = f_resid["TDS_mgL"].values - modelo.predict(f_resid[FEATURES])
    return "detrend_rf", f_resid["Data"].values, resid_arvore


def residuos_sarima():
    s = carregar_serie_02()
    aic, ordem, ordem_sazonal, trend, _ = buscar_melhor_sarima(s)
    modelo = SARIMAX(s, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                      enforce_stationarity=False, enforce_invertibility=False)
    res = modelo.fit(disp=False)
    resid = res.resid.dropna()
    return "sarima", resid.index.values, resid.values


def residuos_hibrido():
    from prophet import Prophet
    s = carregar_serie_02()
    aic, ordem, ordem_sazonal, trend, _ = buscar_melhor_sarima(s)
    modelo = SARIMAX(s, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                      enforce_stationarity=False, enforce_invertibility=False)
    res = modelo.fit(disp=False)
    fitted_sarima = res.fittedvalues

    df = pd.DataFrame({"ds": s.index, "y": s.values})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(df)
    fitted_prophet = pd.Series(m.predict(df)["yhat"].values, index=s.index)

    media = (fitted_sarima + fitted_prophet) / 2
    resid = (s - media).dropna()
    return "hibrido_arima_prophet", resid.index.values, resid.values


def rodar_testes(nome: str, datas, resid: np.ndarray) -> dict:
    resid = np.asarray(resid, dtype=float)
    lb = acorr_ljungbox(resid, lags=[LAG_LJUNG_BOX], return_df=True)
    ljung_stat, ljung_p = float(lb["lb_stat"].iloc[0]), float(lb["lb_pvalue"].iloc[0])

    sw_stat, sw_p = stats.shapiro(resid)

    arch_stat, arch_p, _, _ = het_arch(resid, nlags=LAG_LJUNG_BOX)

    return {
        "metodo": nome, "n_residuos": len(resid),
        "ljung_box_stat": ljung_stat, "ljung_box_pvalor": ljung_p,
        "ljung_box_ok": ljung_p > 0.05,  # H0 = sem autocorrelacao; nao rejeitar e bom sinal
        "shapiro_stat": float(sw_stat), "shapiro_pvalor": float(sw_p),
        "shapiro_ok": float(sw_p) > 0.05,  # H0 = normalidade; nao rejeitar e bom sinal
        "arch_stat": float(arch_stat), "arch_pvalor": float(arch_p),
        "arch_ok": float(arch_p) > 0.05,  # H0 = sem heterocedasticidade condicional; nao rejeitar e bom sinal
    }


def gerar_figura(candidatos: list):
    fig, axes = plt.subplots(len(candidatos), 3, figsize=(13, 3.2 * len(candidatos)))
    for i, (nome, datas, resid) in enumerate(candidatos):
        ax = axes[i, 0]
        ax.plot(datas, resid, color="tab:blue", linewidth=0.8)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_title(f"{nome} — resíduo x tempo", fontsize=9)
        ax.tick_params(labelsize=7)

        ax = axes[i, 1]
        ax.hist(resid, bins=20, color="tab:green", alpha=0.7)
        ax.set_title(f"{nome} — histograma", fontsize=9)
        ax.tick_params(labelsize=7)

        ax = axes[i, 2]
        stats.probplot(resid, plot=ax)
        ax.set_title(f"{nome} — QQ-plot", fontsize=9)
        ax.tick_params(labelsize=7)

    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=130)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_14_diagnostico_residuos"
        linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    with open(RESULTADOS_JSON, "w", encoding="utf-8") as f:
        json.dump(linhas, f, indent=2, ensure_ascii=False, default=lambda o: bool(o) if isinstance(o, np.bool_) else o)
    pd.DataFrame(linhas).to_csv(RESULTADOS_CSV, index=False)


def main():
    print("Calculando residuos in-sample dos 5 candidatos...")
    candidatos = [
        residuos_ols(),
        residuos_detrend_rf(),
        residuos_sarima(),
        residuos_hibrido(),
    ]
    print("(regressao bayesiana: residuos tratados como equivalentes aos da OLS -- ver docstring)")
    nome_ols, datas_ols, resid_ols = candidatos[0]
    candidatos.insert(1, ("regressao_bayesiana", datas_ols, resid_ols))
    print()

    linhas = []
    with iniciar_run("diagnostico_residuos", "script_14_diagnostico_residuos", params={"lag_ljung_box": LAG_LJUNG_BOX}):
        for nome, datas, resid in candidatos:
            linha = rodar_testes(nome, datas, resid)
            linhas.append(linha)
            print(f"--- {nome} (n={linha['n_residuos']}) ---")
            print(f"  Ljung-Box (lag={LAG_LJUNG_BOX}): stat={linha['ljung_box_stat']:.2f} p={linha['ljung_box_pvalor']:.4f} "
                  f"({'sem autocorrelacao detectavel' if linha['ljung_box_ok'] else 'AUTOCORRELACAO detectada'})")
            print(f"  Shapiro-Wilk: stat={linha['shapiro_stat']:.4f} p={linha['shapiro_pvalor']:.4f} "
                  f"({'normalidade nao rejeitada' if linha['shapiro_ok'] else 'NORMALIDADE rejeitada'})")
            print(f"  ARCH: stat={linha['arch_stat']:.2f} p={linha['arch_pvalor']:.4f} "
                  f"({'sem heterocedasticidade condicional detectavel' if linha['arch_ok'] else 'HETEROCEDASTICIDADE detectada'})")
            print()

        gravar_resultados(linhas)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
        gerar_figura(candidatos)

        metricas = {}
        for linha in linhas:
            for k, v in linha.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    metricas[f"{linha['metodo']}_{k}"] = v
        logar_metricas(metricas)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
