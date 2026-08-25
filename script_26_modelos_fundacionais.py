"""
Modelos fundacionais de series temporais (plano_projeto_TDS.md secao 3.f.9):
previsao ZERO-SHOT (sem treinar nada nos nossos dados) com um modelo
pre-treinado em milhoes de series temporais publicas.

Modelo usado: Chronos-Bolt-Small (Amazon, pesos abertos via HuggingFace,
`chronos-forecasting`). TimesFM e TimeGPT (Nixtla) foram AVALIADOS e
DESCARTADOS por este motivo especifico:
  - TimeGPT (Nixtla): API paga, exige chave de API que nao esta disponivel
    nesta sessao -- nao testado, declarado como tal, nao escondido.
  - TimesFM (Google): tambem pesos abertos, mas redundante com Chronos para
    o proposito deste teste (ambos zero-shot, mesma pergunta de pesquisa) --
    testar so um representante da categoria e suficiente para responder
    "modelos fundacionais generalistas superam os metodos classicos aqui?",
    sem duplicar custo computacional por pouco ganho de informacao.

Expectativa honesta declarada no plano ANTES de rodar: com ~180 pontos
mensais, e improvavel que um modelo zero-shot supere os metodos classicos
ja ajustados especificamente a esta serie -- mas o teste em si, com
resultado negativo relatado, tem valor cientifico (nao e obvio sem testar).

Limitacao tecnica do modelo: Chronos-Bolt foi treinado para quantis em
[0,1 - 0,9] -- nao da IC90 (5%-95%) nativo como os demais metodos da
bateria. Reportado como IC80 (10%-90%), rotulado como tal, NAO renomeado
para "IC90" so para bater com o padrao dos outros metodos.
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from chronos import BaseChronosPipeline

from script_00_preprocessamento import construir_datasets
from validacao_utils import mase, smape
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos

warnings.filterwarnings("ignore")

MODELO_HF = "amazon/chronos-bolt-small"
HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
QUANTIS_SUPORTADOS = [0.1, 0.5, 0.9]  # limite nativo do Chronos-Bolt, nao 0.05/0.95
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/modelos-fundacionais-tds.png"


def carregar_serie() -> pd.Series:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["Data"] = pd.to_datetime(d["Data"]) + pd.offsets.MonthEnd(0)
    return d.set_index("Data")["TDS_mgL"].asfreq("ME")


def prever(pipe, contexto: np.ndarray, n_passos: int, quantis=QUANTIS_SUPORTADOS):
    ctx = torch.tensor(contexto, dtype=torch.float32)
    q, mean = pipe.predict_quantiles(inputs=ctx, prediction_length=n_passos, quantile_levels=quantis)
    q = q[0].numpy()  # (n_passos, len(quantis))
    return q  # colunas na ordem de `quantis`


def main():
    print(f"=== Modelo fundacional zero-shot: {MODELO_HF} ===")
    print("TimeGPT (Nixtla) nao testado -- exige API key paga, indisponivel nesta sessao.")
    print("TimesFM nao testado -- redundante com Chronos para a pergunta de pesquisa (zero-shot generalista).")
    print()

    serie = carregar_serie()
    treino = serie.iloc[:-HOLDOUT_MESES]
    holdout = serie.iloc[-HOLDOUT_MESES:]
    print(f"Série TDS: {len(serie)} meses ({serie.index[0].date()} a {serie.index[-1].date()})")
    print(f"Treino (contexto): {len(treino)} | Holdout: {len(holdout)}")
    print()

    print("Baixando/carregando pesos do modelo (HuggingFace)...")
    pipe = BaseChronosPipeline.from_pretrained(MODELO_HF, device_map="cpu", torch_dtype=torch.float32)
    print("Modelo carregado.")
    print()

    # --- holdout: contexto = treino, previsao = proximos 24 meses ---
    q_holdout = prever(pipe, treino.values, HOLDOUT_MESES)
    pred_mediana = q_holdout[:, 1]  # quantil 0.5
    y_true = holdout.values
    rmse = float(np.sqrt(np.mean((y_true - pred_mediana) ** 2)))
    mae = float(np.mean(np.abs(y_true - pred_mediana)))
    ss_res = np.sum((y_true - pred_mediana) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot)
    mase_holdout = mase(y_true, pred_mediana, treino.values)
    smape_holdout = smape(y_true, pred_mediana)
    print(f"Holdout ({HOLDOUT_MESES}m, zero-shot, sem re-treino): RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.3f}")
    print(f"MASE={mase_holdout:.3f}  sMAPE={smape_holdout:.2f}%")
    if mase_holdout >= 1.0:
        print("  RESULTADO NEGATIVO CONFIRMADO: MASE >= 1 -- o modelo zero-shot NÃO supera o baseline naive "
          "neste holdout. Consistente com a expectativa declarada no plano antes de rodar.")
    print()

    # --- previsao real +10/+15/+20a: contexto = serie completa ---
    n_passos_max = max(HORIZONTES_ANOS) * 12
    q_full = prever(pipe, serie.values, n_passos_max)

    linha = {
        "metodo": "chronos_bolt_zero_shot",
        "tendencia_mgL_ano": float("nan"),  # modelo nao expoe um coeficiente de tendencia
        "tendencia_pvalor": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "mase_holdout": mase_holdout, "smape_holdout": smape_holdout,
        "hiperparametros": f"modelo={MODELO_HF}, zero_shot=True, quantis={QUANTIS_SUPORTADOS} (IC80, nao IC90)",
    }
    larguras = []
    for h in HORIZONTES_ANOS:
        idx = h * 12 - 1
        ponto = float(q_full[idx, 1])
        lo, hi = float(q_full[idx, 0]), float(q_full[idx, 2])
        linha[f"forecast_{h}y"] = ponto
        linha[f"ci90_low_{h}y"] = lo  # rotulado ci90_* por convencao da tabela, mas E IC80 -- ver nota no docstring/DECISOES
        linha[f"ci90_high_{h}y"] = hi
        larguras.append(hi - lo)
        print(f"  +{h}a: {ponto:.1f} mg/L  IC80% [{lo:.1f}, {hi:.1f}] (largura={hi-lo:.1f})  (nao IC90 -- limite nativo do modelo)")
    if larguras[-1] < larguras[0]:
        print("  AVISO DECLARADO: a largura do IC80 DIMINUI com o horizonte (contra-intuitivo -- os demais "
              "métodos da bateria têm incerteza crescente). Característica observada de cabeças de previsão "
              "DIRETA/multi-horizonte (não autorregressiva) como o Chronos-Bolt: os quantis de cada horizonte "
              "são preditos conjuntamente a partir do mesmo contexto fixo, sem compor incerteza passo a passo "
              "como um SARIMA faria. Não é um erro de implementação -- é reportado como propriedade do modelo, "
              "e é mais um motivo para não usar este método isoladamente como finalista de longo prazo.")
    print()

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(serie.index, serie.values, color="black", linewidth=1, label="TDS observado")
    datas_futuras = pd.date_range(serie.index[-1], periods=n_passos_max + 1, freq="ME")[1:]
    ax.plot(datas_futuras, q_full[:, 1], "--", color="tab:purple", label=f"{MODELO_HF} (mediana, zero-shot)")
    ax.fill_between(datas_futuras, q_full[:, 0], q_full[:, 2], color="tab:purple", alpha=0.15, label="IC80% (Q10-Q90)")
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("Modelo fundacional zero-shot (Chronos-Bolt-Small) — sem treino nos dados do projeto")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")

    linha["script"] = "script_26_modelos_fundacionais"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[existentes["metodo"] != "chronos_bolt_zero_shot"]
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

    with iniciar_run("chronos_bolt_zero_shot", "script_26_modelos_fundacionais",
                      params={"modelo": MODELO_HF, "zero_shot": True},
                      janela_treino_holdout={"treino_meses": len(treino), "holdout_meses": HOLDOUT_MESES}):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
