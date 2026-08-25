# Material de Apoio — Artigos e Referências sobre Salinidade/TDS em Estações de Tratamento e Métodos de Previsão

> Levantamento feito via busca web em 13/08/2026, organizado por tema. Para cada fonte: o que ela estuda, quais métodos usa e por que interessa a este projeto (LAGWRP, tendência e previsão de TDS a +10/+15/+20 anos, correlações TDS-amônia e TDS-BOD).
>
> **Aviso de honestidade:** o resumo de métodos abaixo vem dos abstracts/resumos acessíveis na busca — antes de citar qualquer um destes no artigo científico, o texto completo deve ser lido e a entrada correspondente criada em `Artigo/refs.bib` com os dados bibliográficos reais (regra da seção 2 do plano). Alguns são paywalled (ScienceDirect/Tandfonline) — o abstract é público, o PDF não.

---

## Tema 1 — O problema em si: conservação de água → salinidade crescente em ETEs (o "gêmeo" do nosso projeto)

Estes são os artigos que estudam exatamente o mesmo fenômeno do projeto, em plantas da mesma região:

### 1.1 Nature Sustainability (2020) — *Unintended consequences of water conservation on the use of treated municipal wastewater* ⭐ referência obrigatória do professor
- **Link:** https://www.nature.com/articles/s41893-020-0529-2
- **O que estuda:** 34 ETEs do sul da Califórnia, 2013–2017 — efeito da conservação de água na vazão e salinidade do efluente.
- **Métodos:** análise estatística de painel de séries mensais de vazão e salinidade; testes de significância (p ≤ 0,05) da mudança pós-conservação.
- **Por que importa:** é o benchmark direto — nossa tendência de TDS no LAGWRP deve ser comparada em direção e magnitude ao que eles acharam. A LAGWRP pode inclusive ser uma das 34 plantas do estudo.

### 1.2 Tran, Schwabe et al. (2017) — *The implications of drought and water conservation on the reuse of municipal wastewater* (Water Research)
- **Links:** https://www.sciencedirect.com/science/article/abs/pii/S0043135417306425 | https://pubmed.ncbi.nlm.nih.gov/28800518/
- **O que estuda:** como seca + conservação reduzem vazão afluente e aumentam concentração de poluentes (especialmente sais), afetando custos e qualidade do efluente.
- **Métodos:** análise de tendência de vazão/concentração e avaliação econômica de estratégias de mitigação.
- **Por que importa:** dá o argumento econômico/operacional para a seção de implicações do nosso artigo.

### 1.3 ACS ES&T Water (2022) — *Dilution and Pollution: Assessing the Impacts of Water Reuse and Flow Reduction on Water Quality in the Los Angeles River Basin* ⭐ mesma bacia do LAGWRP
- **Link:** https://pubs.acs.org/doi/10.1021/acsestwater.2c00005
- **O que estuda:** exatamente a bacia do rio Los Angeles (onde o LAGWRP descarrega) — impacto da redução de vazão e do reúso na qualidade da água. Resultado citado: queda de ~25% no uso interno de água elevou o TDS do efluente em ~50 mg/L em média no sul da Califórnia.
- **⚠️ Verificação (13/08/2026):** o número "+50 mg/L" **não foi confirmado** ao tentar acessar o texto completo (ACS retorna 403; resumos de terceiros — ASCE, ResearchGate — confirmam o desenho do estudo (SWMM, 9 cenários de reúso 0/50/100%, LA River basin) e a direção do efeito (TDS sobe com reúso), mas não citam esse valor específico). **Não usar esse número no artigo** até achar acesso genuíno ao texto completo que o confirme.
- **Métodos:** modelagem de cenários de redução de vazão (5%, 10%, 20%) e balanço de massa de constituintes.
- **Por que importa:** fornece um número regional concreto (+50 mg/L) para confrontar com a nossa taxa de tendência estimada; mesma água receptora dos pontos R-4/R-7/RSW do nosso dataset.

### 1.4 Tandfonline (2023) — *Adapting wastewater management systems in California for water conservation and climate change*
- **Link:** https://www.tandfonline.com/doi/full/10.1080/23789689.2023.2180251
- **O que estuda:** adaptação de sistemas de esgoto da Califórnia à conservação e mudanças climáticas (já estava na lista original do projeto).
- **Por que importa:** seção de recomendações/implicações do artigo.

### 1.5 Complementares de contexto (não acadêmicos, mas úteis)
- CWEA — *Dealing With Declining Wastewater Flows*: https://www.cwea.org/news/dealing-with-declining-flows/ (visão operacional das plantas californianas)
- PPIC — *The Unintended Consequences of Indoor Water Conservation*: https://www.ppic.org/blog/unintended-consequences-indoor-water-conservation/ (política pública)
- ASCE — *Reuse can affect water quality in unintended ways*: https://www.asce.org/publications-and-news/civil-engineering-source/civil-engineering-magazine/article/2022/12/reuse-can-affect-water-quality-in-unintended-ways-study-finds

