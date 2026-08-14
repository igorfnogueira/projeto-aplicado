"""
Baselines obrigatorios (bloco 3 do pedido de aprofundamento): naive, naive
sazonal (m=12), ETS/Holt-Winters e Theta. Nenhum metodo mais sofisticado da
bateria (scripts 01-05, e os que vierem depois) entra no relatorio final sem
vencer estes baselines em MASE -- este script so estabelece o "piso", nao
escolhe finalistas.

O termo sazonal do ETS e o deseasonalize do Theta sao condicionados ao
achado de forca de sazonalidade (Fs) do script_07
(diagnostico_serie_resultados.json) -- Fs>0.64 (limiar de referencia ja usado
em script_07) liga a sazonalidade, caso contrario ela fica desligada. Se
script_07 ainda nao rodou, assume conservadoramente Fs=0 (sem sazonalidade).

IC90%: naive e naive sazonal usam a formula analitica classica de Hyndman
(desvio-padrao dos residuos historicos de passo-fixo, escalado por
sqrt(horizonte) em unidades de ciclo) -- nao ha biblioteca pronta para essas
duas. ETS e Theta usam o IC nativo de cada implementacao do statsmodels
(simulacao no ETS, formula fechada no Theta).

Univariado em TDS (mesma nota de desenho dos scripts 01-05): independe do
tratamento de ND do BOD.
"""

import json
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.forecasting.theta import ThetaModel

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
PERIODO_SAZONAL = 12
LIMIAR_FS_SAZONAL = 0.64  # mesmo limiar de referencia usado em script_07
DIAGNOSTICO_JSON = "diagnostico_serie_resultados.json"
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/baselines-tds.png"

warnings.filterwarnings("ignore")


def carregar_serie_tds() -> pd.Series:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    return pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))


def carregar_usa_sazonalidade() -> bool:
    try:
        with open(DIAGNOSTICO_JSON, encoding="utf-8") as f:
            diag = json.load(f)
        fs = float(diag["forca_sazonalidade_Fs"])
        print(f"  Forca de sazonalidade (script_07): Fs={fs:.3f} -> "
              f"{'sazonalidade LIGADA' if fs > LIMIAR_FS_SAZONAL else 'sazonalidade DESLIGADA'} nos baselines")
        return fs > LIMIAR_FS_SAZONAL
    except Exception:
        print(f"  Aviso: {DIAGNOSTICO_JSON} nao encontrado (rode script_07 primeiro) -- "
              f"assumindo Fs=0 (sazonalidade desligada) conservadoramente.")
        return False


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def tendencia_implicita(pontos_10a: np.ndarray) -> tuple:
    reg = stats.linregress(np.arange(len(pontos_10a)), pontos_10a)
    return reg.slope * 12, reg.pvalue


def montar_forecast_horizontes(linha: dict, ultima_data, pontos, baixos, altos):
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = float(pontos[passo])
        linha[f"ci90_low_{h}y"] = float(baixos[passo])
        linha[f"ci90_high_{h}y"] = float(altos[passo])
        linha[f"ic90_width_{h}y"] = float(altos[passo] - baixos[passo])


# --------------------------------------------------------------------------
# Naive e naive sazonal -- IC90 analitico (Hyndman): sigma dos residuos de
# passo-fixo, escalado por sqrt(horizonte em unidades de ciclo)
# --------------------------------------------------------------------------

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


