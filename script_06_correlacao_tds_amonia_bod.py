"""
Analise de correlacao TDS-Amonia e TDS-BOD (plano_projeto_TDS.md secao 1, objetivo 3;
AI_Project_Instructions.pdf, objetivo 3): investiga como a salinidade crescente pode
afetar o tratamento biologico, correlacionando TDS com Amonia (indicador de
nitrificacao) e TDS com BOD (indicador de remocao de materia organica).

Roda nos DOIS datasets canonicos (tratamento de ND do BOD: A=MDL/2, B=zero) —
aqui a distincao realmente importa, ao contrario dos scripts 01-05 (que eram
univariados em TDS). A correlacao com Amonia e identica nos dois datasets
(Amonia nao depende do tratamento de ND do BOD).

Duas versoes de cada correlacao sao reportadas:
  - BRUTA (Pearson/Spearman sobre as series originais): pode ser inflada pelo
    fato de TDS e os dois indicadores estarem, em maior ou menor grau, subindo
    juntos ao longo do tempo (tendencia comum), sem isso significar covariacao
    mes-a-mes real.
  - DESTENDENCIADA (Pearson/Spearman sobre os RESIDUOS de uma OLS de cada serie
    contra o tempo): remove a tendencia de longo prazo comum, isolando se os
    desvios mensais de TDS realmente acompanham desvios mensais de Amonia/BOD —
    teste mais relevante para a hipotese biologica do projeto (inibicao aguda
    por salinidade), nao apenas coincidencia de ambas subirem ao longo de 15 anos.

Tambem calcula correlacao cruzada destendenciada em defasagens de 0 a 3 meses
(TDS no mes t vs Amonia/BOD no mes t+lag), para checar se ha resposta biologica
com atraso.

Resultados gravados em correlacao_resultados.csv/.json (arquivo proprio,
separado de resultados_comparacao.csv, que e especifico da bateria de
tendencia/previsao de TDS — esta e uma analise diferente, de correlacao).
"""

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from script_00_preprocessamento import construir_datasets

RESULTADOS_CSV = "correlacao_resultados.csv"
RESULTADOS_JSON = "correlacao_resultados.json"
FIGURA_PATH = "Artigo/images/correlacao-tds-amonia-bod.png"
LAGS_MESES = [0, 1, 2, 3]


def residuos_ols(t: np.ndarray, y: np.ndarray) -> np.ndarray:
    reg = stats.linregress(t, y)
    return y - (reg.intercept + reg.slope * t)


def correlacionar(x: np.ndarray, y: np.ndarray) -> dict:
    r_pearson, p_pearson = stats.pearsonr(x, y)
    r_spearman, p_spearman = stats.spearmanr(x, y)
    return {
        "pearson_r": float(r_pearson), "pearson_p": float(p_pearson),
        "spearman_rho": float(r_spearman), "spearman_p": float(p_spearman),
        "n": len(x),
    }


def correlacao_cruzada_defasada(t: np.ndarray, x_resid: np.ndarray, y_raw: np.ndarray, t_y: np.ndarray) -> list:
    """Para cada defasagem k (meses), correlaciona o residuo de x no mes t com
    o residuo de y no mes t+k (TDS levando Amonia/BOD)."""
    linhas = []
    for k in LAGS_MESES:
        if k == 0:
            y_lag_resid = residuos_ols(t_y, y_raw)
            xr, yr = x_resid, y_lag_resid
        else:
            # desloca y para tras k meses (associa TDS[t] com y[t+k])
            if k >= len(y_raw):
                continue
            y_desloc = y_raw[k:]
            t_desloc = t_y[k:]
            y_resid_desloc = residuos_ols(t_desloc, y_desloc)
            xr = x_resid[: len(y_resid_desloc)]
            yr = y_resid_desloc
        if len(xr) < 10:
            continue
        r, p = stats.pearsonr(xr, yr)
        linhas.append({"lag_meses": k, "pearson_r": float(r), "pearson_p": float(p), "n": len(xr)})
    return linhas


def analisar_par(nome: str, d: pd.DataFrame, col_x: str, col_y: str) -> dict:
    sub = d[["Data", "t_anos", col_x, col_y]].dropna().sort_values("Data").reset_index(drop=True)
    x, y, t = sub[col_x].values, sub[col_y].values, sub["t_anos"].values

    bruta = correlacionar(x, y)
    x_resid = residuos_ols(t, x)
    y_resid = residuos_ols(t, y)
    destend = correlacionar(x_resid, y_resid)
    defasada = correlacao_cruzada_defasada(t, x_resid, y, t)

    return {
        "par": nome,
        "n_meses": len(sub),
        "bruta_pearson_r": bruta["pearson_r"], "bruta_pearson_p": bruta["pearson_p"],
        "bruta_spearman_rho": bruta["spearman_rho"], "bruta_spearman_p": bruta["spearman_p"],
        "destend_pearson_r": destend["pearson_r"], "destend_pearson_p": destend["pearson_p"],
        "destend_spearman_rho": destend["spearman_rho"], "destend_spearman_p": destend["spearman_p"],
        "defasagens": defasada,
    }


