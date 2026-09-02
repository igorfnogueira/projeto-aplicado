"""
Compara o TDS de efluente da LAGWRP com um TDS medio ponderado da agua de
origem (LADWP), reconstruido a partir de 21 relatorios anuais de qualidade
da agua (2004-2024) extraidos manualmente (ladwp_tds_por_fonte_historico.csv).

Por que: D-30 (Artigo/DECISOES.md) aponta a lacuna critica -- falta a serie
de TDS da agua de origem. Este script testa se um proxy real (nao mais o
PDSI indireto) construido a partir de dados publicos da LADWP correlaciona
com o TDS de efluente observado.

Limitacao declarada: a media ponderada usa os pesos agregados por
"MWD total" e "agua subterranea total" (nao ha, nos relatorios, o peso
individual de cada ETA da MWD -- Weymouth/Diemer/Jensen -- dentro do total
importado), entao a fonte MWD entra como media simples das 3 ETAs. Os dados
de 2006-2023 (exceto 2024, que foi conferido celula a celula) foram
extraidos em lote e NAO foram checados manualmente contra o PDF original --
ver aviso em ladwp_tds_por_fonte_historico.csv.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

TDS_CSV = "TDS.csv"
LADWP_CSV = "ladwp_tds_por_fonte_historico.csv"
SAIDA_CSV = "ladwp_tds_origem_vs_efluente.csv"
FIGURA = "Artigo/images/ladwp-tds-origem-vs-efluente.png"


def carregar_tds_efluente_anual() -> pd.Series:
    df = pd.read_csv(TDS_CSV, sep=";", decimal=",", encoding="latin1")
    df = df[df["Units"] == "mg/L"]
    df = df[df["Calculated Method"] == "Monthly Average (Mean)"]
    df["Location"] = df["Location"].replace({"EFF-001A": "EFF-001"})
    df = df[df["Location"] == "EFF-001"]
    df["Sampling Date"] = pd.to_datetime(df["Sampling Date"])
    df["ano"] = df["Sampling Date"].dt.year
    anual = df.groupby("ano")["Result"].mean()
    anual.name = "tds_efluente_lagwrp"
    return anual


def carregar_tds_origem_ponderado() -> pd.DataFrame:
    df = pd.read_csv(LADWP_CSV, sep=";")
    linhas = []
    for ano, grupo in df.groupby("ano_relatorio"):
        g = grupo.set_index("fonte")

        def valor(fonte):
            if fonte in g.index and pd.notna(g.loc[fonte, "tds_medio_mg_L"]):
                return float(g.loc[fonte, "tds_medio_mg_L"])
            return np.nan

        def pct(fonte):
            if fonte in g.index and pd.notna(g.loc[fonte, "pct_abastecimento_cidade"]):
                return float(g.loc[fonte, "pct_abastecimento_cidade"])
            return np.nan

        tds_aqueduct = valor("LA Aqueduct Filtration Plant")
        pct_aqueduct = pct("LA Aqueduct Filtration Plant")

        tds_mwd_plantas = [valor(f) for f in ("MWD Weymouth", "MWD Diemer", "MWD Jensen")]
        tds_mwd_plantas = [v for v in tds_mwd_plantas if pd.notna(v)]
        tds_mwd = float(np.mean(tds_mwd_plantas)) if tds_mwd_plantas else np.nan
        pct_mwd = pct("MWD_total_agregado")

        tds_gw_plantas = [valor(f) for f in ("Northern Combined Wells", "Southern Combined Wells")]
        tds_gw_plantas = [v for v in tds_gw_plantas if pd.notna(v)]
        tds_gw = float(np.mean(tds_gw_plantas)) if tds_gw_plantas else np.nan
        pct_gw = pct("Local_Groundwater_agregado")

        pesos = {"aqueduct": pct_aqueduct, "mwd": pct_mwd, "gw": pct_gw}
        tds_fonte = {"aqueduct": tds_aqueduct, "mwd": tds_mwd, "gw": tds_gw}
        soma_pesos = sum(v for v in pesos.values() if pd.notna(v))
        if soma_pesos == 0 or pd.isna(soma_pesos):
            continue

        tds_ponderado = sum(
            pesos[k] * tds_fonte[k] for k in pesos if pd.notna(pesos[k]) and pd.notna(tds_fonte[k])
        ) / soma_pesos

        linhas.append({
            "ano": int(ano),
            "tds_origem_ponderado": round(tds_ponderado, 1),
            "tds_aqueduct": tds_aqueduct,
            "pct_aqueduct": pct_aqueduct,
            "tds_mwd_media_3etas": round(tds_mwd, 1) if pd.notna(tds_mwd) else np.nan,
            "pct_mwd": pct_mwd,
            "tds_groundwater_media": round(tds_gw, 1) if pd.notna(tds_gw) else np.nan,
            "pct_groundwater": pct_gw,
        })

    return pd.DataFrame(linhas).set_index("ano").sort_index()


def main():
    efluente = carregar_tds_efluente_anual()
    origem = carregar_tds_origem_ponderado()

    comparacao = origem.join(efluente, how="inner")
    comparacao.to_csv(SAIDA_CSV, sep=";", decimal=",")

    print("=" * 80)
    print("TDS de origem (ponderado, LADWP) vs. TDS de efluente (LAGWRP) -- por ano")
    print("=" * 80)
    print(comparacao[["tds_origem_ponderado", "tds_efluente_lagwrp", "pct_aqueduct"]].to_string())

    r = comparacao["tds_origem_ponderado"].corr(comparacao["tds_efluente_lagwrp"])
    n = len(comparacao)
    print(f"\nn = {n} anos com dado nos dois lados")
    print(f"Correlacao de Pearson (TDS origem ponderado x TDS efluente LAGWRP): r = {r:.3f}")

    r_aqueduct_pct = comparacao["pct_aqueduct"].corr(comparacao["tds_efluente_lagwrp"])
    print(f"Correlacao (% LA Aqueduct no mix x TDS efluente LAGWRP): r = {r_aqueduct_pct:.3f}")
    print("(esperado: negativa -- mais % de Aqueduct [agua menos salina] deveria vir com efluente menos salino)")

    _, p_valor = stats.pearsonr(comparacao["tds_origem_ponderado"], comparacao["tds_efluente_lagwrp"])
    print(f"p-valor: {p_valor:.6f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    anos = comparacao.index
    ax1.plot(anos, comparacao["tds_origem_ponderado"], "o-", color="tab:orange", label="TDS origem ponderado (LADWP)")
    ax1b = ax1.twinx()
    ax1b.plot(anos, comparacao["tds_efluente_lagwrp"], "s-", color="tab:blue", label="TDS efluente LAGWRP")
    ax1.set_xlabel("Ano")
    ax1.set_ylabel("TDS origem ponderado (mg/L)", color="tab:orange")
    ax1b.set_ylabel("TDS efluente LAGWRP (mg/L)", color="tab:blue")
    ax1.set_title("Série anual: origem vs. efluente")
    ax1.tick_params(axis="y", labelcolor="tab:orange")
    ax1b.tick_params(axis="y", labelcolor="tab:blue")

    ax2.scatter(comparacao["tds_origem_ponderado"], comparacao["tds_efluente_lagwrp"], color="tab:green")
    for ano, row in comparacao.iterrows():
        ax2.annotate(str(ano), (row["tds_origem_ponderado"], row["tds_efluente_lagwrp"]), fontsize=8, xytext=(3, 3), textcoords="offset points")
    coef = np.polyfit(comparacao["tds_origem_ponderado"], comparacao["tds_efluente_lagwrp"], 1)
    xs = np.linspace(comparacao["tds_origem_ponderado"].min(), comparacao["tds_origem_ponderado"].max(), 50)
    ax2.plot(xs, np.polyval(coef, xs), "--", color="gray")
    ax2.set_xlabel("TDS origem ponderado (mg/L)")
    ax2.set_ylabel("TDS efluente LAGWRP (mg/L)")
    ax2.set_title(f"r={r:.3f}, p={p_valor:.6f}, n={n}")

    fig.tight_layout()
    fig.savefig(FIGURA, dpi=150)
    print(f"\nFigura salva em {FIGURA}")


if __name__ == "__main__":
    main()
