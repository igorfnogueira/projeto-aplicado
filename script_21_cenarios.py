"""
Projecao por cenarios climaticos (prompt_wrtds_balanco_cenarios.md, Tarefa 3):
substitui a previsao pontual de longo prazo por uma FAIXA condicionada ao
regime de seca, usando o PDSI ja baixado em script_18 e a relacao PDSI->TDS
de D-37.

Por que cenarios em vez de ponto: script_20 (balanco de massa) mostrou que
extrapolar linearmente carga e vazao por 20 anos cruza valores fisicamente
implausiveis (vazao negativa/perto de zero) -- a serie e dirigida por ciclos
de seca (D-37), e prever seca em +20 anos nao e possivel. Cenarios com faixas
historicamente observadas de PDSI sao a alternativa honesta.

Metodo:
  1. PDSI historico (1895-2026, serie California estadual -- maior LMG% em
     D-37) caracteriza a distribuicao e ajusta um AR(1) simples
     (PDSI_t = mu + phi*(PDSI_{t-1}-mu) + eps).
  2. Regressao TDS ~ PDSI(defasado, mesmo lag de D-37) + intercepto, com
     erro-padrao dos coeficientes e desvio-padrao residual.
  3. Quatro cenarios de trajetoria futura de PDSI (todos simulados pelo MESMO
     AR(1) ajustado no historico, so mudando a media-alvo -- nao se inventa
     um processo novo por cenario):
       - Seco: media-alvo = percentil 10 historico (seca persistente)
       - Normal: media-alvo = media historica
       - Umido: media-alvo = percentil 90 historico
       - Agravamento: media-alvo desliza linearmente da media historica ate
         o percentil 10 ao longo dos 20 anos (secas mais frequentes/intensas)
  4. Monte Carlo (N_SIMULACOES trajetorias por cenario): incerteza do
     coeficiente da regressao (normal ao redor do valor ajustado) + ruido
     residual + variabilidade do proprio PDSI simulado -- NAO incerteza de
     medicao do PDSI em si (fora de escopo).
  5. Para cada horizonte (+10/+15/+20a) e cenario, agrega P5/P50/P95 da
     distribuicao de TDS simulado.

Nao apresenta um unico valor para 2046 -- apresenta a faixa por cenario, com
a ressalva de que cenarios sao projecoes condicionais, nao previsoes.
"""

import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

SEED = 42
N_SIMULACOES = 2000
HORIZONTES_ANOS = [10, 15, 20]
SERIE_PDSI_PRIMARIA = "california_estadual"
ARQUIVO_PDSI = "pdsi_california_estadual.csv"
RESULTADOS_CSV = "cenarios_resultados.csv"
RESULTADOS_JSON = "cenarios_resultados.json"
RESULTADOS_COMPARACAO_CSV = "resultados_comparacao.csv"
RESULTADOS_COMPARACAO_JSON = "resultados_comparacao.json"
FIGURA_FAN = "Artigo/images/cenarios-pdsi-fanchart.png"
FIGURA_HORIZONTES = "Artigo/images/cenarios-pdsi-horizontes.png"


def carregar_lag_otimo() -> int:
    df = pd.read_csv("pdsi_regimes_resultados.csv")
    linha = df[df["serie_pdsi"] == SERIE_PDSI_PRIMARIA].iloc[0]
    return int(linha["lag_melhor_correlacao_meses"])


def carregar_pdsi_historico() -> pd.Series:
    df = pd.read_csv(ARQUIVO_PDSI, parse_dates=["Data"])
    return df.set_index("Data")["pdsi"].sort_index()


def carregar_tds() -> pd.Series:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data")
    d["Data"] = pd.to_datetime(d["Data"]) + pd.offsets.MonthEnd(0)
    return d.set_index("Data")["TDS_mgL"]


def ajustar_ar1(pdsi: pd.Series) -> dict:
    x = pdsi.values[:-1]
    y = pdsi.values[1:]
    mu = float(pdsi.mean())
    X = sm.add_constant(x - mu)
    modelo = sm.OLS(y - mu, X).fit()
    phi = float(modelo.params[1])
    resid_std = float(modelo.resid.std(ddof=2))
    return {"mu": mu, "phi": phi, "resid_std": resid_std,
            "p10": float(pdsi.quantile(0.10)), "p50": float(pdsi.quantile(0.50)), "p90": float(pdsi.quantile(0.90))}


