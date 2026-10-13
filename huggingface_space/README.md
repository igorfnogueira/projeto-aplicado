---
title: TDS LAGWRP Resultados
emoji: 💧
colorFrom: blue
colorTo: gray
sdk: streamlit
sdk_version: "1.57.0"
app_file: streamlit_app.py
pinned: false
license: mit
---

# Tendência de TDS em efluente de ETE — LAGWRP

Dashboard com os resultados de um projeto de pós-graduação (IA Aplicada) analisando a tendência de
longo prazo de sólidos totais dissolvidos (TDS) no efluente da Los Angeles–Glendale Water
Reclamation Plant, a partir de dados públicos eSMR da California Water Boards.

Mostra uma bateria de ~35 métodos de previsão já comparados (estatísticos clássicos, árvores, deep
learning, Bayesiano, híbridos), os 3 finalistas recomendados, a investigação causal do mecanismo
(PDSI, WRTDS, balanço de massa, água de origem), duas rodadas testando o PDSI como covariável
exógena, e a bateria completa de testes de robustez/overfitting — pensado para outros pesquisadores
do mesmo tema comparar contra os próprios resultados sem precisar reproduzir o pipeline completo
(que depende de PyMC, Prophet, XGBoost, LightGBM, entre outros pacotes pesados). Este Space só
consome os resultados já computados (CSVs/figuras em `data/`/`images/`), não roda o pipeline de
treinamento.

As abas seguem a ordem dos achados do projeto (narrativa final → tendência e sua fragilidade →
investigação causal → bateria de previsão → objetivos secundários → métodos avançados → validação e
correções → sobre o projeto), pensado como apoio visual de apresentação, não só exploração livre.

A maioria dos CSVs de `data/` é cópia de `results/` (ou de `data/processed/`, no caso de
`ladwp_tds_origem_vs_efluente.csv`) e precisa ser recopiada quando a fonte mudar, senão o Space
mostra número velho: `resultados_comparacao.csv`, `comparacao_pdsi_antes_depois.csv`,
`comparacao_pdsi_finetuning_multilag.csv`, `testes_robustez_resultados.csv`,
`cv_aninhada_resultados.csv`, `diagnostico_residuos_resultados.csv`, `pdsi_regimes_resultados.csv`,
`wrtds_resultados.csv`, `balanco_massa_resultados.csv`, `matriz_sensibilidade_resultados.csv`,
`cenarios_resultados.csv` e `ladwp_tds_origem_vs_efluente.csv`. `serie_tds_mensal.csv` existe só
neste pacote.

Código-fonte completo, dados e resultados do pipeline:
**https://github.com/igorfnogueira/projeto-aplicado**
