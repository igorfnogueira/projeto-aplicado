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

O valor ROS/Helsel (Dataset F) é o mais bem embasado estatisticamente dos três (regressão em gráfico de probabilidade, r=0,677, p=1,1e-9), mas, como A e B, ainda substitui um único valor em todos os 118 meses ND — as observações são indistinguíveis entre si ("< 3,0"), então nenhum método recupera variação mês a mês real dentro dos meses ND; isso é uma limitação dos dados, não da implementação. O resultado da correlação TDS↔BOD (nula) é o mesmo nos três tratamentos. Ver `plano_projeto_TDS.md` (§1.3), `script_00b_analise_censura_bod.py` e `Artigo/src/metodologia.tex` para o raciocínio completo, as verificações nos dados brutos e os números reais apresentados antes dessa decisão.

## Metodologia (bateria de métodos)

Cada método roda de forma independente e em paralelo, nos dois datasets de tratamento de ND, prevendo TDS para +10, +15 e +20 anos a partir do último dado observado:

| Script | Método |
|---|---|
| `script_00_preprocessamento.py` | Constrói os datasets mensais canônicos a partir dos 4 CSVs brutos |
| `script_01_mann_kendall_theilsen.py` | Mann-Kendall + inclinação de Sen, Theil-Sen, OLS — **implementado** |
| `script_02_arima_sarima.py` | Decomposição STL + ARIMA/SARIMA — **implementado** |
| `script_03_random_forest_gridsearch.py` | Random Forest (CPU) — **implementado** |
| `script_04_xgboost_lightgbm.py` | XGBoost (GPU/CUDA) + LightGBM (CPU) — **implementado** |
| `script_05_prophet_bayesiano.py` | Prophet + regressão bayesiana (PyMC/NUTS) — **implementado** |
| `script_06_correlacao_tds_amonia_bod.py` | Correlação TDS↔Amônia e TDS↔BOD (bruta + destendenciada + defasada) — **implementado** |
| `script_07_analise_estrutura_serie.py` | Força de sazonalidade, estacionariedade ADF/KPSS, quebra estrutural Chow/Pettitt/CUSUM — **implementado** |
| `script_08_baselines.py` | Baselines naive, naive sazonal, ETS/Holt-Winters, Theta — **implementado** |
| `script_09_svr_gp.py` | SVR + Gaussian Process (kernel composto) — **implementado** |
| `script_10_detrend_arvore.py` | Tendência OLS + RF/XGBoost no resíduo (corrige a saturação de árvores) — **implementado** |
| `script_11_multivariado_cloreto.py` | SARIMAX(TDS, exog=Cloreto) — **implementado** |
| `script_12_hibrido_arima_prophet.py` | Ensemble SARIMA+Prophet — **implementado** |
| `script_13_deep_learning.py` | LSTM leve (PyTorch, CPU) — **implementado** |
| `script_14_diagnostico_residuos.py` | Diagnóstico de resíduos (Ljung-Box/Shapiro-Wilk/ARCH) dos candidatos mais fortes — **implementado** |
| `script_15_sintese_final.py` | Tabela consolidada final + gráfico dos finalistas — **implementado** |

**Status atual: projeto completo.** `script_00` a `script_15` implementados e validados — 21 métodos de previsão (10 originais + 4 baselines obrigatórios + 7 adicionais), diagnóstico de estrutura da série, análise de correlação, diagnóstico de resíduos dos candidatos mais fortes, e síntese final embasada na literatura (os quatro objetivos do projeto endereçados). Todo método de previsão reporta MASE, sMAPE, CV expansiva de 5 folds e backtest de origem móvel (`validacao_utils.py`), não só um holdout único de 24 meses.

**Achados notáveis:** o **baseline naive tem o menor MASE de toda a bateria de 21 métodos** no holdout de 24 meses (0,44), com o **Detrend+RF muito próximo** (0,44) — e, ao contrário do Random Forest original, a previsão de longo prazo do Detrend+RF cresce de forma monotônica em vez de saturar (743,5 → 762,2 → 780,9 mg/L em +10/+15/+20a), corrigindo diretamente a limitação de extrapolação de árvores já documentada. O **SVR é o primeiro método de toda a bateria com R² positivo em holdout** (0,04). O **Gaussian Process foi o pior desempenho** (MASE 2,03) — o ajuste por máxima verossimilhança marginal convergiu para um length-scale curto e reverte à média em vez de extrapolar, uma limitação conhecida de GP, reportada tal como obtida, sem reajuste para "ficar bonita". O **Cloreto como regressor exógeno do SARIMAX** tem coeficiente significativo mas não melhora de forma relevante o RMSE/MASE de holdout sobre o SARIMA univariado. O **híbrido SARIMA+Prophet** supera os dois componentes isolados no RMSE de holdout. O **LSTM não venceu o baseline naive** (MASE 0,69 vs. 0,44), confirmando o precedente da literatura de que métodos clássicos/boosting tendem a vencer deep learning leve em séries ambientais mensais curtas — testado e reportado como não-vencedor, não omitido. Ver `Artigo/src/resultados.tex` para a discussão completa.