---

## Tema 2 — Previsão de TDS com machine learning (métodos para testar e comparar)

### 2.1 Springer (2025) — *TDS Prediction with Wavelet Analysis and Trend-Seasonal Decomposition and Machine Learning Algorithms* — Rio Karkheh, Irã
- **Link:** https://link.springer.com/article/10.1007/s41101-025-00390-z
- **Métodos:** transformada wavelet contínua (CWT) para decompor as séries (Ca, HCO3, SO4, Cl) em tendência/sazonalidade/resíduo, usando essas componentes como features para modelos de ML.
- **Ideia testável no nosso projeto:** decompor a série de TDS (STL) e alimentar as componentes como features para os modelos de árvore — variante direta do nosso item "árvores sobre série destendenciada".

### 2.2 MDPI Sustainability (2023) — *Optimization of Fuzzy-Based Machine Learning Techniques for TDS Prediction* (NF-GMDH-GOA)
- **Link:** https://doi.org/10.3390/su15087016
- **Métodos:** sistema neuro-fuzzy (NF-GMDH) otimizado por grasshopper optimization, para TDS mensal.
- **Ideia testável:** a parte transferível é usar otimização de hiperparâmetros populacional (no nosso caso, Optuna já cobre isso sem exotismo).

### 2.3 Engineering Applications of AI (2023) — *Prediction of TDS based on optimization of new hybrid SVM models*
- **Link:** https://www.sciencedirect.com/science/article/abs/pii/S0952197623009648
- **Métodos:** SVM híbrido com otimizadores metaheurísticos para TDS.
- **Ideia testável:** SVR (Support Vector Regression) é um candidato legítimo que ainda não está na nossa bateria — barato de adicionar como método extra de comparação.

### 2.4 Tandfonline (2021) — *An integrated machine learning, noise suppression, and population-based algorithm to improve TDS prediction*
- **Link:** https://www.tandfonline.com/doi/full/10.1080/19942060.2020.1861987
- **Métodos:** ML + supressão de ruído (denoising) + algoritmo populacional; série longa de TDS (1975–2016) com cloreto, temperatura e dureza como preditores.
- **Ideia testável:** usa **cloreto como preditor do TDS** — exatamente o que propusemos no VAR/regressão dinâmica (nosso dataset tem série densa de cloreto).

### 2.5 IWA Water Quality Research Journal (2025) — *ML-driven surface water quality prediction: forecasting TDS and DO levels*
- **Link:** https://iwaponline.com/wqrj/article/60/4/514/109508/
- **Métodos:** comparação de algoritmos de ML com GUI para previsão de TDS/OD.
- **Por que importa:** exemplo recente de benchmark multi-modelo para TDS — estrutura de comparação parecida com o nosso `resultados_comparacao.csv`.

### 2.6 MDPI Water (2024) — *Enhanced TDS Modeling Using Grey Wolf Optimization with Kernel Extreme Learning Machine*
- **Link:** https://doi.org/10.3390/w16192818
- **Métodos:** KELM + otimização grey wolf.
- **Por que importa:** mais um ponto de comparação da família "ML otimizado por metaheurística" — citar como estado da arte, sem necessariamente replicar.

---

## Tema 3 — Previsão de qualidade de efluente em ETEs com ML (BOD, amônia, nutrientes)

### 3.1 ScienceDirect (2024) — *Enhancing wastewater treatment efficiency through ML-driven effluent quality prediction: A plant-level analysis*
- **Link:** https://www.sciencedirect.com/science/article/abs/pii/S2214714423012783
- **Métodos:** ANN, GBM, RF, XGBoost e híbrido RF-GBM em nível de planta; resultado citado: RF melhor para COD/SS (R²≈0,91–0,95), Gradient Boosting melhor para BOD (R²≈0,92).
- **Por que importa:** valida a escolha de árvores/boosting para variáveis de ETE e dá números de referência de R² para BOD.

### 3.2 ScienceDirect (2023) — *Enhancing effluent quality prediction... integration of factor analysis and machine learning*
- **Link:** https://www.sciencedirect.com/science/article/abs/pii/S0960852423014360
- **Métodos:** análise fatorial para seleção de variáveis + ML.
- **Ideia testável:** redução de dimensionalidade antes do ML — no nosso caso simples (4 parâmetros), equivale a testar quais parâmetros auxiliares (Cl, amônia) realmente ajudam a prever TDS.

### 3.3 PMC (2025) — *AI-driven wastewater management through comparative analysis of feature selection techniques and predictive models*
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12259835/
- **Métodos:** RNN, LSTM, RF e SVM para prever amônia em tanques de aeração; comparação de técnicas de seleção de features.
- **Por que importa:** foco em amônia — útil para a nossa análise TDS-amônia.

