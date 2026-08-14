"""
LSTM leve (PyTorch) para o TDS -- bloco 3 do aprofundamento, testado
explicitamente sob a mesma validacao honesta dos demais metodos (MASE
holdout + CV expansiva + backtest de origem movel). O material de apoio
(Tema 6.3) documenta um precedente (XGBoost venceu LSTM em runoff mensal)
que serve de EXPECTATIVA A TESTAR aqui, nao de verdade assumida -- o
resultado real desta secao decide se o metodo "entra no relatorio" como
finalista ou fica registrado como testado-e-nao-vencedor.

Arquitetura deliberadamente pequena (1 camada LSTM, poucas unidades, janela
de 12 meses de lookback): ~180 pontos mensais nao sustentam uma rede grande
sem overffiting severo. CPU apenas (torch CPU-only instalado -- ver
requirements.txt; a serie e pequena demais para GPU valer a pena).

Holdout avaliado em modo one-step (janela real de lookback a cada passo,
mesma convencao ja usada para RF/XGBoost/SVR em scripts anteriores);
previsao recursiva (a previsao de um mes vira input do proximo) para os
horizontes longos e para o CV/backtest de validacao_utils, com IC90 por
bootstrap de residuos (mesma tecnica de script_09/SVR).

Univariado em TDS: independe do tratamento de ND do BOD.
"""

import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy import stats

from script_02_arima_sarima import carregar_serie_tds
from utils.experiment_tracking import iniciar_run, logar_linha_resultado, logar_artefatos
from validacao_utils import validar_metodo

HORIZONTES_ANOS = [10, 15, 20]
HOLDOUT_MESES = 24
ALPHA = 0.10  # IC90%
JANELA = 12
HIDDEN_SIZE = 32
EPOCHS = 200
EPOCHS_CV = 150  # menos epocas nos ~25 folds/origens de CV/backtest, por custo computacional
LR = 0.01
N_BOOTSTRAP = 200
SEED = 42
RESULTADOS_CSV = "resultados_comparacao.csv"
RESULTADOS_JSON = "resultados_comparacao.json"
FIGURA_PATH = "Artigo/images/lstm-tds.png"

warnings.filterwarnings("ignore")
rng = np.random.default_rng(SEED)


class LSTMForecaster(nn.Module):
    def __init__(self, hidden_size: int = HIDDEN_SIZE):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_size, num_layers=1, batch_first=True)
        self.linear = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.linear(out[:, -1, :])


