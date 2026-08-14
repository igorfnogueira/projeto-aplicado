"""
Passo 1 da nova etapa (prompt_pdsi_regimes.md): testa se os ciclos de TDS do
LAGWRP (D-14, Artigo/DECISOES.md) sao explicados por ciclos de seca (PDSI),
antes de investir em WRTDS/balanco de massa/busca de estacao comparadora.

Fonte dos dados de seca: NOAA NCEI nClimDiv (mesmo indice PMDI/PDSI usado
pelo estudo SCSC/DBS&A 2018, ver material_apoio_referencias.md Tema 9).
Arquivos brutos baixados desta sessao:
  - pdsi_raw_climdiv.txt        (climdiv-pdsidv, divisional)
  - pdsi_raw_climdiv_state.txt  (climdiv-pdsist, estadual)

Codigos confirmados na documentacao oficial (nao assumidos):
  - California = state code 04 (divisional-readme.txt, STATE CODE TABLE)
  - Los Angeles County (FIPS 06037) -> climdiv 0406 -> divisao 06
    (county-to-climdivs.txt: "06037 04037 0406")
  - Sacramento/Sierra Norte (FIPS 06067 Sacramento, 06007 Butte -- watershed
    de origem do State Water Project via Feather River/Oroville Dam) ->
    climdiv 0402 -> divisao 02 (county-to-climdivs.txt: "06067 04067 0402",
    "06007 04007 0402")
  - Estadual: prefixo de registro "004005" (state-readme.txt FILE FORMAT:
    state-code 3 digitos "004" + divisao "0" [area-averaged] + elemento "05"=PDSI)
  - Divisional: prefixo "04" + divisao (2 digitos) + "05" (divisional-readme.txt)

Tres series testam mecanismos diferentes (D-29): se a seca do NORTE (Sacramento,
origem do SWP) explicar o TDS do LAGWRP melhor que a seca LOCAL (LA), isso e
evidencia a favor do mecanismo "agua de origem" sobre o mecanismo "conservacao
local" da Nature (2020).
"""

import json
import re
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from script_00_preprocessamento import construir_datasets
from script_07_analise_estrutura_serie import pettitt_test
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

warnings.filterwarnings("ignore")

RAW_STATE = "pdsi_raw_climdiv_state.txt"
RAW_DIV = "pdsi_raw_climdiv.txt"

SERIES_ALVO = {
    "california_estadual": {"tipo": "estado", "prefixo": "004005", "arquivo_saida": "pdsi_california_estadual.csv"},
    "los_angeles_divisao6": {"tipo": "divisao", "prefixo": "040605", "arquivo_saida": "pdsi_los_angeles_divisao.csv"},
    "sacramento_divisao2": {"tipo": "divisao", "prefixo": "040205", "arquivo_saida": "pdsi_sacramento_divisao.csv"},
}

REGIMES = [
    ("2011-01-01", "2012-01-31", "baseline_2011"),
    ("2012-02-01", "2015-12-31", "alta_seca1_2012_2015"),
    ("2016-01-01", "2019-12-31", "queda_2016_2019"),
    ("2020-01-01", "2022-12-31", "alta_seca2_2020_2022"),
    ("2023-01-01", "2026-12-31", "estavel_2023_hoje"),
]

RESULTADOS_CSV = "pdsi_regimes_resultados.csv"
RESULTADOS_JSON = "pdsi_regimes_resultados.json"
FIGURA_OVERLAY = "Artigo/images/pdsi-vs-tds-regimes.png"
FIGURA_CCF = "Artigo/images/pdsi-tds-correlacao-defasagem.png"
MAX_LAG_MESES = 36