### 3.4 PMC (2024) — *A probabilistic deep learning approach to enhance the prediction of wastewater treatment plant effluent quality under shocking load events*
- **Link:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11667701/
- **Métodos:** deep learning probabilístico (previsão com incerteza) para efluente sob eventos de choque.
- **Por que importa:** reforça o princípio central do nosso plano — previsão com incerteza quantificada, não ponto único.

### 3.5 ResearchGate (2021) — *Forecasting effluent and performance of wastewater treatment plant using different machine learning techniques*
- **Link:** https://www.researchgate.net/publication/355439776
- **Métodos:** KNN, SVM, RF, MLP e LSTM comparados para desempenho de ETE.
- **Por que importa:** mais um template de "bateria comparativa" igual à nossa.

---

## Tema 4 — Mecanismo biológico: salinidade inibe nitrificação/remoção de matéria orgânica (fundamenta TDS-amônia e TDS-BOD)

### 4.1 Water Research (2002) — *Nitrification in saline wastewater with high ammonia concentration in an activated sludge unit*
- **Link:** https://www.sciencedirect.com/science/article/abs/pii/S0043135401004675
- **Resultado-chave:** atividade dos oxidadores de amônia caiu 36% a 10 g Cl⁻/L; inibição de ~95% a 40 g Cl⁻/L; sistema colapsa acima de ~525 mM de sal.
- **Por que importa:** números concretos de limiar de inibição — contexto quantitativo para interpretar nossa correlação TDS-amônia (nota: nosso efluente está na casa de centenas de mg/L, bem abaixo desses limiares — a discussão deve ser honesta sobre isso).

### 4.2 Scientific Reports (2016) — *The effects of salinity on nitrification using halophilic nitrifiers in a SBR treating hypersaline wastewater*
- **Link:** https://www.nature.com/articles/srep24825
- **Métodos:** reator SBR, nitrificantes halofílicos, avaliação por faixa de salinidade.
- **Por que importa:** mecanismo + solução (organismos halofílicos) para a seção de implicações.

### 4.3 IWA Water Science & Technology (2002) — *The impact of sea water flushing on biological nitrification-denitrification activated sludge sewage treatment process*
- **Link (PDF):** https://iwaponline.com/wst/article-pdf/46/11-12/209/426159/209.pdf
- **Por que importa:** caso real de planta municipal com salinidade elevada afetando NdeN — mesma configuração de processo do LAGWRP (NdeN desde 2007, conforme brochure).

### 4.4 Já na lista original do projeto (manter):
- Ambiente & Água (2015) — toxicidade da salinidade na nitrificação via respirometria: https://www.ambi-agua.net/seer/index.php/ambi-agua/article/view/1611
- Uygur & Kargı (2004) — inibição por sal na remoção biológica de nutrientes em SBR: https://www.sciencedirect.com/science/article/abs/pii/S0141022903003661
- PMC5006585 (2016) — tratamento de esgoto salino em sistema híbrido: https://pmc.ncbi.nlm.nih.gov/articles/PMC5006585/

---

## Tema 5 — Métodos estatísticos de tendência (Mann-Kendall/Sen) aplicados a qualidade de água

### 5.1 Journal of Pollution (2021) — *Analysis of Water Quality Trends Using the Mann-Kendall Test and Sen's Estimator of Slope in a Tropical River Basin*
- **Link:** https://jpoll.ut.ac.ir/article_84045.html
- **Métodos:** MK + Sen em séries 2001–2010 de parâmetros físico-químicos (incluindo salinidade).
- **Por que importa:** template metodológico direto do nosso `script_01` — mesma aplicação, contexto diferente.

### 5.2 Academia/ResearchGate — *Detecting Surface Water Quality Trends Using Mann-Kendall Tests and Sen's Slope Estimates*
- **Links:** https://www.academia.edu/2783560/ | https://www.researchgate.net/publication/235752471
- **Por que importa:** referência clássica de aplicação de MK/Sen a monitoramento de qualidade de água.

### 5.3 Pacote R `wql` (documentação de mannKen)
- **Link:** https://rdrr.io/cran/wql/man/mannKen.html
- **Por que importa:** implementação de referência (com tratamento de sazonalidade — Seasonal Kendall) para validar nossa implementação Python (`pymannkendall`).

---

## Tema 6 — Comparação de famílias de modelos de séries temporais (SARIMA vs Prophet vs XGBoost vs deep learning)

### 6.1 PMC (2025) — *Forecasting multidrug-resistant organisms trends: comparative study of SARIMA, ETS, Prophet, and NNETAR*
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12894405/
- **Por que importa:** exemplo de desenho experimental "bateria de 4 famílias em série mensal de ~10 anos" — estrutura quase idêntica à nossa, em outro domínio. Bom modelo de como reportar a comparação.

