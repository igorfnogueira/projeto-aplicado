"""
Fine-tuning da representacao do PDSI para os 4 metodos que melhoraram em
D-56 (Artigo/DECISOES.md D-57): Random Forest, XGBoost, LightGBM e
regressao quantilica Q50 -- os unicos, entre os 12 re-treinados em
script_29, cujo RMSE de holdout melhorou ao adicionar o PDSI (lag unico
fixo de 4 meses, herdado de D-37/D-41) como covariavel.

Hipotese testada: um unico lag fixo pode nao ser a melhor representacao
do PDSI para esses 4 metodos. Duas estrategias, escolhidas conforme a
familia do metodo:

- Arvores (RF, XGBoost, LightGBM): adicionar MULTIPLOS lags de PDSI como
  features simultaneas (candidatos 1/2/4/6/8/12 meses) -- arvores toleram
  bem features correlacionadas e podem selecionar a defasagem mais
  informativa via splits/importancia.
- Regressao quantilica (linear, sensivel a multicolinearidade dado o
  PDSI ser fortemente autocorrelacionado, phi=0.894 do AR(1) de D-41):
  em vez de multi-lag simultaneo, SELECIONAR o melhor lag unico por
  validacao cruzada expansiva (TimeSeriesSplit, 5 folds, so no treino,
  sem espiar o holdout) entre os mesmos 6 candidatos.

Criterio de aceitacao (D-57): so contar como melhoria real se o RMSE da
VALIDACAO HONESTA (validacao_utils.validar_metodo -- CV expansiva +
backtest) tambem melhorar frente a versao "_com_pdsi" (lag unico) de
script_29 -- um ganho so no holdout fixo de 24 meses, sem confirmacao na
CV, e tratado como ruido de amostra pequena (n=182 meses), nao evidencia.

Linhas novas em resultados_comparacao.csv/.json com sufixo
"_pdsi_multilag" (arvores) e "_pdsi_lagsel" (quantilica), comparadas
contra as "_com_pdsi" ja existentes -- nao contra a versao original sem
PDSI, que ja foi superada na comparacao de D-56.
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.regression.quantile_regression import QuantReg

from script_03_random_forest_gridsearch import construir_features, FEATURES
from script_04_xgboost_lightgbm import checar_gpu_xgboost
from script_29_bateria_pdsi_covariavel import (
    HORIZONTES_ANOS, HOLDOUT_MESES, RESULTADOS_CSV, RESULTADOS_JSON,
    SEED, carregar_tudo, pdsi_lag_em, metrica_holdout, montar_linha_base,
    treinar_rf_pdsi, treinar_xgb_pdsi, treinar_lgbm_pdsi,
    rodar_quantilica_pdsi, gravar_resultados,
)
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

warnings.filterwarnings("ignore")

LAGS_CANDIDATOS = [1, 2, 4, 6, 8, 12]
FIGURA_PATH = "Artigo/images/pdsi-finetuning-multilag-comparacao.png"
COMPARACAO_CSV = "comparacao_pdsi_finetuning_multilag.csv"

FEATURES_MULTILAG = FEATURES + [f"pdsi_lag{l}" for l in LAGS_CANDIDATOS]


# --------------------------------------------------------------------------
# Arvores (RF, XGBoost, LightGBM): multiplos lags de PDSI como features
# --------------------------------------------------------------------------

def construir_features_multilag(d: pd.DataFrame) -> pd.DataFrame:
    f = construir_features(d)
    d_idx = d.set_index("Data")
    for l in LAGS_CANDIDATOS:
        f[f"pdsi_lag{l}"] = d_idx.reindex(f["Data"])[f"pdsi_lag{l}"].values
    return f


def prever_recursivo_arvore_multilag(modelo, d: pd.DataFrame, pdsi_estendido: pd.Series, n_passos: int):
    historico = d[["Data", "TDS_mgL"]].copy()
    t0 = d["t_anos"].iloc[-1]
    pontos = []
    for passo in range(1, n_passos + 1):
        data_alvo = d["Data"].iloc[-1] + pd.DateOffset(months=passo)
        t_anos = t0 + passo / 12
        lag_1 = historico["TDS_mgL"].iloc[-1]
        lag_12 = historico["TDS_mgL"].iloc[-12] if len(historico) >= 12 else historico["TDS_mgL"].iloc[0]
        media_movel_3 = historico["TDS_mgL"].iloc[-3:].mean()
        linha = {
            "t_anos": t_anos, "mes_sin": np.sin(2 * np.pi * data_alvo.month / 12),
            "mes_cos": np.cos(2 * np.pi * data_alvo.month / 12),
            "lag_1": lag_1, "lag_12": lag_12, "media_movel_3": media_movel_3,
        }
        for l in LAGS_CANDIDATOS:
            linha[f"pdsi_lag{l}"] = float(pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex([data_alvo]), l)[0])
        x = pd.DataFrame([linha])[FEATURES_MULTILAG]
        ponto = float(modelo.predict(x)[0])
        pontos.append(ponto)
        historico = pd.concat([historico, pd.DataFrame([{"Data": data_alvo, "TDS_mgL": ponto}])], ignore_index=True)
    return pontos


def rodar_arvore_multilag(nome_metodo, treinar_fn, d, pdsi_estendido):
    f = construir_features_multilag(d)
    treino, holdout = f.iloc[:-HOLDOUT_MESES], f.iloc[-HOLDOUT_MESES:]

    modelo_treino, _ = treinar_fn(treino[FEATURES_MULTILAG], treino["TDS_mgL"])
    pred_holdout = modelo_treino.predict(holdout[FEATURES_MULTILAG])
    rmse, mae, r2 = metrica_holdout(holdout["TDS_mgL"].values, pred_holdout)

    modelo_full, params_full = treinar_fn(f[FEATURES_MULTILAG], f["TDS_mgL"])
    max_passos = max(HORIZONTES_ANOS) * 12
    d_para_recursao = d[["Data", "TDS_mgL", "t_anos"]]
    pontos = prever_recursivo_arvore_multilag(modelo_full, d_para_recursao, pdsi_estendido, max_passos)

    linha = montar_linha_base(nome_metodo, np.array(pontos))
    linha["metodo"] = f"{nome_metodo}_pdsi_multilag"
    linha["rmse_holdout"], linha["mae_holdout"], linha["r2_holdout"] = rmse, mae, r2
    linha["hiperparametros"] = str(params_full)

    def fit_predict(treino_s, n_passos):
        d_tr = pd.DataFrame({"Data": treino_s.index, "TDS_mgL": treino_s.values})
        d_tr["t_anos"] = (d_tr["Data"] - d_tr["Data"].iloc[0]).dt.days / 365.25
        for l in LAGS_CANDIDATOS:
            d_tr[f"pdsi_lag{l}"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(d_tr["Data"]), l)
        f_tr = construir_features_multilag(d_tr)
        m, _ = treinar_fn(f_tr[FEATURES_MULTILAG], f_tr["TDS_mgL"])
        return np.array(prever_recursivo_arvore_multilag(m, d_tr[["Data", "TDS_mgL", "t_anos"]], pdsi_estendido, n_passos))

    return linha, fit_predict


# --------------------------------------------------------------------------
# Regressao quantilica: selecao do melhor lag unico por CV expansiva
# --------------------------------------------------------------------------

def selecionar_melhor_lag_quantilica(d, pdsi_estendido, lags, holdout_meses=HOLDOUT_MESES):
    """CV expansiva (TimeSeriesSplit, 5 folds) SO no conjunto de treino
    (sem espiar o holdout) para escolher, entre os lags candidatos, o que
    minimiza o RMSE medio de validacao da regressao quantilica (Q50)."""
    treino = d.iloc[:-holdout_meses].reset_index(drop=True)
    tscv = TimeSeriesSplit(n_splits=5)
    scores = {}
    for l in lags:
        pdsi_col = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(treino["Data"]), l)
        t_col = treino["t_anos"].values
        y_col = treino["TDS_mgL"].values
        rmses = []
        for idx_tr, idx_va in tscv.split(t_col):
            try:
                X_tr = sm.add_constant(np.column_stack([t_col[idx_tr], pdsi_col[idx_tr]]))
                r = QuantReg(y_col[idx_tr], X_tr).fit(q=0.5)
                X_va = sm.add_constant(np.column_stack([t_col[idx_va], pdsi_col[idx_va]]), has_constant="add")
                pred = r.predict(X_va)
                rmses.append(float(np.sqrt(mean_squared_error(y_col[idx_va], pred))))
            except Exception:
                continue
        scores[l] = float(np.mean(rmses)) if rmses else float("inf")
    melhor_lag = min(scores, key=scores.get)
    return melhor_lag, scores


def rodar_quantilica_lagsel(d, pdsi_estendido, lags):
    melhor_lag, scores_cv = selecionar_melhor_lag_quantilica(d, pdsi_estendido, lags)
    d_sel = d.copy()
    d_sel["pdsi_lag"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(d_sel["Data"]), melhor_lag)

    linha, fp = rodar_quantilica_pdsi(d_sel, pdsi_estendido, melhor_lag)
    linha["metodo"] = "regressao_quantilica_q50_pdsi_lagsel"
    linha["hiperparametros"] += f", lag_selecionado_meses={melhor_lag} (candidatos={lags}, cv_rmse={scores_cv})"
    return linha, fp, melhor_lag, scores_cv


# --------------------------------------------------------------------------
# Comparacao contra a versao "_com_pdsi" (lag unico, D-56) e gravacao
# --------------------------------------------------------------------------

def montar_comparacao(linhas_novas: list) -> pd.DataFrame:
    existentes = pd.read_csv(RESULTADOS_CSV)
    linhas_cmp = []
    for linha in linhas_novas:
        nome_depois = linha["metodo"]
        nome_antes = nome_depois.replace("_pdsi_multilag", "_com_pdsi").replace("_pdsi_lagsel", "_com_pdsi")
        antes = existentes[existentes["metodo"] == nome_antes]
        if antes.empty:
            continue
        antes = antes.iloc[0]
        cmp = {"metodo": nome_antes.replace("_com_pdsi", "")}
        for col in ["rmse_holdout", "mae_holdout", "r2_holdout", "tendencia_mgL_ano",
                    "cv_rmse_media", "mase_holdout"]:
            v_antes = antes.get(col, np.nan)
            v_depois = linha.get(col, np.nan)
            cmp[f"{col}_antes_com_pdsi"] = v_antes
            cmp[f"{col}_depois_finetuning"] = v_depois
            if pd.notna(v_antes) and v_antes != 0 and pd.notna(v_depois):
                cmp[f"{col}_variacao_pct"] = 100 * (v_depois - v_antes) / abs(v_antes)
            else:
                cmp[f"{col}_variacao_pct"] = np.nan
        linhas_cmp.append(cmp)
    return pd.DataFrame(linhas_cmp)


def gerar_figura(comparacao: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 5))
    y_pos = np.arange(len(comparacao))
    ax.barh(y_pos - 0.2, comparacao["rmse_holdout_antes_com_pdsi"], height=0.4, color="tab:blue", label="RMSE holdout (com PDSI, lag único D-56)")
    ax.barh(y_pos + 0.2, comparacao["rmse_holdout_depois_finetuning"], height=0.4, color="tab:green", label="RMSE holdout (fine-tuning D-57)")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(comparacao["metodo"], fontsize=8)
    ax.set_xlabel("RMSE no holdout (mg/L)")
    ax.set_title("Fine-tuning da representação do PDSI (D-57) — RMSE de holdout")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def main():
    print("=== Fine-tuning da representação do PDSI para os 4 métodos que melhoraram em D-56 ===")
    d, lag_original, pdsi_estendido, ar1 = carregar_tudo()
    for l in LAGS_CANDIDATOS:
        d[f"pdsi_lag{l}"] = pdsi_lag_em(pdsi_estendido, pd.DatetimeIndex(d["Data"]), l)
    print(f"Série TDS: {len(d)} meses | lags candidatos={LAGS_CANDIDATOS} | lag original (D-37/D-56)={lag_original}")
    print()

    serie = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie, holdout_serie = serie.iloc[:-HOLDOUT_MESES], serie.iloc[-HOLDOUT_MESES:]

    linhas = []
    fit_predicts = {}

    print("--- 1. Random Forest + PDSI multi-lag ---")
    linha, fp = rodar_arvore_multilag("random_forest", treinar_rf_pdsi, d, pdsi_estendido)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 2. XGBoost + PDSI multi-lag ---")
    usa_gpu = checar_gpu_xgboost()
    linha, fp = rodar_arvore_multilag("xgboost", lambda X, y: treinar_xgb_pdsi(X, y, usa_gpu), d, pdsi_estendido)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 3. LightGBM + PDSI multi-lag ---")
    linha, fp = rodar_arvore_multilag("lightgbm", treinar_lgbm_pdsi, d, pdsi_estendido)
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print("--- 4. Regressão quantílica (Q50): seleção de lag único por CV expansiva ---")
    linha, fp, melhor_lag, scores_cv = rodar_quantilica_lagsel(d, pdsi_estendido, LAGS_CANDIDATOS)
    print(f"  Lag selecionado por CV (treino apenas): {melhor_lag} meses -- RMSE médio por lag: {scores_cv}")
    linhas.append(linha); fit_predicts[linha["metodo"]] = fp

    print()
    print("--- Validação honesta (CV expansiva + backtest) de cada método ---")
    for linha in linhas:
        try:
            linha.update(validar_metodo(fit_predicts[linha["metodo"]], serie, treino_serie, holdout_serie))
        except Exception as e:
            print(f"  Aviso: validação honesta falhou para {linha['metodo']} ({e}) -- holdout simples já gravado.")
        print(f"  {linha['metodo']}: RMSE_holdout={linha['rmse_holdout']:.2f}  "
              f"RMSE_cv={linha.get('cv_rmse_media', float('nan')):.2f}  R2={linha['r2_holdout']:.3f}")

    gravar_resultados(linhas)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

    print()
    print("--- Comparação: lag único (D-56, '_com_pdsi') vs. fine-tuning (D-57) ---")
    comparacao = montar_comparacao(linhas)
    comparacao.to_csv(COMPARACAO_CSV, index=False)
    for _, row in comparacao.iterrows():
        rmse_h = row.get("rmse_holdout_variacao_pct", float("nan"))
        rmse_cv = row.get("cv_rmse_media_variacao_pct", float("nan"))
        cv_str = f"{rmse_cv:+.1f}%" if pd.notna(rmse_cv) else "n/d"
        print(f"  {row['metodo']}: RMSE holdout {rmse_h:+.1f}%  |  RMSE CV expansiva {cv_str}")
    print(f"\nComparação gravada em {COMPARACAO_CSV}")

    gerar_figura(comparacao)

    with iniciar_run(
        "pdsi_finetuning_multilag", "script_30_pdsi_finetuning_multilag",
        params={"lags_candidatos": LAGS_CANDIDATOS, "n_metodos": len(linhas)}, seed=SEED,
        janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": len(holdout_serie)},
    ):
        for linha in linhas:
            logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH, COMPARACAO_CSV])


if __name__ == "__main__":
    main()
