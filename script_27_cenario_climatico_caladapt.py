"""
Cenario climatico fundamentado em projecao real (nao so reamostragem
historica) -- complemento a script_21_cenarios.py, decidido apos pesquisa
confirmar que nao existe um substituto "plug-and-play" ao PDSI historico
com o mesmo escopo (indice de seca mensal, multiplos cenarios, horizonte de
20 anos, download em lote). A alternativa viavel identificada: usar as
medias de 30 anos de precipitacao projetada (ensemble de 32 modelos LOCA
downscaled, RCP 8.5) da API publica do Cal-Adapt (cal-adapt.org), real e
verificada nesta sessao (nao um "plug-and-play" de indice de seca, mas um
numero real e citavel de mudanca de precipitacao projetada).

Metodo (declarado, nao e um "PDSI verdadeiro" -- e uma calibracao):
  1. Baixa a serie historica de precipitacao mensal da California (NOAA
     NCEI nClimDiv, mesmo arquivo/formato de script_18, elemento 01 =
     Precipitacao) e o PDSI estadual ja baixado em script_18.
  2. Calcula, ano a ano, a anomalia percentual de precipitacao anual frente
     a media historica, e regride o PDSI anual contra essa anomalia --
     ambos series REAIS e observadas, dando a relacao empirica
     precipitacao->PDSI para a California.
  3. Baixa dois rasters REAIS do Cal-Adapt (API publica, sem chave):
     media de 30 anos de precipitacao 1961-1990 (historico) e 2035-2064
     (RCP 8.5, ensemble de 32 modelos LOCA), extrai o pixel no ponto da
     LAGWRP, e calcula a mudanca percentual projetada.
  4. Aplica essa mudanca percentual real na regressao do passo 2 para obter
     um "PDSI-alvo implicito sob RCP 8.5" -- NAO e uma previsao de PDSI
     rigorosa (PDSI depende de temperatura e balanco hidrico do solo, nao
     so precipitacao), e isso e declarado explicitamente como limitacao.
  5. Roda o MESMO motor de Monte Carlo de script_21 (AR(1) + regressao
     TDS~PDSI) com esse PDSI-alvo, como um 5o cenario ("rcp85_caladapt"),
     ao lado dos 4 ja existentes -- nao os substitui.
"""

import io
import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm
from PIL import Image

from script_00_preprocessamento import construir_datasets
from script_18_pdsi_regimes import parse_fixed_width_climdiv
from script_21_cenarios import ajustar_ar1, ajustar_regressao_tds_pdsi, simular_trajetoria_pdsi, HORIZONTES_ANOS
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

SEED = 42
N_SIMULACOES = 2000
LAT_LAGWRP, LON_LAGWRP = 34.1372, -118.27422
NOAA_PRECIP_URL = "https://www.ncei.noaa.gov/pub/data/cirs/climdiv/climdiv-pcpnst-v1.0.0-20260806"
PRECIP_RAW_FILE = "pdsi_raw_climdiv_precip_estadual.txt"
PREFIXO_PRECIP_ESTADUAL = "004001"  # state=004 (California), div=0 (area-averaged), elemento=01 (Precipitacao)

CALADAPT_HIST_TIF = "https://api.cal-adapt.org/media/img/30698/pr_30yavg_ens32avg_historical_1961-1990.LOCA_2016-04-02.16th.CA_NV.tif"
CALADAPT_RCP85_TIF = "https://api.cal-adapt.org/media/img/30700/pr_30yavg_ens32avg_rcp85_2035-2064.LOCA_2016-04-02.16th.CA_NV.tif"
CALADAPT_GEOM_XMIN, CALADAPT_GEOM_YMAX = -124.5625, 43.75  # bounding box confirmado via API (canto superior-esquerdo)
CALADAPT_PIXSIZE = 0.0625

RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
CENARIOS_RESULTADOS_JSON = "cenario_caladapt_resultados.json"
FIGURA_PATH = "Artigo/images/cenario-caladapt-rcp85.png"