def ajustar_regressao_tds_pdsi(tds: pd.Series, pdsi: pd.Series, lag: int) -> dict:
    df = pd.DataFrame({"tds": tds, "pdsi_lag": pdsi.shift(lag)}).dropna()
    X = sm.add_constant(df["pdsi_lag"])
    modelo = sm.OLS(df["tds"], X).fit()
    return {
        "intercepto": float(modelo.params["const"]), "coef_pdsi": float(modelo.params["pdsi_lag"]),
        "se_intercepto": float(modelo.bse["const"]), "se_coef_pdsi": float(modelo.bse["pdsi_lag"]),
        "resid_std": float(modelo.resid.std(ddof=2)), "n": len(df), "r2": float(modelo.rsquared),
    }


def simular_trajetoria_pdsi(ar1: dict, pdsi_inicial: float, n_meses: int, mu_alvo_por_mes: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Simula uma trajetoria mensal de PDSI via o MESMO AR(1) ajustado no
    historico, mas com a media-alvo (mu_alvo_por_mes) especifica do cenario
    -- pode ser constante (seco/normal/umido) ou variavel no tempo
    (agravamento)."""
    traj = np.empty(n_meses)
    anterior = pdsi_inicial
    for m in range(n_meses):
        mu_m = mu_alvo_por_mes[m]
        esperado = mu_m + ar1["phi"] * (anterior - mu_m)
        traj[m] = esperado + rng.normal(0, ar1["resid_std"])
        anterior = traj[m]
    return traj


def definir_cenarios(ar1: dict, n_meses: int) -> dict:
    constante = lambda v: np.full(n_meses, v)
    rampa = np.linspace(ar1["mu"], ar1["p10"], n_meses)
    return {
        "seco": constante(ar1["p10"]),
        "normal": constante(ar1["mu"]),
        "umido": constante(ar1["p90"]),
        "agravamento_climatico": rampa,
    }


def rodar_monte_carlo(ar1: dict, reg: dict, pdsi_inicial: float, lag: int, rng: np.random.Generator) -> pd.DataFrame:
    n_meses = max(HORIZONTES_ANOS) * 12 + lag  # folga para poder indexar t-lag no ultimo horizonte
    cenarios = definir_cenarios(ar1, n_meses)

    linhas = []
    for nome_cenario, mu_por_mes in cenarios.items():
        trajetorias_pdsi = np.empty((N_SIMULACOES, n_meses))
        for s in range(N_SIMULACOES):
            trajetorias_pdsi[s] = simular_trajetoria_pdsi(ar1, pdsi_inicial, n_meses, mu_por_mes, rng)

        coefs = rng.normal(reg["coef_pdsi"], reg["se_coef_pdsi"], N_SIMULACOES)
        intercepts = rng.normal(reg["intercepto"], reg["se_intercepto"], N_SIMULACOES)
        ruido = rng.normal(0, reg["resid_std"], (N_SIMULACOES, len(HORIZONTES_ANOS)))

        for i_h, h in enumerate(HORIZONTES_ANOS):
            mes_alvo = h * 12 - lag - 1  # indice 0-based do PDSI que "explica" o TDS de +h anos (defasagem lag)
            mes_alvo = min(max(mes_alvo, 0), n_meses - 1)
            pdsi_no_horizonte = trajetorias_pdsi[:, mes_alvo]
            tds_simulado = intercepts + coefs * pdsi_no_horizonte + ruido[:, i_h]
            for v in tds_simulado:
                linhas.append({"cenario": nome_cenario, "horizonte_anos": h, "tds_simulado": v})

    return pd.DataFrame(linhas)


def resumir_por_cenario_horizonte(sim: pd.DataFrame) -> pd.DataFrame:
    resumo = sim.groupby(["cenario", "horizonte_anos"])["tds_simulado"].agg(
        p5=lambda s: np.percentile(s, 5), p50=lambda s: np.percentile(s, 50),
        p95=lambda s: np.percentile(s, 95), media="mean", desvio="std",
    ).reset_index()
    return resumo


def gerar_figura_fan(tds: pd.Series, sim: pd.DataFrame, ar1: dict, reg: dict, pdsi_inicial: float, lag: int, rng: np.random.Generator):
    """Fan chart do cenario 'normal' ao longo do tempo (nao so nos 3
    horizontes), para visualizar como a incerteza cresce mes a mes."""
    n_meses = max(HORIZONTES_ANOS) * 12 + lag
    mu_por_mes = np.full(n_meses, ar1["mu"])
    trajetorias_pdsi = np.array([simular_trajetoria_pdsi(ar1, pdsi_inicial, n_meses, mu_por_mes, rng) for _ in range(400)])
    coefs = rng.normal(reg["coef_pdsi"], reg["se_coef_pdsi"], 400)
    intercepts = rng.normal(reg["intercepto"], reg["se_intercepto"], 400)

    meses_tds = np.arange(lag, n_meses)  # TDS(t) usa PDSI(t-lag) -> primeiro TDS valido em t=lag
    tds_traj = np.array([
        intercepts[s] + coefs[s] * trajetorias_pdsi[s, meses_tds - lag] + rng.normal(0, reg["resid_std"], len(meses_tds))
        for s in range(400)
    ])
    datas_futuras = [tds.index[-1] + pd.DateOffset(months=int(m - lag + 1)) for m in meses_tds]

    p5 = np.percentile(tds_traj, 5, axis=0)
    p50 = np.percentile(tds_traj, 50, axis=0)
    p95 = np.percentile(tds_traj, 95, axis=0)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(tds.index, tds.values, color="black", linewidth=1, label="TDS observado")
    ax.plot(datas_futuras, p50, color="tab:blue", linewidth=1.3, label="Cenário normal (mediana)")
    ax.fill_between(datas_futuras, p5, p95, color="tab:blue", alpha=0.15, label="IC90% (cenário normal)")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Projeção condicional (cenário normal) -- não é previsão pontual")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_FAN, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_FAN}")


def gerar_figura_horizontes(resumo: pd.DataFrame):
    fig, axes = plt.subplots(1, len(HORIZONTES_ANOS), figsize=(11, 4), sharey=True)
    cores = {"seco": "tab:red", "normal": "tab:blue", "umido": "tab:green", "agravamento_climatico": "tab:orange"}
    for ax, h in zip(axes, HORIZONTES_ANOS):
        sub = resumo[resumo["horizonte_anos"] == h]
        for _, row in sub.iterrows():
            cor = cores.get(row["cenario"], "gray")
            ax.errorbar(row["cenario"], row["p50"], yerr=[[row["p50"] - row["p5"]], [row["p95"] - row["p50"]]],
                        fmt="o", color=cor, capsize=4)
        ax.set_title(f"+{h} anos")
        ax.tick_params(axis="x", rotation=30, labelsize=7)
    axes[0].set_ylabel("TDS simulado (mg/L)")
    fig.suptitle("Faixa de TDS por cenário climático (mediana + IC90%) -- não é previsão pontual")
    fig.tight_layout()
    fig.savefig(FIGURA_HORIZONTES, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_HORIZONTES}")


def gravar_resultados_comparacao(resumo: pd.DataFrame, t_referencia_anos: float):
    linhas = []
    for cenario in resumo["cenario"].unique():
        sub = resumo[resumo["cenario"] == cenario].set_index("horizonte_anos")
        linha = {
            "metodo": f"cenario_pdsi_{cenario}", "script": "script_21_cenarios",
            "tratamento_nd_bod": "nao_aplicavel_metodo_univariado_tds",
            "tendencia_mgL_ano": float("nan"), "tendencia_pvalor": float("nan"),
            "rmse_holdout": float("nan"), "mae_holdout": float("nan"), "r2_holdout": float("nan"),
            "data_execucao": datetime.now().isoformat(timespec="seconds"),
        }
        for h in HORIZONTES_ANOS:
            linha[f"forecast_{h}y"] = float(sub.loc[h, "p50"])
            linha[f"ci90_low_{h}y"] = float(sub.loc[h, "p5"])
            linha[f"ci90_high_{h}y"] = float(sub.loc[h, "p95"])
        linhas.append(linha)

    novas = pd.DataFrame(linhas)
    metodos_novos = set(novas["metodo"])
    if pd.io.common.file_exists(RESULTADOS_COMPARACAO_CSV):
        existentes = pd.read_csv(RESULTADOS_COMPARACAO_CSV)
        existentes = existentes[~existentes["metodo"].isin(metodos_novos)]
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
    rng = np.random.default_rng(SEED)
    lag = carregar_lag_otimo()
    print(f"=== Projeção por cenários climáticos (PDSI: {SERIE_PDSI_PRIMARIA}, lag={lag} meses de D-37) ===")
    print()

    pdsi_hist = carregar_pdsi_historico()
    tds = carregar_tds()

    ar1 = ajustar_ar1(pdsi_hist)
    print(f"AR(1) do PDSI histórico (1895-2026, n={len(pdsi_hist)}): mu={ar1['mu']:.2f}, phi={ar1['phi']:.3f}, "
          f"resid_std={ar1['resid_std']:.2f}")
    print(f"  Percentis históricos: P10={ar1['p10']:.2f} (seco) | P50={ar1['p50']:.2f} | P90={ar1['p90']:.2f} (úmido)")
    print()

    reg = ajustar_regressao_tds_pdsi(tds, pdsi_hist, lag)
    print(f"Regressão TDS ~ PDSI(lag={lag}): coef={reg['coef_pdsi']:.3f} (se={reg['se_coef_pdsi']:.3f}), "
          f"intercepto={reg['intercepto']:.1f}, R²={reg['r2']:.3f}, resid_std={reg['resid_std']:.1f}, n={reg['n']}")
    print()

    with iniciar_run("cenarios_pdsi", "script_21_cenarios",
                      params={"n_simulacoes": N_SIMULACOES, "seed": SEED, "lag_meses": lag,
                              "serie_pdsi": SERIE_PDSI_PRIMARIA}, seed=SEED):

        pdsi_inicial = float(pdsi_hist.iloc[-1])
        sim = rodar_monte_carlo(ar1, reg, pdsi_inicial, lag, rng)
        resumo = resumir_por_cenario_horizonte(sim)

        print("--- Faixa de TDS por cenário e horizonte (mediana [P5, P95], mg/L) ---")
        for _, row in resumo.iterrows():
            print(f"  {row['cenario']:22s} +{int(row['horizonte_anos']):2d}a: {row['p50']:.0f} "
                  f"[{row['p5']:.0f}, {row['p95']:.0f}]")
        print()

        gerar_figura_fan(tds, sim, ar1, reg, pdsi_inicial, lag, rng)
        gerar_figura_horizontes(resumo)

        resumo.to_csv(RESULTADOS_CSV, index=False)
        resultado = {
            "ar1": ar1, "regressao_tds_pdsi": reg, "lag_meses": lag, "serie_pdsi": SERIE_PDSI_PRIMARIA,
            "resumo_por_cenario_horizonte": resumo.to_dict("records"),
            "script": "script_21_cenarios", "data_execucao": datetime.now().isoformat(timespec="seconds"),
        }
        with open(RESULTADOS_JSON, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

        t_ref = (tds.index[-1] - tds.index[0]).days / 365.25
        gravar_resultados_comparacao(resumo, t_ref)

        metricas = {"ar1_mu": ar1["mu"], "ar1_phi": ar1["phi"], "reg_coef_pdsi": reg["coef_pdsi"],
                    "reg_r2": reg["r2"], "lag_meses": lag}
        for _, row in resumo.iterrows():
            chave = f"{row['cenario']}__{int(row['horizonte_anos'])}y"
            metricas[f"{chave}__p50"] = row["p50"]
            metricas[f"{chave}__p5"] = row["p5"]
            metricas[f"{chave}__p95"] = row["p95"]
        logar_metricas(metricas)
        logar_artefatos([FIGURA_FAN, FIGURA_HORIZONTES, RESULTADOS_CSV])

    return resumo


if __name__ == "__main__":
    main()
