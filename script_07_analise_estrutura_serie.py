"""
Analise de estrutura da serie de TDS -- bloco 1 do pedido de aprofundamento da
bateria (antes de qualquer modelo novo): sazonalidade, estacionariedade e
quebra estrutural. Nao assume sazonalidade anual nem estacionariedade -- os
testes decidem, e sao reportados mesmo quando contraditorios entre si (ADF vs
KPSS testam hipoteses opostas por desenho).

Univariado em TDS (mesma nota de desenho dos scripts 01/02/06): independe do
tratamento de ND do BOD.

MSTL (sazonalidade multipla) nao e rodado separadamente de STL: MSTL existe
para decompor MULTIPLAS periodicidades sazonais simultaneas (ex. diaria+
semanal); nossa serie e mensal com um unico periodo candidato (12), caso em
que MSTL se reduz matematicamente ao STL simples -- rodar os dois seria
redundante, nao um metodo a mais.

Saida: diagnostico_serie_resultados.csv/json (arquivo proprio, mesmo padrao
de correlacao_resultados.csv -- e diagnostico, nao previsao, nao vai para
resultados_comparacao.csv) + figura
Artigo/images/diagnostico-sazonalidade-quebras.png. Rastreado numa run MLflow
(utils/experiment_tracking.py).
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
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import breaks_cusumolsresid
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller, kpss

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

RESULTADOS_CSV = "diagnostico_serie_resultados.csv"
RESULTADOS_JSON = "diagnostico_serie_resultados.json"
FIGURA_PATH = "Artigo/images/diagnostico-sazonalidade-quebras.png"
PERIODO_SAZONAL = 12
BREAKPOINT_APROX = pd.Timestamp("2012-01-01")  # troca aproximada EFF-001 -> EFF-001A
JANELAS_SECA_CA = [("2012-01-01", "2016-12-31"), ("2020-01-01", "2022-12-31")]

warnings.filterwarnings("ignore")


def carregar_serie_tds() -> pd.Series:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    return pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))


# --------------------------------------------------------------------------
# STL + forca de sazonalidade/tendencia (Wang et al., 2006)
# --------------------------------------------------------------------------

def decompor_stl(s: pd.Series):
    stl = STL(s, period=PERIODO_SAZONAL, robust=True).fit()
    var_resid = np.var(stl.resid, ddof=1)
    var_sazonal_resid = np.var(stl.seasonal + stl.resid, ddof=1)
    var_tendencia_resid = np.var(stl.trend + stl.resid, ddof=1)
    f_sazonal = max(0.0, 1 - var_resid / var_sazonal_resid)
    f_tendencia = max(0.0, 1 - var_resid / var_tendencia_resid)
    return stl, float(f_sazonal), float(f_tendencia)


# --------------------------------------------------------------------------
# Estacionariedade: ADF (H0=raiz unitaria/nao-estacionaria) + KPSS (H0=estacionaria)
# --------------------------------------------------------------------------

def testar_estacionariedade(serie: np.ndarray) -> dict:
    adf_stat, adf_p, *_ = adfuller(serie, autolag="AIC")
    kpss_stat, kpss_p, *_ = kpss(serie, regression="c", nlags="auto")
    return {"adf_stat": float(adf_stat), "adf_pvalor": float(adf_p),
            "kpss_stat": float(kpss_stat), "kpss_pvalor": float(kpss_p)}


# --------------------------------------------------------------------------
# Quebra estrutural: Chow (breakpoint fixo ~2012) + Pettitt (sem breakpoint
# pre-definido) + CUSUM dos residuos de uma tendencia linear simples
# --------------------------------------------------------------------------

def chow_test(t: np.ndarray, y: np.ndarray, idx_quebra: int):
    def rss(t_, y_):
        reg = stats.linregress(t_, y_)
        pred = reg.intercept + reg.slope * t_
        return float(np.sum((y_ - pred) ** 2))

    rss_pool = rss(t, y)
    rss1 = rss(t[:idx_quebra], y[:idx_quebra])
    rss2 = rss(t[idx_quebra:], y[idx_quebra:])
    k = 2
    n1, n2 = idx_quebra, len(t) - idx_quebra
    num = (rss_pool - (rss1 + rss2)) / k
    den = (rss1 + rss2) / (n1 + n2 - 2 * k)
    f_stat = num / den
    p_valor = float(1 - stats.f.cdf(f_stat, k, n1 + n2 - 2 * k))
    return float(f_stat), p_valor


def pettitt_test(x: np.ndarray):
    """Teste de Pettitt (1979), nao-parametrico, sem breakpoint pre-definido.
    pymannkendall nao implementa este teste -- implementado diretamente aqui
    (formula padrao da literatura, vetorizada)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    sinais = np.sign(x[:, None] - x[None, :])
    U = np.array([sinais[:t, t:].sum() for t in range(1, n)])
    K = float(np.max(np.abs(U)))
    idx_t = int(np.argmax(np.abs(U)) + 1)  # posicao (0-indexed) onde o novo regime comeca
    p_valor = float(2 * np.exp(-6 * K ** 2 / (n ** 3 + n ** 2)))
    return K, idx_t, p_valor


