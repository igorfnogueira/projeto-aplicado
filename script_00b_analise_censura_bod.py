"""
Analise dos valores nao detectados (ND) do BOD -- apresenta, com numeros reais,
as opcoes A-F de tratamento (plano_projeto_TDS.md secao 1.3 + opcao F pedida
no aprofundamento da bateria, material_apoio_referencias.md Tema 8) para
DECISAO DO USUARIO. Nao decide sozinho, nao altera script_00_preprocessamento.py
ate a decisao.

Opcao F (Kaplan-Meier / Helsel): como o BOD deste dataset tem um UNICO limite
de deteccao (MDL) constante ao longo de todo o periodo (3,0 mg/L), a vantagem
central do Kaplan-Meier (lidar com MULTIPLOS MDLs diferentes) nao se aplica --
o metodo de Helsel apropriado para este caso e ROS (Regression on Order
Statistics / regressao em grafico de probabilidade): ajusta uma reta entre os
valores detectados e seus quantis normais esperados (posicao de plotagem de
Hazen, assumindo que os censurados ocupam os ranks mais baixos), e usa essa
reta para extrapolar o valor esperado da fracao censurada -- em vez de uma
substituicao arbitraria (MDL/2, zero, MDL cheio).

Limitacao honesta de qualquer opcao de substituicao por valor unico (A, B, C
ou F): como as 118 observacoes ND sao indistinguiveis entre si (todas
reportadas so como "< 3,0"), nao ha como recuperar variacao mes-a-mes real
dentro dos meses ND -- mesmo o ROS produz um UNICO valor substituto (a media
estimada da fracao censurada), nao um valor diferente por mes. Isso nao e
um defeito da implementacao, e uma limitacao dos dados.
"""

import numpy as np
import pandas as pd
from scipy import stats

from script_00_preprocessamento import carregar_csv, serie_mensal_canonica, PARAMETROS, calcular_ros_helsel as _ros_valor_substituto


def carregar_bod_mensal() -> pd.DataFrame:
    return serie_mensal_canonica(carregar_csv("BOD.csv"), PARAMETROS["BOD"])


def analisar_padrao_temporal(bod: pd.DataFrame) -> pd.DataFrame:
    b = bod.copy()
    b["ano"] = b["Data"].dt.year
    b["nd"] = (b["Qual"] == "ND").astype(int)
    tab = b.groupby("ano")["nd"].agg(["sum", "count"])
    tab["taxa_nd_pct"] = (tab["sum"] / tab["count"] * 100).round(1)
    return tab


def calcular_ros_helsel(bod: pd.DataFrame) -> dict:
    """Recalcula os mesmos numeros de diagnostico do ROS (Helsel) que
    script_00_preprocessamento.calcular_ros_helsel usa para gerar o dataset
    canonico C -- aqui com estatisticas extras (r, p-valor, faixa prevista)
    so para fins de relatorio/decisao, sem duplicar a formula em si."""
    n_total = len(bod)
    detectados = np.sort(bod.loc[bod["Qual"] == "=", "Result"].values)
    n_det = len(detectados)
    n_cens = n_total - n_det

    ranks_det = np.arange(n_cens + 1, n_total + 1)
    p_det = (ranks_det - 0.5) / n_total
    z_det = stats.norm.ppf(p_det)
    reg = stats.linregress(z_det, detectados)

    ranks_cens = np.arange(1, n_cens + 1)
    p_cens = (ranks_cens - 0.5) / n_total
    z_cens = stats.norm.ppf(p_cens)
    pred_cens = reg.intercept + reg.slope * z_cens
    valor_substituto = _ros_valor_substituto(bod)  # mesma formula, fonte unica

    return {
        "n_total": n_total, "n_detectados": n_det, "n_censurados": n_cens,
        "regressao_r": reg.rvalue, "regressao_p": reg.pvalue,
        "valor_substituto_ros": valor_substituto,
        "pred_cens_min": float(pred_cens.min()), "pred_cens_max": float(pred_cens.max()),
        "n_previstos_negativos": int((pred_cens < 0).sum()),
        "media_geral_ros": float((detectados.sum() + pred_cens.sum()) / n_total),
    }


def comparar_opcoes(bod: pd.DataFrame, valor_ros: float) -> pd.DataFrame:
    detectados = bod.loc[bod["Qual"] == "=", "Result"].values
    n_total = len(bod)
    n_cens = int((bod["Qual"] == "ND").sum())
    opcoes = {
        "A. MDL/2 (1,5 mg/L)": 1.5,
        "B. Zero (0 mg/L)": 0.0,
        "C. MDL cheio (3,0 mg/L)": 3.0,
        "F. ROS/Helsel (valor estimado)": valor_ros,
    }
    linhas = []
    for nome, valor in opcoes.items():
        media_geral = (detectados.sum() + n_cens * valor) / n_total
        linhas.append({"opcao": nome, "valor_substituto_mgL": round(valor, 3),
                        "media_geral_resultante_mgL": round(media_geral, 3)})
    return pd.DataFrame(linhas)


def main():
    bod = carregar_bod_mensal()
    n_total = len(bod)
    n_nd = int((bod["Qual"] == "ND").sum())
    n_det = n_total - n_nd

    print(f"BOD mensal: {n_total} meses ({bod['Data'].min().date()} a {bod['Data'].max().date()})")
    print(f"ND: {n_nd} ({n_nd/n_total*100:.1f}%)  |  Detectados: {n_det} ({n_det/n_total*100:.1f}%)")
    print(f"MDL: {bod['MDL'].unique()} (constante ao longo de todo o periodo)")
    print(f"Detectados -- media={bod.loc[bod['Qual']=='=','Result'].mean():.3f}  "
          f"mediana={bod.loc[bod['Qual']=='=','Result'].median():.3f}  "
          f"min={bod.loc[bod['Qual']=='=','Result'].min():.3f}  "
          f"max={bod.loc[bod['Qual']=='=','Result'].max():.3f}")
    print()

    print("--- Padrao temporal da taxa de ND (por ano) ---")
    print(analisar_padrao_temporal(bod))
    print()
    primeira = bod[bod["Data"] < bod["Data"].median()]
    segunda = bod[bod["Data"] >= bod["Data"].median()]
    print(f"1a metade do periodo: taxa ND = {(primeira['Qual']=='ND').mean()*100:.1f}% (n={len(primeira)})")
    print(f"2a metade do periodo: taxa ND = {(segunda['Qual']=='ND').mean()*100:.1f}% (n={len(segunda)})")
    print("-> Sem padrao monotono claro (nao aumenta nem diminui de forma consistente ano a ano).")
    print()

    ros = calcular_ros_helsel(bod)
    print("--- Opcao F: ROS/Helsel ---")
    print(f"Regressao probabilidade-quantil: r={ros['regressao_r']:.3f} (p={ros['regressao_p']:.2e})")
    print(f"Valor substituto estimado (media da fracao censurada): {ros['valor_substituto_ros']:.3f} mg/L")
    print(f"Faixa prevista por mes censurado: [{ros['pred_cens_min']:.3f}, {ros['pred_cens_max']:.3f}] mg/L "
          f"({ros['n_previstos_negativos']} previsoes negativas)")
    print()

    print("--- Comparacao das opcoes de substituicao ---")
    print(comparar_opcoes(bod, ros["valor_substituto_ros"]).to_string(index=False))


if __name__ == "__main__":
    main()
