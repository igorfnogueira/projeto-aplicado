"""
Matriz de 9 testes de sensibilidade no tratamento de dados
(prompt_tratamento_e_metodos.md Etapa 2; plano_projeto_TDS.md secao 1.4) --
roda ANTES de fixar qualquer tratamento padrao. Cada variante e uma run
MLflow separada; a saida e uma tabela consolidada "decisao x efeito na
tendencia" (ou na correlacao TDS-BOD, no item 1) para o USUARIO decidir --
este script nao fixa nenhum tratamento novo como padrao sozinho.

Metrica de saida: inclinacao de Theil-Sen (mg/L/ano) + p-valor da tendencia
de TDS, exceto no item 1 (ND do BOD), cuja metrica e a correlacao de Pearson
TDS-BOD destendenciada (e isso, nao a tendencia de TDS, que o tratamento de
ND do BOD afeta).
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymannkendall as mk
from lifelines import KaplanMeierFitter
from lifelines.utils import restricted_mean_survival_time
from scipy import stats, optimize
from statsmodels.tsa.seasonal import STL

from script_00_preprocessamento import carregar_csv, serie_mensal_canonica, construir_datasets, PARAMETROS, LOCATIONS_EFLUENTE, calcular_ros_helsel
from utils.experiment_tracking import iniciar_run, logar_metricas

warnings.filterwarnings("ignore")

RESULTADOS_CSV = "matriz_sensibilidade_resultados.csv"
RESULTADOS_JSON = "matriz_sensibilidade_resultados.json"
FIGURA_PATH = "Artigo/images/matriz-sensibilidade.png"
MDL_BOD = 3.0


def theil_sen_trend(datas: pd.Series, valores: np.ndarray) -> dict:
    t = (pd.to_datetime(datas) - pd.to_datetime(datas).iloc[0]).dt.days / 365.25
    slope, intercept, lo, hi = stats.theilslopes(valores, t.values, alpha=0.90)
    tau, p = stats.kendalltau(t.values, valores)
    return {"slope_mgL_ano": float(slope), "pvalor": float(p), "n": len(valores)}


def residuos_ols(t: np.ndarray, y: np.ndarray) -> np.ndarray:
    reg = stats.linregress(t, y)
    return y - (reg.intercept + reg.slope * t)


def correlacao_tds_bod_destend(tds: pd.DataFrame, bod_col: pd.Series, bod_datas: pd.Series) -> dict:
    d = pd.DataFrame({"Data": bod_datas, "BOD_mgL": bod_col}).merge(tds, on="Data", how="inner").dropna()
    t = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    x_resid = residuos_ols(t.values, d["TDS_mgL"].values)
    y_resid = residuos_ols(t.values, d["BOD_mgL"].values)
    r, p = stats.pearsonr(x_resid, y_resid)
    return {"correlacao_r": float(r), "pvalor": float(p), "n": len(d)}


def carregar_tds_base():
    _, _, _, base = construir_datasets()
    return base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)


# --------------------------------------------------------------------------
# Item 1 -- ND do BOD: A/MDL-2, B/zero, F/Kaplan-Meier, G/ROS, H/MLE lognormal
# --------------------------------------------------------------------------

def calcular_km_valor_substituto(detectados: np.ndarray, n_cens: int, n_total: int, mdl: float) -> float:
    C = float(detectados.max()) + mdl  # deslocamento para manter duracoes >=0 no KM
    T = np.concatenate([C - detectados, np.full(n_cens, C - mdl)])
    E = np.concatenate([np.ones(len(detectados)), np.zeros(n_cens)])
    kmf = KaplanMeierFitter()
    kmf.fit(T, event_observed=E)
    rmst = restricted_mean_survival_time(kmf, t=T.max())
    media_populacao = C - rmst
    soma_detectados = detectados.sum()
    return float((media_populacao * n_total - soma_detectados) / n_cens)


def calcular_mle_valor_substituto(detectados: np.ndarray, n_cens: int, mdl: float) -> float:
    def neg_log_lik(params):
        mu, log_sigma = params
        sigma = np.exp(log_sigma)
        ll_det = stats.norm.logpdf(np.log(detectados), mu, sigma).sum()
        p_cens = max(stats.norm.cdf(np.log(mdl), mu, sigma), 1e-10)
        return -(ll_det + n_cens * np.log(p_cens))

    chute = [np.log(detectados.mean()), np.log(detectados.std())]
    res = optimize.minimize(neg_log_lik, chute, method="Nelder-Mead")
    mu, sigma = res.x[0], np.exp(res.x[1])
    z1 = (np.log(mdl) - mu - sigma ** 2) / sigma
    z2 = (np.log(mdl) - mu) / sigma
    return float(np.exp(mu + sigma ** 2 / 2) * stats.norm.cdf(z1) / stats.norm.cdf(z2))


def rodar_item1_nd_bod(tds_base: pd.DataFrame) -> list:
    bod = serie_mensal_canonica(carregar_csv("BOD.csv"), PARAMETROS["BOD"])
    is_nd = bod["Qual"] == "ND"
    detectados = bod.loc[~is_nd, "Result"].values
    n_cens = int(is_nd.sum())
    n_total = len(bod)

    valor_km = calcular_km_valor_substituto(detectados, n_cens, n_total, MDL_BOD)
    valor_mle = calcular_mle_valor_substituto(detectados, n_cens, MDL_BOD)
    valor_ros = float(calcular_ros_helsel(bod))

    variantes = {
        "A_mdl_div_2": 1.5, "B_zero": 0.0,
        "F_kaplan_meier": valor_km, "G_ros_helsel": valor_ros, "H_mle_lognormal": valor_mle,
    }
    linhas = []
    for nome, valor in variantes.items():
        bod_col = bod["Result"].copy()
        bod_col[is_nd] = valor
        r = correlacao_tds_bod_destend(tds_base, bod_col, bod["Data"])
        linhas.append({"item": "1_nd_bod", "variante": nome, "valor_substituto": round(valor, 3),
                        "metrica": "correlacao_tds_bod_destend_r", "valor_metrica": r["correlacao_r"],
                        "pvalor": r["pvalor"], "n": r["n"]})
    return linhas


# --------------------------------------------------------------------------
# Item 2 -- quebra EFF-001 -> EFF-001A
# --------------------------------------------------------------------------

def rodar_item2_quebra_localizacao(tds_base: pd.DataFrame) -> list:
    df = carregar_csv("TDS.csv")
    raw = df[(df["Calculated Method"] == "Monthly Average (Mean)") & (df["Units"] == "mg/L")
             & (df["Location"].isin(LOCATIONS_EFLUENTE))].copy()
    raw["Data"] = pd.to_datetime(raw["Sampling Date"])
    data_transicao = raw.loc[raw["Location"] == "EFF-001", "Data"].max()

    completa = theil_sen_trend(tds_base["Data"], tds_base["TDS_mgL"].values)
    so_eff001a = tds_base[tds_base["Data"] > data_transicao]
    apenas_novo = theil_sen_trend(so_eff001a["Data"], so_eff001a["TDS_mgL"].values)

    return [
        {"item": "2_quebra_localizacao", "variante": "serie_completa", "metrica": "slope_mgL_ano",
         "valor_metrica": completa["slope_mgL_ano"], "pvalor": completa["pvalor"], "n": completa["n"]},
        {"item": "2_quebra_localizacao", "variante": f"so_apos_{data_transicao.date()}", "metrica": "slope_mgL_ano",
         "valor_metrica": apenas_novo["slope_mgL_ano"], "pvalor": apenas_novo["pvalor"], "n": apenas_novo["n"]},
    ]


# --------------------------------------------------------------------------
# Item 3 -- mudanca de MDL/metodo analitico
# --------------------------------------------------------------------------

def rodar_item3_mudanca_mdl() -> list:
    df = carregar_csv("TDS.csv")
    raw = df[(df["Analytical Method"].notna()) & (df["Location"].isin(LOCATIONS_EFLUENTE))].copy()
    raw["Data"] = pd.to_datetime(raw["Sampling Date"])
    raw = raw.sort_values("Data").reset_index(drop=True)
    raw["regime_id"] = (raw["MDL"] != raw["MDL"].shift()).cumsum()

    linhas = []
    regimes = list(raw.groupby("regime_id"))
    for i in range(len(regimes) - 1):
        _, seg_a = regimes[i]
        _, seg_b = regimes[i + 1]
        if len(seg_a) < 3 or len(seg_b) < 3:
            continue
        stat, p = stats.mannwhitneyu(seg_a["Result"], seg_b["Result"], alternative="two-sided")
        linhas.append({
            "item": "3_mudanca_mdl", "variante": f"MDL{seg_a['MDL'].iloc[0]:.0f}_para_MDL{seg_b['MDL'].iloc[0]:.0f}_em_{seg_b['Data'].iloc[0].date()}",
            "metrica": "mannwhitney_p_nivel_TDS", "valor_metrica": float(stat), "pvalor": float(p),
            "n": len(seg_a) + len(seg_b),
        })
    return linhas


# --------------------------------------------------------------------------
# Item 4 -- Monthly Average pronto vs. reagregado das amostras brutas
# --------------------------------------------------------------------------

def rodar_item4_reagregacao(tds_base: pd.DataFrame) -> list:
    df = carregar_csv("TDS.csv")
    raw = df[(df["Analytical Method"].notna()) & (df["Location"].isin(LOCATIONS_EFLUENTE)) & (df["Units"] == "mg/L")].copy()
    raw["Data"] = pd.to_datetime(raw["Sampling Date"])
    raw["AnoMes"] = raw["Data"].dt.to_period("M")
    reagregado = raw.groupby("AnoMes")["Result"].mean().reset_index()
    reagregado["Data"] = reagregado["AnoMes"].dt.to_timestamp(how="end").dt.normalize()

    pronto = tds_base.copy()
    pronto["AnoMes"] = pronto["Data"].dt.to_period("M")
    comp = pronto.merge(reagregado, on="AnoMes", suffixes=("_pronto", "_reagregado")).dropna()
    diff = comp["TDS_mgL"] - comp["Result"]

    t_reag = theil_sen_trend(comp["Data_reagregado"], comp["Result"].values)
    t_pronto = theil_sen_trend(comp["Data_pronto"], comp["TDS_mgL"].values)

    return [
        {"item": "4_reagregacao", "variante": "monthly_average_pronto", "metrica": "slope_mgL_ano",
         "valor_metrica": t_pronto["slope_mgL_ano"], "pvalor": t_pronto["pvalor"], "n": t_pronto["n"]},
        {"item": "4_reagregacao", "variante": "reagregado_amostras_brutas", "metrica": "slope_mgL_ano",
         "valor_metrica": t_reag["slope_mgL_ano"], "pvalor": t_reag["pvalor"], "n": t_reag["n"]},
        {"item": "4_reagregacao", "variante": "diferenca_media_absoluta", "metrica": "diff_mgL",
         "valor_metrica": float(diff.abs().mean()), "pvalor": float("nan"), "n": len(comp)},
    ]


# --------------------------------------------------------------------------
# Item 5 -- agregacao anual: media/mediana x ano civil/hidrologico
# --------------------------------------------------------------------------

def rodar_item5_agregacao_anual(tds_base: pd.DataFrame) -> list:
    d = tds_base.copy()
    d["ano_civil"] = d["Data"].dt.year
    d["ano_hidrologico"] = (d["Data"] + pd.DateOffset(months=3)).dt.year  # desloca out-set -> mesmo "ano"

    linhas = []
    for nome_agg, func_agg in [("media", "mean"), ("mediana", "median")]:
        for nome_ano, col_ano in [("ano_civil", "ano_civil"), ("ano_hidrologico", "ano_hidrologico")]:
            anual = d.groupby(col_ano)["TDS_mgL"].agg(func_agg)
            anual = anual[anual.index.isin(d[col_ano].value_counts()[lambda s: s >= 6].index)]  # exige >=6 meses no ano
            if len(anual) < 5:
                continue
            t = np.arange(len(anual))
            slope, intercept, lo, hi = stats.theilslopes(anual.values, t, alpha=0.90)
            tau, p = stats.kendalltau(t, anual.values)
            linhas.append({
                "item": "5_agregacao_anual", "variante": f"{nome_agg}_{nome_ano}", "metrica": "slope_mgL_ano",
                "valor_metrica": float(slope), "pvalor": float(p), "n": len(anual),
            })
    return linhas


# --------------------------------------------------------------------------
# Item 6 -- outliers
# --------------------------------------------------------------------------

def rodar_item6_outliers(tds_base: pd.DataFrame) -> list:
    y = tds_base["TDS_mgL"].values
    datas = tds_base["Data"]

    completa = theil_sen_trend(datas, y)

    lo, hi = np.percentile(y, [5, 95])
    y_wins = np.clip(y, lo, hi)
    winsor = theil_sen_trend(datas, y_wins)

    s = pd.Series(y, index=pd.DatetimeIndex(datas, freq="ME"))
    stl = STL(s, period=12, robust=True).fit()
    resid_std = stl.resid.std()
    mask = stl.resid.abs() <= 3 * resid_std
    sem_outliers = theil_sen_trend(datas[mask.values], y[mask.values])

    return [
        {"item": "6_outliers", "variante": "completa", "metrica": "slope_mgL_ano",
         "valor_metrica": completa["slope_mgL_ano"], "pvalor": completa["pvalor"], "n": completa["n"]},
        {"item": "6_outliers", "variante": "winsorizada_5_95", "metrica": "slope_mgL_ano",
         "valor_metrica": winsor["slope_mgL_ano"], "pvalor": winsor["pvalor"], "n": winsor["n"]},
        {"item": "6_outliers", "variante": f"stl_residuo_3sigma_removidos_{int((~mask).sum())}pts", "metrica": "slope_mgL_ano",
         "valor_metrica": sem_outliers["slope_mgL_ano"], "pvalor": sem_outliers["pvalor"], "n": sem_outliers["n"]},
    ]


# --------------------------------------------------------------------------
# Item 7 -- meses faltantes
# --------------------------------------------------------------------------

def rodar_item7_meses_faltantes(tds_base: pd.DataFrame) -> list:
    esperado = pd.date_range(tds_base["Data"].min(), tds_base["Data"].max(), freq="ME")
    faltantes = len(esperado) - tds_base["Data"].nunique()
    return [{
        "item": "7_meses_faltantes", "variante": "verificacao_unica",
        "metrica": "n_meses_faltantes", "valor_metrica": float(faltantes), "pvalor": float("nan"),
        "n": len(tds_base),
    }]


# --------------------------------------------------------------------------
# Item 8 -- autocorrelacao no Mann-Kendall
# --------------------------------------------------------------------------

def rodar_item8_autocorrelacao_mk(tds_base: pd.DataFrame) -> list:
    y = tds_base["TDS_mgL"].values
    testes = {
        "MK_simples": mk.original_test,
        "hamed_rao_correcao_variancia": mk.hamed_rao_modification_test,
        "pre_whitening": mk.pre_whitening_modification_test,
        "trend_free_pre_whitening": mk.trend_free_pre_whitening_modification_test,
    }
    linhas = []
    for nome, func in testes.items():
        r = func(y)
        linhas.append({"item": "8_autocorrelacao_mk", "variante": nome, "metrica": "slope_mgL_ano",
                        "valor_metrica": float(r.slope * 12), "pvalor": float(r.p), "n": len(y)})
    r_seas = mk.seasonal_test(y, period=12)
    linhas.append({"item": "8_autocorrelacao_mk", "variante": "seasonal_kendall", "metrica": "slope_mgL_ano",
                   "valor_metrica": float(r_seas.slope), "pvalor": float(r_seas.p), "n": len(y)})
    return linhas


# --------------------------------------------------------------------------
# Item 9 -- escala bruta vs. log
# --------------------------------------------------------------------------

def rodar_item9_escala(tds_base: pd.DataFrame) -> list:
    bruta = theil_sen_trend(tds_base["Data"], tds_base["TDS_mgL"].values)
    log_y = np.log(tds_base["TDS_mgL"].values)
    t = (tds_base["Data"] - tds_base["Data"].iloc[0]).dt.days / 365.25
    slope_log, intercept_log, lo, hi = stats.theilslopes(log_y, t.values, alpha=0.90)
    tau, p_log = stats.kendalltau(t.values, log_y)
    pct_ano = (np.exp(slope_log) - 1) * 100

    return [
        {"item": "9_escala", "variante": "bruta_mgL_ano", "metrica": "slope_mgL_ano",
         "valor_metrica": bruta["slope_mgL_ano"], "pvalor": bruta["pvalor"], "n": bruta["n"]},
        {"item": "9_escala", "variante": "log_pct_ano", "metrica": "pct_ano",
         "valor_metrica": float(pct_ano), "pvalor": float(p_log), "n": len(tds_base)},
    ]


def gerar_figura(df: pd.DataFrame):
    item8 = df[df["item"] == "8_autocorrelacao_mk"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cores = ["tab:green" if p < 0.05 else "tab:red" for p in item8["pvalor"]]
    ax.bar(item8["variante"], item8["pvalor"], color=cores)
    ax.axhline(0.05, color="black", linestyle="--", linewidth=1, label="α=0,05")
    ax.set_ylabel("p-valor")
    ax.set_title("Item 8 — p-valor da tendência de TDS sob correção de autocorrelação")
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def main():
    tds_base = carregar_tds_base()
    print(f"Serie TDS base: {len(tds_base)} meses ({tds_base['Data'].min().date()} a {tds_base['Data'].max().date()})")
    print()

    todas_linhas = []
    with iniciar_run("matriz_sensibilidade", "script_17_matriz_sensibilidade", params={"n_itens": 9}):
        for nome_item, func in [
            ("1_nd_bod", lambda: rodar_item1_nd_bod(tds_base)),
            ("2_quebra_localizacao", lambda: rodar_item2_quebra_localizacao(tds_base)),
            ("3_mudanca_mdl", rodar_item3_mudanca_mdl),
            ("4_reagregacao", lambda: rodar_item4_reagregacao(tds_base)),
            ("5_agregacao_anual", lambda: rodar_item5_agregacao_anual(tds_base)),
            ("6_outliers", lambda: rodar_item6_outliers(tds_base)),
            ("7_meses_faltantes", lambda: rodar_item7_meses_faltantes(tds_base)),
            ("8_autocorrelacao_mk", lambda: rodar_item8_autocorrelacao_mk(tds_base)),
            ("9_escala", lambda: rodar_item9_escala(tds_base)),
        ]:
            print(f"=== Item {nome_item} ===")
            linhas = func()
            for l in linhas:
                print(f"  {l['variante']:45s} {l['metrica']:28s} = {l['valor_metrica']:.4f}   p={l['pvalor']}")
            todas_linhas.extend(linhas)
            print()

        df = pd.DataFrame(todas_linhas)
        df["data_execucao"] = datetime.now().isoformat(timespec="seconds")
        df.to_csv(RESULTADOS_CSV, index=False)
        df.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

        gerar_figura(df)

        metricas = {}
        for _, row in df.iterrows():
            chave = f"{row['item']}__{row['variante']}"[:250]
            if pd.notna(row["valor_metrica"]):
                metricas[chave] = row["valor_metrica"]
        logar_metricas(metricas)


if __name__ == "__main__":
    main()