def baixar_precip_estadual() -> pd.Series:
    print("Baixando precipitação mensal da Califórnia (NOAA NCEI nClimDiv)...")
    resp = requests.get(NOAA_PRECIP_URL, timeout=60)
    resp.raise_for_status()
    with open(PRECIP_RAW_FILE, "w") as f:
        f.write(resp.text)
    s = parse_fixed_width_climdiv(PRECIP_RAW_FILE, PREFIXO_PRECIP_ESTADUAL)
    s.name = "precip_polegadas"
    return s


def extrair_pixel_caladapt(url_tif: str, lat: float, lon: float) -> float:
    """Baixa um GeoTIFF do Cal-Adapt e extrai o valor do pixel mais proximo
    do ponto (lat, lon), usando a caixa delimitadora e o tamanho de pixel ja
    confirmados via a API (mesma grade para as duas series usadas aqui)."""
    resp = requests.get(url_tif, timeout=60)
    resp.raise_for_status()
    im = Image.open(io.BytesIO(resp.content))
    arr = np.array(im, dtype=float)
    col = int(round((lon - CALADAPT_GEOM_XMIN) / CALADAPT_PIXSIZE))
    row = int(round((CALADAPT_GEOM_YMAX - lat) / CALADAPT_PIXSIZE))
    valor = float(arr[row, col])
    return valor


