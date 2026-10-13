"""Dashboard publico dos resultados do projeto TDS/LAGWRP -- pensado para
outros pesquisadores do mesmo tema explorarem e comparar com seus proprios
projetos, sem precisar rodar o pipeline completo (que depende de PyMC,
Prophet, XGBoost, LightGBM etc.). Consome apenas os CSVs/figuras ja
gerados pelo pipeline (pasta data/ e images/), bundlados junto com o Space.
A maioria dos CSVs em data/ sao copia de results/ (ou data/processed/) e
ficam velhos se a fonte mudar sem recopiar -- ver README.md deste pacote
para a lista completa. serie_tds_mensal.csv existe so neste pacote.

As abas seguem a ordem em que o projeto conta sua propria historia (e nao
a ordem em que os scripts foram implementados): narrativa final -> tendencia
e fragilidade -> investigacao causal -> bateria de previsao -> objetivos
secundarios -> metodos avancados (baixa prioridade) -> bateria de validacao
e correcoes -> sobre o projeto. Pensado para apoio visual de apresentacao
de banca, nao so exploracao livre.

Repositorio completo (codigo, dados e resultados): ver link na ultima aba.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from ui_helpers import cabecalho_com_ajuda, injetar_estilo_tooltip

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = Path(__file__).parent / "images"

REPO_URL = "https://github.com/igorfnogueira/projeto-aplicado"

FINALISTAS = {
    "regressao_bayesiana": "Regressão bayesiana",
    "detrend_rf": "Detrend + Random Forest",
    "hibrido_arima_prophet": "Híbrido SARIMA + Prophet",
}

# Métodos cujo rmse_holdout NÃO é um RMSE de previsão de TDS out-of-sample
# comparável aos demais. São análises mecanísticas ou de cenário. WRTDS,
# balanço de massa e os cenários gravam NaN nessa coluna
# (script_20_balanco_massa.py:294 no balanço). O RMSE da checagem de
# cloreto fica em validacao_chloride_rmse (script_20_balanco_massa.py:295),
# não em rmse_holdout. Excluídos do ranking por padrão para não misturar
# com o holdout de 24 meses dos métodos de previsão.
METODOS_NAO_COMPARAVEIS = {
    "wrtds_flow_normalized", "balanco_massa",
    "cenario_pdsi_agravamento_climatico", "cenario_pdsi_normal",
    "cenario_pdsi_seco", "cenario_pdsi_umido", "cenario_pdsi_rcp85_caladapt",
}

# Agrupamento só para navegação da aba "Bateria de previsão por categoria" --
# não existe coluna "categoria" em resultados_comparacao.csv, então o
# agrupamento é mantido aqui (mesmo padrão do dict FINALISTAS acima).
CATEGORIAS_METODO = {
    "naive": "Baselines", "naive_sazonal": "Baselines",
    "ets_holt_winters": "Baselines", "theta": "Baselines",
    "mann_kendall_sen": "Estatístico clássico", "theil_sen": "Estatístico clássico",
    "ols": "Estatístico clássico", "stl_tendencia_linear": "Estatístico clássico",
    "sarima": "Estatístico clássico", "sarima_com_pdsi": "Estatístico clássico",
    "sarimax_cloreto": "Estatístico clássico", "intervencao_arimax_eventos": "Estatístico clássico",
    "random_forest": "Árvore/ML", "random_forest_com_pdsi": "Árvore/ML",
    "random_forest_pdsi_multilag": "Árvore/ML",
    "xgboost": "Árvore/ML", "xgboost_com_pdsi": "Árvore/ML", "xgboost_pdsi_multilag": "Árvore/ML",
    "lightgbm": "Árvore/ML", "lightgbm_com_pdsi": "Árvore/ML", "lightgbm_pdsi_multilag": "Árvore/ML",
    "detrend_rf": "Árvore/ML", "detrend_rf_com_pdsi": "Árvore/ML", "detrend_xgb": "Árvore/ML",
    "svr": "Árvore/ML", "svr_com_pdsi": "Árvore/ML", "gaussian_process": "Árvore/ML",
    "regressao_bayesiana": "Bayesiano/Prophet", "regressao_bayesiana_com_pdsi": "Bayesiano/Prophet",
    "prophet": "Bayesiano/Prophet", "prophet_com_pdsi": "Bayesiano/Prophet",
    "hibrido_arima_prophet": "Híbrido", "hibrido_arima_prophet_com_pdsi": "Híbrido",
    "lstm": "Deep learning/Fundacional", "chronos_bolt_zero_shot": "Deep learning/Fundacional",
    "espaco_estados_dlm": "Avançado (baixa prioridade)", "espaco_estados_dlm_com_pdsi": "Avançado (baixa prioridade)",
    "gam": "Avançado (baixa prioridade)", "gam_com_pdsi": "Avançado (baixa prioridade)",
    "regressao_quantilica_q10": "Avançado (baixa prioridade)", "regressao_quantilica_q50": "Avançado (baixa prioridade)",
    "regressao_quantilica_q90": "Avançado (baixa prioridade)",
    "regressao_quantilica_q50_com_pdsi": "Avançado (baixa prioridade)",
    "regressao_quantilica_q50_pdsi_lagsel": "Avançado (baixa prioridade)",
    "wrtds_flow_normalized": "Mecanístico/cenário", "balanco_massa": "Mecanístico/cenário",
    "cenario_pdsi_agravamento_climatico": "Mecanístico/cenário", "cenario_pdsi_normal": "Mecanístico/cenário",
    "cenario_pdsi_seco": "Mecanístico/cenário", "cenario_pdsi_umido": "Mecanístico/cenário",
    "cenario_pdsi_rcp85_caladapt": "Mecanístico/cenário",
}

st.set_page_config(
    page_title="TDS LAGWRP — resultados",
    page_icon=":material/water_drop:",
    layout="wide",
)
injetar_estilo_tooltip()


@st.cache_data
def carregar_serie() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "serie_tds_mensal.csv", parse_dates=["Data"])


@st.cache_data
def carregar_resultados() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "resultados_comparacao.csv")


@st.cache_data
def carregar_comparacao_pdsi() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "comparacao_pdsi_antes_depois.csv")


@st.cache_data
def carregar_comparacao_finetuning() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "comparacao_pdsi_finetuning_multilag.csv")


@st.cache_data
def carregar_testes_robustez() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "testes_robustez_resultados.csv")


@st.cache_data
def carregar_cv_aninhada() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "cv_aninhada_resultados.csv")


@st.cache_data
def carregar_diagnostico_residuos() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "diagnostico_residuos_resultados.csv")


@st.cache_data
def carregar_pdsi_regimes() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "pdsi_regimes_resultados.csv")


@st.cache_data
def carregar_wrtds() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "wrtds_resultados.csv", parse_dates=["Data"])


@st.cache_data
def carregar_balanco_massa() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "balanco_massa_resultados.csv", parse_dates=["Data"])


@st.cache_data
def carregar_matriz_sensibilidade() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "matriz_sensibilidade_resultados.csv")


@st.cache_data
def carregar_cenarios() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "cenarios_resultados.csv")


@st.cache_data
def carregar_ladwp() -> pd.DataFrame:
    # Mesma convencao do pipeline (CLAUDE.md): separador ';', decimal ','.
    return pd.read_csv(DATA_DIR / "ladwp_tds_origem_vs_efluente.csv", sep=";", decimal=",")


def montar_pontos_forecast(
    resultados: pd.DataFrame, metodos: list[str], ultima_data: pd.Timestamp, ultimo_valor: float
) -> pd.DataFrame:
    linhas = []
    for metodo in metodos:
        row = resultados.loc[resultados["metodo"] == metodo]
        if row.empty:
            continue
        row = row.iloc[0]
        # Ponto de ancoragem em h=0 (hoje, = último valor observado) -- sem ele a
        # linha/banda de IC começa direto em +10a, com um vão sem traço nenhum
        # entre o fim da série histórica e o primeiro ponto de previsão.
        linhas.append({
            "metodo": FINALISTAS.get(metodo, metodo),
            "Data": ultima_data,
            "TDS_mgL": ultimo_valor,
            "ci_baixo": ultimo_valor,
            "ci_alto": ultimo_valor,
        })
        for h in (10, 15, 20):
            linhas.append({
                "metodo": FINALISTAS.get(metodo, metodo),
                "Data": ultima_data + pd.DateOffset(years=h),
                "TDS_mgL": row.get(f"forecast_{h}y"),
                "ci_baixo": row.get(f"ci90_low_{h}y"),
                "ci_alto": row.get(f"ci90_high_{h}y"),
            })
    return pd.DataFrame(linhas)


serie = carregar_serie()
resultados = carregar_resultados()

st.title("Tendência de salinidade (TDS) em efluente de ETE — LAGWRP")
st.caption(
    "Los Angeles–Glendale Water Reclamation Plant · dados públicos eSMR (California Water Boards) · "
    f"{serie['Data'].min():%b/%Y} a {serie['Data'].max():%b/%Y}"
)

with st.container(horizontal=True):
    st.metric("Meses de dados", f"{len(serie)}", border=True)
    st.metric("Métodos comparados", f"{resultados['metodo'].nunique()}", border=True)
    st.metric("TDS médio no último ano", f"{serie['TDS_mgL'].tail(12).mean():.0f} mg/L", border=True)
    ultimo, primeiro_ano = serie["TDS_mgL"].iloc[-12:].mean(), serie["TDS_mgL"].iloc[:12].mean()
    st.metric(
        "Variação desde o 1º ano",
        f"{ultimo - primeiro_ano:+.0f} mg/L",
        border=True,
    )

(
    aba_narrativa, aba_tendencia, aba_causal, aba_metodos,
    aba_secundarios, aba_avancados, aba_validacao, aba_sobre,
) = st.tabs([
    "1. Narrativa final",
    "2. Tendência e fragilidade",
    "3. Investigação causal",
    "4. Bateria de previsão",
    "5. Objetivos secundários",
    "6. Métodos avançados",
    "7. Validação e correções",
    "8. Sobre o projeto",
])

# ---------------------------------------------------------------------------
# 1. Narrativa final
# ---------------------------------------------------------------------------
with aba_narrativa:
    st.subheader("O achado central do projeto")
    st.markdown(
        """
