"""
Estatística clássica de tendência para o TDS (plano_projeto_TDS.md secao 3.a):
  - Mann-Kendall + inclinação de Sen (teste não-parametrico de tendência monotona)
  - Theil-Sen (estimador robusto de inclinação, pareado com o teste de Kendall's tau)
  - OLS (regressão linear classica)

Nota de desenho: os tres metodos usam apenas a serie TDS_mgL (univariados no
tempo). Como TDS_mgL e identico nos dois datasets canonicos gerados pelo
script_00 (a diferenca entre eles esta so no BOD), rodar este script contra
dataset_canonico_bod_mdl2.csv ou dataset_canonico_bod_zero.csv produz o
MESMO resultado. Por isso ele le a serie TDS diretamente via
construir_datasets() do script_00 (uma unica vez), em vez de rodar 2x. A
distincao de tratamento de ND do BOD volta a importar a partir da analise de
correlacao TDS-BOD (objetivo 3 do projeto), nao nestes 3 metodos.

Cada metodo grava uma linha em resultados_comparacao.csv/.json com:
RMSE/MAE/R2 em holdout, tendencia (mg/L/ano) com p-valor, e previsao pontual +
IC90% para +10/+15/+20 anos a partir do ultimo dado observado.
"""

import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/tendencia-tds.png"


def carregar_serie_tds() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    return d


