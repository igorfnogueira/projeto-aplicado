"""
Analise de intervencao / ARIMAX com regressores de evento
(plano_projeto_TDS.md secao 3.f.7): usa eventos conhecidos como variaveis
exogenas -- a seca da California 2012-2016 e a ordem estadual de reducao
obrigatoria de 25% no consumo (abril de 2015) -- para ligar a estatistica
diretamente a causa hipotetizada, em vez de deixar a associacao implicita
(como nos demais metodos univariados da bateria).

Dois regressores de evento, formas diferentes por natureza do evento:
  - seca_2012_2016: pulso (1 durante jan/2012-dez/2016, 0 fora) -- evento
    com inicio E fim conhecidos.
  - ordem_conservacao_2015: degrau (1 a partir de abr/2015, 0 antes) --
    politica permanente, sem data de reversao conhecida.

Ordem SARIMA reaproveitada da busca por AIC de script_02 (mesma decisao de
escopo ja usada em script_11 para o Cloreto): refazer a busca em grade com
exog em cada configuracao seria caro demais para o ganho esperado.

Para a previsao real +10/+15/+20a, os regressores futuros sao fixados em
seca=0 (nao sabemos se havera seca futura -- premissa conservadora, nao um
cenario) e ordem_conservacao=1 (assume-se que a politica de conservacao
permanece em vigor) -- premissas declaradas explicitamente, nao escondidas.
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from script_00_preprocessamento import construir_datasets
from script_02_arima_sarima import buscar_melhor_sarima
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

warnings.filterwarnings("ignore")

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/intervencao-arimax-tds.png"

INICIO_SECA, FIM_SECA = "2012-01-01", "2016-12-31"
INICIO_ORDEM_CONSERVACAO = "2015-04-01"


def carregar_serie_com_eventos() -> tuple:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    tds = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))

    eventos = pd.DataFrame(index=tds.index)
    eventos["seca_2012_2016"] = ((tds.index >= INICIO_SECA) & (tds.index <= FIM_SECA)).astype(float)
    eventos["ordem_conservacao_2015"] = (tds.index >= INICIO_ORDEM_CONSERVACAO).astype(float)
    return tds, eventos


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def exog_futuro(datas_futuras: pd.DatetimeIndex, eventos: pd.DataFrame) -> np.ndarray:
    """Regressores futuros: seca=0 (premissa conservadora, nao sabemos se
    havera seca), ordem_conservacao=1 (assume-se que a politica permanece)."""
    fut = pd.DataFrame(index=datas_futuras)
    fut["seca_2012_2016"] = 0.0
    fut["ordem_conservacao_2015"] = 1.0
    return fut.values


def construir_fit_predict(eventos: pd.DataFrame, ordem, ordem_sazonal, trend):
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        exog_treino = eventos.reindex(treino.index).values
        modelo = SARIMAX(treino, exog=exog_treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                          enforce_stationarity=False, enforce_invertibility=False)
        res = modelo.fit(disp=False)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        exog_fut = exog_futuro(datas_futuras, eventos)
        return res.get_forecast(steps=n_passos, exog=exog_fut).predicted_mean.values
    return fit_predict


def main():
    tds, eventos = carregar_serie_com_eventos()
    treino, holdout = tds.iloc[:-HOLDOUT_MESES], tds.iloc[-HOLDOUT_MESES:]
    print(f"Série TDS: {len(tds)} meses ({tds.index[0].date()} a {tds.index[-1].date()})")
    print(f"Meses em seca (2012-01 a 2016-12): {int(eventos['seca_2012_2016'].sum())}")
    print(f"Meses sob ordem de conservação (a partir de 2015-04): {int(eventos['ordem_conservacao_2015'].sum())}")
    print()

    print("--- Buscando ordem SARIMA (reaproveitada de script_02, mesma decisão de escopo de script_11) ---")
    aic, ordem, ordem_sazonal, trend, _ = buscar_melhor_sarima(treino)
    print(f"  Ordem: order={ordem} seasonal_order={ordem_sazonal} trend={trend} (AIC treino={aic:.2f})")
    print()

    exog_treino = eventos.reindex(treino.index).values
    modelo_treino = SARIMAX(treino, exog=exog_treino, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                             enforce_stationarity=False, enforce_invertibility=False)
    res_treino = modelo_treino.fit(disp=False)
    exog_holdout = eventos.reindex(holdout.index).values
    pred_holdout = res_treino.get_forecast(steps=HOLDOUT_MESES, exog=exog_holdout).predicted_mean.values
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)
    print(f"Holdout ({HOLDOUT_MESES}m, eventos reais): RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.3f}")
    print()

    exog_full = eventos.values
    modelo_full = SARIMAX(tds, exog=exog_full, order=ordem, seasonal_order=ordem_sazonal, trend=trend,
                           enforce_stationarity=False, enforce_invertibility=False)
    res_full = modelo_full.fit(disp=False)
    print(res_full.summary().tables[1])
    print()

    for nome_param in res_full.param_names:
        if "ma.S" in nome_param or "ar.S" in nome_param:
            val = float(res_full.params[nome_param])
            if abs(val) > 0.98:
                print(f"  AVISO DECLARADO: {nome_param}={val:.4f} está no limite do espaço admissível "
                      f"(quase não-invertível/não-estacionário) e com erro-padrão enorme — sinal de "
                      f"instabilidade de estimação na componente sazonal MA, não de um efeito real "
                      f"preciso. Os coeficientes dos eventos (abaixo) continuam interpretáveis, mas a "
                      f"incerteza deste componente específico deve ser lida com cautela.")
    print()

    idx_seca = list(eventos.columns).index("seca_2012_2016")
    idx_ordem = list(eventos.columns).index("ordem_conservacao_2015")
    nomes_exog = [n for n in res_full.param_names if "x1" in n or "x2" in n]
    coef_seca = float(res_full.params[f"x{idx_seca+1}"])
    p_seca = float(res_full.pvalues[f"x{idx_seca+1}"])
    coef_ordem = float(res_full.params[f"x{idx_ordem+1}"])
    p_ordem = float(res_full.pvalues[f"x{idx_ordem+1}"])
    print(f"Coeficiente seca_2012_2016: {coef_seca:+.2f} mg/L (p={p_seca:.4f})")
    print(f"Coeficiente ordem_conservacao_2015: {coef_ordem:+.2f} mg/L (p={p_ordem:.4f})")
    print()
    if p_seca < 0.05:
        print(f"  A seca de 2012-2016 tem efeito {'positivo' if coef_seca > 0 else 'negativo'} "
              f"estatisticamente significativo sobre o nível de TDS -- consistente com D-37/D-14.")
    else:
        print("  O coeficiente da seca não é estatisticamente significativo neste modelo específico "
              "(controlando por SARIMA + ordem de conservação) -- registrado como está, sem forçar leitura.")

    datas_futuras = pd.date_range(tds.index[-1], periods=max(HORIZONTES_ANOS) * 12 + 1, freq="ME")[1:]
    exog_fut = exog_futuro(datas_futuras, eventos)
    fc = res_full.get_forecast(steps=max(HORIZONTES_ANOS) * 12, exog=exog_fut)
    ic = fc.conf_int(alpha=ALPHA)

    linha = {
        "metodo": "intervencao_arimax_eventos",
        "tendencia_mgL_ano": float("nan"),  # tendencia aqui vem dos eventos, nao de um termo linear unico
        "tendencia_pvalor": p_seca,
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "ordem_sarima": f"order={ordem} seasonal_order={ordem_sazonal} trend={trend}",
        "hiperparametros": f"coef_seca={coef_seca:.2f}(p={p_seca:.4f}), coef_ordem_conservacao={coef_ordem:.2f}(p={p_ordem:.4f})",
    }
    print()
    for h in HORIZONTES_ANOS:
        idx = h * 12 - 1
        ponto = float(fc.predicted_mean.iloc[idx])
        lo, hi = float(ic.iloc[idx, 0]), float(ic.iloc[idx, 1])
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = lo
        linha[f"ci90_high_{h}y"] = hi
        print(f"  +{h}a: {ponto:.1f} mg/L  IC90% [{lo:.1f}, {hi:.1f}]  (premissas: sem seca futura, ordem de conservação mantida)")

    linha.update(validar_metodo(construir_fit_predict(eventos, ordem, ordem_sazonal, trend), tds, treino, holdout))
    print()
    print(f"MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(tds.index, tds.values, color="black", linewidth=1, label="TDS observado")
    for _, row in eventos[eventos["seca_2012_2016"] == 1].iterrows():
        pass
    ax.axvspan(pd.Timestamp(INICIO_SECA), pd.Timestamp(FIM_SECA), alpha=0.1, color="tab:orange", label="Seca 2012-2016")
    ax.axvline(pd.Timestamp(INICIO_ORDEM_CONSERVACAO), color="tab:green", linestyle=":", label="Ordem de conservação (abr/2015)")
    ax.plot(datas_futuras, fc.predicted_mean.values, "--", color="tab:blue", label="ARIMAX com eventos (previsão)")
    ax.fill_between(datas_futuras, ic.iloc[:, 0], ic.iloc[:, 1], color="tab:blue", alpha=0.15, label="IC90%")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Análise de intervenção: ARIMAX com regressores de evento (seca, ordem de conservação)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")

    linha["metodo"] = "intervencao_arimax_eventos"
    linha["script"] = "script_25_intervencao_arimax"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[existentes["metodo"] != "intervencao_arimax_eventos"]
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

    with iniciar_run("intervencao_arimax_eventos", "script_25_intervencao_arimax",
                      params={"ordem": str(ordem), "ordem_sazonal": str(ordem_sazonal)},
                      janela_treino_holdout={"treino_meses": len(treino), "holdout_meses": HOLDOUT_MESES}):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
