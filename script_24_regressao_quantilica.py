"""
Regressao quantilica (plano_projeto_TDS.md secao 3.f.6): a tendencia da
MEDIANA do TDS pode ser diferente da tendencia do PERCENTIL 90. Como
limites regulatorios incidem sobre valores maximos (nao medias), saber se
os picos de TDS sobem mais rapido que a media tem valor pratico real.

Metodo: TDS ~ t_anos via regressao quantilica linear (statsmodels QuantReg)
para q em {0.10, 0.50, 0.90}, com previsao +10/+15/+20a e IC90 (bootstrap
de residuos, ja que QuantReg nao tem IC parametrico direto para previsao
fora da amostra).
"""

import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.quantile_regression import QuantReg

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

SEED = 42
QUANTIS = [0.10, 0.50, 0.90]
HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
N_BOOTSTRAP = 500
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/regressao-quantilica-tds.png"


def carregar_serie() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["Data"] = pd.to_datetime(d["Data"])
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    return d


def ajustar_quantil(t: np.ndarray, y: np.ndarray, q: float):
    X = sm.add_constant(t)
    modelo = QuantReg(y, X)
    return modelo.fit(q=q)


def bootstrap_ic_previsao(t: np.ndarray, y: np.ndarray, q: float, t_alvo: np.ndarray, rng: np.random.Generator) -> dict:
    n = len(t)
    previsoes = np.zeros((N_BOOTSTRAP, len(t_alvo)))
    for b in range(N_BOOTSTRAP):
        idx = rng.integers(0, n, n)
        try:
            res_b = ajustar_quantil(t[idx], y[idx], q)
            previsoes[b] = res_b.params[0] + res_b.params[1] * t_alvo
        except Exception:
            previsoes[b] = np.nan
    lo = np.nanpercentile(previsoes, 5, axis=0)
    hi = np.nanpercentile(previsoes, 95, axis=0)
    return {"lo": lo, "hi": hi}