def sens_slope_pares(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    n = len(x)
    pares = []
    for i in range(n - 1):
        dx = x[i + 1:] - x[i]
        dy = y[i + 1:] - y[i]
        validos = dx != 0
        pares.append(dy[validos] / dx[validos])
    return np.sort(np.concatenate(pares))


def sens_slope_estimate(x: np.ndarray, y: np.ndarray):
    """Inclinacao de Sen (mediana das inclinacoes par a par) e intercepto
    associado (mediana de y menos inclinacao vezes mediana de x) — calculado
    diretamente sobre as unidades reais de x (anos), em vez de assumir passo
    unitario como o pymannkendall.original_test faz internamente."""
    inclinacoes = sens_slope_pares(x, y)
    slope = float(np.median(inclinacoes))
    intercept = float(np.median(y) - slope * np.median(x))
    return slope, intercept, inclinacoes


def sens_slope_ic(inclinacoes: np.ndarray, var_s: float, alpha: float = 0.10):
    """IC da inclinacao de Sen pelo metodo nao-parametrico (Gilbert, 1987),
    usando a variancia do estatistico S ja calculada pelo teste de Mann-Kendall
    (var_s independe da escala de x, so depende dos ranks/empates de y)."""
    N = len(inclinacoes)
    z = stats.norm.ppf(1 - alpha / 2)
    c_alpha = z * np.sqrt(var_s)
    m1 = int(np.floor((N - c_alpha) / 2))
    m2 = int(np.ceil((N + c_alpha) / 2))
    m1 = max(m1, 0)
    m2 = min(m2, N - 1)
    return inclinacoes[m1], inclinacoes[m2]


def metrica_holdout(y_true, y_pred):
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def horizonte_t(d: pd.DataFrame, anos: float) -> float:
    return d["t_anos"].iloc[-1] + anos


def rodar_mann_kendall_sen(d: pd.DataFrame, treino: pd.DataFrame, holdout: pd.DataFrame) -> dict:
    # ajuste em treino (inclinacao de Sen em t_anos reais), para metricas de holdout
    slope_tr, intercept_tr, _ = sens_slope_estimate(treino["t_anos"].values, treino["TDS_mgL"].values)
    pred_holdout = intercept_tr + slope_tr * holdout["t_anos"].values
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    # teste de significancia de Mann-Kendall (p-valor e var_s independem da escala de x)
    res_full = mk.original_test(d["TDS_mgL"].values)
    # inclinacao/intercepto de Sen na serie completa, em mg/L/ano reais
    x = d["t_anos"].values
    slope_full, intercept_full, pares = sens_slope_estimate(x, d["TDS_mgL"].values)
    slope_lo, slope_hi = sens_slope_ic(pares, res_full.var_s, ALPHA)

    linha = {
        "metodo": "mann_kendall_sen",
        "tendencia_mgL_ano": slope_full,
        "tendencia_pvalor": res_full.p,
        "tendencia_ic90_baixo": slope_lo,
        "tendencia_ic90_alto": slope_hi,
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
    }
    for h in HORIZONTES_ANOS:
        t_h = horizonte_t(d, h)
        ponto = intercept_full + slope_full * t_h
        # banda de incerteza da tendencia (nao inclui ruido residual) propagada ao horizonte
        lo = intercept_full + slope_lo * t_h
        hi = intercept_full + slope_hi * t_h
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = min(lo, hi)
        linha[f"ci90_high_{h}y"] = max(lo, hi)
    return linha


def rodar_theil_sen(d: pd.DataFrame, treino: pd.DataFrame, holdout: pd.DataFrame) -> dict:
    slope_t, intercept_t, lo_t, hi_t = stats.theilslopes(
        treino["TDS_mgL"].values, treino["t_anos"].values, alpha=1 - ALPHA
    )
    pred_holdout = intercept_t + slope_t * holdout["t_anos"].values
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    slope_f, intercept_f, lo_f, hi_f = stats.theilslopes(
        d["TDS_mgL"].values, d["t_anos"].values, alpha=1 - ALPHA
    )
    # significancia pareada ao Theil-Sen: teste de Kendall's tau (mesma hipotese monotona)
    tau, p_tau = stats.kendalltau(d["t_anos"].values, d["TDS_mgL"].values)

    linha = {
        "metodo": "theil_sen",
        "tendencia_mgL_ano": slope_f,
        "tendencia_pvalor": p_tau,
        "tendencia_ic90_baixo": lo_f,
        "tendencia_ic90_alto": hi_f,
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
    }
    for h in HORIZONTES_ANOS:
        t_h = horizonte_t(d, h)
        ponto = intercept_f + slope_f * t_h
        lo = intercept_f + lo_f * t_h
        hi = intercept_f + hi_f * t_h
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = min(lo, hi)
        linha[f"ci90_high_{h}y"] = max(lo, hi)
    return linha


def rodar_ols(d: pd.DataFrame, treino: pd.DataFrame, holdout: pd.DataFrame) -> dict:
    reg_treino = stats.linregress(treino["t_anos"].values, treino["TDS_mgL"].values)
    pred_holdout = reg_treino.intercept + reg_treino.slope * holdout["t_anos"].values
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    reg_full = stats.linregress(d["t_anos"].values, d["TDS_mgL"].values)
    n = len(d)
    x = d["t_anos"].values
    y = d["TDS_mgL"].values
    y_hat = reg_full.intercept + reg_full.slope * x
    resid = y - y_hat
    dof = n - 2
    s_err = np.sqrt(np.sum(resid ** 2) / dof)
    x_mean = x.mean()
    sxx = np.sum((x - x_mean) ** 2)
    t_crit = stats.t.ppf(1 - ALPHA / 2, dof)

    linha = {
        "metodo": "ols",
        "tendencia_mgL_ano": reg_full.slope,
        "tendencia_pvalor": reg_full.pvalue,
        "tendencia_ic90_baixo": reg_full.slope - t_crit * reg_full.stderr,
        "tendencia_ic90_alto": reg_full.slope + t_crit * reg_full.stderr,
        "rmse_holdout": rmse,
        "mae_holdout": mae,
        "r2_holdout": r2,
    }
    for h in HORIZONTES_ANOS:
        t_h = horizonte_t(d, h)
        ponto = reg_full.intercept + reg_full.slope * t_h
        # intervalo de previsao (predicao de novo ponto), inclui variancia residual
        se_pred = s_err * np.sqrt(1 + 1 / n + (t_h - x_mean) ** 2 / sxx)
        margem = t_crit * se_pred
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = ponto - margem
        linha[f"ci90_high_{h}y"] = ponto + margem
    return linha


def construir_serie_indexada(d: pd.DataFrame) -> pd.Series:
    return pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))


def construir_fit_predict_linear(ajustar_fn):
    """Adaptador generico (validacao_utils.validar_metodo) para os 3 metodos
    deste script, todos de tendencia linear (slope, intercept): treina em
    `treino` (serie com DatetimeIndex) e extrapola os proximos n_passos
    meses em t_anos reais, a partir da mesma origem temporal do treino."""
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        data0 = treino.index[0]
        t = (treino.index - data0).days / 365.25
        slope, intercept = ajustar_fn(t.values, treino.values)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_futuro = (datas_futuras - data0).days / 365.25
        return intercept + slope * t_futuro
    return fit_predict


