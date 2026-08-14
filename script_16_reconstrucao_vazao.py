"""
Reconstrucao da vazao do efluente da LAGWRP (prompt_tratamento_e_metodos.md,
Etapa 1 -- plano_projeto_TDS.md secao 1.5): o dataset traz o MESMO parametro
em mg/L (concentracao) e lb/day (carga massica), que se relacionam pela
identidade padrao do setor:

    lb/day = mg/L * vazao(MGD) * 8,34   =>   vazao(MGD) = lb/day / (mg/L * 8,34)

Isso permite reconstruir a vazao do efluente, que nao aparece explicitamente
no dataset -- peca central para os metodos WRTDS/balanco de massa/cenarios
(plano_projeto_TDS.md secao 3.f.1-3.f.3), MAS SO SE a identidade se sustentar
nos dados reais. Este script so valida; nao roda nenhum metodo novo.

Validacao em duas frentes:
  1. Plausibilidade absoluta: a vazao derivada de TDS deve ser compativel com
     a capacidade nominal de 20 MGD da LAGWRP (brochure institucional).
  2. Consistencia cruzada entre parametros (mais forte): TDS, Cloreto,
     Amonia e BOD sao medidos na MESMA amostra fisica, entao a vazao
     derivada de cada um independentemente deve COINCIDIR se o pareamento
     mg/L<->lb/day for real. Divergencia grande entre as 4 series de vazao
     derivada e evidencia de que a identidade nao se sustenta (ou que o
     pareamento por data esta errado), nao um problema de um parametro so.

Se a vazao nao for plausivel/consistente, o resultado e reportado como tal
e a ideia de usa-la nos metodos 3.f.1-3.f.3 fica descartada -- nao forcada.
"""

import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from script_00_preprocessamento import carregar_csv, LOCATIONS_EFLUENTE, PARAMETROS
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

FATOR_CONVERSAO = 8.34  # lb por milhao de galoes por mg/L (convencao americana padrao)
CAPACIDADE_NOMINAL_MGD = 20.0  # LAGWRP, conforme brochure institucional
FAIXA_PLAUSIVEL_MGD = (2.0, 40.0)  # 10%-200% da capacidade nominal, faixa generosa
RESULTADOS_CSV = "vazao_reconstruida_resultados.csv"
RESULTADOS_JSON = "vazao_reconstruida_resultados.json"
VAZAO_SERIE_CSV = "vazao_reconstruida_serie.csv"
FIGURA_PATH = "Artigo/images/vazao-reconstruida.png"

ARQUIVOS = {"TDS": "TDS.csv", "Chloride": "Chloride.csv", "Ammonia": "Ammonia.csv", "BOD": "BOD.csv"}


def serie_mensal_valor(df: pd.DataFrame, parametro: str, unidade: str) -> pd.DataFrame:
    d = df[
        (df["Parameter"] == parametro)
        & (df["Location"].isin(LOCATIONS_EFLUENTE))
        & (df["Calculated Method"] == "Monthly Average (Mean)")
        & (df["Units"] == unidade)
    ].copy()
    d["Data"] = pd.to_datetime(d["Sampling Date"])
    d = d.sort_values("Data").drop_duplicates(subset="Data", keep="first")
    return d[["Data", "Result"]].rename(columns={"Result": "Result"})


def reconstruir_vazao_parametro(nome: str, arquivo: str) -> pd.DataFrame:
    df = carregar_csv(arquivo)
    mgl = serie_mensal_valor(df, PARAMETROS[nome], "mg/L").rename(columns={"Result": "mgL"})
    lbd = serie_mensal_valor(df, PARAMETROS[nome], "lb/day").rename(columns={"Result": "lbday"})
    m = mgl.merge(lbd, on="Data", how="inner").dropna()
    m = m[m["mgL"] > 0]
    m[f"vazao_mgd_{nome}"] = m["lbday"] / (m["mgL"] * FATOR_CONVERSAO)
    return m[["Data", f"vazao_mgd_{nome}"]]


def avaliar_plausibilidade(vazao: pd.Series) -> dict:
    baixo, alto = FAIXA_PLAUSIVEL_MGD
    fora_faixa = ((vazao < baixo) | (vazao > alto)).sum()
    return {
        "n": len(vazao), "media": float(vazao.mean()), "mediana": float(vazao.median()),
        "min": float(vazao.min()), "max": float(vazao.max()), "std": float(vazao.std()),
        "pct_capacidade_nominal": float(vazao.mean() / CAPACIDADE_NOMINAL_MGD * 100),
        "n_fora_faixa_plausivel": int(fora_faixa), "pct_fora_faixa_plausivel": float(fora_faixa / len(vazao) * 100),
    }


