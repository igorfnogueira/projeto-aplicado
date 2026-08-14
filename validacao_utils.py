"""
Framework de validacao temporal honesta, compartilhado por toda a bateria de
metodologia (script_01 em diante). Bloco 2/5 do pedido de aprofundamento:

- MASE/sMAPE (metricas de erro escala-independente, para comparar metodos
  entre si e contra os baselines de script_08).
- largura/cobertura empirica de IC (so calculavel em folds de CV/backtest,
  nunca no forecast futuro real, onde nao existe y_true para comparar).
- expanding_window_cv: validacao cruzada de series temporais com janela
  expansiva (nunca split aleatorio, nunca vazamento temporal).
- backtest_origem_movel: unico proxy honesto de desempenho nos horizontes de
  10-20 anos -- como nenhum ponto do historico tem *de fato* 10-20 anos de
  futuro observado, o backtest usa horizontes menores (+3/+5 anos) onde ha
  dado real disponivel para comparar, treinando a partir de varias origens
  moveis ao longo da serie.

Cada `fit_predict_fn(treino: pd.Series, n_passos: int) -> np.ndarray` e um
adaptador fino, escrito uma vez por metodo/script, que treina no trecho
`treino` (serie com DatetimeIndex) e retorna a previsao dos proximos
`n_passos` meses. Nao duplica a logica de ajuste ja existente em cada script.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONTES_BACKTEST_MESES = (36, 60)  # +3 e +5 anos -- os unicos horizontes longos com dado real disponivel


def rmse(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def mase(y_true, y_pred, y_treino_historico, m: int = 12) -> float:
    """MASE contra o naive sazonal (m=12) ajustado no proprio treino --
    escala-independente, permite comparar metodos entre si e contra os
    baselines obrigatorios (script_08)."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    hist = np.asarray(y_treino_historico, dtype=float)
    if len(hist) <= m:
        return float("nan")
    denom = np.mean(np.abs(hist[m:] - hist[:-m]))
    if denom == 0:
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / denom)


def smape(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true) + np.abs(y_pred)
    validos = denom != 0
    if not validos.any():
        return float("nan")
    return float(np.mean(200 * np.abs(y_pred[validos] - y_true[validos]) / denom[validos]))


def largura_e_cobertura_ic(y_true, ic_low, ic_high) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    ic_low, ic_high = np.asarray(ic_low, dtype=float), np.asarray(ic_high, dtype=float)
    largura_media = float(np.mean(ic_high - ic_low))
    cobertura_pct = float(np.mean((y_true >= ic_low) & (y_true <= ic_high)) * 100)
    return {"ic90_largura_media": largura_media, "ic90_cobertura_pct": cobertura_pct}


def expanding_window_cv(serie: pd.Series, fit_predict_fn, n_folds: int = 5,
                         horizonte: int = 12, min_treino: int = 60) -> pd.DataFrame:
    """CV de series temporais com janela expansiva: a cada fold, treina em
    serie[:corte] e avalia em serie[corte:corte+horizonte]. Cortes
    igualmente espacados entre min_treino e len(serie)-horizonte -- nunca
    split aleatorio, nunca vazamento temporal (treino sempre estritamente
    anterior ao teste)."""
    n = len(serie)
    primeiro_corte, ultimo_corte = min_treino, n - horizonte
    if ultimo_corte <= primeiro_corte:
        raise ValueError(
            f"Serie curta demais para expanding_window_cv (n={n}, min_treino={min_treino}, horizonte={horizonte})"
        )
    cortes = sorted(set(np.linspace(primeiro_corte, ultimo_corte, n_folds).astype(int)))

    linhas = []
    for i, corte in enumerate(cortes):
        treino = serie.iloc[:corte]
        teste = serie.iloc[corte:corte + horizonte]
        pred = np.asarray(fit_predict_fn(treino, len(teste)), dtype=float)[: len(teste)]
        y_true = teste.values
        linhas.append({
            "fold": i, "corte_idx": int(corte), "corte_data": str(serie.index[corte - 1].date()),
            "n_treino": len(treino), "n_teste": len(teste),
            "rmse": rmse(y_true, pred), "mae": mae(y_true, pred),
            "mase": mase(y_true, pred, treino.values), "smape": smape(y_true, pred),
        })
    return pd.DataFrame(linhas)