FIT_PREDICTS = {
    "mann_kendall_sen": construir_fit_predict_linear(lambda t, y: sens_slope_estimate(t, y)[:2]),
    "theil_sen": construir_fit_predict_linear(lambda t, y: tuple(stats.theilslopes(y, t)[:2])),
    "ols": construir_fit_predict_linear(lambda t, y: (lambda r: (r.slope, r.intercept))(stats.linregress(t, y))),
}


def gravar_resultados(linhas: list):
    for linha in linhas:
        linha["script"] = "script_01_mann_kendall_theilsen"
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


def gerar_figura(d: pd.DataFrame, linhas: list):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(d["Data"], d["TDS_mgL"], color="black", linewidth=1, label="TDS observado")

    ultima_data = d["Data"].iloc[-1]
    cores = {"mann_kendall_sen": "tab:blue", "theil_sen": "tab:green", "ols": "tab:red"}
    for linha in linhas:
        metodo = linha["metodo"]
        t0 = d["t_anos"].iloc[-1]
        anos_futuros = [0] + HORIZONTES_ANOS
        datas_futuras = [ultima_data + pd.Timedelta(days=365.25 * a) for a in anos_futuros]
        pontos = [linha[f"forecast_{h}y"] if h > 0 else d["TDS_mgL"].iloc[-1] for h in anos_futuros]
        baixos = [linha[f"ci90_low_{h}y"] if h > 0 else d["TDS_mgL"].iloc[-1] for h in anos_futuros]
        altos = [linha[f"ci90_high_{h}y"] if h > 0 else d["TDS_mgL"].iloc[-1] for h in anos_futuros]
        cor = cores.get(metodo, "gray")
        ax.plot(datas_futuras, pontos, "--", color=cor, label=f"{metodo} (previsao)")
        ax.fill_between(datas_futuras, baixos, altos, color=cor, alpha=0.12)

    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Tendencia observada e previsao de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def main():
    d = carregar_serie_tds()
    treino = d.iloc[:-HOLDOUT_MESES].reset_index(drop=True)
    holdout = d.iloc[-HOLDOUT_MESES:].reset_index(drop=True)
    serie = construir_serie_indexada(d)
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]

    print(f"Serie TDS: {len(d)} meses ({d['Data'].iloc[0].date()} a {d['Data'].iloc[-1].date()})")
    print(f"Treino: {len(treino)} meses | Holdout: {len(holdout)} meses (ultimos {HOLDOUT_MESES})")
    print()

    linhas = [
        rodar_mann_kendall_sen(d, treino, holdout),
        rodar_theil_sen(d, treino, holdout),
        rodar_ols(d, treino, holdout),
    ]

    for linha in linhas:
        metodo = linha["metodo"]
        linha.update(validar_metodo(FIT_PREDICTS[metodo], serie, treino_serie, holdout_serie))
        for h in HORIZONTES_ANOS:
            baixo, alto = linha[f"ci90_low_{h}y"], linha[f"ci90_high_{h}y"]
            if not (np.isnan(baixo) or np.isnan(alto)):
                linha[f"ic90_width_{h}y"] = alto - baixo

        print(f"--- {metodo} ---")
        print(f"  Tendencia: {linha['tendencia_mgL_ano']:.3f} mg/L/ano (p={linha['tendencia_pvalor']:.4f}, "
              f"IC90% [{linha['tendencia_ic90_baixo']:.3f}, {linha['tendencia_ic90_alto']:.3f}])")
        print(f"  Holdout: RMSE={linha['rmse_holdout']:.2f}  MAE={linha['mae_holdout']:.2f}  R2={linha['r2_holdout']:.3f}  "
              f"MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
        print(f"  CV (5 folds expansivos): RMSE={linha['cv_rmse_media']:.2f}±{linha['cv_rmse_desvio']:.2f}  "
              f"MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}")
        print(f"  Backtest origem movel: MAE(+3a)={linha.get('backtest_mae_36m', float('nan')):.2f}  "
              f"MAE(+5a)={linha.get('backtest_mae_60m', float('nan')):.2f}")
        for h in HORIZONTES_ANOS:
            print(f"  +{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]")
        print()

    gravar_resultados(linhas)
    print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")
    gerar_figura(d, linhas)

    for linha in linhas:
        with iniciar_run(
            linha["metodo"], "script_01_mann_kendall_theilsen",
            params={"alpha_ic": ALPHA},
            janela_treino_holdout={"treino_meses": len(treino), "holdout_meses": len(holdout)},
        ):
            logar_linha_resultado(linha)
            logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
