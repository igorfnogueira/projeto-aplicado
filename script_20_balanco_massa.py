"""
Modelo de balanco de massa (prompt_wrtds_balanco_cenarios.md, Tarefa 2):
em vez de extrapolar TDS diretamente, modela carga de sal (lb/day) e vazao
(MGD) SEPARADAMENTE e deriva TDS = carga / (vazao * 8,34).

Pergunta central: a carga de sal esta estavel/caindo enquanto a vazao cai
(-> confirma diluicao) ou a carga tambem sobe (-> mais sal entrando,
mecanismo diferente)?

CUIDADO DE CIRCULARIDADE (o mesmo risco do script_19, aqui ainda mais direto):
vazao_mgd_TDS foi definida por construcao como carga_TDS / (TDS_mgL * 8,34)
(script_16). Se essa vazao for usada aqui, TDS_previsto = carga_TDS /
(vazao_mgd_TDS * 8,34) = TDS_mgL por IDENTIDADE ALGEBRICA -- validacao
tautologica, R^2=1 garantido, sem nenhum valor cientifico. Por isso a vazao
usada no modelo principal e a derivada do CLORETO (serie independente); a
versao com vazao de TDS e calculada so para EXPOR a tautologia explicitamente
(nao como resultado).

Adaptacao da forma do SCSC (nao aplicada por falta de dado, D-30): o estudo
usa TDS_influente = TDS_origem + SML*populacao/vazao. Nao temos populacao nem
TDS de origem -- a forma usada aqui e a identidade fisica direta
TDS = carga/(vazao*8,34), sem o termo per-capita.
"""

import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from script_00_preprocessamento import carregar_csv, LOCATIONS_EFLUENTE, PARAMETROS
from script_16_reconstrucao_vazao import serie_mensal_valor
from utils.experiment_tracking import iniciar_run, logar_metricas, logar_artefatos

FATOR_CONVERSAO = 8.34
HORIZONTES_ANOS = [10, 15, 20]
RESULTADOS_CSV = "balanco_massa_resultados.csv"
RESULTADOS_JSON = "balanco_massa_resultados.json"
RESULTADOS_COMPARACAO_CSV = "resultados_comparacao.csv"
RESULTADOS_COMPARACAO_JSON = "resultados_comparacao.json"
FIGURA_DECOMP = "Artigo/images/balanco-massa-decomposicao.png"
FIGURA_VALIDACAO = "Artigo/images/balanco-massa-validacao.png"


def carregar_carga_tds() -> pd.DataFrame:
    """Carga de sal do TDS (lb/day), da linha 'Monthly Average (Mean)' em
    lb/day -- dado OBSERVADO diretamente, nao derivado de vazao alguma."""
    df = carregar_csv("TDS.csv")
    carga = serie_mensal_valor(df, PARAMETROS["TDS"], "lb/day").rename(columns={"Result": "carga_lb_dia"})
    return carga


def carregar_tds_mgl() -> pd.DataFrame:
    df = carregar_csv("TDS.csv")
    tds = serie_mensal_valor(df, PARAMETROS["TDS"], "mg/L").rename(columns={"Result": "TDS_mgL"})
    return tds


def theil_sen_trend(t_anos: np.ndarray, y: np.ndarray) -> dict:
    slope, intercept, lo, hi = stats.theilslopes(y, t_anos, alpha=0.90)
    tau, p = stats.kendalltau(t_anos, y)
    return {"slope_ano": float(slope), "intercept": float(intercept),
            "ic90_lo": float(lo), "ic90_hi": float(hi), "pvalor": float(p), "n": len(y)}


def projetar(trend: dict, t_alvo: float) -> tuple:
    ponto = trend["intercept"] + trend["slope_ano"] * t_alvo
    lo = trend["intercept"] + trend["ic90_lo"] * t_alvo
    hi = trend["intercept"] + trend["ic90_hi"] * t_alvo
    return ponto, min(lo, hi), max(lo, hi)


def metrica_validacao(y_true, y_pred) -> dict:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    r, p = stats.pearsonr(y_true, y_pred)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot)
    return {"rmse": rmse, "mae": mae, "correlacao_r": float(r), "correlacao_p": float(p), "r2": r2}