O mecanismo por trás da tendência de TDS é **diluição** — a vazão de efluente cai mais rápido do
que a carga de sal — fortemente ligada a **ciclos de seca**, não uma tendência monotônica simples.

Não há um único "melhor modelo": três finalistas, escolhidos por representarem mecanismos de
extrapolação distintos (estatístico bayesiano, árvore sobre série destendenciada, híbrido
SARIMA+Prophet), convergem para uma faixa semelhante em +20 anos apesar de partirem de abordagens
completamente diferentes. **Essa convergência é tratada como a evidência mais forte — não o ponto
de previsão de nenhum modelo isolado.**

As abas seguintes seguem a ordem em que esse achado foi construído e, na aba 7, a autocrítica
metodológica que qualifica o quão forte essa conclusão pode ser defendida.
        """
    )
    cabecalho_com_ajuda(
        "Figura de síntese (script_15)",
        "Linha cinza = TDS mensal observado (eixo Y em mg/L, eixo X em anos). As 3 linhas coloridas "
        "tracejadas são a extrapolação de cada finalista a partir do fim da série — repare que elas "
        "ficam próximas entre si em +20 anos mesmo vindo de métodos matematicamente muito diferentes. "
        "Isso é o argumento central do projeto, não qualquer linha isolada.",
    )
    st.image(str(IMAGES_DIR / "sintese-final-finalistas.png"))

# ---------------------------------------------------------------------------
# 2. Tendência e sua fragilidade
# ---------------------------------------------------------------------------
with aba_tendencia:
    st.subheader("Série histórica e previsão dos 3 finalistas")
    st.markdown(
        "O projeto não recomenda um único método vencedor — três finalistas, escolhidos por "
        "representarem mecanismos de extrapolação distintos, convergem para uma faixa semelhante "
        "em +20 anos apesar de partirem de abordagens completamente diferentes."
    )

    metodos_selecionados = st.pills(
        "Finalistas exibidos",
        options=list(FINALISTAS.keys()),
        format_func=lambda m: FINALISTAS[m],
        selection_mode="multi",
        default=list(FINALISTAS.keys()),
    )

    if metodos_selecionados:
        pontos = montar_pontos_forecast(
            resultados, metodos_selecionados, serie["Data"].max(), serie["TDS_mgL"].iloc[-1]
        )

        # Domínio do eixo Y calculado só a partir da série histórica e dos pontos
        # de previsão (não do IC90) -- alguns métodos (ex. híbrido SARIMA+Prophet)
        # têm IC90 extremamente largo em +20a (chega a valores negativos, uma
        # limitação já conhecida do projeto), que estouraria a escala se entrasse
        # no cálculo do domínio. As bandas de IC fora do domínio são recortadas
        # (clip=True), não removidas -- a largura real ainda aparece no tooltip.
        y_min = min(serie["TDS_mgL"].min(), pontos["TDS_mgL"].min()) - 50
        y_max = max(serie["TDS_mgL"].max(), pontos["TDS_mgL"].max()) + 100
        escala_y = alt.Scale(domain=[y_min, y_max])

        base_hist = alt.Chart(serie).mark_line(color="#4c4c4c", clip=True).encode(
            x=alt.X("Data:T", title="Data"),
            y=alt.Y("TDS_mgL:Q", title="TDS (mg/L)", scale=escala_y),
        )
        banda_ic = alt.Chart(pontos).mark_area(opacity=0.15, clip=True).encode(
            x="Data:T",
            y=alt.Y("ci_baixo:Q", title="TDS (mg/L)", scale=escala_y),
            y2="ci_alto:Q",
            color=alt.Color("metodo:N", title="Método"),
        )
        linha_forecast = alt.Chart(pontos).mark_line(point=True, strokeDash=[4, 3], clip=True).encode(
            x="Data:T",
            y=alt.Y("TDS_mgL:Q", scale=escala_y),
            color=alt.Color("metodo:N", title="Método"),
            tooltip=["metodo", "Data:T", "TDS_mgL:Q", "ci_baixo:Q", "ci_alto:Q"],
        )
        cabecalho_com_ajuda(
            "Série + previsão dos finalistas",
            "Linha cinza sólida = TDS mensal observado até hoje. Cada cor = um finalista; o ponto "
            "tracejado é a previsão pontual em +10/+15/+20 anos, e a faixa sombreada da mesma cor é o "
            "intervalo de confiança de 90% dessa previsão. Passe o mouse sobre os pontos para ver os "
            "valores exatos. Atenção: a aba 7 mostra que a cobertura real desses IC90 varia de 13% a 91% "
            "dependendo do método/métrica — perto do nominal só para a regressão bayesiana via CV "
            "expansiva (86,7%); trate a largura da faixa dos demais como ilustrativa, não calibrada.",
        )
        st.altair_chart((base_hist + banda_ic + linha_forecast).interactive())
        if (pontos["ci_baixo"] < y_min).any() or (pontos["ci_alto"] > y_max).any():
            st.caption(
                "O IC90% de pelo menos um método selecionado se estende além do eixo mostrado "
                "(ex. o híbrido SARIMA+Prophet chega a valores implausíveis/negativos em +20a) — "
                "passe o mouse sobre os pontos para ver a largura real do intervalo."
            )
    else:
        st.line_chart(serie, x="Data", y="TDS_mgL")

    st.divider()
    st.subheader("A tendência muda de sinal sob um recorte razoável da série")
    st.markdown(
        "Dois testes de robustez (issue #1, `script_31`) recalculam a tendência Mann-Kendall/Theil-Sen "
        "removendo um ano por vez, e removendo os primeiros N anos. O segundo teste encontra uma "
        "**inversão de sinal estatisticamente significativa**: a tendência, positiva na série completa, "
        "fica negativa e significativa ao remover os 3 ou 4 primeiros anos."
    )

    robustez = carregar_testes_robustez()
    sweep_inicio = robustez[robustez["item"] == "5b_remover_primeiros_n_anos"].copy()
    sweep_inicio = sweep_inicio[sweep_inicio["metrica"] == "mann_kendall_sen_slope_mgL_ano"]
    sweep_inicio["anos_removidos"] = (
        sweep_inicio["variante"].str.extract(r"(\d+)").astype(int)
    )
    # O item 5b só cobre N=1..5 -- sem a barra N=0 (série completa) não há
    # referência visual do ponto de partida (+3,91 mg/L/ano) contra o qual a
    # inversão de sinal é comparada. Barra reconstruída a partir da linha
    # mann_kendall_sen de resultados_comparacao.csv, mesma fonte da aba 1/4.
    linha_mk = resultados.loc[resultados["metodo"] == "mann_kendall_sen"].iloc[0]
    baseline = pd.DataFrame([{
        "anos_removidos": 0,
        "valor_metrica": linha_mk["tendencia_mgL_ano"],
        "pvalor": linha_mk["tendencia_pvalor"],
    }])
    sweep_inicio = pd.concat([baseline, sweep_inicio], ignore_index=True).sort_values("anos_removidos")

    cabecalho_com_ajuda(
        "Sweep: removendo os N primeiros anos",
        "Eixo X = quantos anos iniciais da série foram removidos antes de recalcular a tendência (N=0 "
        "= série completa, a tendência 'oficial' do artigo). Eixo Y = a nova inclinação (mg/L por "
        "ano) — positivo significa salinidade subindo, negativo significa caindo. Barras vermelhas "
        "marcam onde o resultado é estatisticamente significativo (p < 0,05). Veja como o sinal muda "
        "de positivo e significativo (N=0) para positivo mas não significativo (N=1) para negativo e "
        "significativo (N=3, N=4) e depois para zero (N=5) — isso é a fragilidade, não um erro de "
        "cálculo.",
    )
    grafico_sweep = (
        alt.Chart(sweep_inicio)
        .mark_bar()
        .encode(
            x=alt.X("anos_removidos:O", title="Anos removidos do início da série"),
            y=alt.Y("valor_metrica:Q", title="Tendência (mg/L/ano)"),
            color=alt.condition(
                "datum.pvalor < 0.05",
                alt.value("#d62728"),
                alt.value("#9aa0a6"),
            ),
            tooltip=[
                alt.Tooltip("anos_removidos:O", title="Anos removidos"),
                alt.Tooltip("valor_metrica:Q", title="Tendência (mg/L/ano)", format=".2f"),
                alt.Tooltip("pvalor:Q", title="p-valor", format=".4f"),
            ],
        )
    )
    st.altair_chart(grafico_sweep)
    st.caption(
        "Barra vermelha = p-valor < 0,05 (estatisticamente significativo). Cinza = não significativo."
    )

# ---------------------------------------------------------------------------
# 3. Investigação causal
# ---------------------------------------------------------------------------
with aba_causal:
    st.subheader("Por que o TDS sobe? A investigação do mecanismo")
    st.markdown(
        "Quatro análises independentes testam o mesmo mecanismo proposto — queda de vazão (ligada a "
        "ciclos de seca, medidos pelo PDSI) superando a queda de carga de sal — a partir de ângulos "
        "diferentes."
    )

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            cabecalho_com_ajuda(
                "PDSI × regimes de TDS (D-37)",
                "O painel mostra a série do índice de seca PDSI (invertido ou não, conforme a figura) "
                "sobreposta aos regimes de TDS identificados por changepoints. Procure por sincronismo: "
                "períodos de seca (PDSI muito negativo) coincidindo com os regimes de TDS mais alto.",
            )
            st.image(str(IMAGES_DIR / "pdsi-vs-tds-regimes.png"))
            pdsi_regimes = carregar_pdsi_regimes()
            linha_ca = pdsi_regimes[pdsi_regimes["serie_pdsi"] == "california_estadual"].iloc[0]
            st.caption(
                f"PDSI estadual (CA), defasagem de {int(linha_ca['lag_melhor_correlacao_meses'])} meses: "
                f"r = {linha_ca['r_bruta']:.2f} (p = {linha_ca['p_bruta_dof_efetivo']:.4f}, "
                f"graus de liberdade efetivos ajustados por autocorrelação)."
            )
    with col2:
        with st.container(border=True):
            cabecalho_com_ajuda(
                "WRTDS — TDS normalizado por vazão",
                "Três linhas: TDS observado (cinza, com ruído), o ajuste WRTDS 'fitted' (azul — a "
                "mesma série suavizada pelo modelo) e a versão 'flow-normalized' (vermelha, mais "
                "grossa — TDS que teria ocorrido com vazão média histórica, removendo o efeito puro "
                "de variação de vazão). Se a vermelha sobe muito menos que a cinza/azul, a tendência "
                "observada é majoritariamente efeito de vazão, não mais sal entrando.",
            )
            st.image(str(IMAGES_DIR / "wrtds-flow-normalized.png"))

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            cabecalho_com_ajuda(
                "Balanço de massa (carga × vazão)",
                "Decompõe o TDS observado em carga de sal (lb/dia) e vazão (MGD). TDS = carga ÷ vazão × "
                "constante. Se a carga for relativamente estável e a vazão cair, o quociente sobe — "
                "esse é o mecanismo de diluição sendo mostrado graficamente.",
            )
            st.image(str(IMAGES_DIR / "balanco-massa-decomposicao.png"))
    with col4:
        with st.container(border=True):
            cabecalho_com_ajuda(
                "TDS na água de origem vs. efluente (LADWP)",
                "Compara o TDS da água que chega à cidade (aqueduto, MWD, água subterrânea — ponderado "
                "pelas proporções de cada fonte) com o TDS do efluente da ETE. Uma correlação alta "
                "sugere que parte da tendência já vem de antes de entrar na rede de esgoto, não só do "
                "processo de tratamento ou da vazão de efluente.",
            )
            st.image(str(IMAGES_DIR / "ladwp-tds-origem-vs-efluente.png"))
            ladwp = carregar_ladwp()
            st.caption(f"Sobreposição de {len(ladwp)} anos entre a série de origem e o efluente da LAGWRP.")

# ---------------------------------------------------------------------------
# 4. Bateria de previsão por categoria
# ---------------------------------------------------------------------------
with aba_metodos:
    st.subheader("Todos os métodos comparados")
    st.markdown(
        "Cada linha é uma execução independente sobre os mesmos dados: RMSE/MAE/R² em *holdout* de 24 meses, "
        "métricas de validação honesta (CV expansiva + *backtest*) e previsão pontual com IC90% em +10/+15/+20 anos."
    )

    categorias_disponiveis = sorted(set(CATEGORIAS_METODO.values()))
    categorias_selecionadas = st.multiselect(
        "Categorias exibidas",
        options=categorias_disponiveis,
        default=[c for c in categorias_disponiveis if c != "Mecanístico/cenário"],
    )

    mostrar_nao_comparaveis = st.checkbox(
        "Incluir também análises mecanísticas/de cenário (WRTDS, balanço de massa, cenários climáticos)",
        value="Mecanístico/cenário" in categorias_selecionadas,
        help=(
            "Essas análises respondem uma pergunta diferente da bateria de previsão (mecanismo, "
            "faixa condicionada ao clima) e não têm um RMSE de holdout de TDS comparável — o balanço "
            "de massa em particular reporta nessa coluna o RMSE de uma validação de circularidade do "
            "Cloreto, não uma previsão de TDS. Incluídas aqui só para referência, não para o ranking."
        ),
    )
    categorias_filtro = set(categorias_selecionadas)
    if mostrar_nao_comparaveis:
        categorias_filtro.add("Mecanístico/cenário")

    resultados_tabela = resultados[
        resultados["metodo"].map(lambda m: CATEGORIAS_METODO.get(m, "Outro")).isin(categorias_filtro)
    ]
    if not mostrar_nao_comparaveis:
        resultados_tabela = resultados_tabela[~resultados_tabela["metodo"].isin(METODOS_NAO_COMPARAVEIS)]

    colunas_exibidas = [
        "metodo", "rmse_holdout", "mae_holdout", "r2_holdout", "mase_holdout",
        "cv_rmse_media", "tendencia_mgL_ano", "tendencia_pvalor",
        "forecast_10y", "forecast_15y", "forecast_20y",
    ]
    ordenar_por = st.selectbox(
        "Ordenar por",
        options=["rmse_holdout", "cv_rmse_media", "mase_holdout", "tendencia_mgL_ano"],
        format_func=lambda c: {
            "rmse_holdout": "RMSE (holdout)",
            "cv_rmse_media": "RMSE (CV expansiva)",
            "mase_holdout": "MASE (holdout)",
            "tendencia_mgL_ano": "Tendência (mg/L/ano)",
        }[c],
    )
    tabela = resultados_tabela[colunas_exibidas].sort_values(ordenar_por, na_position="last").reset_index(drop=True)
    st.dataframe(
        tabela,
        column_config={
            "metodo": st.column_config.TextColumn("Método"),
            "rmse_holdout": st.column_config.NumberColumn("RMSE holdout", format="%.2f"),
            "mae_holdout": st.column_config.NumberColumn("MAE holdout", format="%.2f"),
            "r2_holdout": st.column_config.NumberColumn("R² holdout", format="%.3f"),
            "mase_holdout": st.column_config.NumberColumn("MASE holdout", format="%.3f"),
            "cv_rmse_media": st.column_config.NumberColumn("RMSE CV expansiva", format="%.2f"),
            "tendencia_mgL_ano": st.column_config.NumberColumn("Tendência (mg/L/ano)", format="%.3f"),
            "tendencia_pvalor": st.column_config.NumberColumn("p-valor da tendência", format="%.4f"),
            "forecast_10y": st.column_config.NumberColumn("Previsão +10a", format="%.0f mg/L"),
            "forecast_15y": st.column_config.NumberColumn("Previsão +15a", format="%.0f mg/L"),
            "forecast_20y": st.column_config.NumberColumn("Previsão +20a", format="%.0f mg/L"),
        },
        hide_index=True,
    )

    cabecalho_com_ajuda(
        "RMSE de holdout por método",
        "Barras ordenadas do menor (melhor) para o maior erro. RMSE = erro médio de previsão em mg/L "
        "sobre os últimos 24 meses da série, que nenhum método viu durante o treino. Menor é melhor, "
        "mas compare sempre com a aba 7 — o mesmo método pode ter RMSE de holdout bom e ainda falhar "
        "em diagnósticos de resíduo ou em CV expansiva.",
    )
    grafico_barras = tabela.dropna(subset=["rmse_holdout"]).sort_values("rmse_holdout")
    # st.bar_chart nativo ordena o eixo categórico alfabeticamente por padrão,
    # ignorando a ordem das linhas do DataFrame -- Altair direto com sort
    # explícito é necessário para manter a ordenação por RMSE.
    grafico_rmse = (
        alt.Chart(grafico_barras)
        .mark_bar()
        .encode(
            x=alt.X("rmse_holdout:Q", title="RMSE holdout (mg/L)"),
            y=alt.Y("metodo:N", title="Método", sort=grafico_barras["metodo"].tolist()),
            tooltip=["metodo", "rmse_holdout"],
        )
    )
    st.altair_chart(grafico_rmse)

# ---------------------------------------------------------------------------
# 5. Objetivos secundários
# ---------------------------------------------------------------------------
with aba_secundarios:
    st.subheader("Matriz de sensibilidade (9 decisões de pré-processamento)")
    st.markdown(
        "Testa se 9 decisões metodológicas (tratamento de não-detectados, ponto de quebra, agregação "
        "mensal, outliers, correção de autocorrelação na tendência, escala, entre outras) mudam a "
        "conclusão central. A maioria não muda; a autocorrelação da tendência (item 8) é a exceção "
        "mais relevante — ver a tabela de variantes abaixo e a aba 7 para a decisão tomada (D-15)."
    )
    cabecalho_com_ajuda(
        "Item 8 — autocorrelação na tendência (script_17)",
        "A figura mostra só o item mais relevante dos 9 (ver seletor abaixo para os outros 8): o "
        "p-valor da tendência de TDS sob 5 correções de autocorrelação diferentes para o mesmo teste "
        "Mann-Kendall, contra a linha de referência α=0,05. Barra verde = abaixo da linha (p < 0,05, "
        "tendência estatisticamente significativa); barra vermelha = acima (não significativa) — "
        "duas das 5 correções (Hamed-Rao e pre-whitening) invertem a conclusão.",
    )
    st.image(str(IMAGES_DIR / "matriz-sensibilidade.png"))

    matriz = carregar_matriz_sensibilidade()
    item_selecionado = st.selectbox(
        "Ver item em detalhe",
        options=sorted(matriz["item"].unique()),
    )
    st.dataframe(
        matriz[matriz["item"] == item_selecionado][
            ["variante", "valor_substituto", "metrica", "valor_metrica", "pvalor", "n"]
        ].reset_index(drop=True),
        hide_index=True,
    )

    st.divider()
    st.subheader("Cenários Monte Carlo sob diferentes regimes de PDSI")
    st.markdown(
        "Em vez de prever um único futuro, simula a faixa de TDS esperada sob 4 regimes de seca "
        "(normal, seco, úmido, agravamento climático), usando o PDSI como condicionante."
    )
    cabecalho_com_ajuda(
        "Leque de cenários (fan chart) — cenário normal",
        "Esta figura mostra só o cenário 'normal' (dos 4 simulados — ver tabela abaixo para os outros "
        "3). Linha azul = mediana das 2.000 simulações Monte Carlo; faixa sombreada = intervalo entre "
        "os percentis 5 e 95 — não é uma previsão pontual única, é uma distribuição inteira de "
        "futuros plausíveis.",
    )
    st.image(str(IMAGES_DIR / "cenarios-pdsi-fanchart.png"))

# ---------------------------------------------------------------------------
# 6. Métodos avançados (baixa prioridade)
# ---------------------------------------------------------------------------
with aba_avancados:
    st.subheader("O PDSI (índice de seca) melhora a previsão como covariável?")
    st.markdown(
        "O PDSI já explica bem o *regime* cíclico do TDS (correlação cruzada, D-37, aba 3), mas isso "
        "não significa automaticamente que adicioná-lo como *covariável exógena* melhora o desempenho "
        "preditivo dos métodos. Duas rodadas testaram isso diretamente, com critério de aceitação "
        "rígido: só conta como melhoria real se o RMSE da validação honesta (CV expansiva) também "
        "melhorar, não apenas o *holdout* isolado."
    )

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            cabecalho_com_ajuda(
                "D-56 — bateria original com PDSI",
                "Cada par de barras compara o RMSE do mesmo método sem e com PDSI como covariável. "
                "Barra menor com PDSI = melhora; maior = piora. A maioria piora ou não muda de forma "
                "consistente entre holdout e CV.",
            )
            st.caption("Sem melhora consistente: 4 de 12 métodos melhoraram, 8 pioraram")
            st.image(str(IMAGES_DIR / "bateria-pdsi-covariavel-comparacao.png"))
    with col2:
        with st.container(border=True):
            cabecalho_com_ajuda(
                "D-57 — fine-tuning da representação do PDSI",
                "Mesma lógica de comparação, mas testando múltiplas defasagens (lags) do PDSI em vez "
                "de uma só. Só o XGBoost mostra melhora real (holdout E CV expansiva simultaneamente).",
            )
            st.caption("Só o XGBoost melhorou de fato (holdout e CV expansiva)")
            st.image(str(IMAGES_DIR / "pdsi-finetuning-multilag-comparacao.png"))

    st.subheader("Tabela — antes (sem PDSI) vs. depois (com PDSI, D-56)")
    comp_d56 = carregar_comparacao_pdsi()
    st.dataframe(
        comp_d56[["metodo", "rmse_holdout_antes", "rmse_holdout_depois", "rmse_holdout_variacao_pct"]],
        column_config={
            "metodo": st.column_config.TextColumn("Método"),
            "rmse_holdout_antes": st.column_config.NumberColumn("RMSE sem PDSI", format="%.2f"),
            "rmse_holdout_depois": st.column_config.NumberColumn("RMSE com PDSI", format="%.2f"),
            "rmse_holdout_variacao_pct": st.column_config.NumberColumn("Variação", format="%+.1f%%"),
        },
        hide_index=True,
    )

    st.subheader("Tabela — lag único (D-56) vs. fine-tuning (D-57)")
    comp_d57 = carregar_comparacao_finetuning()
    st.dataframe(
        comp_d57[["metodo", "rmse_holdout_antes_com_pdsi", "rmse_holdout_depois_finetuning",
                  "rmse_holdout_variacao_pct", "cv_rmse_media_variacao_pct"]],
        column_config={
            "metodo": st.column_config.TextColumn("Método"),
            "rmse_holdout_antes_com_pdsi": st.column_config.NumberColumn("RMSE lag único", format="%.2f"),
            "rmse_holdout_depois_finetuning": st.column_config.NumberColumn("RMSE fine-tuning", format="%.2f"),
            "rmse_holdout_variacao_pct": st.column_config.NumberColumn("Variação holdout", format="%+.1f%%"),
            "cv_rmse_media_variacao_pct": st.column_config.NumberColumn("Variação CV expansiva", format="%+.1f%%"),
        },
        hide_index=True,
    )

    st.divider()
    st.caption(
        "Outros métodos exploratórios/baixa prioridade (GAM, regressão quantílica, espaço de estados, "
        "LSTM, Chronos-Bolt, cenário Cal-Adapt RCP 8.5) aparecem na tabela comparativa da aba 4, "
        "categoria \"Avançado (baixa prioridade)\" — não detalhados aqui; existem, mas não fazem parte "
        "do argumento central defendido."
    )

# ---------------------------------------------------------------------------
# 7. Bateria de validação e correções
# ---------------------------------------------------------------------------
with aba_validacao:
    st.subheader("Autocrítica metodológica (issues #1, #9–#15 · script_31/script_32)")
    st.markdown(
        "Esta aba existe para que a banca veja a autocrítica, não só o resultado favorável. Uma "
        "rodada de testes de robustez, fechada em 2026-10-12, qualificou a confiança que se pode "
        "depositar nos achados das abas anteriores."
    )

    robustez = carregar_testes_robustez()

    st.markdown(
        "Quatro testes independentes, cada um batendo num ângulo diferente da confiança que se pode "
        "depositar nos achados das abas anteriores: calibração do IC90%, diferença estatística entre "
        "finalistas, sinal de overfitting e limpeza do resíduo fora da amostra."
    )

    st.subheader("1. O IC90% declarado nem sempre é estatisticamente calibrado")
    cobertura = robustez[
        (robustez["item"] == "1_cobertura_ic")
        & (robustez["metrica"].isin(["cv_ic90_cobertura_pct", "backtest_ic90_cobertura_pct_36m", "backtest_ic90_cobertura_pct_60m"]))
    ]
    cobertura_pivot = cobertura.pivot(index="variante", columns="metrica", values="valor_metrica")
    cabecalho_com_ajuda(
        "Cobertura empírica do IC90% por método",
        "Cada barra é a % de vezes que o intervalo de 90% de confiança realmente conteve o valor "
        "observado, medida de 3 formas (CV expansiva, backtest de 36 e 60 meses). Se a calibração "
        "estivesse correta, toda barra chegaria perto de 90% (linha de referência pontilhada) — na "
        "prática, a maioria fica abaixo do nominal; a regressão bayesiana é a exceção, com cobertura "
        "via CV expansiva (86,7%) próxima de 90%.",
    )
    cobertura_long = cobertura_pivot.reset_index().melt(id_vars="variante", var_name="metrica", value_name="cobertura_pct")
    # Nomes de coluna crus do CSV não servem de rótulo de legenda -- sem este
    # mapeamento a legenda mostra "backtest_ic90_cobertura_pct_36m" truncado.
    NOMES_METRICA_COBERTURA = {
        "cv_ic90_cobertura_pct": "CV expansiva (5 folds)",
        "backtest_ic90_cobertura_pct_36m": "Backtest 36m",
        "backtest_ic90_cobertura_pct_60m": "Backtest 60m",
    }
    cobertura_long["metrica"] = cobertura_long["metrica"].map(NOMES_METRICA_COBERTURA)
    grafico_cobertura = (
        alt.Chart(cobertura_long)
        .mark_bar()
        .encode(
            x=alt.X("variante:N", title="Método"),
            y=alt.Y("cobertura_pct:Q", title="Cobertura empírica do IC90% (%)"),
            color=alt.Color("metrica:N", title="Métrica de validação"),
            xOffset="metrica:N",
            tooltip=["variante", "metrica", alt.Tooltip("cobertura_pct:Q", format=".1f")],
        )
    )
    linha_90 = alt.Chart(pd.DataFrame({"y": [90]})).mark_rule(strokeDash=[4, 2], color="red").encode(y="y:Q")
    st.altair_chart(grafico_cobertura + linha_90)
    st.caption(
        "A cobertura da regressão bayesiana usa a posterior completa (slope + sigma) via NUTS "
        "por fold/origem — diferente do IC só-da-inclinação do OLS, por isso é testada separadamente "
        "(não tratada como equivalente ao OLS aqui, ao contrário dos itens 2-4 abaixo)."
    )

    st.subheader("2. Diebold-Mariano — os finalistas diferem entre si?")
    dm = robustez[robustez["item"] == "2_diebold_mariano"][["variante", "valor_metrica", "pvalor"]]
    dm.columns = ["comparação", "estatística DM", "p-valor"]
    cabecalho_com_ajuda(
        "Teste de Diebold-Mariano por par",
        "Testa se o erro de previsão de um método é estatisticamente diferente do outro, par a par. "
        "p-valor < 0,05 = diferença real. Detrend+RF difere de SARIMA (p=0,044) e do híbrido "
        "(p=0,041) — mas não da regressão bayesiana contra nenhum dos outros.",
    )
    st.dataframe(dm.reset_index(drop=True), hide_index=True)

    st.subheader("3. Gap in-sample × CV × holdout (sinal de overfitting)")
    cabecalho_com_ajuda(
        "Gap in-sample × CV × holdout — finalistas + runner-up",
        "Para cada método, 3 barras: RMSE ajustado na série completa ('in-sample' — o modelo já viu "
        "esses dados), RMSE médio de 5 folds de CV expansiva, e RMSE do holdout de 24 meses nunca "
        "vistos. Uma barra in-sample bem mais baixa que as outras duas é sinal de alerta de "
        "overfitting — repare no Detrend+RF.",
    )
    st.image(str(IMAGES_DIR / "testes-robustez-avancados.png"))
    gap = robustez[robustez["item"] == "4_gap_overfitting"]
    gap_pivot = gap.pivot(index="variante", columns="metrica", values="valor_metrica")[
        ["rmse_in_sample", "rmse_cv", "rmse_holdout"]
    ].reset_index()
    st.dataframe(
        gap_pivot.rename(columns={
            "variante": "método", "rmse_in_sample": "RMSE in-sample",
            "rmse_cv": "RMSE CV expansiva", "rmse_holdout": "RMSE holdout",
        }),
        hide_index=True,
    )

    st.subheader("4. Diagnóstico de resíduos — in-sample vs. holdout")
    cabecalho_com_ajuda(
        "Resíduos in-sample dos 5 candidatos (contexto)",
        "Cada painel mostra o resíduo (erro) do método ao longo de toda a série (182 meses, dados que "
        "o próprio modelo já viu ao ser ajustado), mais Ljung-Box (autocorrelação) e Shapiro-Wilk "
        "(normalidade). Isto é o diagnóstico original (script_14) que motivou escolher o Detrend+RF — "
        "veja a tabela abaixo para o resultado real fora da amostra, que é diferente.",
    )
    st.image(str(IMAGES_DIR / "diagnostico-residuos-finalistas.png"))
    diag = carregar_diagnostico_residuos()
    st.dataframe(
        diag[["metodo", "ljung_box_pvalor", "ljung_box_ok", "shapiro_pvalor", "shapiro_ok"]].rename(columns={
            "metodo": "método", "ljung_box_pvalor": "p-valor Ljung-Box (in-sample)", "ljung_box_ok": "passa Ljung-Box",
            "shapiro_pvalor": "p-valor Shapiro (in-sample)", "shapiro_ok": "passa Shapiro",
        }),
        column_config={
            # Notação científica -- sem isso, p=1.99e-100 vira uma string de
            # ~100 zeros, ilegível e quebra a largura da coluna.
            "p-valor Ljung-Box (in-sample)": st.column_config.NumberColumn(format="%.2e"),
            "p-valor Shapiro (in-sample)": st.column_config.NumberColumn(format="%.2e"),
        },
        hide_index=True,
    )

    cabecalho_com_ajuda(
        "Ljung-Box/Shapiro/ARCH no holdout (24 meses reais) — o achado que importa",
        "Mesmos 3 testes, agora sobre o resíduo genuíno de previsão fora da amostra (24 meses nunca "
        "vistos no treino), não sobre o ajuste na série completa acima. p-valor < 0,05 = teste "
        "rejeitado (problema detectado). Compare com a tabela in-sample: o Detrend+RF deixa de ser "
        "'o único sem autocorrelação' — todos os 5 falham Ljung-Box no holdout.",
    )
    residuos_holdout = robustez[robustez["item"] == "3_residuos_holdout"].copy()
    residuos_holdout[["metodo", "teste"]] = residuos_holdout["variante"].str.split("__", expand=True)
    residuos_holdout_pivot = residuos_holdout.pivot(
        index="metodo", columns="teste", values="valor_metrica"
    )[["ljung_box", "shapiro", "arch"]].reset_index()
    st.dataframe(
        residuos_holdout_pivot.rename(columns={
            "metodo": "método", "ljung_box": "p-valor Ljung-Box (holdout)",
            "shapiro": "p-valor Shapiro (holdout)", "arch": "p-valor ARCH (holdout)",
        }),
        column_config={
            "p-valor Ljung-Box (holdout)": st.column_config.NumberColumn(format="%.3f"),
            "p-valor Shapiro (holdout)": st.column_config.NumberColumn(format="%.3f"),
            "p-valor ARCH (holdout)": st.column_config.NumberColumn(format="%.3f"),
        },
        hide_index=True,
    )

    st.subheader("5. CV aninhada vs. hiperparâmetro fixo")
    cv_aninhada = carregar_cv_aninhada()
    cabecalho_com_ajuda(
        "Hiperparâmetro fixo × CV aninhada por método",
        "Compara o MASE médio de CV usando o mesmo hiperparâmetro para todas as janelas (fixo) contra "
        "re-otimizar o hiperparâmetro em cada janela (aninhado). Diferença pequena (<3,4%) confirma "
        "que usar hiperparâmetro fixo não é a causa de nenhum dos achados acima.",
    )
    cv_pivot = cv_aninhada.pivot(index="metodo", columns="variante", values="cv_mase_media").reset_index()
    st.dataframe(
        cv_pivot.rename(columns={"metodo": "método", "fixo": "MASE (fixo)", "aninhado": "MASE (aninhado)"}),
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# 8. Sobre o projeto
# ---------------------------------------------------------------------------
with aba_sobre:
    st.subheader("Sobre o projeto")
    st.markdown(
        f"""
Projeto de pós-graduação (IA Aplicada) analisando a tendência de longo prazo de sólidos totais
dissolvidos (TDS) no efluente da **Los Angeles–Glendale Water Reclamation Plant (LAGWRP)**, a partir
de dados públicos eSMR (Electronic Self-Monitoring Report) do portal da California Water Boards.

**O que este Space mostra:** resultados já computados de uma bateria de ~35 métodos de previsão
(estatísticos clássicos, árvores, deep learning, Bayesiano, híbridos), diagnósticos estruturais,
investigação causal do mecanismo, e a bateria completa de testes de robustez/overfitting — pensado
para outros pesquisadores do mesmo tema comparar contra seus próprios resultados, sem precisar
reproduzir o pipeline completo (que depende de PyMC, Prophet, XGBoost, LightGBM, entre outros
pacotes pesados).

**Reprodutibilidade:** código-fonte completo, dados e resultados do pipeline estão no repositório público:

[{REPO_URL}]({REPO_URL})

**Licença dos dados:** os dados brutos são públicos (California Water Boards, portal eSMR). Este
Space não republica os arquivos brutos — apenas resultados agregados já computados pelo pipeline.
        """
    )
