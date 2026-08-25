"""
GAM -- Modelo Aditivo Generalizado (plano_projeto_TDS.md secao 3.f.5):
TDS ~ s(tempo) + s(mes-do-ano), via pyGAM. Tendencia suave (spline, nao uma
reta), com banda de confianca nativa -- diferente do espaco de estados
(script_22), aqui a "forma" da tendencia e livre (nao linear nem
necessariamente monotonica), o que e apropriado para uma serie ja
identificada como ciclica (D-14/D-37).

Termo sazonal: tentativa de spline ciclica (basis='cp', continua em jan/dez)
com fallback documentado para P-spline comum se a versao do pyGAM instalada
nao suportar -- declarado explicitamente, nao escondido.
"""

import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pygam import LinearGAM, s

from script_00_preprocessamento import construir_datasets
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/gam-tds.png"


def carregar_serie() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["Data"] = pd.to_datetime(d["Data"])
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    d["mes"] = d["Data"].dt.month
    return d


def construir_termo_sazonal():
    try:
        termo = s(1, basis="cp", n_splines=12)
        LinearGAM(s(0) + termo).fit(np.zeros((20, 2)), np.zeros(20))
        return termo, "ciclica (basis='cp')"
    except Exception:
        return s(1, n_splines=8), "P-spline comum (fallback -- basis 'cp' indisponivel nesta versao do pyGAM)"


LAM_FLOOR_TENDENCIA = 1.0  # ver nota abaixo: GCV irrestrito escolhe lambda~0,001 e extrapola de forma explosiva


def ajustar_gam(X: np.ndarray, y: np.ndarray, termo_sazonal, lam_min_tendencia: float = LAM_FLOOR_TENDENCIA) -> LinearGAM:
    """Ajusta o GAM com um PISO no lambda (suavizacao) do termo de tendencia.

    Decisao metodologica declarada: minimizar GCV sem restricao escolhe
    lambda~0,001 (spline pouco suavizada) -- otimo em ajuste IN-SAMPLE, mas
    produz extrapolacao explosiva (>1900 mg/L em +10a, ~3x o range historico)
    porque GCV nao penaliza o comportamento da derivada da spline fora do
    intervalo observado, uma patologia conhecida de P-splines. Por isso a
    busca de lambda para o termo de tendencia e restrita a >= 1,0 (ainda
    escolhido por GCV dentro dessa faixa, nao fixado arbitrariamente) --
    troca uma pequena piora de ajuste in-sample por extrapolacao estavel. O
    resultado SEM essa restricao e reportado a parte (funcao
    diagnosticar_instabilidade_sem_restricao), nao escondido."""
    termos = s(0, n_splines=8) + termo_sazonal
    gam = LinearGAM(termos)
    lams_tendencia = np.logspace(np.log10(lam_min_tendencia), 3, 10)
    lams_sazonal = np.logspace(-3, 3, 11)
    gam.gridsearch(X, y, lam=[lams_tendencia, lams_sazonal], progress=False)
    return gam


def diagnosticar_instabilidade_sem_restricao(X: np.ndarray, y: np.ndarray, termo_sazonal, t_ultimo: float) -> dict:
    """Reproduz o ajuste SEM piso no lambda, so para reportar a instabilidade
    de extrapolacao como achado declarado (nao usado como resultado oficial)."""
    termos = s(0, n_splines=8) + termo_sazonal
    gam = LinearGAM(termos)
    lams = np.logspace(-3, 3, 11)
    gam.gridsearch(X, y, lam=[lams, lams], progress=False)
    pred_10a = float(gam.predict(np.array([[t_ultimo + 10, 3]]))[0])
    return {"lam_tendencia_sem_piso": float(gam.lam[0][0]), "forecast_10y_sem_piso": pred_10a}


def fit_predict_gam(termo_sazonal):
    def _fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        data0 = treino.index[0]
        t = (treino.index - data0).days / 365.25
        mes = treino.index.month.values
        X = np.column_stack([t.values, mes])
        gam = ajustar_gam(X, treino.values, termo_sazonal)
        datas_futuras = pd.date_range(treino.index[-1], periods=n_passos + 1, freq="ME")[1:]
        t_fut = (datas_futuras - data0).days / 365.25
        X_fut = np.column_stack([t_fut, datas_futuras.month])
        return gam.predict(X_fut)
    return _fit_predict