def resumir_cv(df_cv: pd.DataFrame) -> dict:
    """Agrega os folds de expanding_window_cv em media/desvio por metrica."""
    resumo = {}
    for col in ("rmse", "mae", "mase", "smape"):
        resumo[f"cv_{col}_media"] = float(df_cv[col].mean())
        resumo[f"cv_{col}_desvio"] = float(df_cv[col].std(ddof=1)) if len(df_cv) > 1 else 0.0
    return resumo


def backtest_origem_movel(serie: pd.Series, fit_predict_fn,
                           horizontes_meses=HORIZONTES_BACKTEST_MESES,
                           min_treino: int = 60, passo_origem: int = 6) -> pd.DataFrame:
    """Unico proxy honesto de desempenho nos horizontes longos (10/15/20
    anos): como nenhuma origem tem 10-20 anos de futuro real disponivel,
    mede o erro real em horizontes menores (+3/+5 anos, HORIZONTES_BACKTEST_MESES)
    a partir de varias origens de treino moveis ao longo da serie -- quanto
    mais consistente o erro entre origens, mais confiavel a extrapolacao do
    metodo tende a ser nos horizontes realmente pedidos."""
    n = len(serie)
    linhas = []
    origem = min_treino
    while origem <= n - min(horizontes_meses):
        horizontes_validos = [h for h in horizontes_meses if origem + h <= n]
        if not horizontes_validos:
            origem += passo_origem
            continue
        treino = serie.iloc[:origem]
        pred = np.asarray(fit_predict_fn(treino, max(horizontes_validos)), dtype=float)
        for h in horizontes_validos:
            y_pred_h = pred[h - 1]
            y_true_h = float(serie.iloc[origem + h - 1])
            linhas.append({
                "origem_idx": origem, "origem_data": str(serie.index[origem - 1].date()),
                "horizonte_meses": h,
                "y_true": y_true_h, "y_pred": float(y_pred_h),
                "erro_abs": abs(y_true_h - y_pred_h),
            })
        origem += passo_origem
    return pd.DataFrame(linhas)


def resumir_backtest(df_bt: pd.DataFrame) -> dict:
    """Agrega o backtest de origem movel em MAE por horizonte testado."""
    resumo = {}
    for h, grupo in df_bt.groupby("horizonte_meses"):
        resumo[f"backtest_mae_{h}m"] = float(grupo["erro_abs"].mean())
        resumo[f"backtest_n_origens_{h}m"] = int(len(grupo))
    return resumo


def validar_metodo(fit_predict_fn, serie: pd.Series, treino: pd.Series, holdout: pd.Series,
                    n_folds: int = 5, horizonte_cv: int = 12, min_treino: int = 60) -> dict:
    """Pacote completo de validacao honesta para um metodo (MASE/sMAPE no
    holdout de 24 meses ja existente em cada script + CV expansiva de 5 folds
    + backtest de origem movel em +3/+5 anos) -- pronto para mesclar na
    `linha` de resultados de cada script_0X via `linha.update(...)`.

    Nota de escopo: a cobertura empirica de IC (largura_e_cobertura_ic) NAO e
    calculada aqui -- exigiria que fit_predict_fn tambem retornasse limites
    de IC por fold, o que a maioria dos metodos desta bateria (arvores,
    Prophet, SARIMA) nao expoe de forma uniforme sem conformal prediction ou
    bootstrap de residuos (bloco 5 do pedido de aprofundamento, ainda nao
    implementado). A largura do IC90 do forecast pontual (+10/+15/+20 anos)
    ja calculado por cada script e reportada separadamente, sem custo extra."""
    pred_holdout = np.asarray(fit_predict_fn(treino, len(holdout)), dtype=float)
    resultado = {
        "mase_holdout": mase(holdout.values, pred_holdout, treino.values),
        "smape_holdout": smape(holdout.values, pred_holdout),
    }
    cv = expanding_window_cv(serie, fit_predict_fn, n_folds=n_folds, horizonte=horizonte_cv, min_treino=min_treino)
    resultado.update(resumir_cv(cv))
    bt = backtest_origem_movel(serie, fit_predict_fn, min_treino=min_treino)
    resultado.update(resumir_backtest(bt))
    return resultado