### 6.2 ScienceDirect (2025) — *A hybrid approach to time series forecasting: Integrating ARIMA and Prophet for improved accuracy*
- **Link:** https://www.sciencedirect.com/science/article/pii/S2590123025017748
- **Métodos:** híbrido ARIMA+Prophet.
- **Ideia testável:** híbrido/ensemble entre os nossos métodos — já contemplado no item de ensemble do prompt de aprofundamento.

### 6.3 PMC (2025) — *Forecasting monthly runoff in a glacierized catchment: XGBoost vs deep learning*
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12101857/
- **Resultado-chave:** XGBoost venceu LSTM e RF em série hidrológica mensal (R²≈0,90) — evidência de que em séries ambientais mensais curtas, boosting costuma bater deep learning.
- **Por que importa:** fundamenta a expectativa (que devemos verificar, não assumir) de que LSTM/N-BEATS provavelmente não vencerão os clássicos nos nossos ~180 pontos.

### 6.4 ResearchGate (2024) — *Comparative Analysis of ARIMA, SARIMA and Prophet Model in Forecasting*
- **Link:** https://www.researchgate.net/publication/385157901
- **Por que importa:** referência genérica de comparação entre os três — útil para a metodologia do artigo.

### 6.5 RESCON (2025) — *Comparative forecasting of Water Quality Index using LSTM and XGBoost* (rio Tâmisa)
- **Link:** https://www.researchgate.net/publication/397522798
- **Métodos:** LSTM vs XGBoost, com SARIMA e Prophet como baselines, em índice de qualidade de água.
- **Por que importa:** desenho experimental idêntico ao nosso aplicado a qualidade de água.

---

## Tema 7 — Métodos com incerteza para séries curtas (Gaussian Process, bayesiano)

### 7.1 MDPI Water (2024) — *Scalable and Interpretable Forecasting of Hydrological Time Series Based on Variational Gaussian Processes*
- **Link:** https://doi.org/10.3390/w16142006
- **Métodos:** GP variacional para séries hidrológicas com incerteza.
- **Por que importa:** suporte direto ao GP com kernel composto proposto no aprofundamento da bateria.

### 7.2 AIMS Environmental Science (2021) — *Gaussian process regression for predicting water quality index: Ping River basin, Thailand*
- **Link:** https://www.aimspress.com/article/doi/10.3934/environsci.2021018?viewType=HTML
- **Por que importa:** GPR aplicado exatamente a índice de qualidade de água.

### 7.3 Water Research (2024) — *Improving prediction of groundwater quality in situations of limited monitoring data based on virtual sample generation and GPR*
- **Link:** https://www.sciencedirect.com/science/article/abs/pii/S0043135424013976
- **Por que importa:** ataca o "small sample problem" — nosso caso (~180 pontos). A técnica de geração de amostras virtuais é uma opção se os modelos sofrerem com poucos dados.

### 7.4 ResearchGate (2014) — *Monthly streamflow forecasting using Gaussian Process Regression*
- **Link:** https://www.researchgate.net/publication/260110920
- **Por que importa:** GPR em série ambiental mensal — precedente metodológico direto.

---

## Tema 8 — Tratamento de dados censurados (ND/abaixo do limite de detecção) — crítico para o nosso BOD (65% ND)

### 8.1 Antweiler & Taylor (2008) — *Evaluation of Statistical Treatments of Left-Censored Environmental Data* (Environ. Sci. Technol.)
- **Links:** https://pubs.acs.org/doi/10.1021/es071301c | PDF: https://hh-ra.org/wp-content/uploads/2022/12/antweiler2008.pdf
- **Resultado-chave:** métodos de substituição simples (MDL/2, zero) produzem estatísticas enviesadas; para dados com <70% de censura, **Kaplan-Meier** foi a melhor técnica para estatísticas-resumo.
- **Por que importa:** nosso BOD tem ~65% ND — bem na faixa onde o artigo diz que KM ainda funciona. Isso adiciona uma **opção F (Kaplan-Meier / métodos de Helsel)** à tabela de decisão da seção 1.3 do plano, potencialmente superior às opções A-E listadas.

### 8.2 Helsel — *Statistics for Censored Environmental Data* (livro de referência, práticas "NADA")
- **Link (publicações):** https://www.practicalstats.com/nada/pubs.html
- **Por que importa:** é O autor de referência para não-detectados em dados ambientais; existe implementação Python (`NADA`-like) e R (`NADA`/`NADA2`). Se citarmos qualquer decisão de ND no artigo, Helsel é a citação canônica.

### 8.3 ITRC — *5.7 Nondetects* (guia técnico)
- **Link:** https://projects.itrcweb.org/gsmc-1/Content/GW%20Stats/5%20Methods%20in%20indiv%20Topics/5%207%20Nondetects.htm
- **Por que importa:** guia regulatório prático de qual método usar por faixa de % de censura — bom para justificar a escolha no artigo.

### 8.4 EPA/CLU-IN — *Methods for Handling Non-detect or Censored Data* (handout)
- **Link:** https://clu-in.org/conf/tio/ltmo/Nondetects_handout.pdf
- **Por que importa:** resumo operacional das técnicas, fonte governamental citável.