def rodar_naive_sazonal(s: pd.Series, m: int = PERIODO_SAZONAL) -> dict:
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    resid = treino.values[m:] - treino.values[:-m]
    sigma = float(np.std(resid, ddof=1))
    z = stats.norm.ppf(1 - ALPHA / 2)

    ultimos_m_treino = treino.values[-m:]
    pred_holdout = np.array([ultimos_m_treino[i % m] for i in range(len(holdout))])
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    max_passos = max(HORIZONTES_ANOS) * 12
    ultimos_m = s.values[-m:]
    pontos = np.array([ultimos_m[i % m] for i in range(max_passos)])
    ciclos = np.array([i // m + 1 for i in range(max_passos)])
    margens = z * sigma * np.sqrt(ciclos)
    baixos, altos = pontos - margens, pontos + margens

    linha = {
        "metodo": "naive_sazonal", "tendencia_mgL_ano": 0.0, "tendencia_pvalor": float("nan"),
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
    }
    montar_forecast_horizontes(linha, s.index[-1], pontos, baixos, altos)
    return linha


def fit_predict_naive_sazonal(treino: pd.Series, n_passos: int, m: int = PERIODO_SAZONAL) -> np.ndarray:
    ultimos_m = treino.values[-m:]
    return np.array([ultimos_m[i % m] for i in range(n_passos)])


# --------------------------------------------------------------------------
# ETS / Holt-Winters (aditivo; sazonalidade condicionada ao Fs de script_07)
# --------------------------------------------------------------------------

def ajustar_ets(serie: pd.Series, sazonal: bool):
    modelo = ETSModel(
        serie, error="add", trend="add", damped_trend=False,
        seasonal="add" if sazonal else None,
        seasonal_periods=PERIODO_SAZONAL if sazonal else None,
    )
    return modelo.fit(disp=False)


def rodar_ets(s: pd.Series, sazonal: bool) -> dict:
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    res_treino = ajustar_ets(treino, sazonal)
    pred_holdout = res_treino.forecast(len(holdout)).values
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    res_full = ajustar_ets(s, sazonal)
    max_passos = max(HORIZONTES_ANOS) * 12
    pontos = res_full.forecast(max_passos).values
    n = len(s)
    ic = res_full.get_prediction(start=n, end=n + max_passos - 1).summary_frame(alpha=ALPHA)
    baixos, altos = ic["pi_lower"].values, ic["pi_upper"].values

    tend, tend_p = tendencia_implicita(pontos[: 10 * 12])
    linha = {
        "metodo": "ets_holt_winters", "tendencia_mgL_ano": tend, "tendencia_pvalor": tend_p,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "hiperparametros": str({"error": "add", "trend": "add", "seasonal": "add" if sazonal else None}),
    }
    montar_forecast_horizontes(linha, s.index[-1], pontos, baixos, altos)
    return linha


def construir_fit_predict_ets(sazonal: bool):
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        res = ajustar_ets(treino, sazonal)
        return res.forecast(n_passos).values
    return fit_predict


# --------------------------------------------------------------------------
# Theta (deseasonalize condicionado ao Fs de script_07)
# --------------------------------------------------------------------------

def ajustar_theta(serie: pd.Series, sazonal: bool):
    modelo = ThetaModel(serie, period=PERIODO_SAZONAL, deseasonalize=sazonal)
    return modelo.fit()


def rodar_theta(s: pd.Series, sazonal: bool) -> dict:
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    res_treino = ajustar_theta(treino, sazonal)
    pred_holdout = res_treino.forecast(len(holdout)).values
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    res_full = ajustar_theta(s, sazonal)
    max_passos = max(HORIZONTES_ANOS) * 12
    pontos = res_full.forecast(max_passos).values
    ic = res_full.prediction_intervals(steps=max_passos, alpha=ALPHA)
    baixos, altos = ic.iloc[:, 0].values, ic.iloc[:, 1].values

    tend, tend_p = tendencia_implicita(pontos[: 10 * 12])
    linha = {
        "metodo": "theta", "tendencia_mgL_ano": tend, "tendencia_pvalor": tend_p,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "hiperparametros": str({"deseasonalize": sazonal, "period": PERIODO_SAZONAL}),
    }
    montar_forecast_horizontes(linha, s.index[-1], pontos, baixos, altos)
    return linha


def construir_fit_predict_theta(sazonal: bool):
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        res = ajustar_theta(treino, sazonal)
        return res.forecast(n_passos).values
    return fit_predict


# --------------------------------------------------------------------------

def gerar_figura(s: pd.Series, linhas: list):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(s.index, s.values, color="black", linewidth=1, label="TDS observado")
    cores = {"naive": "gray", "naive_sazonal": "tab:olive", "ets_holt_winters": "tab:pink", "theta": "tab:cyan"}
    ultima_data = s.index[-1]
    for linha in linhas:
        metodo = linha["metodo"]
        anos_futuros = [0] + HORIZONTES_ANOS
        datas_futuras = [ultima_data + pd.DateOffset(months=int(a * 12)) for a in anos_futuros]
        pontos = [linha[f"forecast_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
        baixos = [linha[f"ci90_low_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
        altos = [linha[f"ci90_high_{h}y"] if h > 0 else s.values[-1] for h in anos_futuros]
        cor = cores.get(metodo, "gray")
        ax.plot(datas_futuras, pontos, "--", color=cor, label=f"{metodo} (previsao)")
        ax.fill_between(datas_futuras, baixos, altos, color=cor, alpha=0.12)
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Baselines — previsao de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_08_baselines"
        linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
        linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame(linhas)
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
    sazonal = carregar_usa_sazonalidade()
    print()

    linhas = [
        rodar_naive(s),
        rodar_naive_sazonal(s),
        rodar_ets(s, sazonal),
        rodar_theta(s, sazonal),
    ]
    fit_predicts = {
        "naive": fit_predict_naive,
        "naive_sazonal": fit_predict_naive_sazonal,
        "ets_holt_winters": construir_fit_predict_ets(sazonal),
        "theta": construir_fit_predict_theta(sazonal),
    }

    for linha in linhas:
        linha.update(validar_metodo(fit_predicts[linha["metodo"]], s, treino_serie, holdout_serie))
        imprimir_resumo(linha)

    gravar_resultados(linhas)
    print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(s, linhas)

    for linha in linhas:
        with iniciar_run(
            linha["metodo"], "script_08_baselines",
            params={"sazonalidade_ligada": sazonal},
            janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
        ):
            logar_linha_resultado(linha)
            logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