def gerar_figura(d_amonia: pd.DataFrame, d_bod_a: pd.DataFrame, d_bod_b: pd.DataFrame, d_bod_c: pd.DataFrame):
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6))

    for ax, (titulo, sub, col_y, cor) in zip(axes, [
        ("TDS vs Amônia", d_amonia, "Ammonia_mgL", "tab:orange"),
        ("TDS vs BOD (ND=MDL/2)", d_bod_a, "BOD_mgL", "tab:red"),
        ("TDS vs BOD (ND=0)", d_bod_b, "BOD_mgL", "tab:purple"),
        ("TDS vs BOD (ND=ROS/Helsel)", d_bod_c, "BOD_mgL", "tab:brown"),
    ]):
        sub = sub.dropna(subset=["TDS_mgL", col_y])
        t = sub["t_anos"].values
        x_resid = residuos_ols(t, sub["TDS_mgL"].values)
        y_resid = residuos_ols(t, sub[col_y].values)
        ax.scatter(x_resid, y_resid, s=10, alpha=0.5, color=cor)
        if len(x_resid) > 2:
            reg = stats.linregress(x_resid, y_resid)
            xs = np.linspace(x_resid.min(), x_resid.max(), 50)
            ax.plot(xs, reg.intercept + reg.slope * xs, color="black", linewidth=1)
        ax.set_title(titulo, fontsize=9)
        ax.set_xlabel("Resíduo TDS (mg/L)", fontsize=8)
        ax.set_ylabel("Resíduo (mg/L)", fontsize=8)
        ax.tick_params(labelsize=7)

    fig.suptitle("Correlação destendenciada (resíduos de OLS vs. tempo)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_06_correlacao_tds_amonia_bod"
        linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame(linhas)
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[~existentes["par"].isin(novas["par"])]
        consolidado = pd.concat([existentes, novas.drop(columns=["defasagens"])], ignore_index=True)
    else:
        consolidado = novas.drop(columns=["defasagens"])

    consolidado.to_csv(RESULTADOS_CSV, index=False)

    # JSON mantem a estrutura completa (incluindo defasagens), CSV fica tabular/plano
    if pd.io.common.file_exists(RESULTADOS_JSON):
        import json
        with open(RESULTADOS_JSON, encoding="utf-8") as f:
            existentes_json = {item["par"]: item for item in json.load(f)}
    else:
        existentes_json = {}
    for linha in linhas:
        existentes_json[linha["par"]] = linha
    with open(RESULTADOS_JSON, "w", encoding="utf-8") as f:
        import json
        json.dump(list(existentes_json.values()), f, indent=2, ensure_ascii=False)


def main():
    dataset_a, dataset_b, dataset_c, base = construir_datasets()
    dataset_a["t_anos"] = (dataset_a["Data"] - dataset_a["Data"].iloc[0]).dt.days / 365.25
    dataset_b["t_anos"] = (dataset_b["Data"] - dataset_b["Data"].iloc[0]).dt.days / 365.25
    dataset_c["t_anos"] = (dataset_c["Data"] - dataset_c["Data"].iloc[0]).dt.days / 365.25

    resultados = []
    for nome, d, col_y in [
        ("tds_amonia", dataset_a, "Ammonia_mgL"),
        ("tds_bod_mdl2", dataset_a, "BOD_mgL"),
        ("tds_bod_zero", dataset_b, "BOD_mgL"),
        ("tds_bod_ros", dataset_c, "BOD_mgL"),
    ]:
        r = analisar_par(nome, d, "TDS_mgL", col_y)
        resultados.append(r)
        print(f"--- {nome} (n={r['n_meses']}) ---")
        print(f"  Bruta:         Pearson r={r['bruta_pearson_r']:.3f} (p={r['bruta_pearson_p']:.4f})  Spearman rho={r['bruta_spearman_rho']:.3f} (p={r['bruta_spearman_p']:.4f})")
        print(f"  Destendenciada: Pearson r={r['destend_pearson_r']:.3f} (p={r['destend_pearson_p']:.4f})  Spearman rho={r['destend_spearman_rho']:.3f} (p={r['destend_spearman_p']:.4f})")
        for dlin in r["defasagens"]:
            print(f"    lag {dlin['lag_meses']}m: r={dlin['pearson_r']:.3f} (p={dlin['pearson_p']:.4f}, n={dlin['n']})")
        print()

    gravar_resultados(resultados)
    print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(dataset_a, dataset_a, dataset_b, dataset_c)


if __name__ == "__main__":
    main()