**GPU:** confirmada funcionando nesta máquina com a RTX 4060 Ti — `xgb.XGBRegressor(tree_method="hist", device="cuda")` treina normalmente. O LightGBM instalado via pip, porém, **não** vem com suporte a GPU compilado (`device="gpu"` gera o erro "GPU Tree Learner was not enabled in this build"); roda em CPU como fallback aceito, exatamente como o plano já previa.

## Como rodar

Use um ambiente virtual dedicado (`.venv/`, fora do controle de versão) para manter as dependências deste projeto isoladas do resto da máquina:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python script_00_preprocessamento.py
python script_01_mann_kendall_theilsen.py
python script_02_arima_sarima.py
python script_03_random_forest_gridsearch.py
python script_04_xgboost_lightgbm.py
python script_05_prophet_bayesiano.py
python script_06_correlacao_tds_amonia_bod.py
python script_07_analise_estrutura_serie.py
python script_08_baselines.py
python script_09_svr_gp.py
python script_10_detrend_arvore.py
python script_11_multivariado_cloreto.py
python script_12_hibrido_arima_prophet.py
python script_13_deep_learning.py
python script_14_diagnostico_residuos.py
python script_15_sintese_final.py
```

`script_00` gera `dataset_canonico_bod_mdl2.csv`, `dataset_canonico_bod_zero.csv` e `dataset_canonico_bod_ros.csv` na raiz do projeto. `script_01` ajusta a tendência de TDS (Mann-Kendall/Sen, Theil-Sen, OLS); `script_02` ajusta STL+tendência e SARIMA (ordem escolhida por busca em grade por AIC); `script_03` ajusta um Random Forest (GridSearchCV + TimeSeriesSplit) com previsão recursiva multi-passo; `script_04` ajusta XGBoost e LightGBM da mesma forma, com regressão quantílica (alpha=0,05/0,95) para o IC90%; `script_05` ajusta Prophet e uma regressão bayesiana linear (PyMC/NUTS — nesta máquina não há compilador C++, então o PyTensor cai para o fallback Python puro e a amostragem leva alguns minutos); `script_06` calcula as correlações TDS↔Amônia/BOD; `script_07` roda o diagnóstico estrutural (força de sazonalidade, ADF/KPSS, Chow/Pettitt/CUSUM) que embasa se termos sazonais valem a pena; `script_08` ajusta os 4 baselines obrigatórios. Todo script de método (01-05, 08) também roda a CV expansiva de 5 folds e o backtest de origem móvel (+3/+5 anos) do `validacao_utils.py`, gravando colunas de MASE/sMAPE/CV/backtest junto das métricas de holdout já existentes em `resultados_comparacao.csv`/`.json`, além de regenerar sua figura em `Artigo/images/`.

## Rastreamento de experimentos (MLflow)

As execuções passam a ser rastreadas localmente com [MLflow](https://mlflow.org/) — sem nuvem, sem conta. O metadado de rastreamento fica num SQLite local (`mlflow.db`) e os artefatos (figuras etc.) em `mlruns/`, ambos fora do controle de versão. `utils/experiment_tracking.py` traz os utilitários compartilhados que cada script usa: `iniciar_run()` abre uma run e loga params/seed/janela de treino-holdout/tempo de execução; `logar_metricas()`/`logar_linha_resultado()` logam métricas; `logar_artefatos()` loga arquivos; `exportar_para_resultados_csv()` exporta runs escolhidas de volta para `resultados_comparacao.csv`, substituindo só a linha daquele método. O `resultados_comparacao.csv` continua sendo a fonte enxuta usada pelo notebook e pelo artigo — o MLflow é o histórico mais completo ao lado dele (inclusive tentativas descartadas), conforme `plano_projeto_TDS.md` §4.3.

`script_01` a `script_05`, `script_07` e `script_08` agora abrem uma run de MLflow por método (ou passo de diagnóstico). Para inspecionar as runs:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Estrutura do projeto

```
├── TDS.csv / Chloride.csv / Ammonia.csv / BOD.csv   # exportações brutas do eSMR (uma aba por parâmetro)
├── script_00_preprocessamento.py                     # construtor do dataset canônico
├── dataset_canonico_bod_mdl2.csv / _bod_zero.csv / _bod_ros.csv  # datasets mensais canônicos (gerados)
├── validacao_utils.py                                 # framework de MASE/sMAPE/CV/backtest, usado por 01-05/08
├── utils/experiment_tracking.py                       # utilitários de rastreamento MLflow, usados por todos os scripts
├── diagnostico_serie_resultados.csv / .json            # saida do diagnostico estrutural do script_07 (gerado)
├── notebook.ipynb                                     # notebook único do projeto (pré-processamento, EDA, métodos) — didático, cita GLOSSARIO.md/DECISOES.md o tempo todo
├── Artigo/                                            # artigo científico em LaTeX (template.tex é a raiz compilável)
│   └── DECISOES.md                                    # registro de decisões estilo ADR — o *porquê* de cada escolha metodológica
├── GLOSSARIO.md                                       # todo termo técnico do projeto, explicado (domínios sanitário/regulatório/estatístico)
├── ESCOPO_E_LIMITACOES.md                             # fronteira explícita do estudo: dentro do escopo, fora por escolha, fora por indisponibilidade, fragilidades conhecidas
├── plano_projeto_TDS.md                               # plano de execução, fonte da verdade
├── resultados_comparacao.csv / .json                  # resultados comparativos (21 métodos)
├── diagnostico_residuos_resultados.csv / .json         # saída do diagnóstico de resíduos do script_14 (gerado)
└── tabela_sintese_final.csv                            # tabela consolidada do script_15 (gerado)
```

## Resultados

**Tendência de TDS (script_01, estatística clássica):** os três métodos concordam numa tendência de alta estatisticamente significativa de 3,7–3,9 mg/L/ano (p < 0,01). Ver `Artigo/src/resultados.tex` e `notebook.ipynb` §3.a para a tabela completa, a figura de previsão e a discussão (incluindo a limitação honesta de que uma tendência linear simples performa pior no holdout de 24 meses — R² negativo — mesmo identificando corretamente a direção de longo prazo).

**STL + SARIMA (script_02):** a tendência dessazonalizada do STL (2,9 mg/L/ano) é consistente com a §3.a. A melhor ordem SARIMA por AIC não tem drift explícito, então sua tendência implícita (10,4 mg/L/ano, derivada do caminho previsto) é bem mais acentuada, com IC90% já incluindo valores negativos a partir de +15 anos — a fragilidade esperada e já documentada de extrapolar o SARIMA muito além dos ~15 anos de histórico. Ver `Artigo/src/resultados.tex` e `notebook.ipynb` §3.b.

**Random Forest (script_03):** melhor RMSE em holdout até aqui (41,0, contra 49–51 dos métodos clássicos), mas a previsão de longo prazo **satura** exatamente como o plano previa: +10, +15 e +20 anos convergem para o mesmo valor (704,3 mg/L), e a tendência implícita nos primeiros 10 anos chega a ficar levemente negativa — árvores não extrapolam além do range de valores visto no treino. Reportado explicitamente, não escondido. Ver `Artigo/src/resultados.tex` e `notebook.ipynb` §3.c.

**XGBoost + LightGBM (script_04):** mesma limitação estrutural do Random Forest — as duas tendências implícitas são negativas (-0,91 e -0,51 mg/L/ano), o oposto da tendência real de alta. O XGBoost ainda mostra oscilação não-monotônica entre horizontes (649,6 → 717,6 → 649,6 mg/L em +10/+15/+20 anos), um artefato de boosting quando as features saem do range de treino. Juntos, os três métodos baseados em árvore constroem um argumento empírico (não só teórico) contra depender só de árvores para extrapolar tendência de longo prazo neste projeto. Ver `Artigo/src/resultados.tex` e `notebook.ipynb` §3.c.

**Prophet + regressão bayesiana (script_05):** a regressão bayesiana confirma a tendência clássica (3,74 mg/L/ano, 99,88% de probabilidade posterior de tendência positiva) com um IC90% que cresce suavemente — o comportamento de "incerteza honesta" que motivou escolher esse método. O Prophet surpreende: detecta corretamente a mesma tendência histórica (3,81 mg/L/ano, p<0,0001) pela própria decomposição, mas sua extrapolação **decresce** com o horizonte (636,9 → 604,8 mg/L de +10 a +20 anos) — os changepoints automáticos capturaram uma desaceleração recente local e extrapolam essa inclinação, não a média de 15 anos. Reportado como achado genuíno, não maquiado. Ver `Artigo/src/resultados.tex` §Síntese comparativa para a tabela completa dos 10 métodos e a discussão.

**Conclusão dos 10 métodos:** os cinco métodos com ajuste global linear/estatístico (Mann-Kendall/Sen, Theil-Sen, OLS, STL+tendência, regressão bayesiana) convergem numa tendência de alta consistente e estatisticamente significativa de 2,9–3,9 mg/L/ano (p<0,01). Os métodos baseados em árvore falham em extrapolá-la; SARIMA e Prophet divergem em direções opostas. Nenhum método tem R² positivo em holdout — a evidência mais forte deste projeto é a **convergência** dos métodos estatísticos/bayesiano, não a previsão pontual de um único modelo.

**Diagnóstico estrutural (script_07):** sazonalidade fraca (Fs=0,25, abaixo do limiar de referência 0,64 da literatura) — não assumida por padrão, testada. ADF rejeita a hipótese de raiz unitária e KPSS não rejeita estacionariedade, ambos compatíveis com um processo estacionário em torno de tendência (trend-stationary), não uma caminhada aleatória. Chow (breakpoint ~2012, coincidindo com a troca de código EFF-001→EFF-001A), Pettitt (mudança detectada em 2014-04, dentro da janela de seca da Califórnia 2012-2016) e CUSUM confirmam que a série não é homogênea ao longo do período — reforça a cautela já existente sobre extrapolar muito além do histórico de treino.

**Framework de validação honesta + baselines (script_08, `validacao_utils.py`):** todo método (01-05, 08) agora reporta MASE, sMAPE, CV expansiva de 5 folds e backtest de origem móvel (+3/+5 anos), além do holdout de 24 meses original — não mais um único split treino/teste. Contra os 4 baselines obrigatórios (naive, naive sazonal, ETS/Holt-Winters, Theta), o **baseline naive tem o menor MASE em holdout de toda a bateria de 14 métodos** (0,44). Isso não invalida os métodos focados em tendência — a previsão do naive é uma linha reta, sem captar tendência de longo prazo alguma — mas é um achado genuíno e reportado: nas flutuações de curto prazo desta série, nenhum método (sofisticado ou não) supera de forma confiável "nada muda".

**Diagnóstico de resíduos (script_14):** Ljung-Box, Shapiro-Wilk e ARCH nos resíduos in-sample dos 5 candidatos mais fortes (OLS, regressão bayesiana, Detrend+RF, SARIMA, híbrido SARIMA+Prophet) mostram que **o Detrend+RF é o único sem autocorrelação residual nem heterocedasticidade condicional detectável** — só falha o teste de normalidade (caudas mais pesadas, comum em árvores). Os quatro métodos com forma funcional linear/estocástica explícita falham em pelo menos 2 dos 3 testes.

**Comparação com a literatura:** Schwabe et al. (2020, 34 estações do sul da Califórnia, 2013-2017) e Wolfand et al. (2022, mesma bacia do rio Los Angeles onde a LAGWRP descarrega) encontram a mesma direção de efeito (conservação/reúso de água → maior salinidade/TDS) identificada de forma independente neste projeto. A comparação é deliberadamente qualitativa: o texto completo de nenhum dos dois artigos foi acessível nesta sessão (ambos pagos) — nenhuma magnitude numérica é reproduzida sem verificação direta, só a direção do efeito, confirmada via fontes secundárias genuinamente acessadas (nota institucional, resumo de sociedade profissional), não inventada a partir de um resumo de busca. Ver `Artigo/src/trabalhos-relacionados.tex` e `Artigo/src/resultados.tex` §Comparação com a literatura.

**Síntese final (script_15):** três finalistas complementares recomendados (não um único vencedor, pelo critério de comparação já definido no projeto) — **regressão bayesiana** (incerteza honesta, crescimento suave do IC), **Detrend+RF** (melhor MASE de holdout entre os que captam tendência + resíduos mais limpos) e **híbrido SARIMA+Prophet** (melhor RMSE de holdout entre os métodos de série temporal, IC90 mais largo/cauteloso). Os três convergem para ~760-800 mg/L em +20 anos apesar de mecanismos de extrapolação completamente diferentes — essa convergência, não a previsão pontual de um único modelo, é a evidência mais forte que este projeto produz.

A bateria de 21 métodos, o diagnóstico estrutural, a análise de correlação, o diagnóstico de resíduos e a interpretação à luz da literatura estão completos — os quatro objetivos do projeto endereçados. `dataset_canonico_bod_ros.csv`, `diagnostico_residuos_resultados.csv/json` e `tabela_sintese_final.csv` são saídas adicionais geradas nesta última fase.

## Tratamento de dados robusto (em andamento — aguardando decisão)

Conforme `prompt_tratamento_e_metodos.md`, antes de estender ainda mais a bateria de métodos, dois passos de tratamento de dados foram executados:

**Reconstrução da vazão (`script_16_reconstrucao_vazao.py`):** o dataset traz o mesmo parâmetro em `mg/L` e `lb/day`, relacionados por `lb/day = mg/L × vazão(MGD) × 8,34`. Isso permite reconstruir a vazão do efluente, que não está explícita no dataset. Validado de duas formas: plausibilidade contra a capacidade nominal de 20 MGD da planta, e consistência cruzada entre parâmetros (a vazão derivada independentemente de TDS, Cloreto, Amônia e BOD — medidos na mesma amostra física — deve coincidir se o pareamento for real). **Resultado: a identidade se sustenta** — a vazão derivada de TDS correlaciona 0,997-0,998 com Cloreto/Amônia (0,87 com BOD, mais ruidoso mas ainda forte), com média de ~9,5 MGD (~47% da capacidade nominal), tudo plausível. Isso habilita os métodos WRTDS/balanço de massa/cenários para uma fase futura, pendente de aprovação.

**Matriz de 9 testes de sensibilidade no tratamento de dados (`script_17_matriz_sensibilidade.py`):** rodada ANTES de fixar qualquer tratamento como padrão, cada variante logada com suas próprias métricas no MLflow. **Achados que qualificam a alegação central do projeto** (tendência de alta de TDS estatisticamente significativa): (1) a tendência cai de 3,91 mg/L/ano (p=0,0056, série completa) para 0,84 mg/L/ano (p=0,59, **não significativo**) quando restrita ao período só EFF-001A (2012-2026, 170/182 meses) — os 12 meses iniciais sob EFF-001 têm peso desproporcional; (2) 3 das 4 transições de MDL/método coincidem com mudança estatisticamente significativa no nível médio de TDS; (3) nenhuma das 4 variantes de agregação anual (15 pontos) atinge significância (p 0,30-0,44); (4) o p-valor muda de significativo (0,0056) para **não significativo** sob 2 das 4 correções de autocorrelação testadas (Hamed-Rao p=0,182; pre-whitening p=0,417), continuando significativo nas outras duas (trend-free pre-whitening p=0,0001; Seasonal Kendall p=0,0038). Contrabalançando: a reagregação das amostras brutas bate exatamente com o "Monthly Average" pronto, a tendência é estável com/sem remoção de outliers (3,6-3,9 mg/L/ano, todas p<0,01), não há meses faltantes, e a escala log dá o mesmo p-valor da escala bruta, como esperado (Kendall's tau é invariante a transformação monotônica). **Leitura líquida: a tendência de alta não é um artefato óbvio de outliers ou reagregação, mas é sensível à transição de código de local, a mudanças de MDL, e à correção de autocorrelação — três sinais convergentes de que o p-valor mensal ingênuo pode superestimar a confiança.** Ver `matriz_sensibilidade_resultados.csv` e `notebook.ipynb` §6 para a tabela completa.

**Investigação de acompanhamento — a "quebra" EFF-001→EFF-001A não é artefato; a série é cíclica, não monotônica.** Uma regressão OLS com termo de degrau (isolando a transição de código de local de uma tendência linear no período completo) encontrou um salto de nível aparente grande e significativo (+137 mg/L, p<0,001) e nenhuma tendência linear residual significativa (0,42 mg/L/ano, p=0,75) — mas a inspeção ponto a ponto mostra que a transição em si é contínua (580→598 mg/L de um mês para o outro, mesmo método analítico, mesmo MDL, mesmas coordenadas). O "degrau" é um artefato de ajustar uma reta única + um salto único a uma série que na verdade se move por regimes: o TDS sobe de 563 para 808 mg/L (2011-2015, coincidindo com a seca da Califórnia de 2012-2016), cai para 636 mg/L (2019), sobe de novo para 768 mg/L (2022, segunda seca), e depois recua. A vazão reconstruída (`script_16`) correlaciona com o TDS no sentido esperado (r anual = −0,55, p=0,027), mas não acompanha totalmente o formato fino do ciclo (a vazão ficou estável durante a queda de TDS de 2016-2017) — consistente com evidência independente da literatura (SCSC/DBS&A 2018) de que **o TDS da água de origem, não a conservação local, explica ~88% da variabilidade do TDS de influente** em plantas próximas do Sul da Califórnia, variável que este dataset não contém. Raciocínio e evidência completos em `Artigo/DECISOES.md` (D-13, D-14, D-29–D-31).

**Teste do ciclo de seca (`script_18_pdsi_regimes.py`) — o reenquadramento cíclico agora está confirmado empiricamente, não só plausível visualmente.** Em vez de confiar só no formato da própria série de TDS, o padrão cíclico foi testado contra uma variável externa e independente: o Índice de Severidade de Seca de Palmer (PDSI) mensal do NOAA — o mesmo índice climático usado pelo estudo SCSC/DBS&A (2018) para explicar TDS em 26 estações do Sul da Califórnia. Três séries de PDSI foram testadas (Califórnia estadual; divisão climática de Los Angeles; divisão de Sacramento, bacia de origem do State Water Project), com defasagens de 0-36 meses e p-valores corrigidos por graus de liberdade efetivos sob autocorrelação serial (Pyper & Peterman, 1998). Quatro resultados convergentes: (1) a correlação cruzada bruta é forte e significativa mesmo após a correção de DOF (r=−0,53 a −0,65 em defasagem de 3-4 meses, n efetivo ≈ 22-30 de ~180 nominais); (2) changepoints detectados só no PDSI — cegos às datas do TDS — caem a poucos meses das quatro viradas de regime observadas (2012, 2015, 2019, 2022); (3) a decomposição LMG de importância relativa (`TDS ~ PDSI defasado + vazão reconstruída`) atribui 68-79% da importância ao PDSI nas três séries, mesma ordem de grandeza do benchmark do SCSC (~88% água de origem); (4) o coeficiente do PDSI continua altamente significativo (p<0,0001) mesmo controlando por regime. **Ressalva honesta:** a correlação destendenciada (mês a mês) é bem mais fraca e muda de sinal (r=+0,15 a +0,19) — a seca explica principalmente o *nível* de cada regime, não sua oscilação fina. Desfecho declarado (dos três definidos a priori no protocolo do teste): **o PDSI explica bem os ciclos** — D-14 agora está confirmado, não só proposto. Evidência completa em `Artigo/DECISOES.md` D-37; séries brutas de PDSI e saídas do script em `pdsi_*.csv`.

**Status:** o Passo 1 da Etapa 3 ampliada (este teste de seca) está pronto e confirma o reenquadramento. Os demais métodos da bateria ampliada (WRTDS, balanço de massa, cenários, GAM etc., conforme `prompt_tratamento_e_metodos.md`) ainda não começaram, e serão construídos em torno do padrão de seca/regime, não de uma tendência monotônica. Toda decisão, alternativa considerada e evidência de apoio está registrada em **[`Artigo/DECISOES.md`](Artigo/DECISOES.md)**, um log estilo ADR mantido continuamente junto com o código, junto com **[`GLOSSARIO.md`](GLOSSARIO.md)** (todo termo técnico explicado) e **[`ESCOPO_E_LIMITACOES.md`](ESCOPO_E_LIMITACOES.md)** (fronteiras do estudo e fragilidades conhecidas). Histórico completo de commits e código-fonte reproduzível em **https://github.com/igorfnogueira/projeto-aplicado**.

## Referências

Referência âncora principal: Schwabe et al., *Nature Sustainability* (2020), sobre o aumento da salinidade em esgoto ligado a práticas de conservação de água (indicada pelo professor). Wolfand et al., *ACS ES&T Water* (2022), sobre a mesma bacia do rio Los Angeles. Antweiler e Taylor, *Environmental Science & Technology* (2008), para a técnica ROS/Helsel usada no `script_00b`. Entradas completas em `Artigo/refs.bib`; demais fontes (não verificadas/inacessíveis) listadas em `plano_projeto_TDS.md` (§6) e `material_apoio_referencias.md`.
