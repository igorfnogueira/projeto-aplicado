"""
Pré-processamento: constrói o dataset mensal canônico (TDS, Chloride, Ammonia, BOD)
a partir dos 4 CSVs brutos do eSMR (TDS.csv, Chloride.csv, Ammonia.csv, BOD.csv).

Ver plano_projeto_TDS.md secoes 1.2/1.3/4 para o raciocínio completo por tras de
cada filtro, e script_00b_analise_censura_bod.py para os numeros reais que
embasaram a decisao de tratamento de ND do BOD (aprovada pelo usuario:
rodar a bateria em 3 datasets em paralelo, nao escolher um unico tratamento).

Gera TRES datasets canonicos, lado a lado:
  - dataset_canonico_bod_mdl2.csv  -> ND do BOD = MDL/2       (Opcao A)
  - dataset_canonico_bod_zero.csv  -> ND do BOD = 0           (Opcao B)
  - dataset_canonico_bod_ros.csv   -> ND do BOD = ROS/Helsel  (Opcao F)

Opcao F (ROS -- Regression on Order Statistics, tecnica de Helsel para dados
censurados a esquerda com MDL unico): ajusta uma reta entre os valores
detectados e seus quantis normais esperados (posicao de plotagem de Hazen,
assumindo que os censurados ocupam os ranks mais baixos) e extrapola o valor
esperado da fracao censurada -- data-driven, em vez de uma convencao
arbitraria como MDL/2 ou zero. Produz um UNICO valor substituto (a media da
fracao censurada), nao um valor por mes -- as 118 observacoes ND sao
indistinguiveis entre si (todas so "< MDL"), entao essa e uma limitacao dos
dados, nao da tecnica.
"""

import numpy as np
import pandas as pd
from scipy import stats

LOCATIONS_EFLUENTE = ["EFF-001", "EFF-001A"]
CALC_METHOD_MENSAL = "Monthly Average (Mean)"
UNIDADE_ALVO = "mg/L"

PARAMETROS = {
    "TDS": "Total Dissolved Solids (TDS)",
    "Chloride": "Chloride",
    "Ammonia": "Ammonia, Total (as N)",
    "BOD": "Biochemical Oxygen Demand (BOD) (5-day @ 20 Deg. C)",
}


def carregar_csv(nome_arquivo: str) -> pd.DataFrame:
    return pd.read_csv(nome_arquivo, sep=";", decimal=",")


def serie_mensal_canonica(df: pd.DataFrame, parametro: str) -> pd.DataFrame:
    """Filtra um parâmetro para a série mensal canônica do efluente (EFF-001+EFF-001A,
    Monthly Average (Mean), mg/L) e unifica os dois códigos de local em um só."""
    d = df[df["Parameter"] == parametro].copy()
    d = d[d["Location"].isin(LOCATIONS_EFLUENTE)]
    d = d[d["Calculated Method"] == CALC_METHOD_MENSAL]
    d = d[d["Units"] == UNIDADE_ALVO]
    d["Location"] = "EFF-001"
    d["Data"] = pd.to_datetime(d["Sampling Date"])
    d = d.sort_values("Data").drop_duplicates(subset="Data", keep="first")
    return d[["Data", "Qual", "Result", "MDL", "ML", "RL"]]


def calcular_ros_helsel(bod_mensal: pd.DataFrame) -> float:
    """ROS (Regression on Order Statistics) para MDL unico: regressao dos
    valores detectados contra seus quantis normais esperados (posicao de
    plotagem de Hazen), extrapolada para estimar o valor esperado da fracao
    censurada. Retorna o valor substituto unico (media da fracao censurada
    estimada) a ser usado em todas as observacoes ND."""
    n_total = len(bod_mensal)
    detectados = np.sort(bod_mensal.loc[bod_mensal["Qual"] == "=", "Result"].values)
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
    return float(pred_cens.mean())