def parse_fixed_width_climdiv(caminho: str, prefixo: str) -> pd.Series:
    """Parseia o formato de largura fixa do nClimDiv (state-readme.txt /
    divisional-readme.txt FILE FORMAT): prefixo (codigo+elemento) + ano (4)
    + 12 valores mensais de 7 colunas cada. -99.99 = faltante."""
    linhas = []
    with open(caminho, "r") as f:
        for linha in f:
            if not linha.startswith(prefixo):
                continue
            ano = int(linha[len(prefixo):len(prefixo) + 4])
            resto = linha[len(prefixo) + 4:]
            valores = [resto[i:i + 7] for i in range(0, 84, 7)]
            for mes, v in enumerate(valores, start=1):
                v = v.strip()
                if v == "" or v == "-99.99":
                    continue
                linhas.append({"Data": pd.Timestamp(year=ano, month=mes, day=1) + pd.offsets.MonthEnd(0),
                                "pdsi": float(v)})
    df = pd.DataFrame(linhas).sort_values("Data").drop_duplicates(subset="Data")
    return df.set_index("Data")["pdsi"]


def carregar_series_pdsi() -> pd.DataFrame:
    series = {}
    for nome, cfg in SERIES_ALVO.items():
        arquivo = RAW_STATE if cfg["tipo"] == "estado" else RAW_DIV
        s = parse_fixed_width_climdiv(arquivo, cfg["prefixo"])
        s.to_csv(cfg["arquivo_saida"], header=["pdsi"])
        series[nome] = s
        print(f"{nome}: {len(s)} meses ({s.index.min().date()} a {s.index.max().date()}), "
              f"salvo em {cfg['arquivo_saida']}")
    df = pd.DataFrame(series)
    return df


def carregar_tds() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["Data"] = pd.to_datetime(d["Data"]) + pd.offsets.MonthEnd(0)
    return d.set_index("Data")["TDS_mgL"]


def carregar_vazao() -> pd.Series:
    v = pd.read_csv("vazao_reconstruida_serie.csv", parse_dates=["Data"])
    v["Data"] = v["Data"] + pd.offsets.MonthEnd(0)
    return v.set_index("Data")["vazao_mgd_TDS"]


# ---------------------------------------------------------------------------
# 2.1 -- alinhamento e figura de sobreposicao
# ---------------------------------------------------------------------------

def gerar_figura_overlay(tds: pd.Series, pdsi_df: pd.DataFrame):
    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    ax1.plot(tds.index, tds.values, color="black", linewidth=1.3, label="TDS (mg/L)")
    ax1.set_ylabel("TDS (mg/L)")
    for data_ini, data_fim, nome in REGIMES:
        ax1.axvspan(pd.Timestamp(data_ini), pd.Timestamp(data_fim), alpha=0.05, color="tab:red")

    ax2 = ax1.twinx()
    cores = {"california_estadual": "tab:blue", "los_angeles_divisao6": "tab:orange", "sacramento_divisao2": "tab:green"}
    for col in pdsi_df.columns:
        s = pdsi_df[col].reindex(tds.index)
        ax2.plot(s.index, -s.values, linestyle="--", linewidth=1, alpha=0.8, color=cores.get(col), label=f"PDSI invertido ({col})")
    ax2.set_ylabel("PDSI invertido (seco ↑)")
    ax2.axhline(0, color="gray", linewidth=0.5)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="upper left")
    ax1.set_title("TDS observado × PDSI invertido (hipótese: espelhamento)")
    fig.tight_layout()
    fig.savefig(FIGURA_OVERLAY, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_OVERLAY}")


# ---------------------------------------------------------------------------
# 2.2 -- correlacao cruzada com defasagem + graus de liberdade efetivos
# ---------------------------------------------------------------------------

