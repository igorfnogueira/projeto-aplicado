"""Dashboard publico dos resultados do projeto TDS/LAGWRP -- pensado para
outros pesquisadores do mesmo tema explorarem e comparar com seus proprios
projetos, sem precisar rodar o pipeline completo (que depende de PyMC,
Prophet, XGBoost, LightGBM etc.). Consome apenas os CSVs/figuras ja
gerados pelo pipeline (pasta data/ e images/), bundlados junto com o Space.

Repositorio completo (codigo, artigo, log de decisoes): ver link na aba
"Sobre o projeto".
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = Path(__file__).parent / "images"

REPO_URL = "https://github.com/igorfnogueira/projeto-aplicado"

FINALISTAS = {
    "regressao_bayesiana": "Regressão bayesiana",
    "detrend_rf": "Detrend + Random Forest",
    "hibrido_arima_prophet": "Híbrido SARIMA + Prophet",
}

# Métodos cujo rmse_holdout NÃO é um RMSE de previsão de TDS out-of-sample
# comparável aos demais -- são análises mecanísticas/de cenário com objetivo
# diferente (WRTDS e os cenários já reportam NaN corretamente nessa coluna;
# balanco_massa é o único caso que reporta um número, mas é o RMSE da
# validação de circularidade do Cloreto, script_20_balanco_massa.py:273 --
# não o holdout de TDS). Excluídos do ranking por padrão para não enganar
# quem for comparar contra o próprio trabalho.
METODOS_NAO_COMPARAVEIS = {
    "wrtds_flow_normalized", "balanco_massa",
    "cenario_pdsi_agravamento_climatico", "cenario_pdsi_normal",
    "cenario_pdsi_seco", "cenario_pdsi_umido", "cenario_pdsi_rcp85_caladapt",
}

st.set_page_config(
    page_title="TDS LAGWRP — resultados",
    page_icon=":material/water_drop:",
    layout="wide",
)


@st.cache_data
def carregar_serie() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "serie_tds_mensal.csv", parse_dates=["Data"])
    return df


@st.cache_data
def carregar_resultados() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "resultados_comparacao.csv")


@st.cache_data
def carregar_comparacao_pdsi() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "comparacao_pdsi_antes_depois.csv")


@st.cache_data
def carregar_comparacao_finetuning() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "comparacao_pdsi_finetuning_multilag.csv")


def montar_pontos_forecast(resultados: pd.DataFrame, metodos: list[str], ultima_data: pd.Timestamp) -> pd.DataFrame:
    linhas = []
    for metodo in metodos:
        row = resultados.loc[resultados["metodo"] == metodo]
        if row.empty:
            continue
        row = row.iloc[0]
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

aba_serie, aba_metodos, aba_pdsi, aba_sobre = st.tabs([
    "Série e finalistas",
    "Comparação de métodos",
    "PDSI como covariável",
    "Sobre o projeto",
])

with aba_serie:
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
        pontos = montar_pontos_forecast(resultados, metodos_selecionados, serie["Data"].max())

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
        st.altair_chart((base_hist + banda_ic + linha_forecast).interactive())
        if (pontos["ci_baixo"] < y_min).any() or (pontos["ci_alto"] > y_max).any():
            st.caption(
                "O IC90% de pelo menos um método selecionado se estende além do eixo mostrado "
                "(ex. o híbrido SARIMA+Prophet chega a valores implausíveis/negativos em +20a) — "
                "passe o mouse sobre os pontos para ver a largura real do intervalo."
            )
    else:
        st.line_chart(serie, x="Data", y="TDS_mgL")

    with st.container(border=True):
        st.markdown("**Figura de síntese do artigo** (script_15 — 3 finalistas sobre a série completa)")
        st.image(str(IMAGES_DIR / "sintese-final-finalistas.png"))

with aba_metodos:
    st.subheader("Todos os métodos comparados")
    st.markdown(
        "Cada linha é uma execução independente sobre os mesmos dados: RMSE/MAE/R² em *holdout* de 24 meses, "
        "métricas de validação honesta (CV expansiva + *backtest*) e previsão pontual com IC90% em +10/+15/+20 anos."
    )

    mostrar_nao_comparaveis = st.checkbox(
        "Incluir também análises mecanísticas/de cenário (WRTDS, balanço de massa, cenários climáticos)",
        value=False,
        help=(
            "Essas análises respondem uma pergunta diferente da bateria de previsão (mecanismo, "
            "faixa condicionada ao clima) e não têm um RMSE de holdout de TDS comparável — o balanço "
            "de massa em particular reporta nessa coluna o RMSE de uma validação de circularidade do "
            "Cloreto, não uma previsão de TDS. Incluídas aqui só para referência, não para o ranking."
        ),
    )
    resultados_tabela = resultados if mostrar_nao_comparaveis else resultados[~resultados["metodo"].isin(METODOS_NAO_COMPARAVEIS)]

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

    st.subheader("RMSE de holdout por método")
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

with aba_pdsi:
    st.subheader("O PDSI (índice de seca) melhora a previsão como covariável?")
    st.markdown(
        "O PDSI já explica bem o *regime* cíclico do TDS (correlação cruzada, D-37), mas isso não "
        "significa automaticamente que adicioná-lo como *covariável exógena* melhora o desempenho "
        "preditivo dos métodos. Duas rodadas testaram isso diretamente, com critério de aceitação "
        "rígido: só conta como melhoria real se o RMSE da validação honesta (CV expansiva) também "
        "melhorar, não apenas o *holdout* isolado."
    )

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**D-56 — bateria original com PDSI como covariável**")
            st.caption("Sem melhora consistente: 4 de 12 métodos melhoraram, 8 pioraram")
            st.image(str(IMAGES_DIR / "bateria-pdsi-covariavel-comparacao.png"))
    with col2:
        with st.container(border=True):
            st.markdown("**D-57 — fine-tuning da representação do PDSI**")
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

with aba_sobre:
    st.subheader("Sobre o projeto")
    st.markdown(
        f"""