def tratar_bod(bod_mensal: pd.DataFrame) -> pd.DataFrame:
    """Aplica os tres tratamentos de ND (A: MDL/2, B: zero, F: ROS/Helsel) ao
    BOD mensal. Linhas com Qual == '=' usam o Result reportado nos tres casos."""
    d = bod_mensal.copy()
    is_nd = d["Qual"] == "ND"
    valor_ros = calcular_ros_helsel(bod_mensal)

    d["BOD_mgL_mdl2"] = d["Result"]
    d.loc[is_nd, "BOD_mgL_mdl2"] = d.loc[is_nd, "MDL"] / 2

    d["BOD_mgL_zero"] = d["Result"]
    d.loc[is_nd, "BOD_mgL_zero"] = 0.0

    d["BOD_mgL_ros"] = d["Result"]
    d.loc[is_nd, "BOD_mgL_ros"] = valor_ros

    d["BOD_foi_ND"] = is_nd
    return d[["Data", "BOD_foi_ND", "BOD_mgL_mdl2", "BOD_mgL_zero", "BOD_mgL_ros"]]


def construir_datasets():
    tds = serie_mensal_canonica(carregar_csv("TDS.csv"), PARAMETROS["TDS"])
    chl = serie_mensal_canonica(carregar_csv("Chloride.csv"), PARAMETROS["Chloride"])
    amm = serie_mensal_canonica(carregar_csv("Ammonia.csv"), PARAMETROS["Ammonia"])
    bod = serie_mensal_canonica(carregar_csv("BOD.csv"), PARAMETROS["BOD"])

    tds = tds.rename(columns={"Result": "TDS_mgL"})[["Data", "TDS_mgL"]]
    chl = chl.rename(columns={"Result": "Chloride_mgL"})[["Data", "Chloride_mgL"]]
    amm = amm.rename(columns={"Result": "Ammonia_mgL"})[["Data", "Ammonia_mgL"]]
    bod_tratado = tratar_bod(bod)

    base = tds.merge(chl, on="Data", how="outer")
    base = base.merge(amm, on="Data", how="outer")
    base = base.merge(bod_tratado, on="Data", how="outer")
    base = base.sort_values("Data").reset_index(drop=True)

    colunas_comuns = ["Data", "TDS_mgL", "Chloride_mgL", "Ammonia_mgL", "BOD_foi_ND"]

    dataset_a = base[colunas_comuns + ["BOD_mgL_mdl2"]].rename(
        columns={"BOD_mgL_mdl2": "BOD_mgL"}
    )
    dataset_b = base[colunas_comuns + ["BOD_mgL_zero"]].rename(
        columns={"BOD_mgL_zero": "BOD_mgL"}
    )
    dataset_c = base[colunas_comuns + ["BOD_mgL_ros"]].rename(
        columns={"BOD_mgL_ros": "BOD_mgL"}
    )

    return dataset_a, dataset_b, dataset_c, base


def main():
    dataset_a, dataset_b, dataset_c, base = construir_datasets()

    dataset_a.to_csv("dataset_canonico_bod_mdl2.csv", sep=";", decimal=",", index=False)
    dataset_b.to_csv("dataset_canonico_bod_zero.csv", sep=";", decimal=",", index=False)
    dataset_c.to_csv("dataset_canonico_bod_ros.csv", sep=";", decimal=",", index=False)

    print("Dataset A (BOD ND = MDL/2):      dataset_canonico_bod_mdl2.csv")
    print("Dataset B (BOD ND = 0):          dataset_canonico_bod_zero.csv")
    print("Dataset F (BOD ND = ROS/Helsel): dataset_canonico_bod_ros.csv")
    print()
    print(f"Linhas (meses): {len(base)}  |  Periodo: {base['Data'].min().date()} a {base['Data'].max().date()}")
    print(f"Meses com BOD ND: {int(base['BOD_foi_ND'].sum())} / {base['BOD_foi_ND'].notna().sum()}")
    print()
    print("Valores ausentes por coluna (dataset A):")
    print(dataset_a.isna().sum())


if __name__ == "__main__":
    main()
