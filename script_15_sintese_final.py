"""
Sintese final da bateria de modelagem de TDS (bloco final do aprofundamento):
le resultados_comparacao.csv (21 metodos) e produz (1) uma tabela consolidada
ordenada por MASE de holdout e (2) o grafico unico com a serie historica e a
previsao dos finalistas recomendados, com IC90 sobreposto.

Finalistas escolhidos (nao um unico vencedor, conforme criterio de comparacao
do plano do projeto, secao 5) -- justificativa registrada aqui, nao inventada:
  - regressao_bayesiana: unico metodo com incerteza honesta (IC90 cresce de
    forma suave e proporcional ao horizonte, tendencia estatisticamente
    significativa com probabilidade posterior >99%).
  - detrend_rf: melhor MASE de holdout (0,44) entre os metodos que captam
    tendencia de longo prazo sem saturar/oscilar, e o UNICO candidato sem
    autocorrelacao residual nem heterocedasticidade detectavel (script_14).
  - hibrido_arima_prophet: melhor RMSE de holdout entre os metodos de serie
    temporal, IC90 mais largo (envoltoria de SARIMA+Prophet) -- cenario mais
    cauteloso/conservador para planejamento de infraestrutura, sem a
    explosao do IC do SARIMA isolado.

Nao gera novos ajustes de modelo -- consome exclusivamente o que ja esta em
resultados_comparacao.csv (nenhum numero novo e calculado aqui, so
consolidado e visualizado).
"""

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_artefatos

RESULTADOS_CSV = "resultados_comparacao.csv"
TABELA_FINAL_CSV = "tabela_sintese_final.csv"
FIGURA_PATH = "Artigo/images/sintese-final-finalistas.png"
HORIZONTES_ANOS = [10, 15, 20]
FINALISTAS = ["regressao_bayesiana", "detrend_rf", "hibrido_arima_prophet"]
CORES_FINALISTAS = {"regressao_bayesiana": "tab:pink", "detrend_rf": "tab:olive", "hibrido_arima_prophet": "tab:red"}
NOMES_EXIBICAO = {
    "regressao_bayesiana": "Regressão bayesiana (incerteza honesta)",
    "detrend_rf": "Detrend + RF (melhor MASE + resíduos limpos)",
    "hibrido_arima_prophet": "Híbrido SARIMA+Prophet (cenário cauteloso)",
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
    tabela["finalista"] = tabela["metodo"].isin(FINALISTAS)
    tabela = tabela.sort_values("mase_holdout").reset_index(drop=True)
    tabela.to_csv(TABELA_FINAL_CSV, index=False)
    return tabela


def gerar_figura(d: pd.DataFrame, df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")

    ultima_data = d["Data"].iloc[-1]
    ultimo_valor = d["TDS_mgL"].iloc[-1]
    for metodo in FINALISTAS:
        linha = df[df["metodo"] == metodo]
        if linha.empty:
            continue
        linha = linha.iloc[0]
        anos_futuros = [0] + HORIZONTES_ANOS
        datas_futuras = [ultima_data + pd.DateOffset(months=int(a * 12)) for a in anos_futuros]
        pontos = [ultimo_valor] + [linha[f"forecast_{h}y"] for h in HORIZONTES_ANOS]
        baixos = [ultimo_valor] + [linha[f"ci90_low_{h}y"] for h in HORIZONTES_ANOS]
        altos = [ultimo_valor] + [linha[f"ci90_high_{h}y"] for h in HORIZONTES_ANOS]
        cor = CORES_FINALISTAS[metodo]
        ax.plot(datas_futuras, pontos, "--", color=cor, linewidth=1.6, label=NOMES_EXIBICAO[metodo])
        ax.fill_between(datas_futuras, baixos, altos, color=cor, alpha=0.12)

    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Finalistas recomendados — previsão de TDS com IC90% (+10/+15/+20 anos)")
    ax.legend(fontsize=8, loc="upper left")
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
    print("--- Top 5 por MASE de holdout ---")
    print(tabela[["metodo", "mase_holdout", "cv_mase_media", "r2_holdout", "finalista"]].head(5).to_string(index=False))
    print()

    print("--- Finalistas recomendados ---")
    for metodo in FINALISTAS:
        linha = tabela[tabela["metodo"] == metodo]
        if linha.empty:
            print(f"  AVISO: {metodo} nao encontrado em {RESULTADOS_CSV}")
            continue
        linha = linha.iloc[0]
        print(f"  {NOMES_EXIBICAO[metodo]}")
        print(f"    MASE holdout={linha['mase_holdout']:.3f}  RMSE={linha['rmse_holdout']:.2f}  "
              f"Tendencia={linha['tendencia_mgL_ano']:.2f} mg/L/ano")
        for h in HORIZONTES_ANOS:
            print(f"    +{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]")

    gerar_figura(d, df)

    with iniciar_run("sintese_final", "script_15_sintese_final",
                      params={"finalistas": ",".join(FINALISTAS)}):
        logar_artefatos([FIGURA_PATH, TABELA_FINAL_CSV])


if __name__ == "__main__":
    main()