def main():
    print("=== Cenário climático fundamentado em projeção real (Cal-Adapt, RCP 8.5) ===")
    print()

    # --- 1-2. calibracao empirica precipitacao -> PDSI, com dados reais historicos ---
    precip = baixar_precip_estadual()
    pdsi = pd.read_csv("pdsi_california_estadual.csv", parse_dates=["Data"]).set_index("Data")["pdsi"]

    precip_anual = precip.resample("YE").sum()
    pdsi_anual = pdsi.resample("YE").mean()
    df = pd.DataFrame({"precip": precip_anual, "pdsi": pdsi_anual}).dropna()
    df = df[(df.index.year >= 1961) & (df.index.year <= 2020)]  # mesma janela de referencia do Cal-Adapt (1961-1990) + folga
    media_precip_hist = df["precip"].mean()
    df["anomalia_pct"] = (df["precip"] - media_precip_hist) / media_precip_hist * 100

    X = sm.add_constant(df["anomalia_pct"])
    modelo_calibracao = sm.OLS(df["pdsi"], X).fit()
    print(f"Calibração empírica PDSI ~ anomalia % de precipitação anual (Califórnia, {df.index.year.min()}-{df.index.year.max()}, n={len(df)}):")
    print(f"  intercepto={modelo_calibracao.params['const']:.3f}, coef={modelo_calibracao.params['anomalia_pct']:.4f} "
          f"(p={modelo_calibracao.pvalues['anomalia_pct']:.4f}), R²={modelo_calibracao.rsquared:.3f}")
    print()

    # --- 3. rasters reais do Cal-Adapt ---
    print("Baixando rasters do Cal-Adapt (API pública, sem chave)...")
    precip_hist_caladapt = extrair_pixel_caladapt(CALADAPT_HIST_TIF, LAT_LAGWRP, LON_LAGWRP)
    precip_rcp85_caladapt = extrair_pixel_caladapt(CALADAPT_RCP85_TIF, LAT_LAGWRP, LON_LAGWRP)
    mudanca_pct_precip = (precip_rcp85_caladapt - precip_hist_caladapt) / precip_hist_caladapt * 100
    print(f"  Precipitação média 1961-1990 no ponto da LAGWRP (Cal-Adapt, ensemble 32 modelos LOCA): {precip_hist_caladapt:.3f} mm/dia")
    print(f"  Precipitação média 2035-2064 sob RCP 8.5 (mesmo ponto, mesmo ensemble): {precip_rcp85_caladapt:.3f} mm/dia")
    print(f"  Mudança projetada: {mudanca_pct_precip:+.1f}%")
    print()

    # --- 4. PDSI-alvo implicito sob RCP 8.5 ---
    pdsi_alvo_rcp85 = float(modelo_calibracao.params["const"] + modelo_calibracao.params["anomalia_pct"] * mudanca_pct_precip)
    print(f"PDSI-alvo implícito sob RCP 8.5 (via calibração precipitação->PDSI): {pdsi_alvo_rcp85:.2f}")
    print("ATENÇÃO — isto NÃO é uma previsão rigorosa de PDSI: o índice depende também de temperatura e balanço")
    print("hídrico do solo, não só de precipitação. É uma calibração declarada, não um PDSI projetado oficial.")
    print()

    # --- 5. Monte Carlo com o motor ja existente de script_21 ---
    ar1 = ajustar_ar1(pdsi)
    tds_series = construir_datasets()[3][["Data", "TDS_mgL"]].dropna().sort_values("Data")
    tds_series["Data"] = pd.to_datetime(tds_series["Data"]) + pd.offsets.MonthEnd(0)
    tds_series = tds_series.set_index("Data")["TDS_mgL"]

    lag = pd.read_csv("pdsi_regimes_resultados.csv")
    lag = int(lag[lag["serie_pdsi"] == "california_estadual"]["lag_melhor_correlacao_meses"].iloc[0])
    reg = ajustar_regressao_tds_pdsi(tds_series, pdsi, lag)

    rng = np.random.default_rng(SEED)
    n_meses = max(HORIZONTES_ANOS) * 12 + lag
    mu_por_mes = np.full(n_meses, pdsi_alvo_rcp85)
    pdsi_inicial = float(pdsi.iloc[-1])

    with iniciar_run("cenario_pdsi_rcp85_caladapt", "script_27_cenario_climatico_caladapt",
                      params={"n_simulacoes": N_SIMULACOES, "seed": SEED, "lag_meses": lag,
                              "pdsi_alvo_rcp85": pdsi_alvo_rcp85, "mudanca_pct_precip_caladapt": mudanca_pct_precip},
                      seed=SEED):

        trajetorias_pdsi = np.array([simular_trajetoria_pdsi(ar1, pdsi_inicial, n_meses, mu_por_mes, rng) for _ in range(N_SIMULACOES)])
        coefs = rng.normal(reg["coef_pdsi"], reg["se_coef_pdsi"], N_SIMULACOES)
        intercepts = rng.normal(reg["intercepto"], reg["se_intercepto"], N_SIMULACOES)

        resultado_por_horizonte = {}
        print("--- Cenário 'rcp85_caladapt' (PDSI-alvo fundamentado em projeção real, não histórico) ---")
        for h in HORIZONTES_ANOS:
            mes_alvo = min(max(h * 12 - lag - 1, 0), n_meses - 1)
            pdsi_no_horizonte = trajetorias_pdsi[:, mes_alvo]
            ruido = rng.normal(0, reg["resid_std"], N_SIMULACOES)
            tds_simulado = intercepts + coefs * pdsi_no_horizonte + ruido
            p5, p50, p95 = np.percentile(tds_simulado, [5, 50, 95])
            resultado_por_horizonte[h] = {"p5": float(p5), "p50": float(p50), "p95": float(p95)}
            print(f"  +{h}a: {p50:.0f} [{p5:.0f}, {p95:.0f}] mg/L")
        print()

        # --- comparacao com os 4 cenarios ja existentes ---
        comparacao = pd.read_csv("cenarios_resultados.csv")
        print("--- Comparação com os 4 cenários existentes (script_21, baseados em percentis históricos) ---")
        print(comparacao[comparacao["horizonte_anos"] == 20][["cenario", "p5", "p50", "p95"]].to_string(index=False))
        print(f"  rcp85_caladapt        +20a: {resultado_por_horizonte[20]['p50']:.0f} "
              f"[{resultado_por_horizonte[20]['p5']:.0f}, {resultado_por_horizonte[20]['p95']:.0f}]")
        print()

        # --- figura ---
        fig, ax = plt.subplots(figsize=(7, 4.5))
        cenarios_hist = comparacao[comparacao["horizonte_anos"] == 20].set_index("cenario")
        nomes = list(cenarios_hist.index) + ["rcp85_caladapt"]
        p50s = list(cenarios_hist["p50"]) + [resultado_por_horizonte[20]["p50"]]
        p5s = list(cenarios_hist["p5"]) + [resultado_por_horizonte[20]["p5"]]
        p95s = list(cenarios_hist["p95"]) + [resultado_por_horizonte[20]["p95"]]
        cores = ["tab:red", "tab:blue", "tab:green", "tab:orange", "tab:purple"]
        for i, nome in enumerate(nomes):
            ax.errorbar(nome, p50s[i], yerr=[[p50s[i] - p5s[i]], [p95s[i] - p50s[i]]], fmt="o",
                        color=cores[i % len(cores)], capsize=4)
        ax.set_ylabel("TDS simulado em +20a (mg/L)")
        ax.set_title("Cenários históricos (script_21) vs. cenário fundamentado em projeção real (Cal-Adapt RCP 8.5)")
        ax.tick_params(axis="x", rotation=25, labelsize=8)
        fig.tight_layout()
        fig.savefig(FIGURA_PATH, dpi=140)
        plt.close(fig)
        print(f"Figura salva em {FIGURA_PATH}")

        # --- gravacao ---
        resultado_json = {
            "precip_hist_caladapt_mm_dia": precip_hist_caladapt, "precip_rcp85_caladapt_mm_dia": precip_rcp85_caladapt,
            "mudanca_pct_precip_caladapt": mudanca_pct_precip, "pdsi_alvo_rcp85_implicito": pdsi_alvo_rcp85,
            "calibracao_precip_pdsi": {"intercepto": float(modelo_calibracao.params["const"]),
                                        "coef": float(modelo_calibracao.params["anomalia_pct"]),
                                        "pvalor": float(modelo_calibracao.pvalues["anomalia_pct"]),
                                        "r2": float(modelo_calibracao.rsquared), "n": len(df)},
            "resultado_por_horizonte": resultado_por_horizonte,
            "script": "script_27_cenario_climatico_caladapt", "data_execucao": datetime.now().isoformat(timespec="seconds"),
        }
        with open(CENARIOS_RESULTADOS_JSON, "w", encoding="utf-8") as f:
            json.dump(resultado_json, f, indent=2, ensure_ascii=False)
        print(f"Resultados gravados em {CENARIOS_RESULTADOS_JSON}")

        linha = {
            "metodo": "cenario_pdsi_rcp85_caladapt", "script": "script_27_cenario_climatico_caladapt",
            "tratamento_nd_bod": "nao_aplicavel_metodo_univariado_tds",
            "tendencia_mgL_ano": float("nan"), "tendencia_pvalor": float("nan"),
            "rmse_holdout": float("nan"), "mae_holdout": float("nan"), "r2_holdout": float("nan"),
            "data_execucao": datetime.now().isoformat(timespec="seconds"),
            "hiperparametros": f"pdsi_alvo_rcp85={pdsi_alvo_rcp85:.2f}, mudanca_pct_precip_caladapt={mudanca_pct_precip:.1f}",
        }
        for h in HORIZONTES_ANOS:
            linha[f"forecast_{h}y"] = resultado_por_horizonte[h]["p50"]
            linha[f"ci90_low_{h}y"] = resultado_por_horizonte[h]["p5"]
            linha[f"ci90_high_{h}y"] = resultado_por_horizonte[h]["p95"]

        novas = pd.DataFrame([linha])
        if pd.io.common.file_exists(RESULTADOS_CSV):
            existentes = pd.read_csv(RESULTADOS_CSV)
            existentes = existentes[existentes["metodo"] != "cenario_pdsi_rcp85_caladapt"]
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

        metricas = {"precip_hist_caladapt": precip_hist_caladapt, "precip_rcp85_caladapt": precip_rcp85_caladapt,
                    "mudanca_pct_precip": mudanca_pct_precip, "pdsi_alvo_rcp85": pdsi_alvo_rcp85,
                    "calibracao_r2": modelo_calibracao.rsquared}
        for h, r in resultado_por_horizonte.items():
            metricas[f"{h}y_p50"] = r["p50"]
            metricas[f"{h}y_p5"] = r["p5"]
            metricas[f"{h}y_p95"] = r["p95"]
        logar_metricas(metricas)
        logar_artefatos([FIGURA_PATH, CENARIOS_RESULTADOS_JSON, PRECIP_RAW_FILE])


if __name__ == "__main__":
    main()
