"""
SARIMA para o TDS (secao 3.b da metodologia), com drift e ordem escolhida por
busca em grade por AIC.

Mesma nota de desenho do script_01: o metodo e univariado em TDS, entao o
resultado independe do tratamento de ND do BOD (dataset A vs B do script_00).
Nao ha necessidade de rodar 2x.

Grava uma linha em resultados_comparacao.csv/.json com: RMSE/MAE/R2 em
holdout, tendencia (mg/L/ano) com p-valor, e previsao pontual + IC90% para
+10/+15/+20 anos a partir do ultimo dado observado.

Limitacao conhecida (ja registrada no plano, secao 3.b): horizontes de 10/15/20
anos sao muito maiores que os ~15 anos de historico. O SARIMA extrapola de
forma quase deterministica alem de poucos passos — o IC tende a nao capturar
toda a incerteza real em +20 anos. Isso e reportado, nao escondido.
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


import warnings
from datetime import datetime
from itertools import product

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.statespace.sarimax import SARIMAX

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from utils.validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
PERIODO_SAZONAL = 12
RESULTADOS_CSV = RESULTADOS_COMPARACAO_CSV
RESULTADOS_JSON = RESULTADOS_COMPARACAO_JSON
FIGURA_PATH = figure("sarima-tds.png")
warnings.filterwarnings("ignore")


def carregar_serie_tds() -> pd.Series:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    s = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    return s


def metrica_holdout(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


# --------------------------------------------------------------------------
# SARIMA (com drift) — ordem escolhida por AIC em grade pequena
# --------------------------------------------------------------------------

def buscar_melhor_sarima(treino: pd.Series):
    """Busca em grade por AIC. d=1 fixo (serie claramente nao-estacionaria em
    nivel). D (diferenciacao sazonal) e explorado em {0,1}: com D=1 a serie ja
    fica duplamente diferenciada (d+D=2), e um termo de drift constante nesse
    caso implicaria tendencia QUADRATICA na serie original — por isso o drift
    ('c') so e permitido quando D=0 (diferenciacao total = 1, drift linear)."""
    melhor = None
    for p, q, P, Q, D in product([0, 1, 2], [0, 1, 2], [0, 1], [0, 1], [0, 1]):
        trend = "c" if D == 0 else None
        try:
            modelo = SARIMAX(
                treino, order=(p, 1, q), seasonal_order=(P, D, Q, PERIODO_SAZONAL),
                trend=trend, enforce_stationarity=False, enforce_invertibility=False,
            )
            res = modelo.fit(disp=False)
            if melhor is None or res.aic < melhor[0]:
                melhor = (res.aic, (p, 1, q), (P, D, Q, PERIODO_SAZONAL), trend, res)
        except Exception:
            continue
    return melhor


def rodar_sarima(s: pd.Series) -> dict:
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]

    aic, ordem, ordem_sazonal, trend, res_treino = buscar_melhor_sarima(treino)
    print(f"  Melhor ordem SARIMA (AIC={aic:.1f} em treino): order={ordem} seasonal_order={ordem_sazonal} trend={trend}")

    prev_holdout = res_treino.get_forecast(steps=HOLDOUT_MESES)
    pred_holdout = prev_holdout.predicted_mean.values
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    # refit na serie completa, mesma ordem, para tendencia e previsao final
    modelo_full = SARIMAX(
        s, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
        enforce_stationarity=False, enforce_invertibility=False,
    )
    res_full = modelo_full.fit(disp=False)

    if trend == "c" and "intercept" in res_full.param_names:
        drift_mensal = res_full.params["intercept"]
        drift_p = res_full.pvalues["intercept"]
    else:
        # D=1 escolhido pela busca (sem drift explicito, para evitar tendencia
        # quadratica) — a tendencia efetiva desta previsao e reportada via
        # regressao OLS sobre o proprio caminho previsto (ver abaixo).
        drift_mensal, drift_p = None, None

    max_passos = max(HORIZONTES_ANOS) * 12
    prev_full = res_full.get_forecast(steps=max_passos)
    media = prev_full.predicted_mean
    ic = prev_full.conf_int(alpha=ALPHA)

    if drift_mensal is not None:
        tendencia_ano = drift_mensal * 12
        tendencia_p = drift_p
    else:
        # sem drift explicito no modelo: tendencia efetiva estimada por OLS
        # sobre o proprio caminho previsto (janela de 10 anos, para nao
        # incorporar a possivel instabilidade de longo prazo do modelo)
        passos_10a = 10 * 12
        reg = stats.linregress(np.arange(passos_10a), media.values[:passos_10a])
        tendencia_ano = reg.slope * 12
        tendencia_p = reg.pvalue

    linha = {
        "metodo": "sarima",
        "tendencia_mgL_ano": tendencia_ano,
        "tendencia_pvalor": tendencia_p,
        "tendencia_ic90_baixo": float("nan"),
        "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
        "ordem_sarima": f"order={ordem} seasonal_order={ordem_sazonal} trend={trend}",
    }

    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = float(media.iloc[passo])
        linha[f"ci90_low_{h}y"] = float(ic.iloc[passo, 0])
        linha[f"ci90_high_{h}y"] = float(ic.iloc[passo, 1])

    return linha, res_full, ordem, ordem_sazonal, trend


# --------------------------------------------------------------------------
# Adaptadores fit_predict (validacao_utils.validar_metodo: CV expansiva + backtest)
# --------------------------------------------------------------------------

def construir_fit_predict_sarima(ordem, ordem_sazonal, trend):
    """Ordem fixa (a mesma escolhida por AIC uma unica vez, sobre o treino de
    24 meses de holdout) em vez de repetir a busca em grade a cada fold/
    origem do CV/backtest -- refazer a busca completa (~72 combinacoes) em
    ~25 refits diferentes seria computacionalmente proibitivo para o ganho
    marginal esperado. Decisao de escopo registrada aqui, nao escondida."""
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        modelo = SARIMAX(treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                          enforce_stationarity=False, enforce_invertibility=False)
        res = modelo.fit(disp=False)
        return res.get_forecast(steps=n_passos).predicted_mean.values
    return fit_predict


def gerar_figura(s: pd.Series, linha_sarima: dict):
    fig, ax = plt.subplots(figsize=(7, 4))

    ax.plot(s.index, s.values, color="black", linewidth=1, label="TDS observado")
    ultima_data = s.index[-1]
    anos_futuros = [0] + HORIZONTES_ANOS
    datas_futuras = [ultima_data + pd.DateOffset(months=int(a * 12)) for a in anos_futuros]
    pontos = [linha_sarima[f"forecast_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
    baixos = [linha_sarima[f"ci90_low_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
    altos = [linha_sarima[f"ci90_high_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
    ax.plot(datas_futuras, pontos, "--", color="tab:purple", label="SARIMA (previsao)")
    ax.fill_between(datas_futuras, baixos, altos, color="tab:purple", alpha=0.12)
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Previsao SARIMA (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")

    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_02_arima_sarima"
        linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
        linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame(linhas)

    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[~existentes["metodo"].isin(novas["metodo"])]
        for col in novas.columns:
            if col not in existentes.columns:
                existentes[col] = np.nan
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas

    consolidado.to_csv(RESULTADOS_CSV, index=False)
    consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)


def imprimir_validacao(linha: dict):
    print(f"  Holdout: RMSE={linha['rmse_holdout']:.2f}  MAE={linha['mae_holdout']:.2f}  R2={linha['r2_holdout']:.3f}  "
          f"MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
    print(f"  CV (5 folds expansivos): RMSE={linha['cv_rmse_media']:.2f}±{linha['cv_rmse_desvio']:.2f}  "
          f"MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}")
    print(f"  Backtest origem movel: MAE(+3a)={linha.get('backtest_mae_36m', float('nan')):.2f}  "
          f"MAE(+5a)={linha.get('backtest_mae_60m', float('nan')):.2f}")
    for h in HORIZONTES_ANOS:
        baixo, alto = linha[f"ci90_low_{h}y"], linha[f"ci90_high_{h}y"]
        if not (np.isnan(baixo) or np.isnan(alto)):
            linha[f"ic90_width_{h}y"] = alto - baixo
        print(f"  +{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{baixo:.1f}, {alto:.1f}]")


def main():
    s = carregar_serie_tds()
    treino_serie, holdout_serie = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(s)} meses ({s.index[0].date()} a {s.index[-1].date()})")
    print(f"Treino: {len(s) - HOLDOUT_MESES} meses | Holdout: {HOLDOUT_MESES} meses")
    print()

    print("--- SARIMA ---")
    linha_sarima, res_full, ordem, ordem_sazonal, trend = rodar_sarima(s)
    linha_sarima.update(validar_metodo(
        construir_fit_predict_sarima(ordem, ordem_sazonal, trend), s, treino_serie, holdout_serie
    ))
    print(f"  Tendencia (drift): {linha_sarima['tendencia_mgL_ano']:.3f} mg/L/ano (p={linha_sarima['tendencia_pvalor']:.4f})")
    imprimir_validacao(linha_sarima)
    print()

    gravar_resultados([linha_sarima])
    print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(s, linha_sarima)

    with iniciar_run(
        linha_sarima["metodo"], "script_02_arima_sarima",
        params={"alpha_ic": ALPHA, "periodo_sazonal": PERIODO_SAZONAL},
        janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
    ):
        logar_linha_resultado(linha_sarima)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