def gerar_figura_decomposicao(d: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(8, 8.5), sharex=True)
    axes[0].plot(d["Data"], d["carga_lb_dia"], color="tab:purple")
    axes[0].set_ylabel("Carga de sal (lb/dia)")
    axes[0].set_title("Decomposição do balanço de massa: carga × vazão × TDS")

    axes[1].plot(d["Data"], d["vazao_mgd_chloride"], color="tab:green")
    axes[1].set_ylabel("Vazão (MGD, via Cloreto)")

    axes[2].plot(d["Data"], d["TDS_mgL"], color="black", label="TDS observado", linewidth=1)
    axes[2].plot(d["Data"], d["tds_previsto_vazao_chloride"], color="tab:orange", linestyle="--",
                 label="TDS derivado (carga ÷ vazão de Cloreto)", linewidth=1.2)
    axes[2].set_ylabel("TDS (mg/L)")
    axes[2].legend(fontsize=7)
    axes[2].set_xlabel("Data")

    fig.tight_layout()
    fig.savefig(FIGURA_DECOMP, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_DECOMP}")


def gerar_figura_validacao(d: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(d["TDS_mgL"], d["tds_previsto_vazao_chloride"], s=12, alpha=0.6, color="tab:orange")
    lims = [d[["TDS_mgL", "tds_previsto_vazao_chloride"]].min().min(), d[["TDS_mgL", "tds_previsto_vazao_chloride"]].max().max()]
    ax.plot(lims, lims, color="black", linewidth=0.8, linestyle="--", label="y=x")
    ax.set_xlabel("TDS observado (mg/L)")
    ax.set_ylabel("TDS derivado do balanço de massa (mg/L)")
    ax.set_title("Validação histórica: carga ÷ (vazão de Cloreto × 8,34)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURA_VALIDACAO, dpi=140)
    plt.close(fig)
    print(f"Figura salva em {FIGURA_VALIDACAO}")


def gravar_resultados_comparacao(linha: dict):
    linha = dict(linha)
    linha["metodo"] = "balanco_massa"
    linha["script"] = "script_20_balanco_massa"
    linha["tratamento_nd_bod"] = "nao_aplicavel_metodo_univariado_tds"
    linha["data_execucao"] = datetime.now().isoformat(timespec="seconds")

    novas = pd.DataFrame([linha])
    if pd.io.common.file_exists(RESULTADOS_COMPARACAO_CSV):
        existentes = pd.read_csv(RESULTADOS_COMPARACAO_CSV)
        existentes = existentes[existentes["metodo"] != "balanco_massa"]
        for col in novas.columns:
            if col not in existentes.columns:
                existentes[col] = pd.NA
        for col in existentes.columns:
            if col not in novas.columns:
                novas[col] = pd.NA
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas
    consolidado.to_csv(RESULTADOS_COMPARACAO_CSV, index=False)
    consolidado.to_json(RESULTADOS_COMPARACAO_JSON, orient="records", indent=2, force_ascii=False)


def main():
    print("=== Balanço de massa: TDS = carga(lb/dia) / (vazão(MGD) × 8,34) ===")
    print()

    carga = carregar_carga_tds()
    tds = carregar_tds_mgl()
    vazoes = pd.read_csv("vazao_reconstruida_serie.csv", parse_dates=["Data"])

    d = tds.merge(carga, on="Data", how="inner")
    d = d.merge(vazoes[["Data", "vazao_mgd_TDS", "vazao_mgd_Chloride"]], on="Data", how="inner").dropna()
    d = d.rename(columns={"vazao_mgd_Chloride": "vazao_mgd_chloride"})
    d = d.sort_values("Data").reset_index(drop=True)
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    print(f"Série pareada (TDS mg/L + lb/dia + vazão): {len(d)} meses ({d['Data'].min().date()} a {d['Data'].max().date()})")
    print()

    with iniciar_run("balanco_massa", "script_20_balanco_massa", params={"fator_conversao": FATOR_CONVERSAO}):

        # --- 1. tendencia da carga de sal (independente da vazao) ---
        trend_carga = theil_sen_trend(d["t_anos"].values, d["carga_lb_dia"].values)
        pct_carga = trend_carga["slope_ano"] / d["carga_lb_dia"].mean() * 100
        print(f"--- Carga de sal (lb/dia) ---")
        print(f"  Inclinação: {trend_carga['slope_ano']:.1f} lb/dia/ano ({pct_carga:+.2f}%/ano), p={trend_carga['pvalor']:.4f}")

        # --- 2. tendencia da vazao (independente, via Cloreto) ---
        trend_vazao = theil_sen_trend(d["t_anos"].values, d["vazao_mgd_chloride"].values)
        pct_vazao = trend_vazao["slope_ano"] / d["vazao_mgd_chloride"].mean() * 100
        print(f"--- Vazão (MGD, via Cloreto) ---")
        print(f"  Inclinação: {trend_vazao['slope_ano']:.3f} MGD/ano ({pct_vazao:+.2f}%/ano), p={trend_vazao['pvalor']:.4f}")
        print()

        # --- pergunta central ---
        if pct_carga < 0.5 and pct_vazao < -0.5:
            mecanismo = "diluicao"
            leitura = "carga de sal estável/caindo + vazão caindo -> confirma o mecanismo de DILUIÇÃO (menos água, mesma massa de sal)"
        elif pct_carga > 0.5:
            mecanismo = "mais_sal"
            leitura = "carga de sal também sobe -> há MAIS SAL entrando no sistema, mecanismo adicional/diferente da diluição pura"
        else:
            mecanismo = "indeterminado"
            leitura = "padrão misto -- nem carga claramente estável nem vazão claramente em queda monotônica no período todo"
        print(f"--- Pergunta central: diluição ou mais sal? ---\n  {leitura}\n")

        # --- 3. TDS derivado (validacao historica) com vazao de Cloreto (nao-circular) ---
        d["tds_previsto_vazao_chloride"] = d["carga_lb_dia"] / (d["vazao_mgd_chloride"] * FATOR_CONVERSAO)
        val_chloride = metrica_validacao(d["TDS_mgL"], d["tds_previsto_vazao_chloride"])
        print("--- Validação histórica: TDS derivado (vazão de Cloreto, INDEPENDENTE) vs. observado ---")
        print(f"  RMSE={val_chloride['rmse']:.2f} mg/L | r={val_chloride['correlacao_r']:.3f} (p={val_chloride['correlacao_p']:.2e}) | R²={val_chloride['r2']:.3f}")

        # --- exposicao da tautologia com vazao de TDS (nao e resultado, e checagem) ---
        d["tds_previsto_vazao_tds"] = d["carga_lb_dia"] / (d["vazao_mgd_TDS"] * FATOR_CONVERSAO)
        val_tds = metrica_validacao(d["TDS_mgL"], d["tds_previsto_vazao_tds"])
        print("--- Checagem de tautologia: TDS derivado com vazão do PRÓPRIO TDS (circular por construção) ---")
        print(f"  RMSE={val_tds['rmse']:.4f} mg/L | R2={val_tds['r2']:.6f} (esperado ~1,0 -- identidade algebrica, NAO e validacao)")
        print()

        gerar_figura_decomposicao(d)
        gerar_figura_validacao(d)

        # --- 4. projecao +10/+15/+20a: carga e vazao extrapoladas separadamente ---
        t_ultimo = d["t_anos"].iloc[-1]
        print("--- Projeção +10/+15/+20a (carga e vazão extrapoladas separadamente, via Theil-Sen) ---")
        CAPACIDADE_NOMINAL_MGD = 20.0
        VAZAO_MIN_FISICA_MGD = 0.5  # so para evitar divisao por ~0 na formula, NAO um piso realista
        forecasts = {}
        projecao_implausivel_a_partir_de = None
        for h in HORIZONTES_ANOS:
            t_h = t_ultimo + h
            carga_h, carga_lo, carga_hi = projetar(trend_carga, t_h)
            vazao_h, vazao_lo, vazao_hi = projetar(trend_vazao, t_h)
            vazao_h_calc = vazao_h  # valor cru da extrapolacao linear, antes de qualquer piso
            vazao_h = max(vazao_h, VAZAO_MIN_FISICA_MGD)

            pct_capacidade = vazao_h_calc / CAPACIDADE_NOMINAL_MGD * 100
            if pct_capacidade < 20 and projecao_implausivel_a_partir_de is None:
                projecao_implausivel_a_partir_de = h

            # combinacoes extremas do IC90 de cada componente para o IC90 do TDS derivado
            candidatos = []
            for c in (carga_lo, carga_h, carga_hi):
                for v in (max(vazao_lo, VAZAO_MIN_FISICA_MGD), vazao_h, max(vazao_hi, VAZAO_MIN_FISICA_MGD)):
                    candidatos.append(c / (v * FATOR_CONVERSAO))
            ponto = carga_h / (vazao_h * FATOR_CONVERSAO)
            forecasts[f"forecast_{h}y"] = float(ponto)
            forecasts[f"ci90_low_{h}y"] = float(min(candidatos))
            forecasts[f"ci90_high_{h}y"] = float(max(candidatos))
            aviso = f"  <<< vazão linear extrapolada = {pct_capacidade:.0f}% da capacidade nominal -- FISICAMENTE IMPLAUSÍVEL" if pct_capacidade < 20 else ""
            print(f"  +{h}a: carga={carga_h:,.0f} lb/dia | vazão(linear)={vazao_h_calc:.2f} MGD | "
                  f"TDS derivado={ponto:.1f} mg/L [{min(candidatos):.1f}, {max(candidatos):.1f}]{aviso}")

        if projecao_implausivel_a_partir_de is not None:
            print(f"\n  LIMITAÇÃO REGISTRADA: a extrapolação LINEAR da vazão cruza valores fisicamente "
                  f"implausíveis (<20% da capacidade nominal de {CAPACIDADE_NOMINAL_MGD} MGD) já a partir de "
                  f"+{projecao_implausivel_a_partir_de} anos -- carga e vazão vêm caindo de forma consistente "
                  f"há 15 anos (ambas p<0,0001), mas extrapolar essa reta por décadas não é fisicamente "
                  f"sustentável (a vazão não pode continuar caindo linearmente até zero). Os pontos de TDS "
                  f"derivado acima NÃO devem ser lidos como previsão pontual confiável -- são reportados "
                  f"para expor essa fragilidade, não escondê-la. É exatamente o motivo pelo qual a Tarefa 3 "
                  f"(script_21_cenarios.py) substitui esta extrapolação linear por cenários de PDSI "
                  f"limitados a faixas historicamente observadas, em vez de projetar os componentes ao infinito.")
        print()

        resultado = {
            "trend_carga_lb_dia_ano": trend_carga["slope_ano"], "trend_carga_pct_ano": float(pct_carga), "trend_carga_pvalor": trend_carga["pvalor"],
            "trend_vazao_mgd_ano": trend_vazao["slope_ano"], "trend_vazao_pct_ano": float(pct_vazao), "trend_vazao_pvalor": trend_vazao["pvalor"],
            "mecanismo_identificado": mecanismo,
            "validacao_vazao_chloride": val_chloride,
            "validacao_vazao_tds_tautologia": val_tds,
            "forecasts": forecasts,
            "projecao_implausivel_a_partir_de_anos": projecao_implausivel_a_partir_de,
            "script": "script_20_balanco_massa",
            "data_execucao": datetime.now().isoformat(timespec="seconds"),
        }
        with open(RESULTADOS_JSON, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        d.to_csv(RESULTADOS_CSV, index=False)
        print(f"Resultados gravados em {RESULTADOS_CSV} / {RESULTADOS_JSON}")

        linha_comparacao = {
            "tendencia_mgL_ano": float(
                (trend_carga["intercept"] + trend_carga["slope_ano"] * (t_ultimo + 1)) / ((trend_vazao["intercept"] + trend_vazao["slope_ano"] * (t_ultimo + 1)) * FATOR_CONVERSAO)
                - d["tds_previsto_vazao_chloride"].iloc[-1]
            ),
            "tendencia_pvalor": min(trend_carga["pvalor"], trend_vazao["pvalor"]),
            "rmse_holdout": val_chloride["rmse"], "mae_holdout": val_chloride["mae"], "r2_holdout": val_chloride["r2"],
            **forecasts,
        }
        gravar_resultados_comparacao(linha_comparacao)

        metricas = {
            "trend_carga_pct_ano": pct_carga, "trend_carga_pvalor": trend_carga["pvalor"],
            "trend_vazao_pct_ano": pct_vazao, "trend_vazao_pvalor": trend_vazao["pvalor"],
            "validacao_chloride_rmse": val_chloride["rmse"], "validacao_chloride_r2": val_chloride["r2"],
            "validacao_tautologia_r2": val_tds["r2"],
        }
        metricas.update({f"forecast_{k}": v for k, v in forecasts.items()})
        logar_metricas(metricas)
        logar_artefatos([FIGURA_DECOMP, FIGURA_VALIDACAO, RESULTADOS_CSV])

    return resultado


if __name__ == "__main__":
    main()
