"""
Modelo estrutural de espaco de estados / DLM (plano_projeto_TDS.md secao 3.f.4):
tendencia local + componente sazonal, ajustados via filtro de Kalman
(statsmodels.tsa.statespace.structural.UnobservedComponents). A tendencia e
um ESTADO que evolui no tempo (nao uma diferenciacao como no SARIMA), o que
costuma dar extrapolacao mais estavel em horizontes longos -- e a incerteza
da previsao e nativa do modelo, nao aproximada.

Duas especificacoes testadas (grid pequeno, escolhida por AIC):
  - 'local level' (sem tendencia propria, so nivel + sazonal)
  - 'local linear trend' (nivel + inclinacao, ambos estocasticos) + sazonal
Dado que script_07 mediu sazonalidade fraca (Fs=0,25), o termo sazonal pode
acabar com variancia perto de zero -- isso e reportado como esta, nao
forcado.
"""

import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.structural import UnobservedComponents

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/espaco-estados-tds.png"


def carregar_serie() -> pd.Series:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["Data"] = pd.to_datetime(d["Data"]) + pd.offsets.MonthEnd(0)
    return d.set_index("Data")["TDS_mgL"].asfreq("ME")


def ajustar_modelo(serie: pd.Series, especificacao: str):
    modelo = UnobservedComponents(serie, level=especificacao, seasonal=12, stochastic_seasonal=True)
    return modelo.fit(disp=False)


def escolher_por_aic(serie: pd.Series) -> tuple:
    candidatos = {}
    for espec in ["local level", "local linear trend"]:
        try:
            res = ajustar_modelo(serie, espec)
            candidatos[espec] = res
        except Exception as e:
            print(f"  {espec}: falhou ao ajustar ({e})")
    melhor = min(candidatos, key=lambda k: candidatos[k].aic)
    return melhor, candidatos


def fit_predict_uc(treino: pd.Series, n_passos: int) -> np.ndarray:
    res = ajustar_modelo(treino, "local linear trend")
    fc = res.get_forecast(steps=n_passos)
    return fc.predicted_mean.values


