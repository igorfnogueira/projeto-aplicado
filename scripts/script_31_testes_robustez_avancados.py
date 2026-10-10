"""
Bateria de 5 testes avancados de robustez/overfitting para a bateria de
previsao de TDS (issue #1 do repositorio, spec gerada via /to-spec).

Nao altera nenhum dos scripts 01-30 nem `results/resultados_comparacao.csv`
-- schema tidy proprio (item/variante/metrica/valor_metrica/pvalor/n), mesmo
padrao de `script_17_matriz_sensibilidade.py`:

  1. Cobertura empirica de IC90 (via `largura_e_cobertura_ic`, ja existia em
     utils/validacao_utils.py mas nunca tinha sido ligada a CV/backtest) para
     os metodos com incerteza nativa: Mann-Kendall/Theil-Sen/OLS, SARIMA e o
     hibrido SARIMA+Prophet. `detrend_rf` fica explicitamente de fora (sem IC
     nativo calibravel) -- isso e um achado documentado, nao um bug.
  2. Teste de Diebold-Mariano (correcao HLN de amostra pequena) entre os 3
     finalistas de script_15 + o runner-up imediato do ranking por
     mase_holdout entre os candidatos de script_14.
  3. Diagnostico de residuo OUT-OF-SAMPLE (Ljung-Box/Shapiro/ARCH, mesmas
     funcoes de script_14) dos mesmos 4 metodos, para comparar com o residuo
     IN-SAMPLE ja reportado por script_14.
  4. Tabela/figura do gap RMSE in-sample x CV x holdout para os mesmos 4
     metodos.
  5. Robustez do Mann-Kendall/Theil-Sen a remocao de cada ano da serie
     (leave-one-year-out).

Candidatos cobertos nos itens 2/3/4 (mesmo conjunto de script_14, menos a
regressao_bayesiana que reusa o residuo do OLS por decisao de escopo ja
registrada ali): ols, regressao_bayesiana, detrend_rf, sarima,
hibrido_arima_prophet.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.paths import bootstrap_sys_path, result, figure, RESULTADOS_COMPARACAO_CSV
bootstrap_sys_path()


import itertools
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX

from script_00_preprocessamento import construir_datasets
from script_01_mann_kendall_theilsen import sens_slope_estimate, sens_slope_ic
from script_02_arima_sarima import buscar_melhor_sarima
from script_03_random_forest_gridsearch import carregar_serie_tds, construir_features, FEATURES
from script_10_detrend_arvore import destendenciar, prever_recursivo_residuo
from script_14_diagnostico_residuos import (
    residuos_ols as residuos_ols_full,
    residuos_detrend_rf as residuos_detrend_rf_full,
    residuos_sarima as residuos_sarima_full,
    residuos_hibrido as residuos_hibrido_full,
    rodar_testes,
)
from script_15_sintese_final import FINALISTAS
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos
from utils.validacao_utils import (
    expanding_window_cv_com_ic,
    backtest_origem_movel_com_ic,
    resumir_cv_ic,
    resumir_backtest_ic,
)

warnings.filterwarnings("ignore")

HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
SEED = 42
CANDIDATOS = ["ols", "regressao_bayesiana", "detrend_rf", "sarima", "hibrido_arima_prophet"]
RESULTADOS_CSV = result("testes_robustez_resultados.csv")
RESULTADOS_JSON = result("testes_robustez_resultados.json")
FIGURA_PATH = figure("testes-robustez-avancados.png")


def carregar_dados():
    d = carregar_serie_tds()
    treino, holdout = d.iloc[:-HOLDOUT_MESES].reset_index(drop=True), d.iloc[-HOLDOUT_MESES:].reset_index(drop=True)
    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]
    return d, treino, holdout, serie, treino_serie, holdout_serie


def escolher_runner_up() -> str:
    """Runner-up = melhor mase_holdout entre os candidatos de script_14 que
    NAO sao finalistas de script_15 (ols/sarima)."""
    tabela = pd.read_csv(RESULTADOS_COMPARACAO_CSV)
    candidatos_nao_finalistas = [m for m in CANDIDATOS if m not in FINALISTAS]
    sub = tabela[tabela["metodo"].isin(candidatos_nao_finalistas)].sort_values("mase_holdout")
    return str(sub["metodo"].iloc[0])


# --------------------------------------------------------------------------
# Previsao em treino, avaliada no holdout (24 meses) -- usada nos itens 2 e 3
# --------------------------------------------------------------------------

def _holdout_pred_ols(treino: pd.DataFrame, holdout: pd.DataFrame):
    reg = stats.linregress(treino["t_anos"].values, treino["TDS_mgL"].values)
    pred = reg.intercept + reg.slope * holdout["t_anos"].values
    return holdout["TDS_mgL"].values, pred


def _holdout_pred_detrend_rf(treino: pd.DataFrame, holdout: pd.DataFrame):
    """IMPORTANTE: forecast RECURSIVO (lags alimentados pela propria previsao,
    nunca pelo valor real do holdout) -- achado do /code-review: usar "one-step
    com lags reais" aqui (a mesma convencao de rmse_holdout em script_10, que
    so avalia 1 passo a frente com o valor anterior VERDADEIRO conhecido)
    tornaria o erro de detrend_rf artificialmente pequeno e NAO comparavel ao
    de sarima/hibrido (forecast genuino de 24 passos a frente, sem espiar
    valores reais) -- invalidando o Diebold-Mariano do item 2. Aqui, em vez
    disso, reaproveita-se prever_recursivo_residuo (ja usada por script_10
    para o forecast de longo prazo), que alimenta cada passo com a PREVISAO
    anterior, exatamente como sarima/hibrido fazem a partir da mesma origem
    de treino."""
    treino_resid, reg_treino = destendenciar(treino)
    f_treino_resid = construir_features(treino_resid)
    modelo = RandomForestRegressor(random_state=SEED, n_estimators=300, min_samples_leaf=1, max_depth=10)
    modelo.fit(f_treino_resid[FEATURES], f_treino_resid["TDS_mgL"])

    pontos_resid = prever_recursivo_residuo(modelo, treino_resid, len(holdout))
    tendencia_holdout = reg_treino.intercept + reg_treino.slope * holdout["t_anos"].values
    pred = tendencia_holdout + np.array(pontos_resid)
    return holdout["TDS_mgL"].values, pred


def calcular_erros_holdout(treino, holdout, treino_serie, holdout_serie, ordem_sarima) -> dict:
    """Erro de holdout (y_true - y_pred) por candidato -- usado tanto no
    diagnostico de residuo out-of-sample (item 3) quanto no Diebold-Mariano
    (item 2), calculado uma unica vez e reaproveitado nos dois. `ordem_sarima`
    (order, seasonal_order, trend) e calculado uma unica vez em main() e
    reutilizado aqui e no item 1, para nao repetir a busca em grade (~72
    ajustes) mais de uma vez."""
    ordem, ordem_sazonal, trend = ordem_sarima
    erros = {}

    y_true, pred = _holdout_pred_ols(treino, holdout)
    erros["ols"] = y_true - pred
    erros["regressao_bayesiana"] = erros["ols"]  # mesma decisao de escopo de script_14

    y_true, pred = _holdout_pred_detrend_rf(treino, holdout)
    erros["detrend_rf"] = y_true - pred

    modelo = SARIMAX(treino_serie, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                      enforce_stationarity=False, enforce_invertibility=False)
    res_treino = modelo.fit(disp=False)
    pred_sarima = res_treino.get_forecast(steps=len(holdout_serie)).predicted_mean.values
    erros["sarima"] = holdout_serie.values - pred_sarima

    from prophet import Prophet
    df = pd.DataFrame({"ds": treino_serie.index, "y": treino_serie.values})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(df)
    fc = m.predict(pd.DataFrame({"ds": holdout_serie.index}))
    pred_hibrido = (pred_sarima + fc["yhat"].values) / 2
    erros["hibrido_arima_prophet"] = holdout_serie.values - pred_hibrido

    return erros


# --------------------------------------------------------------------------
# Item 5 -- leave-one-year-out para Mann-Kendall/Theil-Sen
# --------------------------------------------------------------------------

def rodar_item5_leave_one_year_out(d: pd.DataFrame) -> list:
    anos = sorted(d["Data"].dt.year.unique())
    linhas = []
    for ano in anos:
        sub = d[d["Data"].dt.year != ano].reset_index(drop=True)
        if len(sub) < 24:
            continue
        x, y = sub["t_anos"].values, sub["TDS_mgL"].values

        res_mk = mk.original_test(y)
        slope_mk, _, _ = sens_slope_estimate(x, y)
        linhas.append({
            "item": "5_leave_one_year_out", "variante": f"sem_{ano}", "metrica": "mann_kendall_sen_slope_mgL_ano",
            "valor_metrica": slope_mk, "pvalor": float(res_mk.p), "n": len(sub),
        })

        slope_ts, _, _, _ = stats.theilslopes(y, x, alpha=1 - ALPHA)
        _, p_tau = stats.kendalltau(x, y)
        linhas.append({
            "item": "5_leave_one_year_out", "variante": f"sem_{ano}", "metrica": "theil_sen_slope_mgL_ano",
            "valor_metrica": float(slope_ts), "pvalor": float(p_tau), "n": len(sub),
        })
    return linhas


# --------------------------------------------------------------------------
# Item 3 -- diagnostico de residuo out-of-sample (holdout) dos candidatos
# --------------------------------------------------------------------------

def rodar_item3_residuos_holdout(holdout: pd.DataFrame, erros_holdout: dict) -> list:
    datas_holdout = holdout["Data"].values
    linhas = []
    for metodo in CANDIDATOS:
        resultado = rodar_testes(metodo, datas_holdout, erros_holdout[metodo])
        for chave in ("ljung_box_pvalor", "shapiro_pvalor", "arch_pvalor"):
            nome_teste = chave.replace("_pvalor", "")
            linhas.append({
                "item": "3_residuos_holdout", "variante": f"{metodo}__{nome_teste}",
                "metrica": "pvalor", "valor_metrica": resultado[chave], "pvalor": resultado[chave],
                "n": resultado["n_residuos"],
            })
    return linhas


# --------------------------------------------------------------------------
# Item 2 -- Diebold-Mariano entre finalistas + runner-up
# --------------------------------------------------------------------------

def diebold_mariano(e1: np.ndarray, e2: np.ndarray, h: int = 1):
    """DM test (perda quadratica) com correcao de amostra pequena de
    Harvey-Leybourne-Newbold (1997). e1/e2 sao erros (y_true - y_pred) de
    dois metodos sobre o MESMO periodo de holdout."""
    e1, e2 = np.asarray(e1, dtype=float), np.asarray(e2, dtype=float)
    diff = e1 ** 2 - e2 ** 2
    n = len(diff)
    d_mean = diff.mean()
    gamma0 = np.var(diff, ddof=0)
    var_d = gamma0
    for k in range(1, h):
        cov = np.mean((diff[k:] - d_mean) * (diff[:-k] - d_mean))
        var_d += 2 * cov
    if var_d <= 0:
        return float("nan"), float("nan")
    dm_stat = d_mean / np.sqrt(var_d / n)
    correcao = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    dm_stat_corrigido = dm_stat * correcao
    p_valor = float(2 * (1 - stats.t.cdf(abs(dm_stat_corrigido), df=n - 1)))
    return float(dm_stat_corrigido), p_valor


def rodar_item2_diebold_mariano(erros_holdout: dict, runner_up: str) -> list:
    metodos = list(dict.fromkeys(FINALISTAS + [runner_up]))  # preserva ordem, sem duplicar
    linhas = []
    for metodo_a, metodo_b in itertools.combinations(metodos, 2):
        dm_stat, p_valor = diebold_mariano(erros_holdout[metodo_a], erros_holdout[metodo_b])
        linhas.append({
            "item": "2_diebold_mariano", "variante": f"{metodo_a}_vs_{metodo_b}",
            "metrica": "dm_stat", "valor_metrica": dm_stat, "pvalor": p_valor,
            "n": len(erros_holdout[metodo_a]),
        })
    return linhas


# --------------------------------------------------------------------------
# Item 4 -- gap RMSE in-sample x CV x holdout
# --------------------------------------------------------------------------

def rodar_item4_gap_overfitting(runner_up: str) -> list:
    tabela = pd.read_csv(RESULTADOS_COMPARACAO_CSV).set_index("metodo")
    residuos_full = {
        "ols": residuos_ols_full(),
        "detrend_rf": residuos_detrend_rf_full(),
        "sarima": residuos_sarima_full(),
        "hibrido_arima_prophet": residuos_hibrido_full(),
    }
    residuos_full["regressao_bayesiana"] = ("regressao_bayesiana", residuos_full["ols"][1], residuos_full["ols"][2])

    metodos = list(dict.fromkeys(FINALISTAS + [runner_up]))
    linhas = []
    for metodo in metodos:
        _, _, resid_in_sample = residuos_full[metodo]
        rmse_in_sample = float(np.sqrt(np.mean(np.asarray(resid_in_sample, dtype=float) ** 2)))
        linha_tabela = tabela.loc[metodo]
        for nome_metrica, valor in (
            ("rmse_in_sample", rmse_in_sample),
            ("rmse_cv", float(linha_tabela["cv_rmse_media"])),
            ("rmse_holdout", float(linha_tabela["rmse_holdout"])),
        ):
            linhas.append({
                "item": "4_gap_overfitting", "variante": metodo, "metrica": nome_metrica,
                "valor_metrica": valor, "pvalor": float("nan"), "n": float("nan"),
            })
    return linhas


def gerar_figura_item4(df: pd.DataFrame):
    item4 = df[df["item"] == "4_gap_overfitting"]
    if item4.empty:
        return
    pivot = item4.pivot(index="variante", columns="metrica", values="valor_metrica")
    pivot = pivot[["rmse_in_sample", "rmse_cv", "rmse_holdout"]]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(pivot))
    largura = 0.25
    for i, col in enumerate(pivot.columns):
        ax.bar(x + (i - 1) * largura, pivot[col].values, largura, label=col)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=15, fontsize=8)
    ax.set_ylabel("RMSE (mg/L)")
    ax.set_title("Gap in-sample x CV x holdout -- finalistas + runner-up")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


# --------------------------------------------------------------------------
# Item 1 -- cobertura empirica de IC90 (metodos com incerteza nativa)
# --------------------------------------------------------------------------

def _fit_predict_ic_linear(ajustar_fn):
    def fit_predict_ic(treino: pd.Series, n_passos: int):
        data0 = treino.index[0]
        t = (treino.index - data0).days / 365.25
        y = treino.values
        pred_fn_result = ajustar_fn(t, y)
        slope, intercept, slope_lo, slope_hi = pred_fn_result
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_futuro = (datas_futuras - data0).days / 365.25
        pred = intercept + slope * t_futuro
        lo = intercept + slope_lo * t_futuro
        hi = intercept + slope_hi * t_futuro
        return pred, np.minimum(lo, hi), np.maximum(lo, hi)
    return fit_predict_ic


def _ajustar_mk(t, y):
    slope, intercept, pares = sens_slope_estimate(t, y)
    res = mk.original_test(y)
    slope_lo, slope_hi = sens_slope_ic(pares, res.var_s, ALPHA)
    return slope, intercept, slope_lo, slope_hi


def _ajustar_theil_sen(t, y):
    slope, intercept, lo, hi = stats.theilslopes(y, t, alpha=1 - ALPHA)
    return slope, intercept, lo, hi


def _ajustar_ols(t, y):
    reg = stats.linregress(t, y)
    t_crit = stats.t.ppf(1 - ALPHA / 2, len(t) - 2)
    margem = t_crit * reg.stderr
    return reg.slope, reg.intercept, reg.slope - margem, reg.slope + margem


def _fit_predict_ic_sarima(ordem, ordem_sazonal, trend):
    def fit_predict_ic(treino: pd.Series, n_passos: int):
        modelo = SARIMAX(treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                          enforce_stationarity=False, enforce_invertibility=False)
        res = modelo.fit(disp=False)
        prev = res.get_forecast(steps=n_passos)
        pred = prev.predicted_mean.values
        ic = prev.conf_int(alpha=ALPHA)
        return pred, ic.iloc[:, 0].values, ic.iloc[:, 1].values
    return fit_predict_ic


def _fit_predict_ic_hibrido(ordem, ordem_sazonal, trend):
    from prophet import Prophet
    fit_sarima_ic = _fit_predict_ic_sarima(ordem, ordem_sazonal, trend)

    def fit_predict_ic(treino: pd.Series, n_passos: int):
        pred_sarima, ic_low, ic_high = fit_sarima_ic(treino, n_passos)
        df = pd.DataFrame({"ds": treino.index, "y": treino.values})
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m.fit(df)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        fc = m.predict(pd.DataFrame({"ds": datas_futuras}))
        pred = (pred_sarima + fc["yhat"].values) / 2
        return pred, ic_low, ic_high  # IC do SARIMA usado como proxy (decisao de escopo)
    return fit_predict_ic


def rodar_item1_cobertura_ic(serie: pd.Series, ordem_sarima) -> list:
    ordem, ordem_sazonal, trend = ordem_sarima

    fit_predicts_ic = {
        "mann_kendall_sen": _fit_predict_ic_linear(_ajustar_mk),
        "theil_sen": _fit_predict_ic_linear(_ajustar_theil_sen),
        "ols": _fit_predict_ic_linear(_ajustar_ols),
        "sarima": _fit_predict_ic_sarima(ordem, ordem_sazonal, trend),
        "hibrido_arima_prophet": _fit_predict_ic_hibrido(ordem, ordem_sazonal, trend),
    }

    linhas = []
    for metodo, fit_predict_ic in fit_predicts_ic.items():
        df_cv = expanding_window_cv_com_ic(serie, fit_predict_ic, n_folds=5, horizonte=12, min_treino=60)
        resumo_cv = resumir_cv_ic(df_cv)
        df_bt = backtest_origem_movel_com_ic(serie, fit_predict_ic, min_treino=60)
        resumo_bt = resumir_backtest_ic(df_bt)

        # SARIMA/hibrido tem ordem FIXA (decisao de escopo, mesma de script_02)
        # -- quando refeito num fold inicial com pouco treino (perto de
        # min_treino=60), o ajuste pode ficar numericamente instavel e o IC
        # explodir (visto na pratica: largura ~1e10 num fold vs. ~250-300 nos
        # demais). Isso DISTORCE a media -- em vez de escondido, e reportado
        # como aviso explicito (achado relevante: a ordem escolhida no treino
        # inteiro nao e robusta o suficiente para refit em janelas curtas).
        larguras_fold = df_cv["ic90_largura_media"].values
        mediana_largura = float(np.median(larguras_fold))
        if mediana_largura > 0 and larguras_fold.max() > 10 * mediana_largura:
            fold_instavel = int(df_cv.loc[df_cv["ic90_largura_media"].idxmax(), "fold"])
            print(f"  AVISO [{metodo}]: fold {fold_instavel} com IC90 numericamente instavel "
                  f"(largura={larguras_fold.max():.3g} vs. mediana dos demais folds={mediana_largura:.3g}) -- "
                  f"a media cv_ic90_largura_media fica distorcida por esse fold; ver mediana abaixo.")
            linhas.append({
                "item": "1_cobertura_ic", "variante": metodo, "metrica": "cv_ic90_largura_mediana_folds",
                "valor_metrica": mediana_largura, "pvalor": float("nan"), "n": len(df_cv),
            })
            linhas.append({
                "item": "1_cobertura_ic", "variante": metodo, "metrica": "fold_instavel_flag",
                "valor_metrica": 1.0, "pvalor": float("nan"), "n": len(df_cv),
            })

        linhas.append({
            "item": "1_cobertura_ic", "variante": metodo, "metrica": "cv_ic90_cobertura_pct",
            "valor_metrica": resumo_cv["cv_ic90_cobertura_pct"], "pvalor": float("nan"), "n": len(df_cv),
        })
        linhas.append({
            "item": "1_cobertura_ic", "variante": metodo, "metrica": "cv_ic90_largura_media",
            "valor_metrica": resumo_cv["cv_ic90_largura_media"], "pvalor": float("nan"), "n": len(df_cv),
        })
        for h in (36, 60):
            chave_cobertura = f"backtest_ic90_cobertura_pct_{h}m"
            if chave_cobertura in resumo_bt:
                linhas.append({
                    "item": "1_cobertura_ic", "variante": metodo, "metrica": chave_cobertura,
                    "valor_metrica": resumo_bt[chave_cobertura], "pvalor": float("nan"),
                    "n": int((df_bt["horizonte_meses"] == h).sum()),
                })

    linhas.append({
        "item": "1_cobertura_ic", "variante": "detrend_rf", "metrica": "excluido_sem_ic_nativo",
        "valor_metrica": float("nan"), "pvalor": float("nan"), "n": 0,
    })
    return linhas


def gravar_resultados(linhas: list):
    df = pd.DataFrame(linhas)
    df["script"] = "script_31_testes_robustez_avancados"
    df["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    df.to_csv(RESULTADOS_CSV, index=False)
    df.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)
    return df


def main():
    d, treino, holdout, serie, treino_serie, holdout_serie = carregar_dados()
    print(f"Serie TDS: {len(d)} meses ({d['Data'].iloc[0].date()} a {d['Data'].iloc[-1].date()})")

    runner_up = escolher_runner_up()
    print(f"Runner-up (melhor mase_holdout fora dos finalistas, entre ols/sarima): {runner_up}")
    print(f"Finalistas: {FINALISTAS}")
    print()

    with iniciar_run("testes_robustez_avancados", "script_31_testes_robustez_avancados",
                      params={"runner_up": runner_up, "finalistas": ",".join(FINALISTAS)}):
        print("=== Item 5: leave-one-year-out (Mann-Kendall/Theil-Sen) ===")
        linhas_item5 = rodar_item5_leave_one_year_out(d)
        print(f"  {len(linhas_item5)} linhas geradas")
        print()

        print("=== Buscando ordem SARIMA (reaproveitada nos itens 1, 2 e 3) ===")
        _, ordem, ordem_sazonal, trend, _ = buscar_melhor_sarima(treino_serie)
        ordem_sarima = (ordem, ordem_sazonal, trend)
        print(f"  order={ordem} seasonal_order={ordem_sazonal} trend={trend}")
        print()

        print("=== Calculando erros de holdout (usados nos itens 2 e 3) ===")
        erros_holdout = calcular_erros_holdout(treino, holdout, treino_serie, holdout_serie, ordem_sarima)
        print()

        print("=== Item 3: residuo out-of-sample (holdout) dos candidatos ===")
        linhas_item3 = rodar_item3_residuos_holdout(holdout, erros_holdout)
        for l in linhas_item3:
            print(f"  {l['variante']:40s} p={l['valor_metrica']:.4f}")
        print()

        print("=== Item 2: Diebold-Mariano (finalistas + runner-up) ===")
        linhas_item2 = rodar_item2_diebold_mariano(erros_holdout, runner_up)
        for l in linhas_item2:
            print(f"  {l['variante']:45s} dm_stat={l['valor_metrica']:.3f}  p={l['pvalor']:.4f}")
        print()

        print("=== Item 4: gap RMSE in-sample x CV x holdout ===")
        linhas_item4 = rodar_item4_gap_overfitting(runner_up)
        for l in linhas_item4:
            print(f"  {l['variante']:25s} {l['metrica']:15s} = {l['valor_metrica']:.3f}")
        print()

        print("=== Item 1: cobertura empirica de IC90 (metodos com IC nativo) ===")
        linhas_item1 = rodar_item1_cobertura_ic(serie, ordem_sarima)
        for l in linhas_item1:
            print(f"  {l['variante']:22s} {l['metrica']:30s} = {l['valor_metrica']}")
        print()

        todas_linhas = linhas_item5 + linhas_item3 + linhas_item2 + linhas_item4 + linhas_item1
        df = gravar_resultados(todas_linhas)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

        gerar_figura_item4(df)

        metricas = {}
        for _, row in df.iterrows():
            if pd.notna(row["valor_metrica"]):
                chave = f"{row['item']}__{row['variante']}__{row['metrica']}"[:250]
                metricas[chave] = row["valor_metrica"]
        logar_metricas(metricas)
        if FIGURA_PATH.exists():
            logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
