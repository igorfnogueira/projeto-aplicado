"""
Hibrido SARIMA+Prophet para o TDS (bloco 3 do aprofundamento, material de
apoio Tema 6.2): ensemble simples (media aritmetica das previsoes pontuais)
entre dois metodos com mecanismos de extrapolacao bem diferentes -- SARIMA
(estocastico, diferenciacao sazonal) e Prophet (tendencia linear por partes +
decomposicao sazonal aditiva). A ideia testada: se os dois erram em direcoes
diferentes (script_02/05 ja mostraram isso -- SARIMA amplifica a tendencia,
Prophet reverte na extrapolacao), a media pode cancelar parte do erro.

IC90 do ensemble = envoltoria dos dois IC90 individuais (uniao dos limites
inferior/superior) -- mais largo que qualquer um dos dois isolados, refletindo
que a incerteza de "qual dos dois mecanismos de extrapolacao esta certo"
tambem faz parte da incerteza total.

Ordem SARIMA reaproveitada da busca por AIC ja feita em script_02 (mesma
decisao de escopo de outros scripts desta fase). Univariado em TDS: independe
do tratamento de ND do BOD.
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.statespace.sarimax import SARIMAX

from script_02_arima_sarima import carregar_serie_tds, buscar_melhor_sarima
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/hibrido-arima-prophet-tds.png"

warnings.filterwarnings("ignore")


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def prever_sarima(treino: pd.Series, n_passos: int, ordem, ordem_sazonal, trend):
    modelo = SARIMAX(treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                      enforce_stationarity=False, enforce_invertibility=False)
    res = modelo.fit(disp=False)
    prev = res.get_forecast(steps=n_passos)
    ic = prev.conf_int(alpha=ALPHA)
    return prev.predicted_mean.values, ic.iloc[:, 0].values, ic.iloc[:, 1].values


def prever_prophet(treino: pd.Series, n_passos: int):
    from prophet import Prophet
    df_treino = pd.DataFrame({"ds": treino.index, "y": treino.values})
    m = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(df_treino)
    futuro = m.make_future_dataframe(periods=n_passos, freq="MS")
    prev = m.predict(futuro).tail(n_passos)
    return prev["yhat"].values, prev["yhat_lower"].values, prev["yhat_upper"].values


def prever_hibrido(treino: pd.Series, n_passos: int, ordem, ordem_sazonal, trend):
    p_sarima, lo_sarima, hi_sarima = prever_sarima(treino, n_passos, ordem, ordem_sazonal, trend)
    p_prophet, lo_prophet, hi_prophet = prever_prophet(treino, n_passos)
    ponto = (p_sarima + p_prophet) / 2
    baixo = np.minimum(lo_sarima, lo_prophet)
    alto = np.maximum(hi_sarima, hi_prophet)
    return ponto, baixo, alto


def construir_fit_predict_hibrido(ordem, ordem_sazonal, trend):
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        ponto, _, _ = prever_hibrido(treino, n_passos, ordem, ordem_sazonal, trend)
        return ponto
    return fit_predict


def gerar_figura(s: pd.Series, dados):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(s.index, s.values, color="black", linewidth=1, label="TDS observado")
    datas_futuras, pontos, baixos, altos = dados
    ax.plot(datas_futuras, pontos, "--", color="tab:red", label="Hibrido SARIMA+Prophet (previsao)")
    ax.fill_between(datas_futuras, baixos, altos, color="tab:red", alpha=0.15)
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Híbrido SARIMA+Prophet — previsão de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linha: dict):
    linha["script"] = "script_12_hibrido_arima_prophet"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[~existentes["metodo"].isin(novas["metodo"])]
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas
    consolidado.to_csv(RESULTADOS_CSV, index=False)
    consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)


def main():
    s = carregar_serie_tds()
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(s)} meses | Treino: {len(treino)} | Holdout: {len(holdout)}")
    print()

    aic, ordem, ordem_sazonal, trend, _ = buscar_melhor_sarima(treino)
    print(f"Ordem SARIMA reaproveitada de script_02: order={ordem} seasonal_order={ordem_sazonal} trend={trend}")
    print()

    pred_holdout, _, _ = prever_hibrido(treino, len(holdout), ordem, ordem_sazonal, trend)
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    max_passos = max(HORIZONTES_ANOS) * 12
    pontos, baixos, altos = prever_hibrido(s, max_passos, ordem, ordem_sazonal, trend)
    passos_10a = 10 * 12
    reg = stats.linregress(np.arange(passos_10a), pontos[:passos_10a])

    linha = {
        "metodo": "hibrido_arima_prophet", "tendencia_mgL_ano": reg.slope * 12, "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "ordem_sarima": f"order={ordem} seasonal_order={ordem_sazonal} trend={trend}",
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = float(pontos[passo])
        linha[f"ci90_low_{h}y"] = float(baixos[passo])
        linha[f"ci90_high_{h}y"] = float(altos[passo])
        linha[f"ic90_width_{h}y"] = float(altos[passo] - baixos[passo])

    linha.update(validar_metodo(construir_fit_predict_hibrido(ordem, ordem_sazonal, trend), s, treino, holdout))

    print(f"Holdout: RMSE={linha['rmse_holdout']:.2f}  MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
    print(f"CV: MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}  Backtest+3a: MAE={linha.get('backtest_mae_36m', float('nan')):.2f}")
    for h in HORIZONTES_ANOS:
        print(f"+{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]")

    gravar_resultados(linha)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

    datas_futuras = [s.index[-1] + pd.DateOffset(months=p) for p in range(1, max_passos + 1)]
    gerar_figura(s, (datas_futuras, pontos, baixos, altos))

    with iniciar_run(
        "hibrido_arima_prophet", "script_12_hibrido_arima_prophet",
        params={"ordem_sarima": linha["ordem_sarima"]},
        janela_treino_holdout={"treino_meses": len(treino), "holdout_meses": len(holdout)},
    ):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