def main():
    serie = carregar_serie()
    treino_serie = serie.iloc[:-HOLDOUT_MESES]
    holdout_serie = serie.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(serie)} meses ({serie.index[0].date()} a {serie.index[-1].date()})")
    print(f"Treino: {len(treino_serie)} | Holdout: {len(holdout_serie)}")
    print()

    print("--- Selecao de especificacao por AIC (serie completa) ---")
    melhor_espec, candidatos = escolher_por_aic(serie)
    for espec, res in candidatos.items():
        marca = " <= escolhido" if espec == melhor_espec else ""
        print(f"  {espec}: AIC={res.aic:.2f}{marca}")
    print()

    res_full = candidatos[melhor_espec]
    print(res_full.summary().tables[1])
    print()

    var_nivel = float(res_full.params[res_full.param_names.index("sigma2.level")]) if "sigma2.level" in res_full.param_names else float("nan")
    var_sazonal = float(res_full.params[res_full.param_names.index("sigma2.seasonal")]) if "sigma2.seasonal" in res_full.param_names else float("nan")
    print(f"Variancia do nivel (estado estocastico): {var_nivel:.4f}")
    print(f"Variancia do termo sazonal (estado estocastico): {var_sazonal:.6f}"
          f"{'  <- perto de zero, sazonalidade fraca (consistente com script_07, Fs=0,25)' if not np.isnan(var_sazonal) and var_sazonal < 0.01 else ''}")
    print()

    # tendencia media do componente de nivel/inclinacao ao longo da serie (mg/L/ano)
    if "local linear trend" == melhor_espec:
        inclinacao_estado = res_full.states.smoothed["trend"] if "trend" in res_full.states.smoothed.columns else None
        if inclinacao_estado is not None:
            tendencia_media_mensal = float(inclinacao_estado.mean())
            tendencia_mgL_ano = tendencia_media_mensal * 12
        else:
            tendencia_mgL_ano = float("nan")
    else:
        nivel = res_full.states.smoothed["level"]
        t = np.arange(len(nivel))
        tendencia_mgL_ano = float(np.polyfit(t, nivel.values, 1)[0]) * 12
    print(f"Tendencia media do estado de nivel/inclinacao: {tendencia_mgL_ano:.3f} mg/L/ano "
          f"(media do estado ao longo da serie, nao uma reta unica -- a tendencia MUDA no tempo por construcao)")
    print()

    res_treino = ajustar_modelo(treino_serie, melhor_espec)
    fc_holdout = res_treino.get_forecast(steps=HOLDOUT_MESES)
    pred_holdout = fc_holdout.predicted_mean.values
    y_true = holdout_serie.values
    rmse = float(np.sqrt(np.mean((y_true - pred_holdout) ** 2)))
    mae = float(np.mean(np.abs(y_true - pred_holdout)))
    ss_res = np.sum((y_true - pred_holdout) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot)
    print(f"Holdout ({HOLDOUT_MESES}m): RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.3f}")
    print()

    fc_full = res_full.get_forecast(steps=max(HORIZONTES_ANOS) * 12)
    ic = fc_full.conf_int(alpha=ALPHA)
    linha = {
        "metodo": "espaco_estados_dlm",
        "tendencia_mgL_ano": tendencia_mgL_ano,
        "tendencia_pvalor": float("nan"),  # nao ha teste de hipotese unico p/ tendencia variavel no tempo
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
    }
    for h in HORIZONTES_ANOS:
        idx = h * 12 - 1
        ponto = float(fc_full.predicted_mean.iloc[idx])
        lo = float(ic.iloc[idx, 0])
        hi = float(ic.iloc[idx, 1])
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = lo
        linha[f"ci90_high_{h}y"] = hi
        print(f"  +{h}a: {ponto:.1f} mg/L  IC90% [{lo:.1f}, {hi:.1f}]  (largura={hi-lo:.1f})")

    linha.update(validar_metodo(fit_predict_uc, serie, treino_serie, holdout_serie))
    print()
    print(f"MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(serie.index, serie.values, color="black", linewidth=1, label="TDS observado")
    datas_futuras = pd.date_range(serie.index[-1], periods=max(HORIZONTES_ANOS) * 12 + 1, freq="ME")[1:]
    ax.plot(datas_futuras, fc_full.predicted_mean.values, "--", color="tab:blue", label=f"UC ({melhor_espec})")
    ax.fill_between(datas_futuras, ic.iloc[:, 0], ic.iloc[:, 1], color="tab:blue", alpha=0.15, label="IC90%")
    if "local linear trend" == melhor_espec and inclinacao_estado is not None:
        ax2 = ax.twinx()
        ax2.plot(serie.index, inclinacao_estado.values * 12, color="tab:red", linewidth=0.9, alpha=0.7, label="Inclinação do estado (mg/L/ano)")
        ax2.axhline(0, color="tab:red", linestyle=":", linewidth=0.6)
        ax2.set_ylabel("Inclinação do estado (mg/L/ano)", color="tab:red")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title(f"Espaço de estados (UnobservedComponents, {melhor_espec}) — TDS observado e previsão")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")

    linha["script"] = "script_22_espaco_estados"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    linha["ordem_sarima"] = melhor_espec
    linha["hiperparametros"] = f"level={melhor_espec}, seasonal=12, stochastic_seasonal=True, sigma2_seasonal={var_sazonal:.6f}"

    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[existentes["metodo"] != "espaco_estados_dlm"]
        for col in novas.columns:
            if col not in existentes.columns:
                existentes[col] = pd.NA
        for col in existentes.columns:
            if col not in novas.columns:
                novas[col] = pd.NA
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas
    consolidado.to_csv(RESULTADOS_CSV, index=False)
    consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)
    print(f"Resultados gravados em {RESULTADOS_CSV}")

    with iniciar_run("espaco_estados_dlm", "script_22_espaco_estados",
                      params={"especificacao": melhor_espec, "seasonal_period": 12},
                      janela_treino_holdout={"treino_meses": len(treino_serie), "holdout_meses": HOLDOUT_MESES}):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
