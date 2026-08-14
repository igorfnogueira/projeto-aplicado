"""
SARIMAX(TDS, exog=Cloreto) -- bloco 3 do aprofundamento: varios artigos do
material de apoio (Tema 2.4) usam cloreto como preditor de TDS; nosso dataset
tem serie densa de Cloreto na mesma frequencia mensal do TDS, entao testamos
se adiciona-lo como regressor exogeno melhora a previsao em relacao ao SARIMA
univariado ja existente (script_02).

Ordem SARIMA (p,d,q)(P,D,Q,12) reaproveitada da busca por AIC ja feita em
script_02 (mesma decisao de escopo de outros scripts desta fase: refazer a
busca em grade com exog em cada configuracao seria caro demais para o ganho
esperado) -- e o proprio coeficiente do regressor de Cloreto que e novo aqui,
nao a ordem ARIMA em si.

Avaliacao honesta em 2 partes:
  1. Holdout/CV/backtest: usam o Cloreto REALMENTE OBSERVADO no periodo de
     teste (dado historico real, nao inventado) -- mede corretamente "se
     voce soubesse o Cloreto futuro, melhoraria a previsao de TDS".
  2. Previsao real de +10/+15/+20 anos: o Cloreto futuro NAO e observado,
     entao e extrapolado por uma tendencia Theil-Sen propria -- a incerteza
     dessa extrapolacao NAO e propagada para o IC90 final do TDS, subestimando
     a incerteza real. Limitacao registrada explicitamente, nao escondida.

Depende do dataset canonico (TDS+Cloreto), independe do tratamento de ND do
BOD (BOD nao entra neste script).
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

from script_00_preprocessamento import construir_datasets
from script_02_arima_sarima import buscar_melhor_sarima
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/sarimax-cloreto-tds.png"

warnings.filterwarnings("ignore")


def carregar_series_tds_cloreto():
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL", "Chloride_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    tds = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    cloreto = pd.Series(d["Chloride_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    return tds, cloreto


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def construir_fit_predict_sarimax(cloreto: pd.Series, ordem, ordem_sazonal, trend):
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        exog_treino = cloreto.reindex(treino.index).values.reshape(-1, 1)
        modelo = SARIMAX(treino, exog=exog_treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                          enforce_stationarity=False, enforce_invertibility=False)
        res = modelo.fit(disp=False)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        exog_futuro = cloreto.reindex(datas_futuras)
        if exog_futuro.isna().any():
            exog_futuro = exog_futuro.ffill().bfill()
        return res.get_forecast(steps=n_passos, exog=exog_futuro.values.reshape(-1, 1)).predicted_mean.values
    return fit_predict


def extrapolar_cloreto(cloreto: pd.Series, max_passos: int) -> pd.Series:
    """Extrapola o Cloreto futuro por Theil-Sen (robusto), unica forma de
    obter exog para os horizontes +10/+15/+20 anos, ja que nao ha Cloreto
    observado no futuro real."""
    data0 = cloreto.index[0]
    t = (cloreto.index - data0).days / 365.25
    slope, intercept, _, _ = stats.theilslopes(cloreto.values, t.values)
    datas_futuras = pd.date_range(cloreto.index[-1], periods=max_passos + 1, freq="ME")[1:]
    t_futuro = (datas_futuras - data0).days / 365.25
    valores = intercept + slope * t_futuro.values
    return pd.Series(valores, index=datas_futuras)


def rodar_sarimax_cloreto(tds: pd.Series, cloreto: pd.Series, ordem, ordem_sazonal, trend):
    treino, holdout = tds.iloc[:-HOLDOUT_MESES], tds.iloc[-HOLDOUT_MESES:]
    exog_treino = cloreto.reindex(treino.index).values.reshape(-1, 1)
    exog_holdout = cloreto.reindex(holdout.index).values.reshape(-1, 1)

    modelo_treino = SARIMAX(treino, exog=exog_treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                             enforce_stationarity=False, enforce_invertibility=False)
    res_treino = modelo_treino.fit(disp=False)
    pred_holdout = res_treino.get_forecast(steps=len(holdout), exog=exog_holdout).predicted_mean.values
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)
    coef_cloreto_treino = float(res_treino.params.get("x1", float("nan")))

    exog_full = cloreto.reindex(tds.index).values.reshape(-1, 1)
    modelo_full = SARIMAX(tds, exog=exog_full, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                           enforce_stationarity=False, enforce_invertibility=False)
    res_full = modelo_full.fit(disp=False)
    coef_cloreto = float(res_full.params.get("x1", float("nan")))
    coef_cloreto_p = float(res_full.pvalues.get("x1", float("nan")))

    max_passos = max(HORIZONTES_ANOS) * 12
    cloreto_futuro = extrapolar_cloreto(cloreto, max_passos)
    prev_full = res_full.get_forecast(steps=max_passos, exog=cloreto_futuro.values.reshape(-1, 1))
    media = prev_full.predicted_mean
    ic = prev_full.conf_int(alpha=ALPHA)

    passos_10a = 10 * 12
    reg = stats.linregress(np.arange(passos_10a), media.values[:passos_10a])

    linha = {
        "metodo": "sarimax_cloreto", "tendencia_mgL_ano": reg.slope * 12, "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "ordem_sarima": f"order={ordem} seasonal_order={ordem_sazonal} trend={trend}",
        "hiperparametros": str({"coef_cloreto": round(coef_cloreto, 4), "coef_cloreto_p": round(coef_cloreto_p, 4)}),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = float(media.iloc[passo])
        linha[f"ci90_low_{h}y"] = float(ic.iloc[passo, 0])
        linha[f"ci90_high_{h}y"] = float(ic.iloc[passo, 1])
        linha[f"ic90_width_{h}y"] = float(ic.iloc[passo, 1] - ic.iloc[passo, 0])

    datas_futuras = [tds.index[-1] + pd.DateOffset(months=p) for p in range(1, max_passos + 1)]
    return linha, coef_cloreto_treino, (datas_futuras, media.values, ic.iloc[:, 0].values, ic.iloc[:, 1].values)


def gerar_figura(tds, cloreto, dados):
    fig, axes = plt.subplots(2, 1, figsize=(7, 6.2))
    ax = axes[0]
    ax.plot(cloreto.index, cloreto.values, color="tab:green", linewidth=1, label="Cloreto observado")
    ax.set_ylabel("Cloreto (mg/L)")
    ax.set_title("Cloreto observado (regressor exógeno)")
    ax.legend(fontsize=7)

    ax = axes[1]
    ax.plot(tds.index, tds.values, color="black", linewidth=1, label="TDS observado")
    datas_futuras, pontos, baixos, altos = dados
    ax.plot(datas_futuras, pontos, "--", color="tab:blue", label="SARIMAX(TDS, exog=Cloreto)")
    ax.fill_between(datas_futuras, baixos, altos, color="tab:blue", alpha=0.15)
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("SARIMAX com Cloreto como regressor exógeno (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")

    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linha: dict):
    linha["script"] = "script_11_multivariado_cloreto"
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
    tds, cloreto = carregar_series_tds_cloreto()
    treino_tds, holdout_tds = tds.iloc[:-HOLDOUT_MESES], tds.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS+Cloreto: {len(tds)} meses | Treino: {len(treino_tds)} | Holdout: {len(holdout_tds)}")
    print()

    print("Reaproveitando a ordem SARIMA ja escolhida por AIC em script_02 (busca com exog seria cara demais)...")
    aic, ordem, ordem_sazonal, trend, _ = buscar_melhor_sarima(treino_tds)
    print(f"  Ordem: order={ordem} seasonal_order={ordem_sazonal} trend={trend}")
    print()

    linha, coef_treino, dados = rodar_sarimax_cloreto(tds, cloreto, ordem, ordem_sazonal, trend)
    linha.update(validar_metodo(
        construir_fit_predict_sarimax(cloreto, ordem, ordem_sazonal, trend), tds, treino_tds, holdout_tds
    ))

    print(f"Coeficiente do Cloreto (treino): {coef_treino:.4f}")
    print(f"Coeficiente do Cloreto (serie completa): {linha['hiperparametros']}")
    print(f"Holdout (Cloreto REAL observado): RMSE={linha['rmse_holdout']:.2f}  MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
    print(f"CV: MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}  Backtest+3a: MAE={linha.get('backtest_mae_36m', float('nan')):.2f}")

    # comparacao direta com o SARIMA univariado ja gravado por script_02
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        sarima_uni = existentes[existentes["metodo"] == "sarima"]
        if len(sarima_uni):
            print(f"\nComparacao com SARIMA univariado (script_02): "
                  f"RMSE {sarima_uni['rmse_holdout'].iloc[0]:.2f} -> {linha['rmse_holdout']:.2f}  "
                  f"MASE {sarima_uni['mase_holdout'].iloc[0]:.3f} -> {linha['mase_holdout']:.3f}")

    print()
    for h in HORIZONTES_ANOS:
        print(f"+{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]  "
              f"(Cloreto extrapolado por Theil-Sen, incerteza nao propagada)")

    gravar_resultados(linha)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(tds, cloreto, dados)

    with iniciar_run(
        "sarimax_cloreto", "script_11_multivariado_cloreto",
        params={"ordem_sarima": linha["ordem_sarima"]},
        janela_treino_holdout={"treino_meses": len(treino_tds), "holdout_meses": len(holdout_tds)},
    ):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
