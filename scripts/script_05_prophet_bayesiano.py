"""
Prophet para o TDS (secao 3.d da metodologia) — escolhido por expor
explicitamente a incerteza crescente com o horizonte, mais honesto para
extrapolar ~15 anos de historico para +20 anos (ao contrario dos metodos
baseados em arvore, que saturam ou oscilam sem sinalizar a propria
fragilidade).

GPU: nao aplicavel. Prophet usa Stan/CmdStan (sem backend CUDA).

Mesma nota de desenho dos scripts 01-03: univariado em TDS, independe do
tratamento de ND do BOD.

D-73: a regressao bayesiana (PyMC/NUTS), que rodava junto neste script, ja
havia saido da lista de finalistas (D-67/ADR-0001) e agora sai tambem da
bateria publica de metodos na reducao para os 7 metodos citados na revisao
externa de 14/10/2026 -- extraida para
scripts/bateria_estendida/script_35_regressao_bayesiana.py.
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


from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from utils.validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
RESULTADOS_CSV = RESULTADOS_COMPARACAO_CSV
RESULTADOS_JSON = RESULTADOS_COMPARACAO_JSON
FIGURA_PATH = figure("prophet-tds.png")
SEED = 42


def carregar_serie_tds() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    return d


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def rodar_prophet(d: pd.DataFrame) -> dict:
    from prophet import Prophet

    treino, holdout = d.iloc[:-HOLDOUT_MESES], d.iloc[-HOLDOUT_MESES:]
    df_treino = treino[["Data", "TDS_mgL"]].rename(columns={"Data": "ds", "TDS_mgL": "y"})

    modelo_treino = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True,
                             weekly_seasonality=False, daily_seasonality=False)
    modelo_treino.fit(df_treino)
    futuro_holdout = modelo_treino.make_future_dataframe(periods=HOLDOUT_MESES, freq="MS")
    prev_holdout = modelo_treino.predict(futuro_holdout).tail(HOLDOUT_MESES)
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, prev_holdout["yhat"].values)

    df_full = d[["Data", "TDS_mgL"]].rename(columns={"Data": "ds", "TDS_mgL": "y"})
    modelo_full = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True,
                           weekly_seasonality=False, daily_seasonality=False)
    modelo_full.fit(df_full)

    max_passos = max(HORIZONTES_ANOS) * 12
    futuro = modelo_full.make_future_dataframe(periods=max_passos, freq="MS")
    prev_full = modelo_full.predict(futuro)

    # tendencia: regressao OLS sobre a componente "trend" do proprio Prophet, no periodo observado
    hist = prev_full.iloc[: len(d)]
    reg = stats.linregress(d["t_anos"].values, hist["trend"].values)

    linha = {
        "metodo": "prophet",
        "tendencia_mgL_ano": reg.slope,
        "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"),
        "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
    }
    prev_full_indexada = prev_full.set_index("ds")
    for h in HORIZONTES_ANOS:
        data_alvo = d["Data"].iloc[-1] + pd.DateOffset(months=h * 12)
        linha_h = prev_full_indexada.iloc[prev_full_indexada.index.get_indexer([data_alvo], method="nearest")[0]]
        linha[f"forecast_{h}y"] = float(linha_h["yhat"])
        linha[f"ci90_low_{h}y"] = float(linha_h["yhat_lower"])
        linha[f"ci90_high_{h}y"] = float(linha_h["yhat_upper"])

    return linha, prev_full


def construir_fit_predict_prophet():
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        from prophet import Prophet
        df_treino = pd.DataFrame({"ds": treino.index, "y": treino.values})
        m = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True,
                    weekly_seasonality=False, daily_seasonality=False)
        m.fit(df_treino)
        futuro = m.make_future_dataframe(periods=n_passos, freq="MS")
        return m.predict(futuro).tail(n_passos)["yhat"].values
    return fit_predict


def gerar_figura(d, linha_prophet, prev_full_prophet):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")

    ultima_data = d["Data"].iloc[-1]
    prev_futuro = prev_full_prophet[prev_full_prophet["ds"] > ultima_data]
    ax.plot(prev_futuro["ds"], prev_futuro["yhat"], "--", color="tab:green", label="Prophet (previsao)")
    ax.fill_between(prev_futuro["ds"], prev_futuro["yhat_lower"], prev_futuro["yhat_upper"],
                     color="tab:green", alpha=0.12)

    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Prophet — previsao de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linha: dict):
    linha["script"] = "script_05_prophet_bayesiano"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame([linha])
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


def main():
    d = carregar_serie_tds()
    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(d)} meses ({d['Data'].iloc[0].date()} a {d['Data'].iloc[-1].date()})")
    print(f"Treino: {len(d) - HOLDOUT_MESES} meses | Holdout: {HOLDOUT_MESES} meses")
    print()

    print("--- Prophet ---")
    linha_prophet, prev_full_prophet = rodar_prophet(d)
    linha_prophet.update(validar_metodo(construir_fit_predict_prophet(), serie, treino_serie, holdout_serie))
    print(f"  Tendencia: {linha_prophet['tendencia_mgL_ano']:.3f} mg/L/ano (p={linha_prophet['tendencia_pvalor']:.4f})")
    print(f"  Holdout: RMSE={linha_prophet['rmse_holdout']:.2f}  MAE={linha_prophet['mae_holdout']:.2f}  R2={linha_prophet['r2_holdout']:.3f}  "
          f"MASE={linha_prophet['mase_holdout']:.3f}  sMAPE={linha_prophet['smape_holdout']:.2f}%")
    print(f"  CV (5 folds expansivos): RMSE={linha_prophet['cv_rmse_media']:.2f}±{linha_prophet['cv_rmse_desvio']:.2f}  "
          f"MASE={linha_prophet['cv_mase_media']:.3f}±{linha_prophet['cv_mase_desvio']:.3f}")
    for h in HORIZONTES_ANOS:
        baixo, alto = linha_prophet[f"ci90_low_{h}y"], linha_prophet[f"ci90_high_{h}y"]
        if not (np.isnan(baixo) or np.isnan(alto)):
            linha_prophet[f"ic90_width_{h}y"] = alto - baixo
        print(f"  +{h}a: {linha_prophet[f'forecast_{h}y']:.1f} mg/L  IC90% [{baixo:.1f}, {alto:.1f}]")
    print()

    gravar_resultados(linha_prophet)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(d, linha_prophet, prev_full_prophet)

    with iniciar_run(
        "prophet", "script_05_prophet_bayesiano", seed=SEED,
        janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
    ):
        logar_linha_resultado(linha_prophet)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
