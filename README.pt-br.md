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

**Status atual: projeto completo.** `script_00` a `script_15` implementados e validados — 21 métodos de previsão (10 originais + 4 baselines obrigatórios + 7 adicionais), diagnóstico de estrutura da série, análise de correlação, diagnóstico de resíduos dos candidatos mais fortes, e síntese final embasada na literatura (os quatro objetivos do projeto endereçados). Todo método de previsão reporta MASE, sMAPE, CV expansiva de 5 folds e backtest de origem móvel (`utils/validacao_utils.py`), não só um holdout único de 24 meses.

**Achados notáveis:** o **baseline naive tem o menor MASE de toda a bateria de 21 métodos** no holdout de 24 meses (0,44), com o **Detrend+RF muito próximo** (0,44) — e, ao contrário do Random Forest original, a previsão de longo prazo do Detrend+RF cresce de forma monotônica em vez de saturar (743,5 → 762,2 → 780,9 mg/L em +10/+15/+20a), corrigindo diretamente a limitação de extrapolação de árvores já documentada. O **SVR é o primeiro método de toda a bateria com R² positivo em holdout** (0,04). O **Gaussian Process foi o pior desempenho** (MASE 2,03) — o ajuste por máxima verossimilhança marginal convergiu para um length-scale curto e reverte à média em vez de extrapolar, uma limitação conhecida de GP, reportada tal como obtida, sem reajuste para "ficar bonita". O **Cloreto como regressor exógeno do SARIMAX** tem coeficiente significativo mas não melhora de forma relevante o RMSE/MASE de holdout sobre o SARIMA univariado. O **híbrido SARIMA+Prophet** supera os dois componentes isolados no RMSE de holdout. O **LSTM não venceu o baseline naive** (MASE 0,69 vs. 0,44), confirmando o precedente da literatura de que métodos clássicos/boosting tendem a vencer deep learning leve em séries ambientais mensais curtas — testado e reportado como não-vencedor, não omitido. Ver `results/resultados_comparacao.csv`, `results/figures/` e `notebooks/notebook.ipynb` para a discussão completa.

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
python scripts/script_00_preprocessamento.py
python scripts/script_01_mann_kendall_theilsen.py
python scripts/script_02_arima_sarima.py
python scripts/script_03_random_forest_gridsearch.py
python scripts/script_04_xgboost_lightgbm.py
python scripts/script_05_prophet_bayesiano.py
python scripts/script_06_correlacao_tds_amonia_bod.py
python scripts/script_07_analise_estrutura_serie.py
python scripts/script_08_baselines.py
python scripts/script_09_svr_gp.py
python scripts/script_10_detrend_arvore.py
python scripts/script_11_multivariado_cloreto.py
python scripts/script_12_hibrido_arima_prophet.py
python scripts/script_13_deep_learning.py
python scripts/script_14_diagnostico_residuos.py
python scripts/script_15_sintese_final.py

