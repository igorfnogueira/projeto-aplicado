# Prompt para Claude Code — Planejamento do projeto TDS/Salinidade

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

---

Antes de qualquer coisa, leia e explore os seguintes arquivos do projeto:

- `projeto_aplicado_v1__1_.ipynb` — notebook base já iniciado (EDA, merge dos 4 datasets, modelo Random Forest com GridSearchCV)
- `Los_Angeles_Reclamation_Plant_2026_additional_data.xlsx` — dados brutos (abas TDS, Chloride, Ammonia, BOD)
- `Salinidade.pdf` — resumo do projeto de pesquisa (título, objetivos, referências bibliográficas)
- `AI_Project_Instructions.docx` — instruções originais do professor/pós-graduação
- `TreatmentPlant_Brochure-LAGLEN-FINAL.pdf` — contexto institucional da estação de tratamento LAGWRP

Em seguida, busque e leia o conteúdo dos seguintes artigos científicos (use suas ferramentas de busca/leitura web):

1. https://www.nature.com/articles/s41893-020-0529-2 (citado nas instruções como referência obrigatória para a discussão)
2. https://www.tandfonline.com/doi/full/10.1080/23789689.2023.2180251#abstract
3. https://www.ambi-agua.net/seer/index.php/ambi-agua/article/view/1611
4. https://pmc.ncbi.nlm.nih.gov/articles/PMC5006585/
5. https://pubmed.ncbi.nlm.nih.gov/42093163/
6. https://www.sciencedirect.com/science/article/abs/pii/S0141022903003661
7. https://cawaterlibrary.net/document/study-to-evaluate-long-term-trends-and-variations-in-the-average-total-dissolved-solids-concentration-in-wastewater-and-recycled-water/

## O que preciso que você faça

Depois de ler tudo, **NÃO escreva código ainda**. Primeiro, monte um plano detalhado cobrindo:

1. **Objetivos do trabalho** (extraídos das instruções): análise de tendência do TDS ao longo de ~15 anos, modelo preditivo para 10 e 20 anos, correlação TDS-amônia e TDS-BOD, interpretação no contexto de conservação hídrica em Los Angeles.

2. **Bateria de metodologias a testar**, cobrindo diferentes categorias:
   - Estatística clássica de tendência (ex: Mann-Kendall, Theil-Sen, regressão linear simples)
   - Séries temporais clássicas (ex: ARIMA/SARIMA, decomposição sazonal)
   - Modelos baseados em árvore (o Random Forest que já existe no notebook, e comparar com XGBoost/LightGBM)
   - Ao menos uma abordagem adicional que você julgar relevante para prever 10-20 anos à frente com poucos dados históricos (ex: Prophet, regressão bayesiana, ou justifique se achar desnecessário)
   - Para cada metodologia: como ela lida com extrapolação de longo prazo, e quais suas limitações conhecidas nesse tipo de série

3. **Estrutura de execução em paralelo**: proponha como dividir isso em subagents/scripts independentes — um por metodologia — cada um gerando métricas comparáveis (RMSE, R², intervalo de confiança da previsão, significância estatística da tendência) salvas num arquivo comum (`resultados_comparacao.json` ou `.csv`).

4. **Critérios de comparação**: como vamos decidir objetivamente qual(is) modelo(s) levar adiante depois que a bateria rodar.

5. **Como a interpretação com o artigo da Nature e os demais artigos vai entrar na discussão final** (não na modelagem, mas na fundamentação teórica dos resultados).

Ao final, apresente o plano de forma clara e peça minha aprovação antes de gerar qualquer script ou subagent. Se algo nas instruções ou nos artigos for ambíguo, pergunte antes de assumir.
