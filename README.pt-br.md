Language / Idioma: [English](README.md) | **Português**

# Tendência e Previsão de TDS — LAGWRP

Projeto de Pós-Graduação em IA Aplicada (UniSENAI) analisando a tendência de longo prazo da salinidade (TDS — Sólidos Dissolvidos Totais) no esgoto tratado da **Los Angeles–Glendale Water Reclamation Plant (LAGWRP)**, e prevendo o TDS 10, 15 e 20 anos à frente.

## Motivação

O tratamento convencional de esgoto depende de comunidades microbianas para remover matéria orgânica (BOD) e converter amônia em nitrato. Salinidade alta (TDS alto) pode inibir esses processos biológicos, reduzindo a eficiência do tratamento. Em regiões como Los Angeles, medidas de conservação de água reduzem o uso interno de água, o que pode aumentar involuntariamente a salinidade do esgoto — a mesma massa de sais entra no sistema num volume menor de água.

Este projeto:
1. Determina se as concentrações de TDS aumentaram ao longo de um período de ~15 anos, quantificando a taxa de variação.
2. Constrói modelos preditivos para prever o TDS 10, 15 e 20 anos à frente, a partir do último dado observado.
3. Investiga a correlação entre TDS e dois indicadores de desempenho do tratamento: Amônia (nitrificação) e BOD (remoção de matéria orgânica).
4. Discute os achados no contexto das práticas de conservação de água em Los Angeles e das implicações para planejamento de infraestrutura e gestão ambiental, ancorado no artigo da *Nature Sustainability* (2020) indicado pelo professor.

## Dados

Fonte: exportação eSMR (Electronic Self-Monitoring Report) do portal California Water Boards — uma linha por medição, cobrindo TDS, Cloreto, Amônia e BOD no efluente da estação (`EFF-001`/`EFF-001A`, unificados em um único ponto físico) e pontos secundários de água receptora (apenas contexto).

Série mensal canônica: `Location ∈ {EFF-001, EFF-001A}`, `Calculated Method == "Monthly Average (Mean)"`, `Units == "mg/L"`. Período: **fevereiro de 2011 a março de 2026 (182 meses)**.

**Tratamento dos valores não detectados (ND) do BOD:** 65% das médias mensais de BOD são reportadas como não detectadas pela concessionária, com limite de detecção (MDL) constante em 3,0 mg/L durante todo o período. Em vez de escolher um único tratamento, foram construídos três datasets canônicos em paralelo, levados adiante na análise de correlação (a única parte da bateria sensível a essa escolha — ver abaixo):
- `dataset_canonico_bod_mdl2.csv` — ND → MDL/2 (1,5 mg/L)
- `dataset_canonico_bod_zero.csv` — ND → 0
- `dataset_canonico_bod_ros.csv` — ND → estimativa ROS/Helsel (2,517 mg/L, data-driven — ver `script_00b_analise_censura_bod.py`)

O valor ROS/Helsel (Dataset F) é o mais bem embasado estatisticamente dos três (regressão em gráfico de probabilidade, r=0,677, p=1,1e-9), mas, como A e B, ainda substitui um único valor em todos os 118 meses ND — as observações são indistinguíveis entre si ("< 3,0"), então nenhum método recupera variação mês a mês real dentro dos meses ND; isso é uma limitação dos dados, não da implementação. O resultado da correlação TDS↔BOD (nula) é o mesmo nos três tratamentos. Ver `scripts/script_00b_analise_censura_bod.py` e `results/` para o raciocínio completo, as verificações nos dados brutos e os números por trás dessa decisão.

## Metodologia (bateria de métodos)

Cada método roda de forma independente e em paralelo, nos dois datasets de tratamento de ND, prevendo TDS para +10, +15 e +20 anos a partir do último dado observado:

| Script | Método |
|---|---|
| `script_00_preprocessamento.py` | Constrói os datasets mensais canônicos a partir dos 4 CSVs brutos |
| `script_01_mann_kendall_theilsen.py` | Mann-Kendall + inclinação de Sen, Theil-Sen, OLS — **implementado** |
| `script_02_arima_sarima.py` | SARIMA — **implementado** |
| `script_03_random_forest_gridsearch.py` | Utilitários de feature engineering compartilhados por `script_10`/`script_14`/`script_31` (não é mais um método próprio — ver D-73) |
| `script_05_prophet_bayesiano.py` | Prophet — **implementado** |
| `script_06_correlacao_tds_amonia_bod.py` | Correlação TDS↔Amônia e TDS↔BOD (bruta + destendenciada + defasada) — **implementado** |
| `script_07_analise_estrutura_serie.py` | Força de sazonalidade, estacionariedade ADF/KPSS, quebra estrutural Chow/Pettitt/CUSUM — **implementado** |
| `script_08_baselines.py` | Baseline naive — **implementado** |
| `script_10_detrend_arvore.py` | Tendência OLS + RF no resíduo (corrige a saturação de árvores) — **implementado** |
| `script_14_diagnostico_residuos.py` | Diagnóstico de resíduos (Ljung-Box/Shapiro-Wilk/ARCH) dos 3 candidatos mais fortes — **implementado** |
| `script_15_sintese_final.py` | Tabela consolidada de métricas + gráfico dos 7 métodos (sem vencedor recomendado — D-73) — **implementado** |

