"""
Bateria de 5 testes avancados de robustez/overfitting para a bateria de
previsao de TDS (issue #1 do repositorio, spec gerada via /to-spec).

Nao altera nenhum dos scripts 01-30 nem `results/resultados_comparacao.csv`
-- schema tidy proprio (item/variante/metrica/valor_metrica/pvalor/n), mesmo
padrao de `script_17_matriz_sensibilidade.py`:

  1. Cobertura empirica de IC90 (via `largura_e_cobertura_ic`, ja existia em
     utils/validacao_utils.py mas nunca tinha sido ligada a CV/backtest) para
     os metodos com incerteza nativa: Mann-Kendall/Theil-Sen/OLS e SARIMA,
     nativa, `detrend_rf` via bootstrap de residuo (issue #11 -- mesma
     tecnica ja usada em script_09/SVR, bateria estendida), e Prophet via seu
     proprio `yhat_lower`/`yhat_upper` (interval_width=0.90, 2026-10-18,
     achado de `/revisao-academica`: era o unico dos 7 metodos do nucleo
     publico com IC90 nativo nunca testado por este script -- o texto do
     manuscrito generalizava "nenhum tem IC90 bem calibrado" para os 7 sem
     ter testado este). Achado: a cobertura empirica do IC90 do `detrend_rf`
     ficou em ~27% (pior ate que MK/Theil-Sen/OLS, ~37%), confirmando
     quantitativamente a limitacao ja registrada no manuscrito ("IC subestima
     a incerteza total").
  2. Teste de Diebold-Mariano (correcao HLN de amostra pequena) entre os
     CANDIDATOS + o baseline naive (adicionado em 2026-10-15, por pedido
     explicito de revisao: a tabela de MASE ja mostra o naive como o melhor
     da bateria no holdout, mas faltava o teste formal de que essa diferenca
     e estatisticamente significativa, nao so leitura visual da tabela).
  3. Diagnostico de residuo OUT-OF-SAMPLE (Ljung-Box/Shapiro/ARCH, mesmas
     funcoes de script_14) dos mesmos candidatos, para comparar com o residuo
     IN-SAMPLE ja reportado por script_14.
  4. Tabela/figura do gap RMSE in-sample x CV x holdout para os mesmos
     candidatos.
  5. Robustez do Mann-Kendall/Theil-Sen a remocao de cada ano da serie
     (leave-one-year-out).

D-73 (2026-10-15): CANDIDATOS reduzido de 5 para 3 (ols, detrend_rf, sarima)
na reducao da bateria publica para os 7 metodos citados na revisao externa
de 14/10/2026 -- regressao_bayesiana e hibrido_arima_prophet saem da bateria
publica (ver scripts/bateria_estendida/). CANDIDATOS continua uma lista
fixa, independente de qualquer lista de "finalistas" (ja nao existe mais
esse conceito desde script_15 -- ver ADR-0002, que corrigiu exatamente esse
acoplamento antes de ele voltar a existir aqui).
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
    rodar_testes,
)
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
CANDIDATOS = ["ols", "detrend_rf", "sarima"]
RESULTADOS_CSV = result("testes_robustez_resultados.csv")
RESULTADOS_JSON = result("testes_robustez_resultados.json")
FIGURA_PATH = figure("testes-robustez-avancados.png")


def carregar_dados():
    d = carregar_serie_tds()
    treino, holdout = d.iloc[:-HOLDOUT_MESES].reset_index(drop=True), d.iloc[-HOLDOUT_MESES:].reset_index(drop=True)
    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]
    return d, treino, holdout, serie, treino_serie, holdout_serie


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
    de sarima (forecast genuino de 24 passos a frente, sem espiar
    valores reais) -- invalidando o Diebold-Mariano do item 2. Aqui, em vez
    disso, reaproveita-se prever_recursivo_residuo (ja usada por script_10
    para o forecast de longo prazo), que alimenta cada passo com a PREVISAO
    anterior, exatamente como sarima faz a partir da mesma origem
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

    pred_naive = np.repeat(treino_serie.values[-1], len(holdout_serie))
    erros["naive"] = holdout_serie.values - pred_naive  # mesma construcao de script_08.rodar_naive

    y_true, pred = _holdout_pred_detrend_rf(treino, holdout)
    erros["detrend_rf"] = y_true - pred

    modelo = SARIMAX(treino_serie, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                      enforce_stationarity=False, enforce_invertibility=False)
    res_treino = modelo.fit(disp=False)
    pred_sarima = res_treino.get_forecast(steps=len(holdout_serie)).predicted_mean.values
    erros["sarima"] = holdout_serie.values - pred_sarima

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


def rodar_item5b_remover_primeiros_n_anos(d: pd.DataFrame, max_n: int = 5) -> list:
    """Extensao do item 5 (issue #12): em vez de remover um unico ano
    isolado, remove cumulativamente os N primeiros anos (N=1..max_n) para
    delimitar com mais precisao quantos anos iniciais sao necessarios para a
    tendencia voltar a ser significativa -- mesma logica de MK/Theil-Sen do
    item 5, so troca o criterio de remocao."""
    anos = sorted(d["Data"].dt.year.unique())
    linhas = []
    for n in range(1, max_n + 1):
        if n >= len(anos):
            break
        anos_removidos = set(anos[:n])
        sub = d[~d["Data"].dt.year.isin(anos_removidos)].reset_index(drop=True)
        if len(sub) < 24:
            continue
        x, y = sub["t_anos"].values, sub["TDS_mgL"].values

        res_mk = mk.original_test(y)
        slope_mk, _, _ = sens_slope_estimate(x, y)
        linhas.append({
            "item": "5b_remover_primeiros_n_anos", "variante": f"sem_primeiros_{n}_anos",
            "metrica": "mann_kendall_sen_slope_mgL_ano",
            "valor_metrica": slope_mk, "pvalor": float(res_mk.p), "n": len(sub),
        })

        slope_ts, _, _, _ = stats.theilslopes(y, x, alpha=1 - ALPHA)
        _, p_tau = stats.kendalltau(x, y)
        linhas.append({
            "item": "5b_remover_primeiros_n_anos", "variante": f"sem_primeiros_{n}_anos",
            "metrica": "theil_sen_slope_mgL_ano",
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


def rodar_item2_diebold_mariano(erros_holdout: dict) -> list:
    # "naive" incluido por pedido explicito de revisao (2026-10-15): a tabela de
    # MASE de script_14/resultados.tex ja mostra o naive como menor MASE de
    # holdout de toda a bateria, mas nenhuma comparacao estatistica formal
    # contra os candidatos existia ainda -- sem ela, a limitacao (d) do
    # manuscrito ("naive supera a maioria dos metodos sofisticados") fica sem
    # teste de significancia, so leitura visual da tabela de MASE.
    #
    # Usa CANDIDATOS (fixo, igual aos itens 1/3/4) -- ja nao ha lista de
    # "finalistas" de onde derivar isso (D-73/ADR-0002: CANDIDATOS e
    # deliberadamente independente de qualquer lista de recomendados, pelo
    # mesmo motivo que motivou ADR-0002 antes de D-73: acoplar este item a uma
    # lista que muda com a recomendacao do momento tornaria a comparacao
    # irreproduzivel assim que a recomendacao mudasse de novo).
    metodos = list(dict.fromkeys(CANDIDATOS + ["naive"]))  # preserva ordem, sem duplicar
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

def rodar_item4_gap_overfitting() -> list:
    tabela = pd.read_csv(RESULTADOS_COMPARACAO_CSV).set_index("metodo")
    residuos_full = {
        "ols": residuos_ols_full(),
        "detrend_rf": residuos_detrend_rf_full(),
        "sarima": residuos_sarima_full(),
    }

    linhas = []
    for metodo in CANDIDATOS:
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
    ax.set_title("Gap in-sample x CV x holdout -- candidatos")
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


def _ic_implausivel(ic_low: np.ndarray, ic_high: np.ndarray, desvio_treino: float) -> bool:
    largura = ic_high - ic_low
    if not np.all(np.isfinite(largura)):
        return True
    if desvio_treino <= 0:
        return False
    return bool(largura.max() > 50 * desvio_treino)


def _fit_predict_ic_sarima(ordem, ordem_sazonal, trend):
    """Achado do /to-spec (issue #10): a ordem fixa, reajustada num treino
    curto (perto de min_treino=60), pode degenerar numericamente e o IC
    explodir (visto na pratica: largura ~1e10 num fold vs. ~250-300 nos
    demais) mesmo com o forecast pontual permanecendo razoavel (auditoria da
    issue #13 confirmou que o RMSE de ponto NAO sofre o mesmo problema).
    Corrige na raiz em vez de so sinalizar: (1) detecta IC nao-finito ou
    implausivelmente largo (>50x o desvio-padrao do proprio treino do fold);
    (2) se implausivel, reajusta com enforce_stationarity/invertibility=True
    (restricoes mais fortes, tendem a evitar esse tipo de explosao); (3) se
    AINDA assim degenerar, cai para um IC de fallback por desvio-padrao do
    residuo in-sample do fold, crescendo com sqrt(horizonte) -- mesma familia
    de tecnica "IC por dispersao de residuo" ja usada no projeto (script_10/
    script_09/script_13), nao uma tecnica nova."""
    def fit_predict_ic(treino: pd.Series, n_passos: int):
        desvio_treino = float(np.std(treino.values, ddof=1)) if len(treino) > 1 else 0.0

        res = SARIMAX(treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                       enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        prev = res.get_forecast(steps=n_passos)
        pred = prev.predicted_mean.values
        ic = prev.conf_int(alpha=ALPHA)
        ic_low, ic_high = ic.iloc[:, 0].values, ic.iloc[:, 1].values

        if _ic_implausivel(ic_low, ic_high, desvio_treino):
            try:
                res_restrito = SARIMAX(treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                                        enforce_stationarity=True, enforce_invertibility=True).fit(disp=False)
                prev_restrito = res_restrito.get_forecast(steps=n_passos)
                ic_restrito = prev_restrito.conf_int(alpha=ALPHA)
                ic_low_r, ic_high_r = ic_restrito.iloc[:, 0].values, ic_restrito.iloc[:, 1].values
                if not _ic_implausivel(ic_low_r, ic_high_r, desvio_treino):
                    pred = prev_restrito.predicted_mean.values
                    ic_low, ic_high = ic_low_r, ic_high_r
                else:
                    raise ValueError("IC ainda implausivel apos refit restrito")
            except Exception:
                # fallback: IC por desvio-padrao do residuo in-sample do
                # proprio fold, crescendo com sqrt(horizonte) -- mesma logica
                # ja usada em script_10.rodar_detrend para o residuo da arvore.
                resid_in_sample = res.resid.dropna().values
                desvio_resid = float(np.std(resid_in_sample, ddof=1)) if len(resid_in_sample) > 1 else desvio_treino
                z = stats.norm.ppf(1 - ALPHA / 2)
                passos = np.arange(1, n_passos + 1)
                margem = z * desvio_resid * np.sqrt(passos / 12)
                ic_low = pred - margem
                ic_high = pred + margem

        return pred, ic_low, ic_high
    return fit_predict_ic


def _prever_recursivo_residuo_boot(modelo, d_resid: pd.DataFrame, n_passos: int,
                                    residuos_boot: np.ndarray, n_boot: int, rng: np.random.Generator):
    """Mesma tecnica de bootstrap de residuo ja usada em
    script_09.prever_recursivo_svr (injeta um residuo do treino por passo
    recursivo, N replicas, percentis 5/95 como IC90) -- aqui replicada para o
    modelo RF do Detrend+arvore (sobre a serie ja destendenciada), em vez de
    chamada diretamente, porque a previsao recursiva depende das features
    especificas de cada modelo (script_09 nao exporta essa parte separada do
    ajuste do SVR)."""
    # Nota de performance (2 reescritas): a 1a versao reconstruia um
    # pd.DataFrame por passo + pd.concat para crescer o historico -- O(n^2)
    # por caminho, inviavel com n_boot=200 x ~25 folds/origens (rodou por
    # mais de 1h sem terminar). A 2a versao trocou para listas/arrays puros
    # mas ainda chamava modelo.predict() uma vez por (passo, replica) --
    # medido: cada chamada de RandomForestRegressor.predict() tem ~24ms de
    # overhead FIXO (dispatch do joblib.Parallel, independente do numero de
    # linhas -- 1 linha ou 200 linhas custam o mesmo, confirmado por
    # benchmark), entao 200 replicas x 60 passos = 12000 chamadas ~ 5 min SO
    # pra esse overhead. Fix real: vetorizar as n_boot replicas num UNICO
    # predict() por passo (200 linhas de uma vez), reduzindo de
    # n_boot*n_passos para n_passos chamadas -- ~200x menos overhead.
    historico_base = list(d_resid["TDS_mgL"].values)
    data_base = d_resid["Data"].iloc[-1]
    t0 = float(d_resid["t_anos"].iloc[-1])

    def _linha_features(historico: list, t_anos: float, sin_m: float, cos_m: float) -> list:
        lag_1 = historico[-1]
        lag_12 = historico[-12] if len(historico) >= 12 else historico[0]
        media_movel_3 = sum(historico[-3:]) / len(historico[-3:])
        return [t_anos, sin_m, cos_m, lag_1, lag_12, media_movel_3]

    def caminho_central() -> list:
        historico = list(historico_base)
        pontos = []
        for passo in range(1, n_passos + 1):
            data_alvo = data_base + pd.DateOffset(months=passo)
            t_anos = t0 + passo / 12
            sin_m, cos_m = np.sin(2 * np.pi * data_alvo.month / 12), np.cos(2 * np.pi * data_alvo.month / 12)
            x = np.array([_linha_features(historico, t_anos, sin_m, cos_m)])
            ponto = float(modelo.predict(x)[0])
            pontos.append(ponto)
            historico.append(ponto)
        return pontos

    ponto_central = caminho_central()
    if n_boot == 0:
        return ponto_central, ponto_central, ponto_central

    historicos = [list(historico_base) for _ in range(n_boot)]
    replicas = np.empty((n_boot, n_passos))
    for passo in range(1, n_passos + 1):
        data_alvo = data_base + pd.DateOffset(months=passo)
        t_anos = t0 + passo / 12
        sin_m, cos_m = np.sin(2 * np.pi * data_alvo.month / 12), np.cos(2 * np.pi * data_alvo.month / 12)
        X = np.array([_linha_features(h, t_anos, sin_m, cos_m) for h in historicos])
        pontos_passo = modelo.predict(X) + rng.choice(residuos_boot, size=n_boot)
        replicas[:, passo - 1] = pontos_passo
        for i, h in enumerate(historicos):
            h.append(float(pontos_passo[i]))

    baixos = np.percentile(replicas, 100 * ALPHA / 2, axis=0)
    altos = np.percentile(replicas, 100 * (1 - ALPHA / 2), axis=0)
    return ponto_central, baixos.tolist(), altos.tolist()


def _fit_predict_ic_detrend_rf(n_boot: int = 200):
    """IC calibrado para detrend_rf (issue #11) -- e o unico dos CANDIDATOS
    sem incerteza nativa testavel. Reusa destendenciar/construir_features/
    RandomForestRegressor ja importados + a tecnica de bootstrap de residuo
    ja estabelecida no projeto (script_09, SVR, bateria estendida)."""
    rng = np.random.default_rng(SEED)

    def fit_predict_ic(treino: pd.Series, n_passos: int):
        d_treino = pd.DataFrame({"Data": treino.index, "TDS_mgL": treino.values})
        d_treino["t_anos"] = (d_treino["Data"] - d_treino["Data"].iloc[0]).dt.days / 365.25
        treino_resid, reg_treino = destendenciar(d_treino)
        f_treino_resid = construir_features(treino_resid)
        modelo = RandomForestRegressor(random_state=SEED, n_estimators=300, min_samples_leaf=1, max_depth=10)
        modelo.fit(f_treino_resid[FEATURES], f_treino_resid["TDS_mgL"])
        resid_boot = f_treino_resid["TDS_mgL"].values - modelo.predict(f_treino_resid[FEATURES])

        pontos_resid, baixos_resid, altos_resid = _prever_recursivo_residuo_boot(
            modelo, treino_resid, n_passos, resid_boot, n_boot, rng
        )

        t0 = d_treino["t_anos"].iloc[-1]
        passos = np.arange(1, n_passos + 1)
        tendencia_futura = reg_treino.intercept + reg_treino.slope * (t0 + passos / 12)

        pred = tendencia_futura + np.array(pontos_resid)
        ic_low = tendencia_futura + np.array(baixos_resid)
        ic_high = tendencia_futura + np.array(altos_resid)
        return pred, ic_low, ic_high
    return fit_predict_ic


def _fit_predict_ic_prophet():
    """IC nativo do Prophet (yhat_lower/yhat_upper, interval_width=1-ALPHA),
    mesmo ajuste de script_05.rodar_prophet -- unico dos 7 metodos do nucleo
    publico com incerteza nativa que faltava neste item (achado de
    /revisao-academica, 2026-10-18)."""
    def fit_predict_ic(treino: pd.Series, n_passos: int):
        from prophet import Prophet
        df_treino = pd.DataFrame({"ds": treino.index, "y": treino.values})
        m = Prophet(interval_width=1 - ALPHA, yearly_seasonality=True,
                    weekly_seasonality=False, daily_seasonality=False)
        m.fit(df_treino)
        futuro = m.make_future_dataframe(periods=n_passos, freq="MS")
        prev = m.predict(futuro).tail(n_passos)
        return prev["yhat"].values, prev["yhat_lower"].values, prev["yhat_upper"].values
    return fit_predict_ic


def rodar_item1_cobertura_ic(serie: pd.Series, ordem_sarima) -> list:
    ordem, ordem_sazonal, trend = ordem_sarima

    fit_predicts_ic = {
        "mann_kendall_sen": _fit_predict_ic_linear(_ajustar_mk),
        "theil_sen": _fit_predict_ic_linear(_ajustar_theil_sen),
        "ols": _fit_predict_ic_linear(_ajustar_ols),
        "sarima": _fit_predict_ic_sarima(ordem, ordem_sazonal, trend),
        "detrend_rf": _fit_predict_ic_detrend_rf(n_boot=200),
        "prophet": _fit_predict_ic_prophet(),
    }

    linhas = []
    for metodo, fit_predict_ic in fit_predicts_ic.items():
        df_cv = expanding_window_cv_com_ic(serie, fit_predict_ic, n_folds=5, horizonte=12, min_treino=60)
        resumo_cv = resumir_cv_ic(df_cv)
        df_bt = backtest_origem_movel_com_ic(serie, fit_predict_ic, min_treino=60)
        resumo_bt = resumir_backtest_ic(df_bt)

        # Sanidade pos-fix (issue #10): mesmo com o refit restrito/fallback em
        # _fit_predict_ic_sarima, verificar fold a fold (nao so a media
        # agregada, que um unico fold atipico entre 5 dilui ate ~2x e nao
        # dispara um limiar de 10x) se algum fold continua discrepante da
        # mediana entre folds -- mesmo criterio da versao original do check
        # (fold.max() > 10x mediana), restaurado apos o /code-review apontar
        # que a comparacao so agregada (media vs mediana) era bem menos
        # sensivel. Quando dispara, persiste a linha no CSV (nao so print),
        # para uma analise futura do manuscrito saber que um fold foi
        # sinalizado como atipico mesmo apos a correcao.
        larguras_fold = df_cv["ic90_largura_media"].values
        mediana_largura = resumo_cv["cv_ic90_largura_mediana"]
        if mediana_largura > 0 and larguras_fold.max() > 10 * mediana_largura:
            fold_atipico = int(df_cv.loc[df_cv["ic90_largura_media"].idxmax(), "fold"])
            print(f"  AVISO [{metodo}]: fold {fold_atipico} com IC90 atipico "
                  f"(largura={larguras_fold.max():.3g} vs. mediana entre folds={mediana_largura:.3g}) "
                  f"mesmo apos o refit restrito/fallback de _fit_predict_ic_sarima.")
            linhas.append({
                "item": "1_cobertura_ic", "variante": metodo, "metrica": "fold_atipico_pos_fix_flag",
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
        linhas.append({
            "item": "1_cobertura_ic", "variante": metodo, "metrica": "cv_ic90_largura_mediana",
            "valor_metrica": resumo_cv["cv_ic90_largura_mediana"], "pvalor": float("nan"), "n": len(df_cv),
        })
        for h in (36, 60):
            chave_cobertura = f"backtest_ic90_cobertura_pct_{h}m"
            if chave_cobertura in resumo_bt:
                linhas.append({
                    "item": "1_cobertura_ic", "variante": metodo, "metrica": chave_cobertura,
                    "valor_metrica": resumo_bt[chave_cobertura], "pvalor": float("nan"),
                    "n": int((df_bt["horizonte_meses"] == h).sum()),
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
    print(f"Candidatos: {CANDIDATOS}")
    print()

    with iniciar_run("testes_robustez_avancados", "script_31_testes_robustez_avancados",
                      params={"candidatos": ",".join(CANDIDATOS)}):
        print("=== Item 5: leave-one-year-out (Mann-Kendall/Theil-Sen) ===")
        linhas_item5 = rodar_item5_leave_one_year_out(d)
        print(f"  {len(linhas_item5)} linhas geradas")
        print()

        print("=== Item 5b: remover primeiros N anos (N=1..5) ===")
        linhas_item5b = rodar_item5b_remover_primeiros_n_anos(d, max_n=5)
        for l in linhas_item5b:
            print(f"  {l['variante']:25s} {l['metrica']:30s} = {l['valor_metrica']:.3f}  p={l['pvalor']:.4f}")
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

        print("=== Item 2: Diebold-Mariano (candidatos + naive) ===")
        linhas_item2 = rodar_item2_diebold_mariano(erros_holdout)
        for l in linhas_item2:
            print(f"  {l['variante']:45s} dm_stat={l['valor_metrica']:.3f}  p={l['pvalor']:.4f}")
        print()

        print("=== Item 4: gap RMSE in-sample x CV x holdout ===")
        linhas_item4 = rodar_item4_gap_overfitting()
        for l in linhas_item4:
            print(f"  {l['variante']:25s} {l['metrica']:15s} = {l['valor_metrica']:.3f}")
        print()

        print("=== Item 1: cobertura empirica de IC90 (metodos com IC nativo) ===")
        linhas_item1 = rodar_item1_cobertura_ic(serie, ordem_sarima)
        for l in linhas_item1:
            print(f"  {l['variante']:22s} {l['metrica']:30s} = {l['valor_metrica']}")
        print()

        todas_linhas = linhas_item5 + linhas_item5b + linhas_item3 + linhas_item2 + linhas_item4 + linhas_item1
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