def testar_quebra_estrutural(d: pd.DataFrame) -> dict:
    t = d["t_anos"].values
    y = d["TDS_mgL"].values

    idx_quebra = int((d["Data"] < BREAKPOINT_APROX).sum())
    idx_quebra = min(max(idx_quebra, 5), len(d) - 5)  # garante >=5 pontos de cada lado
    chow_f, chow_p = chow_test(t, y, idx_quebra)

    _, idx_pettitt, p_pettitt = pettitt_test(y)
    data_pettitt = d["Data"].iloc[idx_pettitt] if idx_pettitt < len(d) else None

    resid = y - (stats.linregress(t, y).intercept + stats.linregress(t, y).slope * t)
    cusum_stat, cusum_p, _ = breaks_cusumolsresid(resid, ddof=2)

    dentro_janela_seca = any(
        pd.Timestamp(ini) <= data_pettitt <= pd.Timestamp(fim)
        for ini, fim in JANELAS_SECA_CA
    ) if data_pettitt is not None else False

    return {
        "chow_breakpoint_data": str(d["Data"].iloc[idx_quebra].date()),
        "chow_f_stat": chow_f, "chow_pvalor": chow_p,
        "pettitt_indice_mudanca": idx_pettitt,
        "pettitt_data_mudanca": str(data_pettitt.date()) if data_pettitt is not None else None,
        "pettitt_pvalor": p_pettitt,
        "pettitt_dentro_janela_seca_ca": bool(dentro_janela_seca),
        "cusum_stat": float(cusum_stat), "cusum_pvalor": float(cusum_p),
    }


def gerar_figura(s: pd.Series, stl, d: pd.DataFrame):
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))

    ax = axes[0, 0]
    ax.plot(s.index, s.values, color="black", linewidth=1, label="TDS observado")
    ax.plot(s.index, stl.trend, color="tab:blue", linewidth=1.5, label="Tendencia STL")
    ax.axvline(BREAKPOINT_APROX, color="tab:red", linestyle=":", alpha=0.7, label="~2012 (EFF-001->EFF-001A)")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Serie observada e tendencia STL")
    ax.legend(fontsize=7)

    ax = axes[0, 1]
    ax.plot(s.index, stl.seasonal, color="tab:green", linewidth=1)
    ax.set_title("Componente sazonal (STL, periodo=12)")
    ax.set_ylabel("mg/L")

    ax = axes[1, 0]
    plot_acf(s.values, ax=ax, lags=36)
    ax.set_title("ACF (nivel)")

    ax = axes[1, 1]
    plot_pacf(s.values, ax=ax, lags=36, method="ywm")
    ax.set_title("PACF (nivel)")

    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linha: dict):
    linha = dict(linha)
    linha["script"] = "script_07_analise_estrutura_serie"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    with open(RESULTADOS_JSON, "w", encoding="utf-8") as f:
        json.dump(linha, f, indent=2, ensure_ascii=False)
    pd.DataFrame([linha]).to_csv(RESULTADOS_CSV, index=False)