---

## Tema 9 — Estudo SCSC/DBS&A (2018) — LIDO NA ÍNTEGRA ⭐⭐ o mais importante do acervo

**Referência completa:** Daniel B. Stephens & Associates, Inc. (2018). *Study to Evaluate Long-Term Trends and Variations in the Average Total Dissolved Solids Concentration in Wastewater and Recycled Water*. Southern California Salinity Coalition (administrada pelo National Water Research Institute), 30 de março de 2018. Costa Mesa, California.

**Status de leitura:** texto completo lido (via conversão para `.txt`). Diferente das demais entradas deste arquivo, os números abaixo vêm do **texto integral verificado**, não de abstract.

**Arquivo local:** `SCSC-TDS-Trends-Study.docx` / `.txt` na raiz do projeto.

### 9.1 O achado que reenquadra o mecanismo causal do nosso projeto

O estudo modelou TDS de influente como função de duas variáveis explicativas — TDS da água de origem e consumo interno per capita — e decompôs a importância relativa de cada uma (pacote R `relaimpo`, método lmg):

| Bacia | R² | Importância: TDS de origem | Importância: consumo per capita |
|---|---|---|---|
| EMWD Combinado | 0,979 | **88,2%** | 11,8% |
| EMWD Perris Valley | 0,923 | **99,0%** | 1,0% |
| EMWD Moreno Valley | 0,965 | **99,0%** | 1,0% |
| EMWD San Jacinto | 0,644 | **97,1%** | 2,9% |
| EMWD Temecula Valley | 0,903 | **80,8%** | 19,2% |
| IEUA (geral) | 0,747 | 67,2% | 32,8% |
| IEUA CCWRF | 0,742 | 32,8% | **67,2%** |
| OCSD | 0,534 | 60,8% | 39,2% |
| SDCWA Padre Dam | 0,832 | 97,8% | 2,2% |

**Conclusão do estudo:** "Volume-weighted source water TDS concentration is the significant determiner of influent TDS. Source TDS explains more of the variability in influent/effluent TDS than any other factor, **including decreased indoor water use**."

**Magnitude da conservação:** apenas **1,2 a 1,7 mg/L de aumento no TDS para cada 1,0 gpcd de redução** no consumo interno.

**Magnitude do driver dominante:** o TDS da água importada tem correlação inversa forte com ciclos de seca (PMDI). Variação entre anos secos e úmidos: **~300 mg/L para água do Colorado River Aqueduct** e **~200 mg/L para água do State Water Project**.

**⚠️ Implicação direta para o nosso projeto:** essa amplitude (200-300 mg/L) é grande o bastante para explicar sozinha os ciclos observados no LAGWRP. Ou seja, o estudo dá respaldo mecanístico independente ao **reenquadramento cíclico/por regime** (ver `Artigo/DECISOES.md`, D-14): a variável explicativa correta provavelmente não é "tempo decorrido", é **qualidade da água de origem seguindo ciclos de seca**. O mecanismo da Nature (2020) — conservação → menos diluição — é real, mas é o efeito **menor** dos dois.

### 9.2 Distribuição de tendências nas 26 estações

- **Efluente (26 ETEs):** 15 em alta, 7 sem tendência, 4 em queda (~60% em alta).
- **Influente (14 ETEs):** 9 em alta, 4 estáveis, 1 em queda.
- As 4 em queda incluem as 2 do Santa Clarita Valley, com causa conhecida: remoção de ~8.000 abrandadores de água autoregeneráveis (SRWS), reduzindo ~80 mg/L de TDS no influente.

### 9.3 Influente ≈ Efluente (Tabela 8 do estudo) — reverte parcialmente nossa decisão sobre Point Loma

"Most of the case studies found that TDS entering a WWTP nearly matched the discharge water quality from the WWTP's effluent. Therefore influent water quality is used as a proxy or surrogate to understand the WWTP effluent water quality."

R² de influente vs. efluente: **Point Loma 0,98** (o mais alto), Temecula Valley 0,90, Moreno Valley 0,87, Perris Valley 0,86, RP-1 0,83, CCWRF 0,87, Padre Dam 0,73, RP-2/RP-5 0,74, RP-4 0,68, North City 0,63, San Jacinto 0,61, OCSD Plant 1 0,46, South Bay 0,45, RPU 0,41.

→ Ver revisão da decisão D-20 em `Artigo/DECISOES.md`.

### 9.4 Séries longas identificadas (candidatas a comparador)

- **La Cañada WRP: 1984-2016** — a série contínua mais longa do estudo.
- **Long Beach WRP: desde 1992** — segunda mais longa contínua.
- **San Jose Creek, Whittier Narrows, Pomona:** dados desde 1984, **mas com lacuna de ~10 anos** do início dos 1990 ao início dos 2000.
- Sistema JOS (LACSD): JWPCP (único que descarrega no oceano), La Cañada, Long Beach, Los Coyotes, Pomona, San Jose Creek, Whittier Narrows. As demais do JOS são majoritariamente plantas de reúso.