**Status atual: projeto completo.** `script_00` a `script_15` implementados e validados — **7 métodos de previsão** (Mann-Kendall/Sen, Theil-Sen, OLS, SARIMA, Prophet, naive, Detrend+RF), diagnóstico de estrutura da série, análise de correlação, diagnóstico de resíduos, e síntese final embasada na literatura (os quatro objetivos do projeto endereçados). Todo método de previsão reporta MASE, sMAPE, CV expansiva de 5 folds e backtest de origem móvel (`utils/validacao_utils.py`), não só um holdout único de 24 meses.

**D-73 (2026-10-15): a bateria foi reduzida de 15 para esses 7 métodos**, igualando exatamente os métodos que uma revisão externa do manuscrito citou com resultado (ela reenquadrou os modelos de previsão como "verificações auxiliares da dificuldade de previsão", não como fonte de uma previsão recomendada de longo prazo). A tendência isolada do STL, o Random Forest puro, a regressão bayesiana, naive sazonal/ETS/Theta, Detrend+XGBoost e o híbrido SARIMA+Prophet — todos parte da bateria original de 15 métodos — foram para `scripts/bateria_estendida/` (só local); nenhum resultado mudou, eles só deixaram de ser o núcleo reportado do artigo. Ver `docs/adr/0001`–`0003` para o histórico completo da decisão, incluindo por que isso também significou abandonar de vez o conceito de "finalista recomendado" (um híbrido de dois métodos era um dos dois finalistas; sem ele, um único "finalista" remanescente contradiria o próprio critério de comparação do projeto, "não um único vencedor").

Uma bateria de triagem mais ampla (XGBoost, LightGBM, SVR, Gaussian Process, SARIMAX com Cloreto, LSTM, espaço de estados, GAM, regressão quantílica, análise de intervenção, modelo fundacional zero-shot, e re-treino com PDSI como covariável) também foi testada durante o desenvolvimento — nada disso mudou as conclusões centrais, então fica mantida localmente em `scripts/bateria_estendida/` (gitignored), fora do artigo/repositório público.

**Achados notáveis:** o **baseline naive tem o menor MASE de toda a bateria de 7 métodos** no holdout de 24 meses (0,436), com o **Detrend+RF muito próximo** (0,441) — e, ao contrário do Random Forest puro (mantido localmente — satura em 704,3 mg/L nos três horizontes), a previsão de longo prazo do Detrend+RF cresce de forma monotônica em vez de saturar (743,5 → 762,2 → 780,9 mg/L em +10/+15/+20a), corrigindo diretamente a limitação de extrapolação de árvores já documentada. Ver `results/resultados_comparacao.csv`, `results/figures/` e `notebooks/notebook.ipynb` para a discussão completa.

**GPU:** confirmada funcionando nesta máquina com a RTX 4060 Ti para o script de XGBoost da bateria estendida (`tree_method="hist", device="cuda"`) — não necessária para a bateria principal pública, que roda em CPU.

## Como rodar

Use um ambiente virtual dedicado (`.venv/`, fora do controle de versão) para manter as dependências deste projeto isoladas do resto da máquina:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python scripts/script_00_preprocessamento.py
python scripts/script_01_mann_kendall_theilsen.py
python scripts/script_02_arima_sarima.py
python scripts/script_05_prophet_bayesiano.py
python scripts/script_06_correlacao_tds_amonia_bod.py
python scripts/script_07_analise_estrutura_serie.py
python scripts/script_08_baselines.py
python scripts/script_10_detrend_arvore.py
python scripts/script_14_diagnostico_residuos.py
python scripts/script_15_sintese_final.py