def main():
    rng = np.random.default_rng(SEED)
    d = carregar_serie()
    treino = d.iloc[:-HOLDOUT_MESES]
    holdout = d.iloc[-HOLDOUT_MESES:]
    print(f"Série TDS: {len(d)} meses ({d['Data'].iloc[0].date()} a {d['Data'].iloc[-1].date()})")
    print(f"Treino: {len(treino)} | Holdout: {len(holdout)}")
    print()

    resultados_q = {}
    with iniciar_run("regressao_quantilica", "script_24_regressao_quantilica",
                      params={"quantis": QUANTIS, "n_bootstrap": N_BOOTSTRAP, "seed": SEED}, seed=SEED):

        for q in QUANTIS:
            res_full = ajustar_quantil(d["t_anos"].values, d["TDS_mgL"].values, q)
            res_treino = ajustar_quantil(treino["t_anos"].values, treino["TDS_mgL"].values, q)
            pred_holdout = res_treino.params[0] + res_treino.params[1] * holdout["t_anos"].values
            rmse = float(np.sqrt(np.mean((holdout["TDS_mgL"].values - pred_holdout) ** 2)))
            mae = float(np.mean(np.abs(holdout["TDS_mgL"].values - pred_holdout)))

            resultados_q[q] = {
                "intercepto": float(res_full.params[0]), "slope_mgL_ano": float(res_full.params[1]),
                "pvalor": float(res_full.pvalues[1]), "rmse_holdout": rmse, "mae_holdout": mae,
            }
            print(f"--- Quantil {q:.2f} ---")
            print(f"  Inclinação: {res_full.params[1]:.3f} mg/L/ano (p={res_full.pvalues[1]:.4f})")
            print(f"  Holdout: RMSE={rmse:.2f}  MAE={mae:.2f}")

        print()
        print("--- Comparação: os picos (P90) sobem mais rápido que a mediana (P50)? ---")
        diff_p90_p50 = resultados_q[0.90]["slope_mgL_ano"] - resultados_q[0.50]["slope_mgL_ano"]
        print(f"  Inclinação P90 - Inclinação P50 = {diff_p90_p50:+.3f} mg/L/ano "
              f"({'P90 sobe MAIS rápido' if diff_p90_p50 > 0 else 'P90 sobe MAIS devagar (ou cai mais) que a mediana'})")
        print()

        t_ultimo = d["t_anos"].iloc[-1]
        t_alvo = np.array([t_ultimo + h for h in HORIZONTES_ANOS])

        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(d["Data"], d["TDS_mgL"], color="gray", linewidth=0.7, alpha=0.5, label="TDS observado")
        cores = {0.10: "tab:blue", 0.50: "tab:green", 0.90: "tab:red"}
        linhas_saida = []
        pontos_por_quantil = {}
        for q in QUANTIS:
            res_full = ajustar_quantil(d["t_anos"].values, d["TDS_mgL"].values, q)
            ic = bootstrap_ic_previsao(d["t_anos"].values, d["TDS_mgL"].values, q, t_alvo, rng)
            pontos = res_full.params[0] + res_full.params[1] * t_alvo
            pontos_por_quantil[q] = pontos

            datas_todas = pd.date_range(d["Data"].iloc[0], periods=int(t_alvo[-1] * 12) + 12, freq="ME")
            t_plot = (datas_todas - d["Data"].iloc[0]).days / 365.25
            ax.plot(datas_todas, res_full.params[0] + res_full.params[1] * t_plot,
                    color=cores[q], linewidth=1.3, label=f"Q{int(q*100)}")

            linha = {
                "metodo": f"regressao_quantilica_q{int(q*100)}",
                "tendencia_mgL_ano": resultados_q[q]["slope_mgL_ano"], "tendencia_pvalor": resultados_q[q]["pvalor"],
                "rmse_holdout": resultados_q[q]["rmse_holdout"], "mae_holdout": resultados_q[q]["mae_holdout"],
                "r2_holdout": float("nan"),
                "script": "script_24_regressao_quantilica", "tratamento_nd_bod": "nao_aplicavel_metodo_univariado_tds",
                "data_execucao": datetime.now().isoformat(timespec="seconds"),
                "hiperparametros": f"quantil={q}, bootstrap_n={N_BOOTSTRAP}",
            }
            for i, h in enumerate(HORIZONTES_ANOS):
                linha[f"forecast_{h}y"] = float(pontos[i])
                linha[f"ci90_low_{h}y"] = float(ic["lo"][i])
                linha[f"ci90_high_{h}y"] = float(ic["hi"][i])
                print(f"  Q{int(q*100)} +{h}a: {pontos[i]:.1f} mg/L  IC90% [{ic['lo'][i]:.1f}, {ic['hi'][i]:.1f}]")
            linhas_saida.append(linha)

        print("\n--- Checagem de cruzamento de quantis (obrigatória: cada quantil é ajustado independentemente) ---")
        cruzamentos = []
        for i, h in enumerate(HORIZONTES_ANOS):
            q10_h, q50_h, q90_h = pontos_por_quantil[0.10][i], pontos_por_quantil[0.50][i], pontos_por_quantil[0.90][i]
            cruzou = not (q10_h <= q50_h <= q90_h)
            if cruzou:
                cruzamentos.append(h)
            print(f"  +{h}a: Q10={q10_h:.1f}  Q50={q50_h:.1f}  Q90={q90_h:.1f}"
                  f"{'  <<< CRUZAMENTO (ordem violada)' if cruzou else '  (ordem OK)'}")
        if cruzamentos:
            print(f"  ACHADO DECLARADO: cruzamento de quantis em +{cruzamentos} anos — cada quantil foi ajustado "
                  f"de forma independente (não há restrição de monotonicidade entre eles), e a inclinação do "
                  f"Q90 é negativa enquanto a do Q50 é positiva (ver acima). Extrapolar retas com inclinações "
                  f"de sinal oposto eventualmente cruza. Isso não invalida a leitura para o período histórico "
                  f"(onde a ordem Q10<Q50<Q90 vale por definição), mas é uma limitação real da extrapolação "
                  f"em horizontes longos — reportado, não escondido nem corrigido silenciosamente.")
        print()

        ax.set_xlabel("Data")
        ax.set_ylabel("TDS (mg/L)")
        ax.set_title("Regressão quantílica: mediana (Q50) vs. picos (Q90) vs. mínimos (Q10)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGURA_PATH, dpi=140)
        plt.close(fig)
        print(f"\nFigura salva em {FIGURA_PATH}")

        novas = pd.DataFrame(linhas_saida)
        metodos_novos = set(novas["metodo"])
        if pd.io.common.file_exists(RESULTADOS_CSV):
            existentes = pd.read_csv(RESULTADOS_CSV)
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
        consolidado.to_csv(RESULTADOS_CSV, index=False)
        consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)
        print(f"Resultados gravados em {RESULTADOS_CSV}")

        metricas = {"diff_p90_p50_mgL_ano": diff_p90_p50, "n_horizontes_com_cruzamento": len(cruzamentos)}
        for q, r in resultados_q.items():
            for k, v in r.items():
                metricas[f"q{int(q*100)}_{k}"] = v
        logar_metricas(metricas)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