**⚠️ Nota importante:** as agências participantes são EMWD, IEUA, MWDSC, OCSD, OCWD, SDCWA, LACSD, SAWPA, City of San Bernardino e Riverside Public Utilities. **A cidade de Los Angeles (LASAN) não participa** — portanto nem o LAGWRP nem o Tillman estão entre as 26 estações. A recomendação do Tillman (D-22) não é validada nem contradita por esta lista.

### 9.5 Métodos transferíveis para a nossa bateria

**Modelo determinístico (balanço de massa) — alternativa fisicamente fundamentada à extrapolação estatística:**
```
TDS_influente = TDS_origem + (SML × população) / (vazão em MGD)
```
onde SML = carga de sal per capita ≈ **0,15-0,18 lb/hab/dia** (média de 0,17 nas bacias do estudo; faixa observada de 0,04 a 0,4 conforme perfil industrial). Conversa diretamente com a nossa reconstrução de vazão (§1.5 do plano) — já temos o denominador.

**Modelo estatístico:** regressão linear múltipla `TDS_influente ~ TDS_origem + vazão_per_capita`, com decomposição de importância relativa via `relaimpo` (método lmg, Grömping 2006/2015). Em Python, equivalente via `statsmodels` + implementação de LMG.

**Variáveis climáticas usadas:** PMDI (Modified Palmer Drought Severity Index, NOAA) e 8-Station Index (DWR, precipitação em 8 estações da Sierra Norte, média de referência 51,8 pol. para 1966-2015).

**IFU (increment from use):** diferença entre TDS de influente e de origem, faixa de **200 a 400 mg/L** na literatura e nas bacias estudadas.

### 9.6 Achado de implicação prática forte (para a seção de implicações do artigo)

"The duration of rolling-average periods can determine whether or not an agency is in violation of their permit limits. A compliance limit based on a **5-year rolling average instead of a 1-year rolling average** for the Perris Valley WWTP would have kept the WWTP within permit limits."

→ A escolha da janela de média móvel não é detalhe técnico: define conformidade regulatória. Material direto para discutir implicações de gestão no nosso artigo, e conecta com a análise de janela móvel já prevista (§3.e do plano).

### 9.7 Cenário futuro projetado pelo estudo

Se as tendências de alta continuarem, mais agências vão se aproximar ou exceder limites de outorga, podendo exigir instalação de dessalinização. A legislação californiana (AB-968 §10608.25) exige redução para 55 gpcd até 2025 — algumas agências já atingiram e acreditam ter chegado ao limite razoável de conservação interna, o que implica que **a curva de conservação tende a achatar**, reduzindo ainda mais a contribuição desse fator daqui para frente.

---

## Como usar este material (sugestão de fluxo)

1. **Para a decisão de ND do BOD (mais urgente):** ler Tema 8 antes de decidir — a evidência de Antweiler & Taylor sugere que Kaplan-Meier pode ser melhor que todas as opções A-E já listadas no plano (proposta: adicionar como opção F).
2. **Para replicar métodos e comparar:** Temas 2, 3 e 6 listam exatamente quais modelos cada artigo usou e os R²/erros reportados — dá para montar uma tabela "nosso resultado vs. literatura" no artigo.
3. **Para a discussão dos resultados:** Tema 1 (mecanismo conservação→salinidade, com o número regional de +50 mg/L) e Tema 4 (mecanismo biológico, com limiares de inibição) são a espinha dorsal da interpretação.
4. **Para a metodologia do artigo:** Temas 5, 6 e 7 fornecem os precedentes que justificam cada família de método da nossa bateria.

---

## Tema 10 — Comparação internacional: o mecanismo se repete fora da Califórnia?

**Por que este tema existe (enquadramento, não acúmulo de referências):** o achado central do
projeto se decompõe em duas partes de natureza diferente:

- A **diluição** (carga de sal caindo, vazão caindo mais rápido → concentração sobe) é **física**.
  Deveria valer em qualquer lugar onde haja conservação, independente de geografia.
- O **efeito da água de origem** (88% segundo o SCSC, seca → qualidade da água importada) é
  **regional**. Depende do portfólio californiano de SWP/Colorado.

A comparação internacional serve para testar **qual parte do achado é universal e qual é local**.

> **Estado de leitura:** todas as entradas abaixo vêm de **buscas e abstracts**, não de textos
> completos. Nenhuma deve ser citada no artigo antes de leitura integral e verificação
> bibliográfica (regra da §2 do plano).

### 10.1 Austrália — Millennium Drought (1997-2010) ⭐ o análogo mais próximo

**Contexto:** seca de ~13 anos, com restrições severas em todas as capitais continentais por volta
de 2006. É o experimento natural mais parecido com o caso californiano — conservação forçada e
prolongada, com dados institucionais.