Projeto de pós-graduação (IA Aplicada) analisando a tendência de longo prazo de sólidos totais
dissolvidos (TDS) no efluente da **Los Angeles–Glendale Water Reclamation Plant (LAGWRP)**, a partir
de dados públicos eSMR (Electronic Self-Monitoring Report) do portal da California Water Boards.

**O que este Space mostra:** resultados já computados de uma bateria de ~30 métodos de previsão
(estatísticos clássicos, árvores, deep learning, Bayesiano, híbridos), diagnósticos estruturais, e
duas rodadas testando o PDSI (índice de seca) como covariável — pensado para outros pesquisadores do
mesmo tema comparar contra seus próprios resultados, sem precisar reproduzir o pipeline completo
(que depende de PyMC, Prophet, XGBoost, LightGBM, entre outros pacotes pesados).

**Reprodutibilidade:** código-fonte completo, artigo científico (LaTeX) e o log de decisões
metodológicas (formato ADR, com alternativas descartadas e motivo) estão no repositório público:

[{REPO_URL}]({REPO_URL})

**Achado central:** o mecanismo por trás da tendência de TDS é diluição (queda de vazão de efluente
mais rápida que a queda da carga de sal), fortemente ligado a ciclos de seca — não uma tendência
monotônica simples. Não há um único "melhor modelo": três finalistas com mecanismos de extrapolação
diferentes convergem para uma faixa semelhante em +20 anos, e essa convergência é tratada como a
evidência mais forte, não o ponto de previsão de nenhum modelo isolado.

**Licença dos dados:** os dados brutos são públicos (California Water Boards, portal eSMR). Este
Space não republica os arquivos brutos — apenas resultados agregados já publicados no artigo.
        """
    )
