> **Atenção — estado desatualizado:** este dashboard reflete o estado do projeto em D-66 (15 métodos centrais, 3 finalistas) e **NÃO** foi atualizado para D-73 (2026-10-15, bateria reduzida a 7 métodos, conceito de finalista abandonado — ver `docs/adr/0003` no repositório principal). **Não usar como referência do estado atual do artigo.**

# Tendência de TDS em efluente de ETE — LAGWRP

**Hospedagem pública descontinuada em 2026-10-13** (o dashboard deixou de ser deliverable público —
ver `docs_local/01_manuscrito/Artigo/DECISOES.md`; o deploy antigo em tds-lagwrp.streamlit.app parou
de atualizar quando `streamlit_app.py` saiu do rastreamento do `main`, já que o Streamlit Community
Cloud lê o entrypoint direto do branch). Para usar, rode localmente: `streamlit run streamlit_app.py`
(a partir desta pasta).

Dashboard com os resultados de um projeto de pós-graduação (IA Aplicada) analisando a tendência de
longo prazo de sólidos totais dissolvidos (TDS) no efluente da Los Angeles–Glendale Water
Reclamation Plant, a partir de dados públicos eSMR da California Water Boards.

Mostra a bateria de 15 métodos de previsão centrais do artigo público (estatísticos clássicos,
árvore, Bayesiano, híbrido) e, como registro histórico rotulado à parte (abas "Bateria de previsão
(completa)" e "Bateria estendida (triagem, fora do artigo)" — ver D-66), a bateria de triagem mais
ampla testada durante o desenvolvimento (árvores adicionais, deep learning, SVR/GP, espaço de
estados, GAM, regressão quantílica, intervenção, modelo fundacional), os 3 finalistas recomendados,
a investigação causal do mecanismo (PDSI, WRTDS, balanço de massa, água de origem), duas rodadas
testando o PDSI como covariável exógena, e a bateria completa de testes de robustez/overfitting —
pensado para outros pesquisadores do mesmo tema comparar contra os próprios resultados sem precisar
reproduzir o pipeline completo (que depende de PyMC, Prophet, XGBoost, LightGBM, entre outros
pacotes pesados). Este Space só consome os resultados já computados (CSVs/figuras em
`data/`/`images/`), não roda o pipeline de treinamento.

As abas seguem a ordem dos achados do projeto (narrativa final → tendência e sua fragilidade →
investigação causal → bateria de previsão (completa) → objetivos secundários → bateria estendida
(triagem, fora do artigo) → validação e correções → sobre o projeto), pensado como apoio visual de
apresentação, não só exploração livre.

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