**Achado relevante encontrado na busca:** durante o período, a salinidade aumentou na **Western
Treatment Plant** (Melbourne) como resultado de intrusão de sal **e redução do volume afluente** —
exatamente o mecanismo de diluição do nosso projeto, num contexto geográfico e de fonte de água
completamente diferente. Também relevante: Victoria estabeleceu meta de reúso de 20% do afluente
até 2010, e superou (24,1% em 2009/10) — ou seja, houve **desvio para reúso simultâneo à
conservação**, que é a mesma ambiguidade causal que temos em aberto no LAGWRP.

**Referências a buscar na íntegra:**
- *Adapting Urban Water Systems to a Changing Climate: Lessons from the Millennium Drought in
  Southeast Australia* — Environmental Science & Technology:
  https://pubs.acs.org/doi/10.1021/es400618z
- *Water reuse and recycling in Australia — history, current situation and future perspectives*:
  https://www.sciencedirect.com/science/article/pii/S2666445320300064
- Australian Water Partnership — *Building Resilience to Drought: The Millennium Drought and Water
  Reform* (PDF público): https://waterpartnership.org.au/wp-content/uploads/2024/03/AWN-Building-Resilience-to-Drought.pdf

### 10.2 Israel — o caso mais maduro de regulação de salinidade em efluente

Recicla ~85-86% do esgoto (maior taxa mundial). Desde 2010, as normas israelenses incluem, **pela
primeira vez, padrões explícitos de salinidade** no efluente tratado — justamente por causa deste
problema. Relevante para a seção de implicações: mostra um caminho regulatório que a Califórnia
ainda não tomou.

Nota conceitual confirmada na literatura israelense/espanhola, que reforça o nosso §1 do glossário:
o tratamento convencional **remove matéria orgânica e sólidos suspensos, mas não sais** — por isso
o efluente tratado tem condutividade elétrica alta, refletindo a carga total de eletrólitos.

**Referências a buscar:**
- *Reducing salinity of treated waste water with large scale desalination* (Water Research):
  https://www.sciencedirect.com/science/article/abs/pii/S0043135420308587
- *New Standards for Treated Wastewater Reuse in Israel*:
  https://www.researchgate.net/publication/225262222
- *Irrigation with water containing salts: macro-data national case study in Israel*:
  https://www.sciencedirect.com/science/article/abs/pii/S0378377415301542

### 10.3 Espanha — contexto mediterrâneo

Reúsa 40-70% do efluente (variando por região). Estudos documentam aumento de condutividade
elétrica em solos irrigados com efluente secundário, e concentrações de cloreto de **609-668 mg/L**
em canais que recebem mistura de água subterrânea e efluente tratado.

**Referências:**
- *Salt accumulation in soils and plants under reclaimed water irrigation in urban parks of Madrid*:
  https://www.sciencedirect.com/science/article/abs/pii/S0378377418307005
- *Salinity effect of irrigation with treated wastewater in basal soil respiration, SE Spain*:
  https://www.researchgate.net/publication/258614930

### 10.4 Dados brutos baixáveis — o que existe e o que não existe

**Achado honesto da busca: dados brutos de TDS/salinidade de efluente, em série temporal por planta,
são raros fora da Califórnia.** O eSMR/CIWQS é excepcionalmente aberto. A maioria dos países publica
apenas agregados nacionais ou os resultados já processados em artigos.

**A melhor fonte encontrada — Melbourne Water (Austrália), com ressalvas importantes:**

O governo de Victoria publica dados **diários** de qualidade de água da Eastern Treatment Plant,
tanto de entrada quanto de saída, com licença **Creative Commons BY 4.0** (uso livre com atribuição):

- Efluente tratado (saída): https://discover.data.vic.gov.au/dataset/wastewater-outlet-daily-treated-water-quality-eastern-treatment-plant-etp
- Afluente bruto (entrada): https://discover.data.vic.gov.au/dataset/wastewater-inlet-daily-raw-water-quality-eastern-treatment-plant-etp
- Download direto (CSV): `https://data-melbournewater.opendata.arcgis.com/api/download/v1/items/ccbcb0ba949b43dca75311aa1137e3fc/csv?layers=0`
- Contato para dados adicionais: enquiry@melbournewater.com.au

**⚠️ Duas limitações que reduzem muito o valor desse dataset para o nosso projeto:**

1. **Não contém TDS, salinidade nem condutividade.** Os parâmetros publicados são: Amônia (mg/L),
   BOD (mg/L), COD (mg/L), Nitrato+Nitrito (mg/L) e Nitrogênio total (mg/L). Sem a variável central
   do trabalho, não é possível replicar a análise de TDS.
2. **A série começa em 2014** (o serviço se chama `MWC_ETP_Daily_EffluentQuality_From2014`) —
   portanto **não cobre a Millennium Drought** (1997-2010), que é justamente o período de interesse.