# investigacao causal/mecanismo (ver secao abaixo)
python scripts/script_16_reconstrucao_vazao.py
python scripts/script_17_matriz_sensibilidade.py
python scripts/script_18_pdsi_regimes.py
python scripts/script_19_wrtds.py
python scripts/script_20_balanco_massa.py
python scripts/script_21_cenarios.py
python scripts/script_28_ladwp_tds_origem.py
python scripts/script_31_testes_robustez_avancados.py
```

Bateria de triagem estendida (local, gitignorada — não faz parte do repositório público): `python scripts/bateria_estendida/script_XX_....py`.

`script_00` gera `dataset_canonico_bod_mdl2.csv`, `dataset_canonico_bod_zero.csv` e `dataset_canonico_bod_ros.csv` em `data/processed/`. `script_01` ajusta a tendência de TDS (Mann-Kendall/Sen, Theil-Sen, OLS); `script_02` ajusta SARIMA (ordem escolhida por busca em grade por AIC); `script_03` agora é só um módulo utilitário de features (sem entrada de linha de comando — `script_10`/`script_14`/`script_31` importam `carregar_serie_tds`/`construir_features`/`FEATURES`); `script_05` ajusta Prophet; `script_06` calcula as correlações TDS↔Amônia/BOD; `script_07` roda o diagnóstico estrutural (força de sazonalidade, ADF/KPSS, Chow/Pettitt/CUSUM) que embasa se termos sazonais valem a pena; `script_08` ajusta o baseline naive; `script_10` ajusta tendência OLS + Random Forest no resíduo. Todo script de método também roda a CV expansiva de 5 folds e o backtest de origem móvel (+3/+5 anos) do `utils/validacao_utils.py`, gravando colunas de MASE/sMAPE/CV/backtest junto das métricas de holdout já existentes em `results/resultados_comparacao.csv`/`.json`, além de regenerar sua figura em `results/figures/`. `script_16` reconstrói a vazão do efluente; `script_17` roda a matriz de 9 testes de sensibilidade no tratamento de dados; `script_18` baixa e testa o índice de seca PDSI do NOAA contra os ciclos de TDS; `script_19`/`script_20`/`script_21` são WRTDS, balanço de massa e cenários climáticos — ver a seção "Tratamento de dados robusto e bateria ampliada" abaixo para os resultados de cada um.

## Rastreamento de experimentos (MLflow)

As execuções passam a ser rastreadas localmente com [MLflow](https://mlflow.org/) — sem nuvem, sem conta. O metadado de rastreamento fica num SQLite local (`mlflow.db`) e os artefatos (figuras etc.) em `mlruns/`, ambos fora do controle de versão. `utils/experiment_tracking.py` traz os utilitários compartilhados que cada script usa: `iniciar_run()` abre uma run e loga params/seed/janela de treino-holdout/tempo de execução; `logar_metricas()`/`logar_linha_resultado()` logam métricas; `logar_artefatos()` loga arquivos; `exportar_para_resultados_csv()` exporta runs escolhidas de volta para `results/resultados_comparacao.csv`, substituindo só a linha daquele método. O `results/resultados_comparacao.csv` continua sendo a fonte enxuta usada pelo notebook e pelo dashboard — o MLflow é o histórico mais completo ao lado dele (inclusive tentativas descartadas).

`script_01`, `script_02`, `script_05`, `script_07`, `script_08` e `script_10` agora abrem uma run de MLflow por método (ou passo de diagnóstico). Para inspecionar as runs:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Estrutura do projeto

```
├── data/
│   ├── raw/              # eSMR (TDS/Chloride/Ammonia/BOD.csv, xlsx), PDSI bruto, ETEs comparadoras
│   └── processed/        # datasets canônicos, vazão, séries PDSI, extratos LADWP
├── scripts/              # script_00 … script_21, script_28, script_31 (+ script_00b) — bateria principal/pública
│   └── bateria_estendida/ # bateria de triagem mais ampla — local, gitignorada
├── utils/
│   ├── paths.py          # caminhos canônicos (raw/processed/result/figure)
│   ├── experiment_tracking.py
│   └── validacao_utils.py
├── results/
│   ├── resultados_comparacao.csv / .json
│   ├── *_resultados.* / tabela_sintese_final.csv / comparacao_pdsi_*
│   └── figures/          # PNGs gerados pelo pipeline
├── notebooks/            # notebook.ipynb didático
├── docs/
│   ├── GLOSSARIO.md      # glossário de domínio público
│   └── adr/              # registros de decisão arquitetural (0001–0003)
├── README.md / README.pt-br.md / CLAUDE.md / requirements.txt
```

Material de apoio local (artigo LaTeX, plano de execução, prompts de processo, logs de decisão, PDFs) pode existir no disco, mas **não** faz parte do repositório público.

## Resultados

**Tendência de TDS (script_01, estatística clássica):** os três métodos concordam numa tendência de alta estatisticamente significativa de 3,7–3,9 mg/L/ano (p < 0,01). Ver `results/figures/tendencia-tds.png`, `results/resultados_comparacao.csv` e `notebooks/notebook.ipynb` para a tabela completa, a figura de previsão e a discussão (incluindo a limitação honesta de que uma tendência linear simples performa pior no holdout de 24 meses — R² negativo — mesmo identificando corretamente a direção de longo prazo).

**SARIMA (script_02):** a melhor ordem por AIC não tem drift explícito, então sua tendência implícita (10,4 mg/L/ano, derivada do caminho previsto) é bem mais acentuada que a dos métodos clássicos, com IC90% já incluindo valores negativos a partir de +15 anos — a fragilidade esperada e já documentada de extrapolar o SARIMA muito além dos ~15 anos de histórico. A tendência dessazonalizada isolada do STL (2,9 mg/L/ano, consistente com a §3.a) não faz mais parte da bateria principal (D-73) — mantida localmente (`scripts/bateria_estendida/script_33_stl_tendencia.py`). Ver `results/figures/sarima-tds.png`, `results/resultados_comparacao.csv` e `notebooks/notebook.ipynb`.

**Prophet (script_05):** detecta corretamente a tendência histórica (3,81 mg/L/ano, p<0,0001) pela própria decomposição, mas sua extrapolação **decresce** com o horizonte (636,9 → 604,8 mg/L de +10 a +20 anos) — os changepoints automáticos capturaram uma desaceleração recente local e extrapolam essa inclinação, não a média de 15 anos. Reportado como achado genuíno, não maquiado. Random Forest puro e regressão bayesiana — ambos parte da bateria original — não fazem mais parte do núcleo (D-73): a previsão do Random Forest satura em 704,3 mg/L nos três horizontes (árvores não extrapolam além do range de treino); a regressão bayesiana confirmou a tendência clássica (3,74 mg/L/ano, 99,5-99,9% de probabilidade posterior de tendência positiva) com um IC90% que cresce suavemente, mas perdeu de forma significativa contra o naive num teste de Diebold-Mariano (ver "Robustez" abaixo) — ambos mantidos localmente em `scripts/bateria_estendida/`. Ver `results/tabela_sintese_final.csv`, `results/figures/sintese-final-metodos.png` e `notebooks/notebook.ipynb` para a tabela completa e a discussão.

**Conclusão da bateria principal de 7 métodos:** os métodos clássicos/estatísticos (Mann-Kendall/Sen, Theil-Sen, OLS) convergem numa tendência de alta consistente e estatisticamente significativa de 3,7–3,9 mg/L/ano (p<0,01). SARIMA e Prophet divergem em direções opostas ao extrapolar. Nenhum método tem R² positivo em holdout — o naive tem o menor MASE isolado (0,436) de toda a bateria. Ver "Bateria de robustez e overfitting" abaixo para o motivo de nada disso ser lido como uma previsão confiante de longo prazo.

**Diagnóstico estrutural (script_07):** sazonalidade fraca (Fs=0,25, abaixo do limiar de referência 0,64 da literatura) — não assumida por padrão, testada. ADF rejeita a hipótese de raiz unitária e KPSS não rejeita estacionariedade, ambos compatíveis com um processo estacionário em torno de tendência (trend-stationary), não uma caminhada aleatória. Chow (breakpoint ~2012, coincidindo com a troca de código EFF-001→EFF-001A), Pettitt (mudança detectada em 2014-04, dentro da janela de seca da Califórnia 2012-2016) e CUSUM confirmam que a série não é homogênea ao longo do período — reforça a cautela já existente sobre extrapolar muito além do histórico de treino.

**Framework de validação honesta + baselines (script_08, `utils/validacao_utils.py`):** todo método agora reporta MASE, sMAPE, CV expansiva de 5 folds e backtest de origem móvel (+3/+5 anos), além do holdout de 24 meses original — não mais um único split treino/teste. O único baseline obrigatório da bateria principal agora é o naive (D-73 — naive sazonal/ETS/Holt-Winters/Theta foram para `scripts/bateria_estendida/script_36_baselines_estendidos.py`), e ele continua com **o menor MASE em holdout de toda a bateria de 7 métodos** (0,436). Isso não invalida os métodos focados em tendência — a previsão do naive é uma linha reta, sem captar tendência de longo prazo alguma — mas é um achado genuíno e reportado: nas flutuações de curto prazo desta série, nenhum método (sofisticado ou não) supera de forma confiável "nada muda".

**Diagnóstico de resíduos (script_14):** Ljung-Box, Shapiro-Wilk e ARCH nos resíduos in-sample dos 3 candidatos mais fortes (OLS, Detrend+RF, SARIMA — D-73 tirou a regressão bayesiana e o híbrido SARIMA+Prophet dessa comparação junto com o resto da bateria) mostram que **o Detrend+RF é o único sem autocorrelação residual nem heterocedasticidade condicional detectável** — só falha o teste de normalidade (caudas mais pesadas, comum em árvores). OLS e SARIMA, com forma funcional linear/estocástica explícita, falham em pelo menos 2 dos 3 testes.

**Comparação com a literatura:** Schwabe et al. (2020, 34 estações do sul da Califórnia, 2013-2017) e Wolfand et al. (2022, mesma bacia do rio Los Angeles onde a LAGWRP descarrega) encontram a mesma direção de efeito (conservação/reúso de água → maior salinidade/TDS) identificada de forma independente neste projeto. A comparação é deliberadamente qualitativa: o texto completo de nenhum dos dois artigos foi acessível nesta sessão (ambos pagos) — nenhuma magnitude numérica é reproduzida sem verificação direta, só a direção do efeito, confirmada via fontes secundárias genuinamente acessadas (nota institucional, resumo de sociedade profissional), não inventada a partir de um resumo de busca. Ver `notebooks/notebook.ipynb` e `results/` para a síntese embasada na literatura.

**Síntese final (script_15, D-73 — sem vencedor recomendado):** o híbrido SARIMA+Prophet era um dos dois "finalistas" recomendados por uma versão anterior desta síntese, escolhido pelo IC90 mais cauteloso/conservador; ele não faz mais parte da bateria principal (ver "Status" acima). Sem ele, recomendar o único método remanescente (Detrend+RF) como "finalista" isolado contradiria o próprio critério de comparação do projeto ("não um único vencedor") — então o `script_15` foi reescrito para abandonar de vez o enquadramento de finalista: agora só reporta MASE/sMAPE/R²/tendência/IC90 dos 7 métodos principais, ordenados por MASE de holdout, com naive e Detrend+RF praticamente empatados no topo (0,436 vs. 0,441) e nenhum método destacado como recomendação. A regressão bayesiana, a terceira candidata considerada para uma vaga de finalista antes de D-73, já havia sido descartada (D-67) depois que um teste de Diebold-Mariano dedicado contra o naive mostrou que ela perde de forma significativa (p=0,015) — agora ela está fora da bateria principal por completo, não só do rótulo de finalista. Ver `docs/adr/0001`–`0003` para o histórico completo da decisão.

A bateria de 7 métodos principais, o diagnóstico estrutural, a análise de correlação, o diagnóstico de resíduos e a interpretação à luz da literatura estão completos — os quatro objetivos do projeto endereçados. `dataset_canonico_bod_ros.csv`, `diagnostico_residuos_resultados.csv/json` e `tabela_sintese_final.csv` são saídas adicionais geradas nesta última fase.

## Tratamento de dados robusto e bateria ampliada (Etapa 3)

Antes de estender ainda mais a bateria de métodos, dois passos de tratamento de dados foram executados:

**Reconstrução da vazão (`script_16_reconstrucao_vazao.py`):** o dataset traz o mesmo parâmetro em `mg/L` e `lb/day`, relacionados por `lb/day = mg/L × vazão(MGD) × 8,34`. Isso permite reconstruir a vazão do efluente, que não está explícita no dataset. Validado de duas formas: plausibilidade contra a capacidade nominal de 20 MGD da planta, e consistência cruzada entre parâmetros (a vazão derivada independentemente de TDS, Cloreto, Amônia e BOD — medidos na mesma amostra física — deve coincidir se o pareamento for real). **Resultado: a identidade se sustenta** — a vazão derivada de TDS correlaciona 0,997-0,998 com Cloreto/Amônia (0,87 com BOD, mais ruidoso mas ainda forte), com média de ~9,5 MGD (~47% da capacidade nominal), tudo plausível. Isso habilitou os métodos WRTDS, balanço de massa e cenários climáticos — todos implementados, ver abaixo.

**Matriz de 9 testes de sensibilidade no tratamento de dados (`script_17_matriz_sensibilidade.py`):** rodada ANTES de fixar qualquer tratamento como padrão, cada variante logada com suas próprias métricas no MLflow. **Achados que qualificam a alegação central do projeto** (tendência de alta de TDS estatisticamente significativa): (1) a tendência cai de 3,91 mg/L/ano (p=0,0056, série completa) para 0,84 mg/L/ano (p=0,59, **não significativo**) quando restrita ao período só EFF-001A (2012-2026, 170/182 meses) — os 12 meses iniciais sob EFF-001 têm peso desproporcional; (2) 3 das 4 transições de MDL/método coincidem com mudança estatisticamente significativa no nível médio de TDS; (3) nenhuma das 4 variantes de agregação anual (15 pontos) atinge significância (p 0,30-0,44); (4) o p-valor muda de significativo (0,0056) para **não significativo** sob 2 das 4 correções de autocorrelação testadas (Hamed-Rao p=0,182; pre-whitening p=0,417), continuando significativo nas outras duas (trend-free pre-whitening p=0,0001; Seasonal Kendall p=0,0038). Contrabalançando: a reagregação das amostras brutas bate exatamente com o "Monthly Average" pronto, a tendência é estável com/sem remoção de outliers (3,6-3,9 mg/L/ano, todas p<0,01), não há meses faltantes, e a escala log dá o mesmo p-valor da escala bruta, como esperado (Kendall's tau é invariante a transformação monotônica). **Leitura líquida: a tendência de alta não é um artefato óbvio de outliers ou reagregação, mas é sensível à transição de código de local, a mudanças de MDL, e à correção de autocorrelação — três sinais convergentes de que o p-valor mensal ingênuo pode superestimar a confiança.** Ver `matriz_sensibilidade_resultados.csv` e `notebook.ipynb` §6 para a tabela completa.

**Investigação de acompanhamento — a "quebra" EFF-001→EFF-001A não é artefato; a série é cíclica, não monotônica.** Uma regressão OLS com termo de degrau (isolando a transição de código de local de uma tendência linear no período completo) encontrou um salto de nível aparente grande e significativo (+137 mg/L, p<0,001) e nenhuma tendência linear residual significativa (0,42 mg/L/ano, p=0,75) — mas a inspeção ponto a ponto mostra que a transição em si é contínua (580→598 mg/L de um mês para o outro, mesmo método analítico, mesmo MDL, mesmas coordenadas). O "degrau" é um artefato de ajustar uma reta única + um salto único a uma série que na verdade se move por regimes: o TDS sobe de 563 para 808 mg/L (2011-2015, coincidindo com a seca da Califórnia de 2012-2016), cai para 636 mg/L (2019), sobe de novo para 768 mg/L (2022, segunda seca), e depois recua. A vazão reconstruída (`script_16`) correlaciona com o TDS no sentido esperado (r anual = −0,55, p=0,027), mas não acompanha totalmente o formato fino do ciclo (a vazão ficou estável durante a queda de TDS de 2016-2017) — consistente com evidência independente da literatura (SCSC/DBS&A 2018) de que **o TDS da água de origem, não a conservação local, explica ~88% da variabilidade do TDS de influente** em plantas próximas do Sul da Califórnia, variável que este dataset não contém. Raciocínio e evidência completos em `results/matriz_sensibilidade_resultados.csv`, `results/figures/` e nos scripts acima (IDs de decisão D-13, D-14, D-29–D-31).

**Teste do ciclo de seca (`script_18_pdsi_regimes.py`) — o reenquadramento cíclico agora está confirmado empiricamente, não só plausível visualmente.** Em vez de confiar só no formato da própria série de TDS, o padrão cíclico foi testado contra uma variável externa e independente: o Índice de Severidade de Seca de Palmer (PDSI) mensal do NOAA — o mesmo índice climático usado pelo estudo SCSC/DBS&A (2018) para explicar TDS em 26 estações do Sul da Califórnia. Três séries de PDSI foram testadas (Califórnia estadual; divisão climática de Los Angeles; divisão de Sacramento, bacia de origem do State Water Project), com defasagens de 0-36 meses e p-valores corrigidos por graus de liberdade efetivos sob autocorrelação serial (Pyper & Peterman, 1998). Quatro resultados convergentes: (1) a correlação cruzada bruta é forte e significativa mesmo após a correção de DOF (r=−0,53 a −0,65 em defasagem de 3-4 meses, n efetivo ≈ 22-30 de ~180 nominais); (2) changepoints detectados só no PDSI — cegos às datas do TDS — caem a poucos meses das quatro viradas de regime observadas (2012, 2015, 2019, 2022); (3) a decomposição LMG de importância relativa (`TDS ~ PDSI defasado + vazão reconstruída`) atribui 67-79% da importância ao PDSI nas três séries, mesma ordem de grandeza do benchmark do SCSC (~88% água de origem); (4) o coeficiente do PDSI continua altamente significativo (p<0,0001) mesmo controlando por regime. **Ressalva honesta:** a correlação destendenciada (mês a mês) é bem mais fraca e muda de sinal (r=+0,15 a +0,19) — a seca explica principalmente o *nível* de cada regime, não sua oscilação fina. Desfecho declarado (dos três definidos a priori no protocolo do teste): **o PDSI explica bem os ciclos** — D-14 agora está confirmado, não só proposto. Evidência completa em `results/pdsi_regimes_resultados.csv` / `.json` e `data/processed/pdsi_*.csv` (ID de decisão D-37).

**WRTDS — normalização por vazão (`script_19_wrtds.py`):** confirmado o padrão cíclico, a pergunta virou "há tendência *por baixo* dos ciclos, depois de descontar a vazão?". Implementação própria (não o pacote R `EGRET`, sem equivalente Python maduro): regressão ponderada localmente (kernel tricúbico em tempo/log-vazão/sazonalidade) + flow-normalização. **Resultado: a tendência bruta (+0,58%/ano, p=0,0056) cai para −0,13%/ano (p=0,064, não significativa)** depois de descontar a vazão — quase toda a tendência aparente é efeito de vazão. Checagem de circularidade obrigatória (vazão derivada de Cloreto, independente do TDS) confirma: diferença de só 0,024 pontos percentuais/ano frente à versão com vazão de TDS. Ver `results/wrtds_resultados.csv` / `.json` e `results/figures/wrtds-*.png` (ID de decisão D-39).

**Balanço de massa (`script_20_balanco_massa.py`):** modela carga de sal (lb/dia) e vazão (MGD) separadamente e deriva `TDS = carga ÷ (vazão × 8,34)`. **Carga de sal caiu −3,20%/ano e vazão caiu −3,85%/ano (p<0,0001 nos dois) — confirma diluição, não mais sal entrando no sistema.** Validação histórica não-circular (vazão de Cloreto) tem R²=0,94; a checagem de tautologia (vazão do próprio TDS) dá R²=1,000000 exato, como esperado por identidade algébrica — reportado como checagem, não como resultado. Achado negativo registrado: extrapolar carga e vazão linearmente por 20 anos cruza vazão fisicamente implausível (negativa em +20a) — motivo direto da próxima etapa. Ver `results/balanco_massa_resultados.csv` / `.json` e `results/figures/balanco-massa-*.png` (ID de decisão D-40).

**Cenários climáticos (`script_21_cenarios.py`):** substitui a extrapolação linear implausível por uma projeção condicional via Monte Carlo (AR(1) no PDSI histórico de 1895-2026 + regressão TDS~PDSI). Quatro cenários (seco/normal/úmido/agravamento climático), faixas fisicamente plausíveis em +20 anos: seco 718 [588, 846] mg/L; agravamento climático 714 [591, 842]; normal 658 [529, 783]; úmido 594 [462, 721]. **Não há um número único para 2046** — a faixa condicionada ao clima é a resposta honesta que os dados permitem. Ver `results/cenarios_resultados.csv` / `.json` e `results/figures/cenarios-pdsi-*.png` (ID de decisão D-41).

**Uma bateria de triagem mais ampla (espaço de estados, GAM, regressão quantílica, análise de intervenção, modelo fundacional zero-shot, e um 5º cenário climático fundamentado em projeção real do Cal-Adapt/RCP 8.5) também foi testada — tudo reforça, de ângulos independentes, que não há tendência residual clara além do efeito de vazão/regime, e nada disso mudou as conclusões centrais.** Mantida localmente em `scripts/bateria_estendida/` (gitignorada), fora do repositório/artigo público.

**TDS real da água de origem via 21 anos de relatórios da LADWP (`script_28_ladwp_tds_origem.py`, D-54).** A lacuna de dado mais crítica do projeto (D-30 — sem série de TDS da água de origem, só o proxy indireto do PDSI) foi parcialmente preenchida com dado primário real: 21 relatórios anuais de qualidade da água da LADWP (2004-2024), cada um publicando o TDS médio por fonte de abastecimento (LA Aqueduct, poços locais, e as três ETAs da MWD — Weymouth, Diemer, Jensen) e o percentual de mistura de cada ano. Construída uma série de TDS de origem ponderado e comparada ao TDS anual de efluente da LAGWRP (14 anos de sobreposição, 2011-2024): **r=0,912 (p=0,000005)** — mais forte que a correlação já obtida com o PDSI (D-37, LMG 67-79%). Todos os 21 anos (100%, não uma amostra) foram conferidos manualmente célula a célula contra os PDFs originais, sem nenhuma discrepância. Limitações declaradas: o peso da MWD é uma média simples das suas 3 estações (o peso real de cada uma não é publicado em nenhum dos 21 relatórios); a série é anual, não mensal (os relatórios não publicam detalhamento mensal); cobre só o lado Los Angeles (LADWP) da área de serviço da LAGWRP, não o lado Glendale.

**PDSI como covariável, e seu fine-tuning (bateria estendida, D-56/D-57).** Com o PDSI já mostrado como explicação do *regime* cíclico (D-37), restava a pergunta direta: adicioná-lo como covariável também melhora o *desempenho preditivo*? Métodos que aceitam regressor exógeno por desenho foram re-treinados com o PDSI. **Resultado: sem melhora consistente** — a maioria piorou, e só um método (XGBoost) manteve ganho real sob o critério mais rígido de validação honesta (CV expansiva, não só o *holdout* fixo). Números completos mantidos localmente em `results/bateria_estendida/` (IDs de decisão D-56/D-57).

**Status:** a bateria principal e a investigação causal (WRTDS, balanço de massa, cenários, reconstrução de vazão, matriz de sensibilidade, regimes PDSI, TDS de origem LADWP) estão completas e públicas. A bateria de triagem mais ampla confirmou e aprofundou o reenquadramento cíclico de D-14/D-37 sem alterá-lo, e fica mantida localmente (ver D-45–D-50 para cada um). Logs de decisão, glossário e o artigo LaTeX ficam apenas no disco local, em `docs_local/` (gitignored) e **não** fazem parte deste repositório público. Histórico completo de commits e código-fonte reproduzível em **https://github.com/igorfnogueira/projeto-aplicado**.

## Bateria de robustez e overfitting (`script_31`)

Antes de tratar qualquer resultado acima como definitivo, uma bateria dedicada testou os 3 candidatos da bateria principal com tendência explícita (OLS, Detrend+RF, SARIMA — D-73 tirou a regressão bayesiana e o híbrido SARIMA+Prophet junto com o resto da bateria) contra overfitting e incerteza superconfiante — arquivo próprio `results/testes_robustez_resultados.csv`/`.json`, sem alterar `resultados_comparacao.csv`.

**Cobertura empírica do IC90 (`script_31`, item 1):** o intervalo de confiança de 90% declarado por cada método deveria conter o valor real ~90% das vezes sob validação cruzada/backtest — e não cobre, em nenhum dos 6 métodos testados. Mann-Kendall/Sen, Theil-Sen e OLS cobrem só 37–38% (CV) e 27% (backtest de 36/60 meses); o Detrend+RF, com intervalo calibrado via bootstrap de resíduo (mesma técnica já usada no SVR do `script_09`, bateria estendida), cobre apenas 27% (CV) e 13–45% (backtest). O Prophet cobre 47% (CV), mas cai para 33% (backtest de 36 meses) e 0% (backtest de 60 meses) — o pior resultado isolado de todo o teste. SARIMA sai melhor (75% CV, 80–91% backtest), mas ainda abaixo do nominal, e a largura do seu intervalo em CV (~247 mg/L) é cerca de 3× maior que a dos demais (~87–97 mg/L). **A incerteza declarada pelos 6 métodos é superconfiante frente ao protocolo de validação honesto.**

**Diebold-Mariano (`script_31`, item 2):** comparações par a par de acurácia de previsão (correção HLN de amostra pequena, n=24 meses de holdout) entre os 3 candidatos e o baseline naive — conjunto fixo, independente de qualquer lista de "finalistas" (ADR-0002/D-73: amarrar esse item a uma lista de recomendados tornava o próprio teste que motivou D-67, regressao_bayesiana_vs_naive, irreproduzível depois que esse método saiu da bateria) — mostram o Detrend+RF significativamente diferente do SARIMA (p=0,044). Contra o naive, nenhum de OLS, Detrend+RF ou SARIMA é significativamente diferente (p=0,81, p=0,15, e OLS p=0,015 — o ajuste in-sample do OLS é próximo o bastante da antiga construção da regressão bayesiana para reproduzir o mesmo achado de D-67 sob outro nome de método).

**Diagnóstico de resíduo out-of-sample (`script_31`, item 3):** diferente do quadro in-sample do `script_14` (onde o Detrend+RF era o único candidato a passar nos testes de autocorrelação e heterocedasticidade), **os 3 candidatos falham no teste de Ljung-Box sobre o resíduo do holdout de 24 meses** (p=0,024–0,049) — autocorrelação de resíduo out-of-sample que o diagnóstico in-sample não capturou. Shapiro-Wilk e ARCH passam para todos os métodos nesse horizonte.

**Gap de RMSE in-sample × CV × holdout (`script_31`, item 4):** o Detrend+RF mostra a assinatura de overfitting mais evidente — RMSE in-sample de 19,4 salta para 76,7 sob CV (vs. 49,8 no holdout), um gap de ~4× que o único split treino/teste teria escondido por completo. OLS e SARIMA mostram um gap menor, mas real (ex.: SARIMA: 78,0 in-sample → 90,8 CV → 48,4 holdout).

**Leave-one-year-out e sweep "remover os N primeiros anos" (`script_31`, item 5/5b):** remover qualquer ano isolado mantém a tendência de Mann-Kendall/Theil-Sen positiva, geralmente ainda significativa (1,2–5,4 mg/L/ano), exceto quando 2011 ou 2012 é removido isoladamente (não significativo, p=0,29–0,45). Remover cumulativamente os primeiros N anos é mais drástico: a inclinação **muda de sinal e de significância** conforme N cresce — de +1,2 mg/L/ano (N=1, p=0,45) para −4,2 (N=3, p=0,017, *significativo negativo*) e −4,6 (N=4, p=0,027, *significativo negativo*), antes de colapsar para ~0 (N=5, p=0,91). A afirmação central do projeto ("tendência de alta estatisticamente significativa") **não é robusta** à quantidade de anos iniciais (2011–2015) incluídos.

Um diagnóstico separado (`script_32`, bateria estendida, local) checou hiperparâmetro fixo vs. aninhado para os métodos de árvore/kernel da bateria estendida — CV aninhada mudou o MASE em no máximo ~3,4% ao custo de 3–200× mais tempo de computação, confirmando que o atalho de hiperparâmetro fixo usado no resto do projeto é uma simplificação segura, não um viés otimista.

Ver `results/testes_robustez_resultados.csv`/`.json` e `results/figures/testes-robustez-avancados.png` para os números completos; `notebooks/notebook.ipynb` discute esses achados junto com o resto da análise.

## Referências

Referência âncora principal: Schwabe et al., *Nature Sustainability* (2020), sobre o aumento da salinidade em esgoto ligado a práticas de conservação de água (indicada pelo professor). Wolfand et al., *ACS ES&T Water* (2022), sobre a mesma bacia do rio Los Angeles. Antweiler e Taylor, *Environmental Science & Technology* (2008), para a técnica ROS/Helsel usada no `script_00b`.