def gerar_figura(vazoes: pd.DataFrame):
    fig, axes = plt.subplots(2, 1, figsize=(8, 7))
    ax = axes[0]
    for col in vazoes.columns:
        if col.startswith("vazao_mgd_"):
            ax.plot(vazoes["Data"], vazoes[col], label=col.replace("vazao_mgd_", ""), linewidth=1, alpha=0.8)
    ax.axhline(CAPACIDADE_NOMINAL_MGD, color="black", linestyle=":", label=f"Capacidade nominal ({CAPACIDADE_NOMINAL_MGD} MGD)")
    ax.set_ylabel("Vazão derivada (MGD)")
    ax.set_title("Vazão reconstruída por parâmetro (lb/day ÷ (mg/L × 8,34))")
    ax.legend(fontsize=7)

    ax = axes[1]
    cols_vazao = [c for c in vazoes.columns if c.startswith("vazao_mgd_")]
    if "vazao_mgd_TDS" in cols_vazao:
        for col in cols_vazao:
            if col == "vazao_mgd_TDS":
                continue
            sub = vazoes[["vazao_mgd_TDS", col]].dropna()
            ax.scatter(sub["vazao_mgd_TDS"], sub[col], s=10, alpha=0.5, label=col.replace("vazao_mgd_", ""))
        lims = [vazoes[cols_vazao].min().min(), vazoes[cols_vazao].max().max()]
        ax.plot(lims, lims, color="black", linewidth=0.8, linestyle="--", label="y=x")
        ax.set_xlabel("Vazão derivada de TDS (MGD)")
        ax.set_ylabel("Vazão derivada de outro parâmetro (MGD)")
        ax.set_title("Consistência cruzada entre parâmetros")
        ax.legend(fontsize=7)

    fig.tight_layout()
    fig.savefig(FIGURA_PATH, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_PATH}")


def main():
    print(f"Fator de conversao: {FATOR_CONVERSAO} lb/(MGD*mg/L)  |  Capacidade nominal LAGWRP: {CAPACIDADE_NOMINAL_MGD} MGD")
    print()

    series = []
    plausibilidade = {}
    for nome, arquivo in ARQUIVOS.items():
        s = reconstruir_vazao_parametro(nome, arquivo)
        series.append(s)
        col = f"vazao_mgd_{nome}"
        stats = avaliar_plausibilidade(s[col])
        plausibilidade[nome] = stats
        print(f"--- Vazao derivada de {nome} (n={stats['n']} meses pareados mg/L<->lb/day) ---")
        print(f"  Media={stats['media']:.2f} MGD  Mediana={stats['mediana']:.2f}  "
              f"Min={stats['min']:.2f}  Max={stats['max']:.2f}  DP={stats['std']:.2f}")
        print(f"  {stats['pct_capacidade_nominal']:.1f}% da capacidade nominal em media  |  "
              f"{stats['n_fora_faixa_plausivel']}/{stats['n']} meses fora da faixa plausivel "
              f"{FAIXA_PLAUSIVEL_MGD} MGD ({stats['pct_fora_faixa_plausivel']:.1f}%)")
        print()

    vazoes = series[0]
    for s in series[1:]:
        vazoes = vazoes.merge(s, on="Data", how="outer")
    vazoes = vazoes.sort_values("Data").reset_index(drop=True)
    vazoes.to_csv(VAZAO_SERIE_CSV, index=False)

    cols_vazao = [c for c in vazoes.columns if c.startswith("vazao_mgd_")]
    corr = vazoes[cols_vazao].corr()
    print("--- Consistencia cruzada entre parametros (correlacao de Pearson) ---")
    print(corr.round(3).to_string())
    print()

    corr_media_tds = corr.loc["vazao_mgd_TDS", [c for c in cols_vazao if c != "vazao_mgd_TDS"]].mean()
    identidade_sustenta = (corr_media_tds > 0.5) and (plausibilidade["TDS"]["pct_fora_faixa_plausivel"] < 20)

    print(f"Correlacao media de vazao(TDS) com os demais parametros: {corr_media_tds:.3f}")
    if identidade_sustenta:
        print("CONCLUSAO: a identidade lb/day=mg/L*vazao*8,34 SE SUSTENTA nos dados "
              "(plausivel + consistente entre parametros independentes) -- habilitada para uso "
              "futuro em WRTDS/balanco de massa/cenarios (Etapa 3, aguardando aprovacao).")
    else:
        print("CONCLUSAO: a identidade NAO se sustenta de forma confiavel nos dados "
              "(implausivel e/ou inconsistente entre parametros) -- NAO sera usada para "
              "WRTDS/balanco de massa/cenarios; reportado como limitacao, nao forcado.")
    print()

    with iniciar_run("reconstrucao_vazao", "script_16_reconstrucao_vazao",
                      params={"fator_conversao": FATOR_CONVERSAO, "capacidade_nominal_mgd": CAPACIDADE_NOMINAL_MGD}):
        resultado = {
            "fator_conversao": FATOR_CONVERSAO,
            "capacidade_nominal_mgd": CAPACIDADE_NOMINAL_MGD,
            "plausibilidade_por_parametro": plausibilidade,
            "correlacao_cruzada": corr.round(4).to_dict(),
            "correlacao_media_tds_outros": float(corr_media_tds),
            "identidade_sustenta": bool(identidade_sustenta),
            "script": "script_16_reconstrucao_vazao",
            "data_execucao": datetime.now().isoformat(timespec="seconds"),
        }
        with open(RESULTADOS_JSON, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        pd.DataFrame([{
            "parametro": nome, **stats
        } for nome, stats in plausibilidade.items()]).to_csv(RESULTADOS_CSV, index=False)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON} / {VAZAO_SERIE_CSV}")

        gerar_figura(vazoes)

        metricas = {"correlacao_media_tds_outros": corr_media_tds, "identidade_sustenta": float(identidade_sustenta)}
        for nome, stats in plausibilidade.items():
            for k, v in stats.items():
                metricas[f"{nome}_{k}"] = v
        logar_metricas(metricas)
        logar_artefatos([FIGURA_PATH, VAZAO_SERIE_CSV])


if __name__ == "__main__":
    main()