**Uso residual possível:** os dados de BOD e amônia poderiam servir como comparador para a análise
de correlação, mas sem TDS não há o que correlacionar. **Avaliação honesta: provavelmente não vale
o esforço de integração.** Registrado aqui para que a decisão fique documentada, e para que ninguém
refaça essa busca depois.

**Outros portais verificados:** data.gov.au e o ArcGIS Hub da Melbourne Water espelham os mesmos
datasets, sem parâmetros adicionais.

**Busca adicional (2026-08-20), incluindo download e inspeção real de um candidato:**

- **UK Environment Agency — National Real Time Water Quality Data**
  (`environment.data.gov.uk`): CSV/telemetria real, tem condutividade, 2019-2022. **Descartado**:
  são estações de monitoramento ambiental genérico (rios), sem indicação de serem efluente de ETE.
- **EEA Waterbase-UWWTD** (`eea.europa.eu`): CSV real, cobertura de toda a UE. **Descartado**: os
  parâmetros de efluente reportados são só BOD/COD/SST/N/P — confirmado na lista de indicadores do
  próprio dataset, sem condutividade/TDS.
- **Sydney Water / SA Water / NSW / SA (Austrália)**: nenhum dataset de TDS/condutividade de
  efluente em aberto encontrado — só água potável e descrições genéricas de programas de
  monitoramento.
- **Israel Water Authority**: existe um "banco de dados integrado" de monitoramento de
  esgoto/água reciclada, mas nada publicamente baixável — consistente com o achado da seção 10.2
  (há norma regulatória, não há dado aberto).
- **ACA Catalunya**: API de sensores em tempo real (Sentilo) existe, mas sem confirmação de que
  condutividade/TDS de esgoto esteja entre os parâmetros expostos.
- **UNEP GEMS/Water — Global Freshwater Quality Archive** (Zenodo,
  `zenodo.org/records/14230628`, `GFQA_v2.zip`, 108,7 MB) ⭐ único candidato baixado e
  **efetivamente inspecionado**, não só triado por metadado de página. 20M+ medições, 608
  parâmetros, 13.660 estações, 37 países, 1906-2023 — inclui `Electrical_Conductance.csv` (34 MB) e
  `Salinity.csv`. **Resultado da inspeção: DESCARTADO, de forma definitiva.** A coluna `Water Type`
  de `GEMStat_station_metadata.csv` tem só 5 categorias (River, Groundwater, Lake, Reservoir,
  Wetland) — nenhuma é efluente de ETE. Busca textual por "wastewater/effluent/sewage/WWTP" nas
  descrições das 13.660 estações retornou 56 ocorrências, todas rios/reservatórios **influenciados
  por** ou **próximos a** descarga de esgoto, não pontos de monitoramento do próprio efluente — o
  mesmo erro de categoria que este projeto já havia identificado e evitado com os pontos `R-4`/`R-7`
  (D-07). Arquivo baixado, inspecionado e descartado do disco (não teria uso).

**Conclusão honesta e final desta linha de busca:** dado bruto de TDS/condutividade
especificamente de **efluente de ETE** (não rio, não água potável, não monitoramento ambiental
genérico), aberto, baixável e com série temporal multi-ano, não foi localizado fora da Califórnia
apesar de duas rodadas de busca (Tema 10 original + esta). O eSMR/CIWQS californiano continua sendo
excepcional nesse aspecto, não a norma — isso é, em si, um achado relevante para a seção de
limitações de generalização do artigo (§6 de `ESCOPO_E_LIMITACOES.md`): a comparação internacional
deste trabalho é necessariamente qualitativa (literatura), não numérica (dados brutos), porque a
segunda opção não existe de forma acessível.

### 10.5 Como usar este tema no artigo

O caminho de maior valor é **discussão, não replicação de dados**:

1. O caso da Western Treatment Plant (Austrália) mostra o **mesmo mecanismo de diluição** em outro
   continente, com outra fonte de água — evidência de que essa parte do achado é universal.
2. O caso israelense mostra o **desfecho regulatório** de longo prazo (padrões de salinidade no
   efluente), útil para a seção de implicações.
3. A ambiguidade australiana entre conservação e desvio para reúso é **a mesma que temos em aberto**
   — citá-la mostra que a limitação do nosso trabalho é reconhecida na literatura, não um descuido.

---

## Ressalvas

- Vários links (ScienceDirect, Tandfonline, ResearchGate) têm só o abstract público — o texto completo pode exigir acesso institucional da UniSENAI.
- Nenhuma dessas fontes foi adicionada a `Artigo/refs.bib` ainda — isso só acontece quando forem efetivamente citadas no texto, com dados bibliográficos verificados no texto completo (regra do plano, seção 2).
- Os números citados (R², limiares de inibição, +50 mg/L) vieram dos abstracts/resumos de busca — conferir no texto completo antes de reproduzir no artigo.