def metrica_holdout(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return rmse, mae, r2


def criar_janelas(normalizada: np.ndarray, janela: int):
    X = [normalizada[i:i + janela] for i in range(len(normalizada) - janela)]
    y = [normalizada[i + janela] for i in range(len(normalizada) - janela)]
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def treinar_lstm(valores: np.ndarray, janela: int = JANELA, epochs: int = EPOCHS,
                  hidden_size: int = HIDDEN_SIZE, seed: int = SEED):
    torch.manual_seed(seed)
    media, desvio = float(valores.mean()), float(valores.std())
    normalizada = (valores - media) / desvio
    X, y = criar_janelas(normalizada, janela)
    X_t = torch.tensor(X).unsqueeze(-1)
    y_t = torch.tensor(y).unsqueeze(-1)

    modelo = LSTMForecaster(hidden_size)
    otim = torch.optim.Adam(modelo.parameters(), lr=LR)
    perda_fn = nn.MSELoss()
    modelo.train()
    for _ in range(epochs):
        otim.zero_grad()
        perda = perda_fn(modelo(X_t), y_t)
        perda.backward()
        otim.step()
    modelo.eval()
    return modelo, media, desvio


def prever_one_step(modelo, valores: np.ndarray, media: float, desvio: float, janela: int, n_avaliar: int):
    normalizada = (valores - media) / desvio
    n = len(valores)
    preds = []
    with torch.no_grad():
        for i in range(n - n_avaliar, n):
            x = torch.tensor(normalizada[i - janela:i], dtype=torch.float32).view(1, janela, 1)
            preds.append(modelo(x).item() * desvio + media)
    return np.array(preds)


def prever_recursivo(modelo, valores: np.ndarray, media: float, desvio: float, janela: int, n_passos: int,
                      residuos_boot: np.ndarray = None, n_boot: int = 0):
    normalizada_base = list((valores[-janela:] - media) / desvio)

    def caminho(injetar: bool):
        hist = list(normalizada_base)
        pontos = []
        with torch.no_grad():
            for _ in range(n_passos):
                x = torch.tensor(hist[-janela:], dtype=torch.float32).view(1, janela, 1)
                pred = modelo(x).item() * desvio + media
                if injetar:
                    pred = pred + rng.choice(residuos_boot)
                pontos.append(pred)
                hist.append((pred - media) / desvio)
        return pontos

    central = caminho(False)
    if n_boot == 0:
        return central, central, central
    replicas = np.array([caminho(True) for _ in range(n_boot)])
    baixos = np.percentile(replicas, 100 * ALPHA / 2, axis=0)
    altos = np.percentile(replicas, 100 * (1 - ALPHA / 2), axis=0)
    return central, baixos.tolist(), altos.tolist()


def construir_fit_predict_lstm():
    def fit_predict(treino: pd.Series, n_passos: int) -> np.ndarray:
        modelo, media, desvio = treinar_lstm(treino.values, epochs=EPOCHS_CV)
        pontos, _, _ = prever_recursivo(modelo, treino.values, media, desvio, JANELA, n_passos)
        return np.array(pontos)
    return fit_predict


def gerar_figura(s: pd.Series, datas_futuras, pontos, baixos, altos):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(s.index, s.values, color="black", linewidth=1, label="TDS observado")
    ax.plot(datas_futuras, pontos, "--", color="tab:purple", label="LSTM (previsão recursiva)")
    ax.fill_between(datas_futuras, baixos, altos, color="tab:purple", alpha=0.15)
    ax.set_xlabel("Data")
    ax.set_ylabel("TDS (mg/L)")
    ax.set_title("LSTM — previsão de TDS (+10/+15/+20 anos)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def gravar_resultados(linha: dict):
    linha["script"] = "script_13_deep_learning"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")
    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        existentes = existentes[~existentes["metodo"].isin(novas["metodo"])]
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas
    consolidado.to_csv(RESULTADOS_CSV, index=False)
    consolidado.to_json(RESULTADOS_JSON, orient="records", indent=2, force_ascii=False)


def main():
    s = carregar_serie_tds()
    treino, holdout = s.iloc[:-HOLDOUT_MESES], s.iloc[-HOLDOUT_MESES:]
    print(f"Serie TDS: {len(s)} meses | Treino: {len(treino)} | Holdout: {len(holdout)}")
    print(f"Arquitetura: LSTM 1 camada, {HIDDEN_SIZE} unidades, janela={JANELA} meses, {EPOCHS} epocas (CPU)")
    print()

    modelo_treino, media_tr, desvio_tr = treinar_lstm(treino.values)
    pred_holdout = prever_one_step(modelo_treino, s.values, media_tr, desvio_tr, JANELA, len(holdout))
    rmse, mae, r2 = metrica_holdout(holdout.values, pred_holdout)

    modelo_full, media_full, desvio_full = treinar_lstm(s.values)
    residuos = s.values[JANELA:] - np.array([
        modelo_full(torch.tensor((s.values[i - JANELA:i] - media_full) / desvio_full,
                                  dtype=torch.float32).view(1, JANELA, 1)).item() * desvio_full + media_full
        for i in range(JANELA, len(s))
    ])
    max_passos = max(HORIZONTES_ANOS) * 12
    pontos, baixos, altos = prever_recursivo(modelo_full, s.values, media_full, desvio_full, JANELA,
                                              max_passos, residuos, N_BOOTSTRAP)

    passos_10a = 10 * 12
    reg = stats.linregress(np.arange(passos_10a), pontos[:passos_10a])

    linha = {
        "metodo": "lstm", "tendencia_mgL_ano": reg.slope * 12, "tendencia_pvalor": reg.pvalue,
        "tendencia_ic90_baixo": float("nan"), "tendencia_ic90_alto": float("nan"),
        "rmse_holdout": rmse, "mae_holdout": mae, "r2_holdout": r2,
        "hiperparametros": str({"janela": JANELA, "hidden_size": HIDDEN_SIZE, "epochs": EPOCHS}),
    }
    for h in HORIZONTES_ANOS:
        passo = h * 12 - 1
        linha[f"forecast_{h}y"] = pontos[passo]
        linha[f"ci90_low_{h}y"] = baixos[passo]
        linha[f"ci90_high_{h}y"] = altos[passo]
        linha[f"ic90_width_{h}y"] = altos[passo] - baixos[passo]

    linha.update(validar_metodo(construir_fit_predict_lstm(), s, treino, holdout))

    print(f"Holdout (one-step): RMSE={linha['rmse_holdout']:.2f}  MASE={linha['mase_holdout']:.3f}  sMAPE={linha['smape_holdout']:.2f}%")
    print(f"CV: MASE={linha['cv_mase_media']:.3f}±{linha['cv_mase_desvio']:.3f}  Backtest+3a: MAE={linha.get('backtest_mae_36m', float('nan')):.2f}")

    if pd.io.common.file_exists(RESULTADOS_CSV):
        existentes = pd.read_csv(RESULTADOS_CSV)
        mase_naive = existentes.loc[existentes["metodo"] == "naive", "mase_holdout"]
        if len(mase_naive):
            venceu = linha["mase_holdout"] < mase_naive.iloc[0]
            print(f"\nMASE holdout do LSTM ({linha['mase_holdout']:.3f}) vs. naive ({mase_naive.iloc[0]:.3f}): "
                  f"{'LSTM venceu' if venceu else 'LSTM NAO venceu'} o baseline mais forte da bateria.")

    for h in HORIZONTES_ANOS:
        print(f"+{h}a: {linha[f'forecast_{h}y']:.1f} mg/L  IC90% [{linha[f'ci90_low_{h}y']:.1f}, {linha[f'ci90_high_{h}y']:.1f}]")

    gravar_resultados(linha)
    print(f"\nResultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

    datas_futuras = [s.index[-1] + pd.DateOffset(months=p) for p in range(1, max_passos + 1)]
    gerar_figura(s, datas_futuras, pontos, baixos, altos)

    with iniciar_run(
        "lstm", "script_13_deep_learning",
        params={"janela": JANELA, "hidden_size": HIDDEN_SIZE, "epochs": EPOCHS}, seed=SEED,
        janela_treino_holdout={"treino_meses": len(treino), "holdout_meses": len(holdout)},
    ):
        logar_linha_resultado(linha)
        logar_artefatos([FIGURA_PATH])


if __name__ == "__main__":
    main()
