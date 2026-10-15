"""
Baseline obrigatorio (bloco 3 do pedido de aprofundamento): naive. Nenhum
metodo mais sofisticado da bateria entra no relatorio final sem vencer este
baseline em MASE -- este script so estabelece o "piso", nao escolhe
finalistas.

IC90%: formula analitica classica de Hyndman (desvio-padrao dos residuos
historicos de passo-fixo, escalado por sqrt(horizonte) em unidades de
ciclo).

Univariado em TDS (mesma nota de desenho dos scripts 01-05): independe do
tratamento de ND do BOD.

D-73: naive sazonal, ETS/Holt-Winters e Theta, que rodavam junto neste
script, deixaram de ser reportados como metodo publico na reducao da
bateria para os 7 metodos citados na revisao externa de 14/10/2026 (que so
cita o naive simples na tabela 3.6) -- extraidos para
scripts/bateria_estendida/script_36_baselines_estendidos.py.
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
FIGURA_PATH = figure("baselines-tds.png")
warnings.filterwarnings("ignore")


def carregar_serie_tds() -> pd.Series:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    return pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def montar_forecast_horizontes(linha: dict, ultima_data, pontos, baixos, altos):
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = float(pontos[passo])
        linha[f"ci90_low_{h}y"] = float(baixos[passo])
        linha[f"ci90_high_{h}y"] = float(altos[passo])
        linha[f"ic90_width_{h}y"] = float(altos[passo] - baixos[passo])


def rodar_naive(s: pd.Series) -> dict:
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    resid = np.diff(treino.values)
    sigma = float(np.std(resid, ddof=1))
    z = stats.norm.ppf(1 - ALPHA / 2)

    pred_holdout = np.repeat(treino.values[-1], len(holdout))
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    max_passos = max(HORIZONTES_ANOS) * 12
    pontos = np.repeat(s.values[-1], max_passos)
    margens = z * sigma * np.sqrt(np.arange(1, max_passos + 1))
    baixos, altos = pontos - margens, pontos + margens

    linha = {
        "metodo": "naive", "tendencia_mgL_ano": 0.0, "tendencia_pvalor": float("nan"),
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
    }
    montar_forecast_horizontes(linha, s.index[-1], pontos, baixos, altos)
    return linha


def fit_predict_naive(treino: pd.Series, n_passos: int) -> np.ndarray:
    return np.repeat(treino.values[-1], n_passos)


def gerar_figura(s: pd.Series, linha: dict):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(s.index, s.values, color="black", linewidth=1, label="TDS observado")
    ultima_data = s.index[-1]
    anos_futuros = [0] + HORIZONTES_ANOS
    datas_futuras = [ultima_data + pd.DateOffset(months=int(a * 12)) for a in anos_futuros]
    pontos = [linha[f"forecast_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
    baixos = [linha[f"ci90_low_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
    altos = [linha[f"ci90_high_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
    ax.plot(datas_futuras, pontos, "--", color="gray", linewidth=1.4, label="naive (previsao)")
    ax.fill_between(datas_futuras, baixos, altos, color="gray", alpha=0.12)
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Baseline naive — previsao de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linha: dict):
    linha["script"] = "script_08_baselines"
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


def imprimir_resumo(linha: dict):
    print(f"--- {linha['metodo']} ---")
    print(f"  Holdout: RMSE={linha['rmse_holdout']:.2f}  MAE={linha['mae_holdout']:.2f}  R2={linha['r2_holdout']:.3f}  "
          f"MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
    print(f"  CV (5 folds expansivos): RMSE={linha['cv_rmse_media']:.2f}±{linha['cv_rmse_desvio']:.2f}  "
          f"MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}")
    print(f"  Backtest origem movel: MAE(+3a)={linha.get('backtest_mae_36m', float('nan')):.2f}  "
          f"MAE(+5a)={linha.get('backtest_mae_60m', float('nan')):.2f}")
    for h in HORIZONTES_ANOS:
        print(f"  +{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]")
    print()


def main():
    s = carregar_serie_tds()
    treino_serie, holdout_serie = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(s)} meses ({s.index[0].date()} a {s.index[-1].date()})")
    print(f"Treino: {len(s) - HOLDOUT_MESES} meses | Holdout: {HOLDOUT_MESES} meses")
    print()

    linha = rodar_naive(s)
    linha.update(validar_metodo(fit_predict_naive, s, treino_serie, holdout_serie))
    imprimir_resumo(linha)

    gravar_resultados(linha)
    print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(s, linha)

    with iniciar_run(
        "naive", "script_08_baselines",
        janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
    ):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