def main():
    s = carregar_serie_tds()
    d = pd.DataFrame({"Data": s.index, "TDS_mgL": s.values})
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25

    print(f"Serie TDS: {len(s)} meses ({s.index[0].date()} a {s.index[-1].date()})")
    print()

    with iniciar_run("diagnostico_estrutura", "script_07_analise_estrutura_serie",
                      params={"periodo_sazonal": PERIODO_SAZONAL}):
        stl, f_sazonal, f_tendencia = decompor_stl(s)
        print(f"Forca de sazonalidade (Fs, Wang et al.): {f_sazonal:.3f}")
        print(f"Forca de tendencia (Ft): {f_tendencia:.3f}")
        print(f"  -> {'sazonalidade forte' if f_sazonal > 0.64 else 'sazonalidade fraca/moderada'} "
              f"(limiar de referencia Fs>0.64 usado na literatura de forecasting; nao 'prova' "
              f"causal, e uma heuristica para decidir se termos sazonais valem a pena)")
        print()

        estac_nivel = testar_estacionariedade(s.values)
        estac_diff = testar_estacionariedade(np.diff(s.values))
        print(f"ADF nivel: stat={estac_nivel['adf_stat']:.3f} p={estac_nivel['adf_pvalor']:.4f} "
              f"(H0=nao-estacionaria; {'rejeita H0' if estac_nivel['adf_pvalor'] < 0.05 else 'nao rejeita H0'})")
        print(f"KPSS nivel: stat={estac_nivel['kpss_stat']:.3f} p={estac_nivel['kpss_pvalor']:.4f} "
              f"(H0=estacionaria; {'rejeita H0' if estac_nivel['kpss_pvalor'] < 0.05 else 'nao rejeita H0'})")
        print(f"ADF 1a diferenca: stat={estac_diff['adf_stat']:.3f} p={estac_diff['adf_pvalor']:.4f}")
        print(f"KPSS 1a diferenca: stat={estac_diff['kpss_stat']:.3f} p={estac_diff['kpss_pvalor']:.4f}")
        print()

        quebra = testar_quebra_estrutural(d)
        print(f"Chow test (breakpoint {quebra['chow_breakpoint_data']}): "
              f"F={quebra['chow_f_stat']:.3f} p={quebra['chow_pvalor']:.4f}")
        print(f"Pettitt test: mudanca detectada em {quebra['pettitt_data_mudanca']} "
              f"(p={quebra['pettitt_pvalor']:.4f}, dentro de janela de seca CA: {quebra['pettitt_dentro_janela_seca_ca']})")
        print(f"CUSUM (residuos de tendencia OLS): stat={quebra['cusum_stat']:.3f} p={quebra['cusum_pvalor']:.4f}")
        print()

        linha = {
            "n_meses": len(s),
            "forca_sazonalidade_Fs": f_sazonal,
            "forca_tendencia_Ft": f_tendencia,
            "adf_nivel_stat": estac_nivel["adf_stat"], "adf_nivel_pvalor": estac_nivel["adf_pvalor"],
            "kpss_nivel_stat": estac_nivel["kpss_stat"], "kpss_nivel_pvalor": estac_nivel["kpss_pvalor"],
            "adf_diff_stat": estac_diff["adf_stat"], "adf_diff_pvalor": estac_diff["adf_pvalor"],
            "kpss_diff_stat": estac_diff["kpss_stat"], "kpss_diff_pvalor": estac_diff["kpss_pvalor"],
            **quebra,
        }
        gravar_resultados(linha)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

        gerar_figura(s, stl, d)

        metricas_numericas = {k: v for k, v in linha.items()
                               if isinstance(v, (int, float)) and not isinstance(v, bool)}
        logar_metricas(metricas_numericas)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
