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

Mostra uma bateria de ~30 métodos de previsão já comparados (estatísticos clássicos, árvores, deep
learning, Bayesiano, híbridos), os 3 finalistas recomendados, e duas rodadas testando o PDSI (índice
de seca) como covariável exógena — pensado para outros pesquisadores do mesmo tema comparar contra
os próprios resultados sem precisar reproduzir o pipeline completo (que depende de PyMC, Prophet,
XGBoost, LightGBM, entre outros pacotes pesados). Este Space só consome os resultados já computados
(CSVs/figuras em `data/`/`images/`), não roda o pipeline de treinamento.

Código-fonte completo, dados e resultados do pipeline:
**https://github.com/igorfnogueira/projeto-aplicado**
