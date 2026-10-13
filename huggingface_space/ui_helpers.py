"""Componentes de UI reutilizados nas abas do dashboard -- hoje só o ícone
de ajuda com explicação de leitura de gráfico, usado em todo gráfico/imagem
do app (ver streamlit_app.py).
"""

import streamlit as st

_CSS = """
<style>
.info-pop {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: help;
    font-size: 1rem;
    line-height: 1;
}
.info-pop .info-box {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    z-index: 999;
    right: 0;
    top: 140%;
    width: 320px;
    background: #262730;
    color: #fafafa;
    border: 1px solid #4a4a4a;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 0.82rem;
    font-weight: 400;
    line-height: 1.45;
    text-align: left;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.35);
    transition: opacity 0.12s ease;
    pointer-events: none;
}
.info-pop:hover .info-box {
    visibility: visible;
    opacity: 1;
}
.grafico-cabecalho {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
}
.grafico-cabecalho .titulo {
    font-weight: 600;
    font-size: 1rem;
}
</style>
"""


def injetar_estilo_tooltip() -> None:
    """Chamar uma vez por página, antes de qualquer cabecalho_com_ajuda."""
    st.markdown(_CSS, unsafe_allow_html=True)


def cabecalho_com_ajuda(titulo: str, explicacao: str) -> None:
    """Título de bloco (estilo subheader) com um ícone 'ℹ️' à direita que,
    ao passar o mouse, mostra como ler o gráfico/imagem abaixo.
    """
    st.markdown(
        f"""
        <div class="grafico-cabecalho">
            <span class="titulo">{titulo}</span>
            <span class="info-pop">ℹ️<span class="info-box">{explicacao}</span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