def main():
    d = carregar_serie()
    treino = d.iloc[:-HOLDOUT_MESES].reset_index(drop=True)
    holdout = d.iloc[-HOLDOUT_MESES:].reset_index(drop=True)
    print(f"Serie TDS: {len(d)} meses ({d['Data'].iloc[0].date()} a {d['Data'].iloc[-1].date()})")
    print(f"Treino: {len(treino)} | Holdout: {len(holdout)}")
    print()

    termo_sazonal, tipo_sazonal = construir_termo_sazonal()
    print(f"Termo sazonal: {tipo_sazonal}")
    print()

    X_treino = np.column_stack([treino["t_anos"].values, treino["mes"].values])
    gam_treino = ajustar_gam(X_treino, treino["TDS_mgL"].values, termo_sazonal)
    X_holdout = np.column_stack([holdout["t_anos"].values, holdout["mes"].values])
    pred_holdout = gam_treino.predict(X_holdout)
    y_true = holdout["TDS_mgL"].values
    rmse = float(np.sqrt(np.mean((y_true - pred_holdout) ** 2)))
    mae = float(np.mean(np.abs(y_true - pred_holdout)))
    ss_res = np.sum((y_true - pred_holdout) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot)
    print(f"Holdout ({HOLDOUT_MESES}m): RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.3f}")
    print()

    X_full = np.column_stack([d["t_anos"].values, d["mes"].values])
    gam_full = ajustar_gam(X_full, d["TDS_mgL"].values, termo_sazonal)
    print(f"lambdas escolhidos por gridsearch (GCV, com piso={LAM_FLOOR_TENDENCIA} na tendência): {gam_full.lam}")
    print(f"EDoF (graus de liberdade efetivos): {gam_full.statistics_['edof']:.2f}")
    print()

    diagnostico_instabilidade = diagnosticar_instabilidade_sem_restricao(
        X_full, d["TDS_mgL"].values, termo_sazonal, d["t_anos"].iloc[-1]
    )
    print("--- Diagnóstico declarado: GCV SEM piso no lambda (não usado como resultado oficial) ---")
    print(f"  lambda ótimo por GCV puro: {diagnostico_instabilidade['lam_tendencia_sem_piso']:.4f}")
    print(f"  Previsão +10a resultante: {diagnostico_instabilidade['forecast_10y_sem_piso']:.1f} mg/L "
          f"(~{diagnostico_instabilidade['forecast_10y_sem_piso']/d['TDS_mgL'].iloc[-1]:.1f}x o último valor observado "
          f"-- extrapolação explosiva, patologia conhecida de P-splines sob GCV irrestrito)")
    print()

    # significancia dos termos (p-valores aproximados do pyGAM, via teste F)
    resumo_termos = gam_full.summary()

    # tendencia media local (derivada numerica do termo suave s(0) nos ultimos 24 meses vs primeiros 24)
    t_grid = np.linspace(d["t_anos"].min(), d["t_anos"].max(), 200)
    XX = gam_full.generate_X_grid(term=0, n=200)
    pdep, conf = gam_full.partial_dependence(term=0, X=XX, width=0.90)
    inclinacao_local = np.gradient(pdep, XX[:, 0])
    tendencia_media_mgL_ano = float(inclinacao_local.mean())
    print(f"Tendência média do termo suave s(tempo): {tendencia_media_mgL_ano:.3f} mg/L/ano "
          f"(derivada numérica média — a inclinação real varia ao longo da série, não é uma reta)")
    print()

    t_ultimo = d["t_anos"].iloc[-1]
    linha = {
        "metodo": "gam",
        "tendencia_mgL_ano": tendencia_media_mgL_ano,
        "tendencia_pvalor": float("nan"),  # GAM nao tem p-valor unico de tendencia (termo suave, nao linear)
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
    }
    for h in HORIZONTES_ANOS:
        t_h = t_ultimo + h
        X_h = np.array([[t_h, ((d["Data"].iloc[-1] + pd.DateOffset(years=h)).month)]])
        ponto = float(gam_full.predict(X_h)[0])
        ic = gam_full.prediction_intervals(X_h, width=0.90)
        lo, hi = float(ic[0, 0]), float(ic[0, 1])
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = lo
        linha[f"ci90_high_{h}y"] = hi
        print(f"  +{h}a: {ponto:.1f} mg/L  IC90% [{lo:.1f}, {hi:.1f}]")
    print()

    serie_indexada = pd.Series(d["TDS_mgL"].values, index=pd.DatetimeIndex(d["Data"], freq="ME"))
    treino_serie = serie_indexada.iloc[:-HOLDOUT_MESES]
    holdout_serie = serie_indexada.iloc[-HOLDOUT_MESES:]
    linha.update(validar_metodo(fit_predict_gam(termo_sazonal), serie_indexada, treino_serie, holdout_serie))
    print(f"MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(d["Data"], d["TDS_mgL"], color="gray", linewidth=0.8, alpha=0.6, label="TDS observado")
    ax.plot(d["Data"], gam_full.predict(X_full), color="tab:blue", linewidth=1.4, label="GAM ajustado")
    datas_futuras = [d["Data"].iloc[-1] + pd.DateOffset(months=int(h * 12)) for h in HORIZONTES_ANOS]
    pontos = [linha[f"forecast_{h}y"] for h in HORIZONTES_ANOS]
    los = [linha[f"ci90_low_{h}y"] for h in HORIZONTES_ANOS]
    his = [linha[f"ci90_high_{h}y"] for h in HORIZONTES_ANOS]
    ax.plot([d["Data"].iloc[-1]] + datas_futuras, [d["TDS_mgL"].iloc[-1]] + pontos, "--", color="tab:red", label="Previsão")
    ax.fill_between(datas_futuras, los, his, color="tab:red", alpha=0.15, label="IC90%")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title(f"GAM: s(tempo) + s(mês, {tipo_sazonal.split('(')[0].strip()})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")

    linha["script"] = "script_23_gam"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    linha["hiperparametros"] = (
        f"n_splines_tempo=8, termo_sazonal={tipo_sazonal}, lam={list(gam_full.lam)}, "
        f"edof={gam_full.statistics_['edof']:.2f}, lam_floor_tendencia={LAM_FLOOR_TENDENCIA}, "
        f"lam_sem_piso={diagnostico_instabilidade['lam_tendencia_sem_piso']:.4f}, "
        f"forecast_10y_sem_piso={diagnostico_instabilidade['forecast_10y_sem_piso']:.1f}"
    )

    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[existentes["metodo"] != "gam"]
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

    with iniciar_run("gam", "script_23_gam", params={"termo_sazonal": tipo_sazonal, "n_splines_tempo": 8},
                      janela_treino_holdout={"treino_meses": len(treino), "holdout_meses": HOLDOUT_MESES}):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
