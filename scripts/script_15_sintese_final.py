"""
Sintese final da bateria de modelagem de TDS (bloco final do aprofundamento):
le resultados_comparacao.csv e produz (1) uma tabela consolidada ordenada por
MASE de holdout e (2) uma figura com a serie historica e a previsao de cada
um dos 7 metodos do nucleo publico, com IC90 sobreposto.

D-73 (2026-10-15): abandona o conceito de "finalista recomendado". Ate
entao, FINALISTAS elegia 2 metodos (detrend_rf, hibrido_arima_prophet) como
recomendacao destacada, com uma figura de convergencia em +20 anos. Na
reducao da bateria publica para os 7 metodos citados na revisao externa
(Mann-Kendall/Sen, Theil-Sen, OLS, SARIMA, Prophet, naive, Detrend+RF), o
hibrido SARIMA+Prophet -- um dos 2 finalistas -- saiu da bateria publica
(ver D-73 em scripts/bateria_estendida/), o que deixaria um unico "finalista"
sobrevivente: contradiz a propria premissa original ("nao um unico
vencedor"). Em vez de forcar uma recomendacao com 1 metodo so, este script
passa a reportar apenas as metricas de cada metodo (MASE/R2 de holdout),
igual ao formato da tabela 3.6 da revisao externa -- sem eleger vencedor.

Nao gera novos ajustes de modelo -- consome exclusivamente o que ja esta em
resultados_comparacao.csv (nenhum numero novo e calculado aqui, so
consolidado e visualizado).
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.paths import (
    bootstrap_sys_path,
    raw,
    processed,
    result,
    figure,
    RESULTADOS_COMPARACAO_CSV,
    RESULTADOS_COMPARACAO_JSON,
)
bootstrap_sys_path()


from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_artefatos

RESULTADOS_CSV = RESULTADOS_COMPARACAO_CSV
TABELA_FINAL_CSV = result("tabela_sintese_final.csv")
FIGURA_PATH = figure("sintese-final-metodos.png")
HORIZONTES_ANOS = [10, 15, 20]

# Os 7 metodos do nucleo publico (D-73) -- os demais metodos presentes em
# resultados_comparacao.csv (causais/mecanismo: balanco_massa, wrtds,
# cenarios; e os arquivados em bateria_estendida, se alguem rodar aqueles
# scripts localmente) nao entram na figura, so na tabela consolidada.
METODOS_NUCLEO = [
    "mann_kendall_sen", "theil_sen", "ols", "sarima", "prophet", "naive", "detrend_rf",
]
CORES_NUCLEO = {
    "mann_kendall_sen": "tab:blue", "theil_sen": "tab:orange", "ols": "tab:green",
    "sarima": "tab:purple", "prophet": "tab:brown", "naive": "gray", "detrend_rf": "tab:olive",
}
NOMES_EXIBICAO = {
    "mann_kendall_sen": "Mann-Kendall/Sen", "theil_sen": "Theil-Sen", "ols": "OLS",
    "sarima": "SARIMA", "prophet": "Prophet", "naive": "Naive", "detrend_rf": "Detrend + RF",
}


def carregar_serie_tds():
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    return d


def gerar_tabela_consolidada(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["metodo", "tendencia_mgL_ano", "tendencia_pvalor", "rmse_holdout", "mae_holdout",
            "mase_holdout", "smape_holdout", "cv_mase_media", "r2_holdout"]
    for h in HORIZONTES_ANOS:
        cols += [f"forecast_{h}y", f"ci90_low_{h}y", f"ci90_high_{h}y"]
    tabela = df[cols].copy()
    tabela = tabela.sort_values("mase_holdout").reset_index(drop=True)
    tabela.to_csv(TABELA_FINAL_CSV, index=False)
    return tabela


def gerar_figura(d: pd.DataFrame, df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")

    ultima_data = d["Data"].iloc[-1]
    ultimo_valor = d["TDS_mgL"].iloc[-1]
    for metodo in METODOS_NUCLEO:
        linha = df[df["metodo"] == metodo]
        if linha.empty:
            continue
        linha = linha.iloc[0]
        anos_futuros = [0] + HORIZONTES_ANOS
        datas_futuras = [ultima_data + pd.DateOffset(months=int(a * 12)) for a in anos_futuros]
        pontos = [ultimo_valor] + [linha[f"forecast_{h}y"] for h in HORIZONTES_ANOS]
        baixos = [ultimo_valor] + [linha[f"ci90_low_{h}y"] for h in HORIZONTES_ANOS]
        altos = [ultimo_valor] + [linha[f"ci90_high_{h}y"] for h in HORIZONTES_ANOS]
        cor = CORES_NUCLEO[metodo]
        ax.plot(datas_futuras, pontos, "--", color=cor, linewidth=1.3, label=NOMES_EXIBICAO[metodo])
        ax.fill_between(datas_futuras, baixos, altos, color=cor, alpha=0.08)

    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Bateria de 7 métodos — previsão de TDS com IC90% (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def main():
    d = carregar_serie_tds()
    df = pd.read_csv(RESULTADOS_CSV)
    print(f"Metodos na bateria: {df['metodo'].nunique()}")
    print()

    tabela = gerar_tabela_consolidada(df)
    print(f"Tabela consolidada salva em {TABELA_FINAL_CSV}")
    print()
    print("--- Bateria do nucleo publico, por MASE de holdout ---")
    tabela_nucleo = tabela[tabela["metodo"].isin(METODOS_NUCLEO)]
    print(tabela_nucleo[["metodo", "mase_holdout", "r2_holdout", "cv_mase_media"]].to_string(index=False))
    print()
    print("Nenhum metodo e recomendado como vencedor (D-73) -- ver tabela completa para "
          "MASE/R2/tendencia/IC90 de cada um.")

    gerar_figura(d, df)

    with iniciar_run("sintese_final", "script_15_sintese_final",
                      params={"metodos_nucleo": ",".join(METODOS_NUCLEO)}):
        logar_artefatos([FIGURA_PATH, TABELA_FINAL_CSV])


if __name__ == "__main__":
    main()