# Etapa 3 -- tratamento de dados robusto e bateria ampliada (ver secao abaixo)
python scripts/script_16_reconstrucao_vazao.py
python scripts/script_17_matriz_sensibilidade.py
python scripts/script_18_pdsi_regimes.py
python scripts/script_19_wrtds.py
python scripts/script_20_balanco_massa.py
python scripts/script_21_cenarios.py
python scripts/script_22_espaco_estados.py
python scripts/script_23_gam.py
python scripts/script_24_regressao_quantilica.py
python scripts/script_25_intervencao_arimax.py
python scripts/script_26_modelos_fundacionais.py
python scripts/script_27_cenario_climatico_caladapt.py
python scripts/script_28_ladwp_tds_origem.py
```

`script_00` gera `dataset_canonico_bod_mdl2.csv`, `dataset_canonico_bod_zero.csv` e `dataset_canonico_bod_ros.csv` em `data/processed/`. `script_01` ajusta a tendência de TDS (Mann-Kendall/Sen, Theil-Sen, OLS); `script_02` ajusta STL+tendência e SARIMA (ordem escolhida por busca em grade por AIC); `script_03` ajusta um Random Forest (GridSearchCV + TimeSeriesSplit) com previsão recursiva multi-passo; `script_04` ajusta XGBoost e LightGBM da mesma forma, com regressão quantílica (alpha=0,05/0,95) para o IC90%; `script_05` ajusta Prophet e uma regressão bayesiana linear (PyMC/NUTS — nesta máquina não há compilador C++, então o PyTensor cai para o fallback Python puro e a amostragem leva alguns minutos); `script_06` calcula as correlações TDS↔Amônia/BOD; `script_07` roda o diagnóstico estrutural (força de sazonalidade, ADF/KPSS, Chow/Pettitt/CUSUM) que embasa se termos sazonais valem a pena; `script_08` ajusta os 4 baselines obrigatórios. Todo script de método (01-05, 08) também roda a CV expansiva de 5 folds e o backtest de origem móvel (+3/+5 anos) do `utils/validacao_utils.py`, gravando colunas de MASE/sMAPE/CV/backtest junto das métricas de holdout já existentes em `results/resultados_comparacao.csv`/`.json`, além de regenerar sua figura em `results/figures/`. `script_16` reconstrói a vazão do efluente; `script_17` roda a matriz de 9 testes de sensibilidade no tratamento de dados; `script_18` baixa e testa o índice de seca PDSI do NOAA contra os ciclos de TDS; `script_19`/`script_20`/`script_21` são WRTDS, balanço de massa e cenários climáticos — ver a seção "Tratamento de dados robusto e bateria ampliada" abaixo para os resultados de cada um.

## Rastreamento de experimentos (MLflow)

As execuções passam a ser rastreadas localmente com [MLflow](https://mlflow.org/) — sem nuvem, sem conta. O metadado de rastreamento fica num SQLite local (`mlflow.db`) e os artefatos (figuras etc.) em `mlruns/`, ambos fora do controle de versão. `utils/experiment_tracking.py` traz os utilitários compartilhados que cada script usa: `iniciar_run()` abre uma run e loga params/seed/janela de treino-holdout/tempo de execução; `logar_metricas()`/`logar_linha_resultado()` logam métricas; `logar_artefatos()` loga arquivos; `exportar_para_resultados_csv()` exporta runs escolhidas de volta para `results/resultados_comparacao.csv`, substituindo só a linha daquele método. O `results/resultados_comparacao.csv` continua sendo a fonte enxuta usada pelo notebook e pelo dashboard — o MLflow é o histórico mais completo ao lado dele (inclusive tentativas descartadas).

`script_01` a `script_05`, `script_07` e `script_08` agora abrem uma run de MLflow por método (ou passo de diagnóstico). Para inspecionar as runs:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Estrutura do projeto

```
├── data/
│   ├── raw/              # eSMR (TDS/Chloride/Ammonia/BOD.csv, xlsx), PDSI bruto, ETEs comparadoras
│   └── processed/        # datasets canônicos, vazão, séries PDSI, extratos LADWP
├── scripts/              # script_00 … script_30 (+ script_00b) — rodar: python scripts/script_XX_....py
├── utils/
│   ├── paths.py          # caminhos canônicos (raw/processed/result/figure)
│   ├── experiment_tracking.py
│   └── validacao_utils.py
├── results/
│   ├── resultados_comparacao.csv / .json
│   ├── *_resultados.* / tabela_sintese_final.csv / comparacao_pdsi_*
│   └── figures/          # PNGs gerados pelo pipeline
├── notebooks/            # notebook.ipynb didático
├── huggingface_space/    # dashboard Streamlit (cópias em data/ e images/)
├── README.md / README.pt-br.md / CLAUDE.md / requirements.txt
```

Material de apoio local (artigo LaTeX, plano de execução, prompts de processo, logs de decisão, PDFs) pode existir no disco, mas **não** faz parte do repositório público.

## Resultados

**Tendência de TDS (script_01, estatística clássica):** os três métodos concordam numa tendência de alta estatisticamente significativa de 3,7–3,9 mg/L/ano (p < 0,01). Ver `results/figures/tendencia-tds.png`, `results/resultados_comparacao.csv` e `notebooks/notebook.ipynb` para a tabela completa, a figura de previsão e a discussão (incluindo a limitação honesta de que uma tendência linear simples performa pior no holdout de 24 meses — R² negativo — mesmo identificando corretamente a direção de longo prazo).

**STL + SARIMA (script_02):** a tendência dessazonalizada do STL (2,9 mg/L/ano) é consistente com a §3.a. A melhor ordem SARIMA por AIC não tem drift explícito, então sua tendência implícita (10,4 mg/L/ano, derivada do caminho previsto) é bem mais acentuada, com IC90% já incluindo valores negativos a partir de +15 anos — a fragilidade esperada e já documentada de extrapolar o SARIMA muito além dos ~15 anos de histórico. Ver `results/figures/stl-sarima-tds.png`, `results/resultados_comparacao.csv` e `notebooks/notebook.ipynb`.

**Random Forest (script_03):** melhor RMSE em holdout até aqui (41,0, contra 49–51 dos métodos clássicos), mas a previsão de longo prazo **satura** exatamente como o plano previa: +10, +15 e +20 anos convergem para o mesmo valor (704,3 mg/L), e a tendência implícita nos primeiros 10 anos chega a ficar levemente negativa — árvores não extrapolam além do range de valores visto no treino. Reportado explicitamente, não escondido. Ver `results/figures/random-forest-tds.png`, `results/resultados_comparacao.csv` e `notebooks/notebook.ipynb`.

**XGBoost + LightGBM (script_04):** mesma limitação estrutural do Random Forest — as duas tendências implícitas são negativas (-0,91 e -0,51 mg/L/ano), o oposto da tendência real de alta. O XGBoost ainda mostra oscilação não-monotônica entre horizontes (649,6 → 717,6 → 649,6 mg/L em +10/+15/+20 anos), um artefato de boosting quando as features saem do range de treino. Juntos, os três métodos baseados em árvore constroem um argumento empírico (não só teórico) contra depender só de árvores para extrapolar tendência de longo prazo neste projeto. Ver `results/figures/xgboost-lightgbm-tds.png`, `results/resultados_comparacao.csv` e `notebooks/notebook.ipynb`.

**Prophet + regressão bayesiana (script_05):** a regressão bayesiana confirma a tendência clássica (3,74 mg/L/ano, 99,88% de probabilidade posterior de tendência positiva) com um IC90% que cresce suavemente — o comportamento de "incerteza honesta" que motivou escolher esse método. O Prophet surpreende: detecta corretamente a mesma tendência histórica (3,81 mg/L/ano, p<0,0001) pela própria decomposição, mas sua extrapolação **decresce** com o horizonte (636,9 → 604,8 mg/L de +10 a +20 anos) — os changepoints automáticos capturaram uma desaceleração recente local e extrapolam essa inclinação, não a média de 15 anos. Reportado como achado genuíno, não maquiado. Ver `results/tabela_sintese_final.csv`, `results/figures/sintese-final-finalistas.png` e `notebooks/notebook.ipynb` para a tabela completa e a discussão.

**Conclusão dos 10 métodos:** os cinco métodos com ajuste global linear/estatístico (Mann-Kendall/Sen, Theil-Sen, OLS, STL+tendência, regressão bayesiana) convergem numa tendência de alta consistente e estatisticamente significativa de 2,9–3,9 mg/L/ano (p<0,01). Os métodos baseados em árvore falham em extrapolá-la; SARIMA e Prophet divergem em direções opostas. Nenhum método tem R² positivo em holdout — a evidência mais forte deste projeto é a **convergência** dos métodos estatísticos/bayesiano, não a previsão pontual de um único modelo.

**Diagnóstico estrutural (script_07):** sazonalidade fraca (Fs=0,25, abaixo do limiar de referência 0,64 da literatura) — não assumida por padrão, testada. ADF rejeita a hipótese de raiz unitária e KPSS não rejeita estacionariedade, ambos compatíveis com um processo estacionário em torno de tendência (trend-stationary), não uma caminhada aleatória. Chow (breakpoint ~2012, coincidindo com a troca de código EFF-001→EFF-001A), Pettitt (mudança detectada em 2014-04, dentro da janela de seca da Califórnia 2012-2016) e CUSUM confirmam que a série não é homogênea ao longo do período — reforça a cautela já existente sobre extrapolar muito além do histórico de treino.

**Framework de validação honesta + baselines (script_08, `utils/validacao_utils.py`):** todo método (01-05, 08) agora reporta MASE, sMAPE, CV expansiva de 5 folds e backtest de origem móvel (+3/+5 anos), além do holdout de 24 meses original — não mais um único split treino/teste. Contra os 4 baselines obrigatórios (naive, naive sazonal, ETS/Holt-Winters, Theta), o **baseline naive tem o menor MASE em holdout de toda a bateria de 14 métodos** (0,44). Isso não invalida os métodos focados em tendência — a previsão do naive é uma linha reta, sem captar tendência de longo prazo alguma — mas é um achado genuíno e reportado: nas flutuações de curto prazo desta série, nenhum método (sofisticado ou não) supera de forma confiável "nada muda".

**Diagnóstico de resíduos (script_14):** Ljung-Box, Shapiro-Wilk e ARCH nos resíduos in-sample dos 5 candidatos mais fortes (OLS, regressão bayesiana, Detrend+RF, SARIMA, híbrido SARIMA+Prophet) mostram que **o Detrend+RF é o único sem autocorrelação residual nem heterocedasticidade condicional detectável** — só falha o teste de normalidade (caudas mais pesadas, comum em árvores). Os quatro métodos com forma funcional linear/estocástica explícita falham em pelo menos 2 dos 3 testes.

**Comparação com a literatura:** Schwabe et al. (2020, 34 estações do sul da Califórnia, 2013-2017) e Wolfand et al. (2022, mesma bacia do rio Los Angeles onde a LAGWRP descarrega) encontram a mesma direção de efeito (conservação/reúso de água → maior salinidade/TDS) identificada de forma independente neste projeto. A comparação é deliberadamente qualitativa: o texto completo de nenhum dos dois artigos foi acessível nesta sessão (ambos pagos) — nenhuma magnitude numérica é reproduzida sem verificação direta, só a direção do efeito, confirmada via fontes secundárias genuinamente acessadas (nota institucional, resumo de sociedade profissional), não inventada a partir de um resumo de busca. Ver `notebooks/notebook.ipynb` e `results/` para a síntese embasada na literatura.

**Síntese final (script_15):** três finalistas complementares recomendados (não um único vencedor, pelo critério de comparação já definido no projeto) — **regressão bayesiana** (incerteza honesta, crescimento suave do IC), **Detrend+RF** (melhor MASE de holdout entre os que captam tendência + resíduos mais limpos) e **híbrido SARIMA+Prophet** (melhor RMSE de holdout entre os métodos de série temporal, IC90 mais largo/cauteloso). Os três convergem para ~760-800 mg/L em +20 anos apesar de mecanismos de extrapolação completamente diferentes — essa convergência, não a previsão pontual de um único modelo, é a evidência mais forte que este projeto produz.

A bateria de 21 métodos, o diagnóstico estrutural, a análise de correlação, o diagnóstico de resíduos e a interpretação à luz da literatura estão completos — os quatro objetivos do projeto endereçados. `dataset_canonico_bod_ros.csv`, `diagnostico_residuos_resultados.csv/json` e `tabela_sintese_final.csv` são saídas adicionais geradas nesta última fase.

## Tratamento de dados robusto e bateria ampliada (Etapa 3)

Antes de estender ainda mais a bateria de métodos, dois passos de tratamento de dados foram executados:

**Reconstrução da vazão (`script_16_reconstrucao_vazao.py`):** o dataset traz o mesmo parâmetro em `mg/L` e `lb/day`, relacionados por `lb/day = mg/L × vazão(MGD) × 8,34`. Isso permite reconstruir a vazão do efluente, que não está explícita no dataset. Validado de duas formas: plausibilidade contra a capacidade nominal de 20 MGD da planta, e consistência cruzada entre parâmetros (a vazão derivada independentemente de TDS, Cloreto, Amônia e BOD — medidos na mesma amostra física — deve coincidir se o pareamento for real). **Resultado: a identidade se sustenta** — a vazão derivada de TDS correlaciona 0,997-0,998 com Cloreto/Amônia (0,87 com BOD, mais ruidoso mas ainda forte), com média de ~9,5 MGD (~47% da capacidade nominal), tudo plausível. Isso habilitou os métodos WRTDS, balanço de massa e cenários climáticos — todos implementados, ver abaixo.

**Matriz de 9 testes de sensibilidade no tratamento de dados (`script_17_matriz_sensibilidade.py`):** rodada ANTES de fixar qualquer tratamento como padrão, cada variante logada com suas próprias métricas no MLflow. **Achados que qualificam a alegação central do projeto** (tendência de alta de TDS estatisticamente significativa): (1) a tendência cai de 3,91 mg/L/ano (p=0,0056, série completa) para 0,84 mg/L/ano (p=0,59, **não significativo**) quando restrita ao período só EFF-001A (2012-2026, 170/182 meses) — os 12 meses iniciais sob EFF-001 têm peso desproporcional; (2) 3 das 4 transições de MDL/método coincidem com mudança estatisticamente significativa no nível médio de TDS; (3) nenhuma das 4 variantes de agregação anual (15 pontos) atinge significância (p 0,30-0,44); (4) o p-valor muda de significativo (0,0056) para **não significativo** sob 2 das 4 correções de autocorrelação testadas (Hamed-Rao p=0,182; pre-whitening p=0,417), continuando significativo nas outras duas (trend-free pre-whitening p=0,0001; Seasonal Kendall p=0,0038). Contrabalançando: a reagregação das amostras brutas bate exatamente com o "Monthly Average" pronto, a tendência é estável com/sem remoção de outliers (3,6-3,9 mg/L/ano, todas p<0,01), não há meses faltantes, e a escala log dá o mesmo p-valor da escala bruta, como esperado (Kendall's tau é invariante a transformação monotônica). **Leitura líquida: a tendência de alta não é um artefato óbvio de outliers ou reagregação, mas é sensível à transição de código de local, a mudanças de MDL, e à correção de autocorrelação — três sinais convergentes de que o p-valor mensal ingênuo pode superestimar a confiança.** Ver `matriz_sensibilidade_resultados.csv` e `notebook.ipynb` §6 para a tabela completa.

**Investigação de acompanhamento — a "quebra" EFF-001→EFF-001A não é artefato; a série é cíclica, não monotônica.** Uma regressão OLS com termo de degrau (isolando a transição de código de local de uma tendência linear no período completo) encontrou um salto de nível aparente grande e significativo (+137 mg/L, p<0,001) e nenhuma tendência linear residual significativa (0,42 mg/L/ano, p=0,75) — mas a inspeção ponto a ponto mostra que a transição em si é contínua (580→598 mg/L de um mês para o outro, mesmo método analítico, mesmo MDL, mesmas coordenadas). O "degrau" é um artefato de ajustar uma reta única + um salto único a uma série que na verdade se move por regimes: o TDS sobe de 563 para 808 mg/L (2011-2015, coincidindo com a seca da Califórnia de 2012-2016), cai para 636 mg/L (2019), sobe de novo para 768 mg/L (2022, segunda seca), e depois recua. A vazão reconstruída (`script_16`) correlaciona com o TDS no sentido esperado (r anual = −0,55, p=0,027), mas não acompanha totalmente o formato fino do ciclo (a vazão ficou estável durante a queda de TDS de 2016-2017) — consistente com evidência independente da literatura (SCSC/DBS&A 2018) de que **o TDS da água de origem, não a conservação local, explica ~88% da variabilidade do TDS de influente** em plantas próximas do Sul da Califórnia, variável que este dataset não contém. Raciocínio e evidência completos em `results/matriz_sensibilidade_resultados.csv`, `results/figures/` e nos scripts acima (IDs de decisão D-13, D-14, D-29–D-31).

**Teste do ciclo de seca (`script_18_pdsi_regimes.py`) — o reenquadramento cíclico agora está confirmado empiricamente, não só plausível visualmente.** Em vez de confiar só no formato da própria série de TDS, o padrão cíclico foi testado contra uma variável externa e independente: o Índice de Severidade de Seca de Palmer (PDSI) mensal do NOAA — o mesmo índice climático usado pelo estudo SCSC/DBS&A (2018) para explicar TDS em 26 estações do Sul da Califórnia. Três séries de PDSI foram testadas (Califórnia estadual; divisão climática de Los Angeles; divisão de Sacramento, bacia de origem do State Water Project), com defasagens de 0-36 meses e p-valores corrigidos por graus de liberdade efetivos sob autocorrelação serial (Pyper & Peterman, 1998). Quatro resultados convergentes: (1) a correlação cruzada bruta é forte e significativa mesmo após a correção de DOF (r=−0,53 a −0,65 em defasagem de 3-4 meses, n efetivo ≈ 22-30 de ~180 nominais); (2) changepoints detectados só no PDSI — cegos às datas do TDS — caem a poucos meses das quatro viradas de regime observadas (2012, 2015, 2019, 2022); (3) a decomposição LMG de importância relativa (`TDS ~ PDSI defasado + vazão reconstruída`) atribui 68-79% da importância ao PDSI nas três séries, mesma ordem de grandeza do benchmark do SCSC (~88% água de origem); (4) o coeficiente do PDSI continua altamente significativo (p<0,0001) mesmo controlando por regime. **Ressalva honesta:** a correlação destendenciada (mês a mês) é bem mais fraca e muda de sinal (r=+0,15 a +0,19) — a seca explica principalmente o *nível* de cada regime, não sua oscilação fina. Desfecho declarado (dos três definidos a priori no protocolo do teste): **o PDSI explica bem os ciclos** — D-14 agora está confirmado, não só proposto. Evidência completa em `results/pdsi_regimes_resultados.csv` / `.json` e `data/processed/pdsi_*.csv` (ID de decisão D-37).

**WRTDS — normalização por vazão (`script_19_wrtds.py`):** confirmado o padrão cíclico, a pergunta virou "há tendência *por baixo* dos ciclos, depois de descontar a vazão?". Implementação própria (não o pacote R `EGRET`, sem equivalente Python maduro): regressão ponderada localmente (kernel tricúbico em tempo/log-vazão/sazonalidade) + flow-normalização. **Resultado: a tendência bruta (+0,58%/ano, p=0,0056) cai para −0,13%/ano (p=0,064, não significativa)** depois de descontar a vazão — quase toda a tendência aparente é efeito de vazão. Checagem de circularidade obrigatória (vazão derivada de Cloreto, independente do TDS) confirma: diferença de só 0,024 pontos percentuais/ano frente à versão com vazão de TDS. Ver `results/wrtds_resultados.csv` / `.json` e `results/figures/wrtds-*.png` (ID de decisão D-39).

**Balanço de massa (`script_20_balanco_massa.py`):** modela carga de sal (lb/dia) e vazão (MGD) separadamente e deriva `TDS = carga ÷ (vazão × 8,34)`. **Carga de sal caiu −3,20%/ano e vazão caiu −3,85%/ano (p<0,0001 nos dois) — confirma diluição, não mais sal entrando no sistema.** Validação histórica não-circular (vazão de Cloreto) tem R²=0,94; a checagem de tautologia (vazão do próprio TDS) dá R²=1,000000 exato, como esperado por identidade algébrica — reportado como checagem, não como resultado. Achado negativo registrado: extrapolar carga e vazão linearmente por 20 anos cruza vazão fisicamente implausível (negativa em +20a) — motivo direto da próxima etapa. Ver `results/balanco_massa_resultados.csv` / `.json` e `results/figures/balanco-massa-*.png` (ID de decisão D-40).

**Cenários climáticos (`script_21_cenarios.py`):** substitui a extrapolação linear implausível por uma projeção condicional via Monte Carlo (AR(1) no PDSI histórico de 1895-2026 + regressão TDS~PDSI). Quatro cenários (seco/normal/úmido/agravamento climático), faixas fisicamente plausíveis em +20 anos: seco 718 [588, 846] mg/L; agravamento climático 714 [591, 842]; normal 658 [529, 783]; úmido 594 [462, 721]. **Não há um número único para 2046** — a faixa condicionada ao clima é a resposta honesta que os dados permitem. Ver `results/cenarios_resultados.csv` / `.json` e `results/figures/cenarios-pdsi-*.png` (ID de decisão D-41).

**A seção 3.f do plano original está agora 100% implementada (9/9 métodos, 35 no total da bateria) — os 5 métodos restantes (`script_22`-`script_26`) reforçam, de ângulos independentes, que não há tendência residual clara além do efeito de vazão/regime.** Espaço de estados (`script_22`, D-45): a variância estimada do estado de tendência é ~0 — mesmo com liberdade para variar, o modelo não encontrou evidência de tendência genuinamente variável no tempo. GAM (`script_23`, D-46): a suavização por GCV sem restrição escolhe um lambda que extrapola de forma explosiva (1.910 mg/L em +10a) — patologia conhecida de P-splines, corrigida com um piso de suavização declarado (resultado plausível: 576,5 mg/L em +10a). Regressão quantílica (`script_24`, D-47): na direção **oposta** à hipótese de trabalho, a inclinação do Q90 (picos) é negativa (−3,05 mg/L/ano, p=0,026) enquanto Q10/Q50 sobem — os picos não estão subindo mais rápido que a mediana, estão caindo, e os três quantis cruzam ao extrapolar (limitação reportada com honestidade, não reordenada silenciosamente). Análise de intervenção (`script_25`, D-48): controlando pela ordem de conservação de 2015, o coeficiente isolado da seca de 2012-2016 não é significativo (p=0,206) — o efeito da seca provavelmente opera pelo canal de vazão (D-39/D-40), não como salto de nível isolado; o termo sazonal MA do modelo também mostrou instabilidade de estimação, reportada como tal. Modelo fundacional zero-shot (`script_26`, D-49): o Chronos-Bolt-Small, testado contra uma expectativa **declarada antes de rodar** de não superar os métodos clássicos, confirmou essa expectativa (MASE 0,59 vs. 0,44 do naive) — e sua largura de intervalo **diminui** com o horizonte (o oposto de todos os outros métodos), propriedade conhecida de cabeças de previsão diretas multi-horizonte, não um bug.

**Um 5º cenário, fundamentado em projeção climática real, não em histórico (`script_27_cenario_climatico_caladapt.py`, D-51).** Os 4 cenários de `script_21` reamostram a distribuição *histórica* do PDSI. Pesquisa dedicada não achou um substituto "pronto" com o mesmo escopo, mas a API pública do Cal-Adapt (`cal-adapt.org`, projeções LOCA-*downscaled*, RCP 8.5) permitiu construir um 5º cenário real: extraímos o pixel de precipitação da LAGWRP em dois rasters reais do Cal-Adapt (histórico 1961-1990 vs. RCP 8.5 2035-2064, ensemble de 32 modelos) — mudança projetada de apenas −2,3%. Convertemos essa mudança num "PDSI-alvo implícito" (−0,69) via calibração empírica própria (regressão real precipitação↔PDSI da Califórnia, R²=0,64) — **não é um PDSI oficial projetado**, é uma calibração declarada como tal. Resultado: 662-670 mg/L nos três horizontes, entre os cenários "normal" e "seco" já existentes — plausível, sem contradizer nem repetir o que já tínhamos.

**TDS real da água de origem via 21 anos de relatórios da LADWP (`script_28_ladwp_tds_origem.py`, D-54).** A lacuna de dado mais crítica do projeto (D-30 — sem série de TDS da água de origem, só o proxy indireto do PDSI) foi parcialmente preenchida com dado primário real: 21 relatórios anuais de qualidade da água da LADWP (2004-2024), cada um publicando o TDS médio por fonte de abastecimento (LA Aqueduct, poços locais, e as três ETAs da MWD — Weymouth, Diemer, Jensen) e o percentual de mistura de cada ano. Construída uma série de TDS de origem ponderado e comparada ao TDS anual de efluente da LAGWRP (14 anos de sobreposição, 2011-2024): **r=0,912 (p=0,000005)** — mais forte que a correlação já obtida com o PDSI (D-37, LMG 67-79%). Todos os 21 anos (100%, não uma amostra) foram conferidos manualmente célula a célula contra os PDFs originais, sem nenhuma discrepância. Limitações declaradas: o peso da MWD é uma média simples das suas 3 estações (o peso real de cada uma não é publicado em nenhum dos 21 relatórios); a série é anual, não mensal (os relatórios não publicam detalhamento mensal); cobre só o lado Los Angeles (LADWP) da área de serviço da LAGWRP, não o lado Glendale.

**PDSI como covariável, e seu fine-tuning (`script_29_bateria_pdsi_covariavel.py`/`script_30_pdsi_finetuning_multilag.py`, D-56/D-57).** Com o PDSI já mostrado como explicação do *regime* cíclico (D-37), restava a pergunta direta: adicioná-lo como covariável também melhora o *desempenho preditivo*? Os 12 métodos da bateria original que aceitam regressor exógeno por desenho foram re-treinados com o PDSI (mesma defasagem de 4 meses de D-37/D-41) adicionado, gerando linhas `<metodo>_com_pdsi` em `results/resultados_comparacao.csv` sem alterar as originais. **Resultado: sem melhora consistente** — só 4 dos 12 métodos melhoraram o RMSE de *holdout* (XGBoost −13,8%, regressão quantílica Q50 −26,6%, Random Forest −2,5%, LightGBM −1,5%); os outros 8 pioraram, alguns bastante (Prophet +18,5%, híbrido SARIMA+Prophet +17,0%). Para esses 4, uma rodada de fine-tuning testou uma representação mais rica do PDSI (múltiplos lags simultâneos para os métodos de árvore; lag único selecionado por CV para a regressão quantílica), sob um critério mais rígido — só contou como ganho real se o RMSE da CV expansiva honesta também melhorasse, não só o *holdout* fixo de 24 meses. **Só o XGBoost melhorou de fato** (*holdout* −5,3%, CV −2,0%); Random Forest e LightGBM pioraram nas duas métricas; a seleção de lag da regressão quantílica confirmou que o lag original de 4 meses já era o ótimo entre os candidatos testados — um resultado negativo útil, não um bug. Ver `results/comparacao_pdsi_antes_depois.csv`, `results/comparacao_pdsi_finetuning_multilag.csv` e `results/figures/bateria-pdsi-*.png` / `pdsi-finetuning-*.png` (IDs de decisão D-56/D-57).

**Status:** a Etapa 3 ampliada está completa — todos os 9/9 métodos da seção 3.f do plano original estão implementados (WRTDS, balanço de massa, cenários, espaço de estados, GAM, regressão quantílica, análise de intervenção, SVR, modelos fundacionais), todos confirmando e aprofundando o reenquadramento cíclico de D-14/D-37 (ver D-45–D-50 para cada um). Logs de decisão, glossário e o artigo LaTeX ficam apenas no disco local (gitignored) e **não** fazem parte deste repositório público. Histórico completo de commits e código-fonte reproduzível em **https://github.com/igorfnogueira/projeto-aplicado**.

## Referências

Referência âncora principal: Schwabe et al., *Nature Sustainability* (2020), sobre o aumento da salinidade em esgoto ligado a práticas de conservação de água (indicada pelo professor). Wolfand et al., *ACS ES&T Water* (2022), sobre a mesma bacia do rio Los Angeles. Antweiler e Taylor, *Environmental Science & Technology* (2008), para a técnica ROS/Helsel usada no `script_00b`.