def n_efetivo(x: np.ndarray, y: np.ndarray, max_lag_acf: int = 20) -> float:
    """Graus de liberdade efetivos sob autocorrelacao (Pyper & Peterman,
    1998; formula de Bartlett truncada): penaliza o n nominal pela soma dos
    produtos das autocorrelacoes de x e y, porque series autocorrelacionadas
    tem menos informacao independente do que n sugere (mesma armadilha
    documentada em D-15 para o Mann-Kendall mensal)."""
    n = len(x)
    max_lag_acf = min(max_lag_acf, n // 4)
    x_c, y_c = x - x.mean(), y - y.mean()

    def acf(v, k):
        return float(np.corrcoef(v[:-k], v[k:])[0, 1]) if k > 0 else 1.0

    soma = 0.0
    for k in range(1, max_lag_acf + 1):
        soma += (1 - k / n) * acf(x_c, k) * acf(y_c, k)
    denom = 1 + 2 * soma
    n_eff = n / denom if denom > 0 else float(n)
    return float(np.clip(n_eff, 3, n))


def correlacao_cruzada_defasagem(tds: pd.Series, pdsi: pd.Series, max_lag: int = MAX_LAG_MESES) -> pd.DataFrame:
    """PDSI defasado por `lag` meses vs TDS contemporaneo: lag positivo =
    PDSI de `lag` meses atras. Reporta correlacao bruta e sobre as series
    diferenciadas (1a diferenca -- remove tendencia/nivel comum, mitiga
    correlacao espuria de duas series autocorrelacionadas nao-estacionarias)."""
    df = pd.DataFrame({"tds": tds, "pdsi": pdsi}).dropna()
    tds_d = df["tds"].diff().dropna()
    pdsi_d = df["pdsi"].diff().dropna()

    linhas = []
    for lag in range(0, max_lag + 1):
        pdsi_lag = df["pdsi"].shift(lag)
        par = pd.DataFrame({"tds": df["tds"], "pdsi_lag": pdsi_lag}).dropna()
        if len(par) < 24:
            continue
        r_bruta, _ = stats.pearsonr(par["tds"], par["pdsi_lag"])
        n_eff_bruta = n_efetivo(par["tds"].values, par["pdsi_lag"].values)
        t_stat = r_bruta * np.sqrt(max(n_eff_bruta - 2, 1) / max(1 - r_bruta ** 2, 1e-9))
        p_bruta = float(2 * (1 - stats.t.cdf(abs(t_stat), max(n_eff_bruta - 2, 1))))

        pdsi_lag_d = pdsi_d.shift(lag)
        par_d = pd.DataFrame({"tds_d": tds_d, "pdsi_lag_d": pdsi_lag_d}).dropna()
        if len(par_d) >= 24:
            r_dest, _ = stats.pearsonr(par_d["tds_d"], par_d["pdsi_lag_d"])
            n_eff_dest = n_efetivo(par_d["tds_d"].values, par_d["pdsi_lag_d"].values)
            t_stat_d = r_dest * np.sqrt(max(n_eff_dest - 2, 1) / max(1 - r_dest ** 2, 1e-9))
            p_dest = float(2 * (1 - stats.t.cdf(abs(t_stat_d), max(n_eff_dest - 2, 1))))
        else:
            r_dest, p_dest, n_eff_dest = float("nan"), float("nan"), float("nan")

        linhas.append({"lag_meses": lag, "r_bruta": r_bruta, "p_bruta_dof_efetivo": p_bruta,
                        "n_efetivo_bruta": n_eff_bruta, "r_destendenciada": r_dest,
                        "p_destendenciada_dof_efetivo": p_dest, "n_efetivo_destendenciada": n_eff_dest,
                        "n_par": len(par)})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 2.3 -- changepoints no PDSI, independentes das datas do TDS
# ---------------------------------------------------------------------------

def segmentacao_binaria_pettitt(y: np.ndarray, datas: pd.DatetimeIndex, min_segmento: int = 24, alpha: float = 0.05, prof_max: int = 4) -> list:
    """Deteccao de multiplos changepoints via segmentacao binaria recursiva
    com o teste de Pettitt (script_07): acha a quebra mais forte, testa
    significancia, e repete dentro de cada metade -- sem usar as datas do
    TDS como informacao (a serie de entrada e so o PDSI)."""
    resultados = []

    def recursao(inicio, fim, profundidade):
        if fim - inicio < 2 * min_segmento or profundidade > prof_max:
            return
        _, idx_local, p = pettitt_test(y[inicio:fim])
        if p >= alpha:
            return
        idx_global = inicio + idx_local
        resultados.append({"data": datas[idx_global], "p_valor": p, "profundidade": profundidade})
        recursao(inicio, idx_global, profundidade + 1)
        recursao(idx_global, fim, profundidade + 1)

    recursao(0, len(y), 0)
    return sorted(resultados, key=lambda r: r["data"])


def comparar_changepoints(changepoints: list, datas_esperadas=("2012-01-01", "2015-06-01", "2019-06-01", "2022-06-01")) -> pd.DataFrame:
    linhas = []
    for data_esp in datas_esperadas:
        data_esp = pd.Timestamp(data_esp)
        if changepoints:
            mais_proxima = min(changepoints, key=lambda c: abs((c["data"] - data_esp).days))
            diff_meses = (mais_proxima["data"] - data_esp).days / 30.44
        else:
            mais_proxima, diff_meses = None, float("nan")
        linhas.append({
            "virada_esperada_tds": str(data_esp.date()),
            "changepoint_pdsi_mais_proximo": str(mais_proxima["data"].date()) if mais_proxima else None,
            "diferenca_meses": diff_meses,
            "p_valor_changepoint": mais_proxima["p_valor"] if mais_proxima else None,
            "dentro_de_12_meses": bool(abs(diff_meses) <= 12) if not np.isnan(diff_meses) else False,
        })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 2.4 -- decomposicao LMG (2 preditores: PDSI defasado e vazao)
# ---------------------------------------------------------------------------

def lmg_2_preditores(y: np.ndarray, x1: np.ndarray, x2: np.ndarray) -> dict:
    """LMG (Lindeman, Merenda & Gold) para exatamente 2 preditores: formula
    fechada, media sobre as 2 ordens possiveis de entrada (equivalente ao
    pacote R `relaimpo`, metodo lmg, usado pelo SCSC/DBS&A 2018 -- Tema 9.5).
    LMG_x1 = 0.5*(R2(x1) + [R2(x1,x2) - R2(x2)])
    LMG_x2 = 0.5*(R2(x2) + [R2(x1,x2) - R2(x1)])
    """
    def r2(*xs):
        X = sm.add_constant(np.column_stack(xs))
        return sm.OLS(y, X).fit().rsquared

    r2_x1, r2_x2, r2_x1x2 = r2(x1), r2(x2), r2(x1, x2)
    lmg_x1 = 0.5 * (r2_x1 + (r2_x1x2 - r2_x2))
    lmg_x2 = 0.5 * (r2_x2 + (r2_x1x2 - r2_x1))
    total = lmg_x1 + lmg_x2
    return {
        "r2_total": r2_x1x2, "r2_so_pdsi": r2_x1, "r2_so_vazao": r2_x2,
        "lmg_pdsi": lmg_x1, "lmg_vazao": lmg_x2,
        "pct_pdsi": 100 * lmg_x1 / total if total > 0 else float("nan"),
        "pct_vazao": 100 * lmg_x2 / total if total > 0 else float("nan"),
    }


def decompor_mecanismos(tds: pd.Series, pdsi: pd.Series, vazao: pd.Series, melhor_lag: int) -> dict:
    df = pd.DataFrame({"tds": tds, "pdsi_lag": pdsi.shift(melhor_lag), "vazao": vazao}).dropna()
    resultado = lmg_2_preditores(df["tds"].values, df["pdsi_lag"].values, df["vazao"].values)
    resultado["n"] = len(df)
    resultado["lag_pdsi_usado_meses"] = melhor_lag

    X = sm.add_constant(df[["pdsi_lag", "vazao"]])
    modelo = sm.OLS(df["tds"], X).fit()
    resultado["coef_pdsi"] = float(modelo.params["pdsi_lag"])
    resultado["p_pdsi"] = float(modelo.pvalues["pdsi_lag"])
    resultado["coef_vazao"] = float(modelo.params["vazao"])
    resultado["p_vazao"] = float(modelo.pvalues["vazao"])
    return resultado


# ---------------------------------------------------------------------------
# 2.5 -- regressao por regime
# ---------------------------------------------------------------------------

def regressao_por_regime(tds: pd.Series, pdsi: pd.Series, melhor_lag: int) -> dict:
    df = pd.DataFrame({"tds": tds, "pdsi_lag": pdsi.shift(melhor_lag)}).dropna()
    df["regime"] = "fora"
    for data_ini, data_fim, nome in REGIMES:
        mask = (df.index >= data_ini) & (df.index <= data_fim)
        df.loc[mask, "regime"] = nome
    dummies = pd.get_dummies(df["regime"], drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([df[["pdsi_lag"]], dummies], axis=1))
    modelo = sm.OLS(df["tds"], X).fit()
    return {
        "coef_pdsi_intra_regime": float(modelo.params["pdsi_lag"]),
        "p_pdsi_intra_regime": float(modelo.pvalues["pdsi_lag"]),
        "r2_com_regime_e_pdsi": float(modelo.rsquared),
        "n": len(df),
    }


def main():
    print("=== Etapa 1: parsing dos dados de seca (PDSI, NOAA NCEI nClimDiv) ===")
    pdsi_df = carregar_series_pdsi()
    tds = carregar_tds()
    vazao = carregar_vazao()
    print()

    periodo_comum = tds.index.intersection(pdsi_df.dropna(how="all").index)
    print(f"TDS: {len(tds)} meses ({tds.index.min().date()} a {tds.index.max().date()})")
    print(f"Periodo comum TDS x PDSI: {len(periodo_comum)} meses")
    print()

    with iniciar_run("pdsi_regimes", "script_18_pdsi_regimes", params={"max_lag_meses": MAX_LAG_MESES, "n_regimes": len(REGIMES)}):
        gerar_figura_overlay(tds, pdsi_df)

        print("=== Etapa 2.2: correlacao cruzada com defasagem (0-36 meses) ===")
        resultados_ccf = {}
        melhores_lags = {}
        for col in pdsi_df.columns:
            ccf = correlacao_cruzada_defasagem(tds, pdsi_df[col])
            resultados_ccf[col] = ccf
            idx_melhor_bruta = ccf["r_bruta"].abs().idxmax()
            idx_melhor_dest = ccf["r_destendenciada"].abs().idxmax()
            melhores_lags[col] = int(ccf.loc[idx_melhor_bruta, "lag_meses"])
            print(f"--- {col} ---")
            print(f"  Correlacao BRUTA maxima: lag={ccf.loc[idx_melhor_bruta,'lag_meses']:.0f}m, "
                  f"r={ccf.loc[idx_melhor_bruta,'r_bruta']:.3f}, p(dof efetivo)={ccf.loc[idx_melhor_bruta,'p_bruta_dof_efetivo']:.4f}, "
                  f"n_efetivo={ccf.loc[idx_melhor_bruta,'n_efetivo_bruta']:.1f} (n nominal={ccf.loc[idx_melhor_bruta,'n_par']:.0f})")
            print(f"  Correlacao DESTENDENCIADA maxima: lag={ccf.loc[idx_melhor_dest,'lag_meses']:.0f}m, "
                  f"r={ccf.loc[idx_melhor_dest,'r_destendenciada']:.3f}, p(dof efetivo)={ccf.loc[idx_melhor_dest,'p_destendenciada_dof_efetivo']:.4f}")
            print()

        # figura de correlacao cruzada
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for col, ccf in resultados_ccf.items():
            ax.plot(ccf["lag_meses"], ccf["r_bruta"], label=f"{col} (bruta)", linewidth=1.3)
            ax.plot(ccf["lag_meses"], ccf["r_destendenciada"], "--", label=f"{col} (destendenciada)", linewidth=1, alpha=0.7)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_xlabel("Defasagem do PDSI (meses)")
        ax.set_ylabel("Correlação de Pearson (TDS × PDSI defasado)")
        ax.set_title("Correlação cruzada TDS × PDSI por defasagem")
        ax.legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(FIGURA_CCF, dpi=140)
        plt.close(fig)
        print(f"Figura salva em {FIGURA_CCF}")
        print()

        print("=== Etapa 2.3: changepoints no PDSI (independente, sem informar datas do TDS) ===")
        resultados_changepoints = {}
        for col in pdsi_df.columns:
            s = pdsi_df[col].dropna()
            s = s[(s.index >= "2005-01-01") & (s.index <= "2026-12-31")]  # janela com folga antes de 2011 p/ deteccao de borda
            cps = segmentacao_binaria_pettitt(s.values, s.index)
            comp = comparar_changepoints(cps)
            resultados_changepoints[col] = comp
            print(f"--- {col}: {len(cps)} changepoint(s) detectado(s) ---")
            for cp in cps:
                print(f"  {cp['data'].date()}  p={cp['p_valor']:.4f}  (profundidade {cp['profundidade']})")
            print(comp.to_string(index=False))
            print()

        print("=== Etapa 2.4: decomposicao dos mecanismos (LMG: PDSI defasado vs. vazao) ===")
        resultados_lmg = {}
        for col in pdsi_df.columns:
            lag = melhores_lags[col]
            lmg = decompor_mecanismos(tds, pdsi_df[col], vazao, lag)
            resultados_lmg[col] = lmg
            print(f"--- {col} (lag={lag}m) ---")
            print(f"  R2 total={lmg['r2_total']:.3f} | LMG PDSI={lmg['pct_pdsi']:.1f}% | LMG vazao={lmg['pct_vazao']:.1f}%")
            print(f"  (benchmark SCSC: agua de origem ~88% / consumo per capita ~12%)")
            print(f"  coef PDSI={lmg['coef_pdsi']:.3f} (p={lmg['p_pdsi']:.4f}) | coef vazao={lmg['coef_vazao']:.3f} (p={lmg['p_vazao']:.4f})")
            print()

        print("=== Etapa 2.5: PDSI ainda explica dentro dos regimes, ou o efeito e absorvido pelas dummies? ===")
        resultados_regime = {}
        for col in pdsi_df.columns:
            lag = melhores_lags[col]
            rr = regressao_por_regime(tds, pdsi_df[col], lag)
            resultados_regime[col] = rr
            print(f"--- {col} (lag={lag}m) --- coef PDSI intra-regime={rr['coef_pdsi_intra_regime']:.3f} "
                  f"(p={rr['p_pdsi_intra_regime']:.4f}), R2 total={rr['r2_com_regime_e_pdsi']:.3f}, n={rr['n']}")
        print()

        # -------------------------------------------------------------
        # consolidacao e gravacao
        # -------------------------------------------------------------
        linhas_saida = []
        for col in pdsi_df.columns:
            ccf = resultados_ccf[col]
            idx_melhor = ccf["r_bruta"].abs().idxmax()
            linha = {
                "serie_pdsi": col,
                "lag_melhor_correlacao_meses": int(ccf.loc[idx_melhor, "lag_meses"]),
                "r_bruta": float(ccf.loc[idx_melhor, "r_bruta"]),
                "p_bruta_dof_efetivo": float(ccf.loc[idx_melhor, "p_bruta_dof_efetivo"]),
                "n_efetivo_bruta": float(ccf.loc[idx_melhor, "n_efetivo_bruta"]),
                "r_destendenciada_mesmo_lag": float(ccf.loc[idx_melhor, "r_destendenciada"]),
                "p_destendenciada_mesmo_lag": float(ccf.loc[idx_melhor, "p_destendenciada_dof_efetivo"]),
                **{f"lmg_{k}": v for k, v in resultados_lmg[col].items()},
                **{f"regime_{k}": v for k, v in resultados_regime[col].items()},
                "n_changepoints_detectados": len(resultados_changepoints[col]),
                "changepoints_dentro_12m_de_4": int(comparar_changepoints(
                    segmentacao_binaria_pettitt(
                        pdsi_df[col].dropna()[(pdsi_df[col].dropna().index >= "2005-01-01")].values,
                        pdsi_df[col].dropna()[(pdsi_df[col].dropna().index >= "2005-01-01")].index,
                    )
                )["dentro_de_12_meses"].sum()),
                "data_execucao": datetime.now().isoformat(timespec="seconds"),
            }
            linhas_saida.append(linha)

        df_saida = pd.DataFrame(linhas_saida)
        df_saida.to_csv(RESULTADOS_CSV, index=False)
        df_saida.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

        metricas = {}
        for _, row in df_saida.iterrows():
            prefixo = row["serie_pdsi"]
            for col, val in row.items():
                if col in ("serie_pdsi", "data_execucao"):
                    continue
                if pd.notna(val) and isinstance(val, (int, float, np.integer, np.floating)):
                    metricas[f"{prefixo}__{col}"] = val
        logar_metricas(metricas)
        logar_artefatos([FIGURA_OVERLAY, FIGURA_CCF, RESULTADOS_CSV] + [cfg["arquivo_saida"] for cfg in SERIES_ALVO.values()])

    return df_saida


if __name__ == "__main__":
    main()
