"""
WRTDS / normalizacao por vazao (prompt_wrtds_balanco_cenarios.md, Tarefa 1):
separa a variacao de TDS causada por variacao de vazao daquela que resta
depois de descontar a vazao ("flow-normalized"), respondendo a pergunta que
D-37 tornou central: ha tendencia de TDS POR BAIXO dos ciclos de seca/vazao?

Metodo (Hirsch et al., 2010, WRTDS -- Weighted Regressions on Time, Discharge,
and Season): regressao ponderada localmente de log(concentracao) sobre tempo,
log(vazao) e sazonalidade, com pesos por proximidade nas 3 dimensoes (kernel
tricubico). A normalizacao por vazao integra a regressao ajustada sobre a
distribuicao HISTORICA de vazao em cada instante -- isolando o efeito do
tempo/regime do efeito puramente hidrologico.

IMPLEMENTACAO PROPRIA, NAO o pacote R EGRET (nao ha equivalente maduro em
Python -- avaliado e descartado, ver docstring de main()). E uma versao
simplificada do WRTDS real: janelas de meia-largura FIXAS (o EGRET expande
adaptativamente a janela quando poucos pontos tem peso não-nulo; aqui não).
Declarado explicitamente, nao rotulado como implementacao completa.

Adaptacao de contexto: WRTDS foi desenhado para rios (vazao = hidrologia).
Aqui "vazao" e vazao de EFLUENTE (dirigida por consumo/conservacao, nao por
precipitacao direta) -- a matematica se aplica, a interpretacao NAO e a
mesma, e isso e declarado na metodologia do artigo.

Risco de circularidade (obrigatorio verificar, nao so declarar): a vazao
padrao usada (vazao_mgd_TDS) foi derivada DO PROPRIO TDS (lb/day de TDS /
mg/L de TDS / 8,34). Usar essa vazao para "explicar" o TDS pode ser
tautologico. Teste: repete tudo com vazao_mgd_Chloride (serie
independente) e compara -- se divergir muito, a circularidade se confirma e
o achado com vazao_mgd_TDS nao se sustenta sozinho.
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

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

warnings.filterwarnings("ignore")

HORIZONTES_ANOS = [10, 15, 20]
HALF_WINDOW_ANOS = 7.0      # meia-largura temporal (default EGRET: windowY=7)
HALF_WINDOW_LOGQ = 2.0      # meia-largura em log(vazao) (default EGRET: windowQ=2)
HALF_WINDOW_SAZONAL = 0.5   # meia-largura sazonal, em fracao de ano (default EGRET: windowS=0.5)
RESULTADOS_CSV = "wrtds_resultados.csv"
RESULTADOS_JSON = "wrtds_resultados.json"
RESULTADOS_COMPARACAO_CSV = "resultados_comparacao.csv"
RESULTADOS_COMPARACAO_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/wrtds-flow-normalized.png"
FIGURA_CIRCULARIDADE = "Artigo/images/wrtds-circularidade.png"


def tricube(d: np.ndarray, h: float) -> np.ndarray:
    """Kernel tricubico padrao do WRTDS/LOESS: peso 0 fora da janela [-h,h]."""
    u = np.clip(np.abs(d) / h, 0, 1)
    return (1 - u ** 3) ** 3


def dist_sazonal_circular(doy_a: np.ndarray, doy_b: float, periodo: float = 365.25) -> np.ndarray:
    """Distancia circular em fracao de ano (0 a 0,5) entre dois dias do ano."""
    frac_a = doy_a / periodo
    frac_b = doy_b / periodo
    d = np.abs(frac_a - frac_b)
    return np.minimum(d, 1 - d)


def carregar_serie_tds() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["Data"] = pd.to_datetime(d["Data"])
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    d["doy"] = d["Data"].dt.dayofyear
    d["log_tds"] = np.log(d["TDS_mgL"])
    return d


def ajustar_wrtds(d: pd.DataFrame, col_vazao: str) -> pd.DataFrame:
    """Para cada mes observado, ajusta uma regressao ponderada localmente
    (tempo, log(vazao), sazonalidade) e retorna: valor ajustado no ponto
    (WRTDS "fitted"), e a media da predicao sobre TODA a distribuicao
    historica de vazao no mesmo instante de tempo/estacao ("flow-normalized").
    """
    t = d["t_anos"].values
    logq = np.log(d[col_vazao].values)
    doy = d["doy"].values
    y = d["log_tds"].values
    n = len(d)

    fitted = np.full(n, np.nan)
    flow_normalized = np.full(n, np.nan)
    n_efetivo_peso = np.full(n, np.nan)

    sin_doy = np.sin(2 * np.pi * doy / 365.25)
    cos_doy = np.cos(2 * np.pi * doy / 365.25)

    for i in range(n):
        w_tempo = tricube(t - t[i], HALF_WINDOW_ANOS)
        w_logq = tricube(logq - logq[i], HALF_WINDOW_LOGQ)
        w_saz = tricube(dist_sazonal_circular(doy, doy[i]), HALF_WINDOW_SAZONAL)
        w = w_tempo * w_logq * w_saz
        n_efetivo_peso[i] = w.sum()

        validos = w > 1e-6
        if validos.sum() < 8:  # minimo de pontos para 4 parametros + folga
            continue

        X = np.column_stack([np.ones(n), t, logq, sin_doy, cos_doy])[validos]
        yv = y[validos]
        wv = w[validos]

        # OLS ponderado via minimos quadrados (equivalente a WLS)
        W = np.diag(wv)
        try:
            beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ yv)
        except np.linalg.LinAlgError:
            continue

        x_i = np.array([1, t[i], logq[i], sin_doy[i], cos_doy[i]])
        fitted[i] = x_i @ beta

        # flow-normalizacao: media da predicao sobre TODA a distribuicao
        # historica de log(vazao), no mesmo t[i]/sazonalidade (Hirsch et al. 2010)
        X_fn = np.column_stack([
            np.ones(n), np.full(n, t[i]), logq, np.full(n, sin_doy[i]), np.full(n, cos_doy[i]),
        ])
        flow_normalized[i] = float(np.mean(X_fn @ beta))

    out = d.copy()
    out["wrtds_fitted_log"] = fitted
    out["wrtds_flow_normalized_log"] = flow_normalized
    out["wrtds_fitted_mgL"] = np.exp(fitted)
    out["wrtds_flow_normalized_mgL"] = np.exp(flow_normalized)
    out["n_efetivo_peso"] = n_efetivo_peso
    return out


def theil_sen_trend(t_anos: np.ndarray, y: np.ndarray) -> dict:
    validos = ~np.isnan(y)
    slope, intercept, lo, hi = stats.theilslopes(y[validos], t_anos[validos], alpha=0.90)
    tau, p = stats.kendalltau(t_anos[validos], y[validos])
    return {"slope_ano": float(slope), "intercept": float(intercept),
            "ic90_lo": float(lo), "ic90_hi": float(hi), "pvalor": float(p), "n": int(validos.sum())}


def prever_horizontes(t_ultimo: float, trend: dict) -> dict:
    saida = {}
    for h in HORIZONTES_ANOS:
        t_h = t_ultimo + h
        ponto = trend["intercept"] + trend["slope_ano"] * t_h
        lo = trend["intercept"] + trend["ic90_lo"] * t_h
        hi = trend["intercept"] + trend["ic90_hi"] * t_h
        saida[f"forecast_{h}y"] = ponto
        saida[f"ci90_low_{h}y"] = min(lo, hi)
        saida[f"ci90_high_{h}y"] = max(lo, hi)
    return saida


def gerar_figura(d: pd.DataFrame, wrtds_tds: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(d["Data"], d["TDS_mgL"], color="gray", linewidth=0.9, alpha=0.6, label="TDS observado")
    ax.plot(wrtds_tds["Data"], wrtds_tds["wrtds_fitted_mgL"], color="tab:blue", linewidth=1.2, label="WRTDS ajustado (fitted)")
    ax.plot(wrtds_tds["Data"], wrtds_tds["wrtds_flow_normalized_mgL"], color="tab:red", linewidth=1.8, label="Flow-normalized (efeito da vazão descontado)")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("WRTDS: TDS ajustado × flow-normalized (vazão derivada de TDS)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gerar_figura_circularidade(fn_tds: pd.DataFrame, fn_chloride: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(fn_tds["Data"], fn_tds["wrtds_flow_normalized_mgL"], color="tab:red", linewidth=1.6,
            label="Flow-normalized (vazão derivada de TDS -- circular)")
    ax.plot(fn_chloride["Data"], fn_chloride["wrtds_flow_normalized_mgL"], color="tab:green", linewidth=1.6, linestyle="--",
            label="Flow-normalized (vazão derivada de Cloreto -- independente)")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS flow-normalized (mg/L)")
    ax.set_title("Checagem de circularidade: vazão de TDS vs. vazão de Cloreto")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_CIRCULARIDADE, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_CIRCULARIDADE}")


def gravar_resultados_comparacao(linha: dict):
    linha = dict(linha)
    linha["metodo"] = "wrtds_flow_normalized"
    linha["script"] = "script_19_wrtds"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_COMPARACAO_CSV):
        existentes = pd.read_csv(RESULTADOS_COMPARACAO_CSV)
        existentes = existentes[existentes["metodo"] != "wrtds_flow_normalized"]
        for col in novas.columns:
            if col not in existentes.columns:
                existentes[col] = pd.NA
        for col in existentes.columns:
            if col not in novas.columns:
                novas[col] = pd.NA
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas
    consolidado.to_csv(RESULTADOS_COMPARACAO_CSV, index=False)
    consolidado.to_json(RESULTADOS_COMPARACAO_JSON, orient="records", indent=2, force_ascii=False)


def main():
    print("=== WRTDS / normalização por vazão (implementação própria, ver docstring) ===")
    print(f"Janelas: tempo±{HALF_WINDOW_ANOS}a, log(vazão)±{HALF_WINDOW_LOGQ}, sazonal±{HALF_WINDOW_SAZONAL} (frações de ano)")
    print()

    d = carregar_serie_tds()
    vazoes = pd.read_csv("vazao_reconstruida_serie.csv", parse_dates=["Data"])
    d = d.merge(vazoes[["Data", "vazao_mgd_TDS", "vazao_mgd_Chloride"]], on="Data", how="inner").dropna()
    print(f"Série TDS×vazão pareada: {len(d)} meses ({d['Data'].min().date()} a {d['Data'].max().date()})")
    print()

    with iniciar_run("wrtds_flow_normalized", "script_19_wrtds",
                      params={"half_window_anos": HALF_WINDOW_ANOS, "half_window_logq": HALF_WINDOW_LOGQ,
                              "half_window_sazonal": HALF_WINDOW_SAZONAL}):

        # --- resultado principal: vazao derivada de TDS ---
        wrtds_tds = ajustar_wrtds(d, "vazao_mgd_TDS")
        trend_bruta = theil_sen_trend(d["t_anos"].values, d["log_tds"].values)
        trend_fn_tds = theil_sen_trend(wrtds_tds["t_anos"].values, wrtds_tds["wrtds_flow_normalized_log"].values)

        pct_ano_bruta = (np.exp(trend_bruta["slope_ano"]) - 1) * 100
        pct_ano_fn = (np.exp(trend_fn_tds["slope_ano"]) - 1) * 100

        print("--- Tendência bruta (log TDS, Theil-Sen) ---")
        print(f"  {pct_ano_bruta:.3f} %/ano  (p={trend_bruta['pvalor']:.4f}, n={trend_bruta['n']})")
        print("--- Tendência flow-normalized (vazão de TDS) ---")
        print(f"  {pct_ano_fn:.3f} %/ano  (p={trend_fn_tds['pvalor']:.4f}, n={trend_fn_tds['n']})")
        print()

        # --- checagem de circularidade: vazao derivada de Cloreto ---
        wrtds_chloride = ajustar_wrtds(d, "vazao_mgd_Chloride")
        trend_fn_chloride = theil_sen_trend(wrtds_chloride["t_anos"].values, wrtds_chloride["wrtds_flow_normalized_log"].values)
        pct_ano_fn_chloride = (np.exp(trend_fn_chloride["slope_ano"]) - 1) * 100

        corr_fn, p_corr_fn = stats.pearsonr(
            wrtds_tds["wrtds_flow_normalized_mgL"].dropna(),
            wrtds_chloride.loc[wrtds_tds["wrtds_flow_normalized_mgL"].dropna().index, "wrtds_flow_normalized_mgL"],
        )
        diff_pct_pontos = abs(pct_ano_fn - pct_ano_fn_chloride)
        circularidade_preocupante = diff_pct_pontos > 1.0 or corr_fn < 0.7

        print("--- Checagem de circularidade (vazão de Cloreto, série independente) ---")
        print(f"  Tendência flow-normalized (vazão de Cloreto): {pct_ano_fn_chloride:.3f} %/ano (p={trend_fn_chloride['pvalor']:.4f})")
        print(f"  Correlação entre as duas séries flow-normalized: r={corr_fn:.3f} (p={p_corr_fn:.2e})")
        print(f"  Diferença absoluta entre as tendências: {diff_pct_pontos:.3f} pontos percentuais/ano")
        if circularidade_preocupante:
            print("  ALERTA: divergência relevante -- o achado com vazão de TDS NÃO se sustenta sozinho, reportado como tal.")
        else:
            print("  As duas vazões (dependente e independente do TDS) produzem conclusão qualitativamente igual -- circularidade não invalida o achado.")
        print()

        gerar_figura(d, wrtds_tds)
        gerar_figura_circularidade(wrtds_tds, wrtds_chloride)

        t_ultimo = d["t_anos"].iloc[-1]
        forecasts_log = prever_horizontes(t_ultimo, trend_fn_tds)
        forecasts_mgL = {k: float(np.exp(v)) if "forecast" in k or "ci90" in k else v for k, v in forecasts_log.items()}

        resultado = {
            "trend_bruta_pct_ano": float(pct_ano_bruta), "trend_bruta_pvalor": trend_bruta["pvalor"],
            "trend_flow_normalized_vazao_tds_pct_ano": float(pct_ano_fn), "trend_flow_normalized_vazao_tds_pvalor": trend_fn_tds["pvalor"],
            "trend_flow_normalized_vazao_chloride_pct_ano": float(pct_ano_fn_chloride), "trend_flow_normalized_vazao_chloride_pvalor": trend_fn_chloride["pvalor"],
            "correlacao_entre_flow_normalized_tds_vs_chloride": float(corr_fn),
            "diferenca_absoluta_pct_ano": float(diff_pct_pontos),
            "circularidade_preocupante": bool(circularidade_preocupante),
            "forecasts_flow_normalized_mgL": forecasts_mgL,
            "script": "script_19_wrtds",
            "data_execucao": datetime.now().isoformat(timespec="seconds"),
        }
        with open(RESULTADOS_JSON, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        wrtds_tds.drop(columns=["log_tds"]).to_csv(RESULTADOS_CSV, index=False)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

        linha_comparacao = {
            "tendencia_mgL_ano": float(np.exp(trend_fn_tds["intercept"] + trend_fn_tds["slope_ano"] * (t_ultimo + 1))
                                        - np.exp(trend_fn_tds["intercept"] + trend_fn_tds["slope_ano"] * t_ultimo)),
            "tendencia_pvalor": trend_fn_tds["pvalor"],
            "rmse_holdout": float("nan"), "mae_holdout": float("nan"), "r2_holdout": float("nan"),
            **forecasts_mgL,
        }
        gravar_resultados_comparacao(linha_comparacao)

        metricas = {k: v for k, v in resultado.items() if isinstance(v, (int, float, bool))}
        for h, v in forecasts_mgL.items():
            metricas[f"forecast_{h}"] = v
        logar_metricas(metricas)
        logar_artefatos([FIGURA_PATH, FIGURA_CIRCULARIDADE, RESULTADOS_CSV])

    return resultado


if __name__ == "__main__":
    main()
