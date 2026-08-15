# Glossário — Projeto Aplicado TDS/LAGWRP

> **Para que serve:** este projeto cruza três domínios que não se sobrepõem naturalmente —
> engenharia sanitária, regulação ambiental americana e estatística/ML. Este arquivo explica
> cada termo usado no projeto, por que ele importa aqui, e onde aparece.
>
> Criado por exigência da própria governança do projeto (`GOVERNANCA_DOCUMENTACAO_TEMPLATE.md`,
> gatilho: "Introduzir um termo de domínio novo específico do negócio → GLOSSARY.md").
>
> **Regra de manutenção:** todo termo técnico novo que entrar no projeto entra aqui também.

---

## 1. Domínio sanitário (o que está sendo medido)

### TDS — Total Dissolved Solids (Sólidos Dissolvidos Totais)
Massa de todo material dissolvido na água (sais, minerais, matéria orgânica dissolvida), medida
em mg/L. É a variável-alvo central do projeto. Funciona como medida prática de **salinidade**.
Não é uma substância específica — é um agregado, o que importa porque sua composição pode mudar
sem que o valor total mude.

**No projeto:** série mensal do efluente do LAGWRP, ~600 mg/L, 182 pontos (2011-2026).

### BOD / DBO — Biochemical Oxygen Demand (Demanda Bioquímica de Oxigênio)
Quantidade de oxigênio que microrganismos consomem para degradar a matéria orgânica presente na
água, medida ao longo de 5 dias a 20 °C (por isso "BOD5 @ 20 °C" no dataset). **BOD baixo no
efluente = tratamento eficiente**, porque significa que sobrou pouca matéria orgânica.

**No projeto:** 65% das medições são "não detectado" — o tratamento remove tão bem que fica abaixo
do limite do método. Isso virou o problema de dado censurado (ver §4).

### Nitrificação
Processo biológico em que bactérias autotróficas convertem amônia (NH₃/NH₄⁺) em nitrito e depois
em nitrato. É o mecanismo que remove nitrogênio amoniacal do esgoto. Essas bactérias são
**sensíveis à salinidade** — daí a hipótese central do professor: TDS alto inibiria a nitrificação,
elevando a amônia no efluente.

**No projeto:** fundamenta a análise de correlação TDS-amônia.

### Amônia (Ammonia, Total as N)
Nitrogênio amoniacal. Usada como **indicador de desempenho da nitrificação**: se sobe, o processo
biológico está falhando.

### Influente vs. Efluente
- **Influente:** o esgoto bruto que *entra* na estação.
- **Efluente:** a água tratada que *sai* da estação.

**Importante:** o estudo SCSC mostra que TDS de influente e efluente são altamente correlacionados
(R² de 0,41 a 0,98 conforme a planta), porque o tratamento convencional **não remove sais** — ele
remove matéria orgânica e nitrogênio. O sal atravessa a estação praticamente intacto.

### Água receptora (Receiving Water)
O corpo d'água onde o efluente é descarregado. No caso do LAGWRP, o **Rio Los Angeles**.

**No projeto:** os pontos `R-4`, `R-7`, `RSW-650`, `RSW-654` monitoram a água receptora, não o
efluente — por isso foram mantidos apenas como contexto (D-07).

### Tratamento terciário
Nível de tratamento além do secundário (biológico), incluindo filtração e desinfecção. Produz água
com qualidade para reúso em irrigação e usos industriais.

### NdeN — Nitrificação-Desnitrificação
Configuração de processo que primeiro converte amônia em nitrato (nitrificação) e depois converte
nitrato em nitrogênio gasoso (desnitrificação), removendo nitrogênio do sistema. **O LAGWRP opera
NdeN desde 2007** (conforme o brochure institucional) — data relevante porque antecede o início da
nossa série (2011), então não introduz quebra no período analisado.

### Reúso / Água reciclada (Recycled Water)
Efluente tratado destinado a uso não potável (irrigação, indústria, recarga de aquífero). Relevante
porque **plantas majoritariamente de reúso podem não ter descarga em água superficial** — motivo
pelo qual o San Jose Creek apareceu como "No Discharge" (D-21).

### SRWS — Self-Regenerating Water Softener (abrandador de água autoregenerável)
Equipamento doméstico que remove dureza da água usando sal, e descarta salmoura no esgoto. **Fonte
significativa de sal no influente.** O estudo SCSC documenta que remover ~8.000 unidades no Santa
Clarita Valley reduziu ~80 mg/L de TDS — uma das poucas causas conhecidas de tendência de *queda*
de TDS.

---

## 2. Regulatório e fontes de dados

### NPDES — National Pollutant Discharge Elimination System
Sistema federal americano (Clean Water Act) de outorgas para descarga de poluentes em águas
superficiais. Cada planta outorgada tem um ID (ex. LAGWRP: análogo; Tillman: `CA0056227`;
Point Loma: `CA0107409`).

**Consequência prática:** plantas **sem** outorga NPDES (prefixo `CAU`, "Unpermitted") não aparecem
com dados de efluente no sistema federal — foi o caso da Perris Valley (`CAU001102`), que opera sob
licença estadual (WDR) por focar em reúso/descarte no solo.

### eSMR — Electronic Self-Monitoring Report
Relatório eletrônico de automonitoramento que as estações californianas submetem ao estado.
**É a fonte dos dados originais deste projeto** (TDS.csv, Chloride.csv, BOD.csv, Ammonia.csv),
via portal CIWQS. Formato rico: uma linha por medição, com método analítico, limites de detecção,
qualificador e unidade.

### CIWQS — California Integrated Water Quality System
Portal do California Water Boards que hospeda o eSMR. **Fonte preferida do projeto** (D-19) porque
entrega formato idêntico ao já processado, série desde 2010, e ambas as unidades (mg/L e lb/day).

### DMR — Discharge Monitoring Report / ECHO
DMR é o relatório de conformidade submetido à EPA federal; **ECHO** (Enforcement and Compliance
History Online) é o portal que o publica. **Rejeitado como fonte** neste projeto (D-19): contém só
o que a outorga obriga a reportar, em formato de conformidade, com janela curta e cobertura
irregular.

### Colunas do dataset eSMR

| Coluna | O que é |
|---|---|
| `Location` | Ponto de monitoramento (`EFF-001`/`EFF-001A` = efluente; `R-*`/`RSW-*` = água receptora) |
| `Parameter` | Qual substância foi medida |
| `Analytical Method` | Método de laboratório — **preenchido = medição bruta** |
| `Calculated Method` | Tipo de cálculo derivado — **preenchido = valor calculado** (ex. "Daily Discharge", "Monthly Average (Mean)") |
| `Qual` | Qualificador: `=` valor medido; `ND` não detectado |
| `Result` | O valor (vazio quando `ND`) |
| `Units` | `mg/L` (concentração) ou `lb/day` (carga mássica) |
| `MDL`, `ML`, `RL` | Limites de detecção/quantificação (ver abaixo) |

**Padrão estrutural importante:** cada amostra gera **duas linhas** — uma com `Analytical Method`
(medição bruta, mg/L, pode ser ND) e outra com `Calculated Method` (valor derivado, sem limites de
detecção, `Qual` sempre `=`). Não é inconsistência do arquivo (ver §1.2 do plano).

### MDL, ML, RL — limites de detecção e quantificação
- **MDL (Method Detection Limit):** menor concentração que o método consegue distinguir de zero com
  confiança estatística. Abaixo dela, o resultado é reportado como `ND`.
- **ML (Minimum Level):** menor concentração que pode ser *quantificada* com precisão aceitável
  (na Califórnia, tipicamente o menor padrão de calibração).
- **RL (Reporting Limit):** limite abaixo do qual o laboratório reporta como não detectado.

**Por que importa:** o MDL do TDS **mudou 4 vezes** ao longo da série (28→25→35→28→35 mg/L), e três
dessas mudanças coincidem com diferenças de nível estatisticamente detectáveis — o que confunde
mudança de método com mudança real (D-17).

### ND — Non-Detect (não detectado)
Resultado abaixo do limite de detecção. **Não significa "zero"** — significa "menor que o limite,
valor desconhecido". Tratar como zero introduz viés (ver §4).

### NODI — No Data Indicator
Código do DMR indicando por que não há valor. `C` = "No Discharge" (não houve descarga no período).

---

## 3. Unidades e a conversão-chave

### mg/L — miligramas por litro
Unidade de **concentração**. É o que os objetivos do projeto pedem.

### lb/day — libras por dia
Unidade de **carga mássica**: quanta massa da substância é descarregada por dia. É concentração ×
vazão. Grandeza fisicamente diferente de mg/L.

### MGD — Million Gallons per Day
Milhões de galões por dia. Unidade padrão de vazão de estações americanas. **Capacidade nominal do
LAGWRP: 20 MGD.**

### gpcd — gallons per capita per day
Galões por habitante por dia. Métrica de consumo. Usada pelo SCSC como proxy de uso interno de
água. Meta legal californiana: **55 gpcd até 2025** (AB-968).

### O fator 8,34 — a conversão que destravou a vazão ⭐
```
lb/day = mg/L × vazão(MGD) × 8,34
```
**De onde vem:** 1 galão de água pesa ≈ 8,34 lb. Logo, 1 milhão de galões pesa 8,34 milhões de lb.
Como 1 mg/L ≈ 1 ppm (1 parte por milhão) em solução aquosa diluída, uma concentração de 1 mg/L em
8,34 milhões de lb de água corresponde a 8,34 lb de soluto.

**Por que é central no projeto:** invertendo a fórmula, obtém-se a **vazão do efluente**, que não
existe explicitamente no dataset:
```
vazão(MGD) ≈ lb/day ÷ (mg/L × 8,34)
```
Validada com TDS e Cloreto independentemente, dando 9,4863 e 9,4877 MGD (diferença de 0,015%) —
ver D-12.

---

## 4. Estatística de dados censurados

### Dado censurado à esquerda (left-censored)
Observação que se sabe estar **abaixo** de um limite, sem valor exato conhecido. É o caso dos `ND`.
Distinto de dado faltante: aqui há informação (sabemos que é pequeno), só não há precisão.

### Substituição simples (MDL/2, zero, MDL)
Abordagem de trocar cada `ND` por um valor fixo. Simples, mas a literatura (Antweiler & Taylor,
2008) mostra que **produz estatísticas enviesadas**, especialmente com muitos censurados.

### Kaplan-Meier
Método não paramétrico originalmente de análise de sobrevivência, adaptado para dados censurados
ambientais. **Recomendado para séries com menos de 70% de censura** — nosso BOD tem 65%.

### ROS — Regression on Order Statistics
Método de Helsel: ajusta uma distribuição aos dados detectados e usa essa distribuição para imputar
os censurados, preservando a estrutura estatística.

### MLE — Maximum Likelihood Estimation
Estima os parâmetros da distribuição (tipicamente lognormal) considerando explicitamente a censura
na função de verossimilhança.

---

## 5. Estatística de tendência

### Mann-Kendall
Teste **não paramétrico** de tendência monotônica. Não assume normalidade nem linearidade — só
avalia se os valores tendem a subir ou descer ao longo do tempo. Padrão em qualidade de água.

### Sen's slope / Theil-Sen
Estimador robusto da magnitude da tendência: a **mediana** de todas as inclinações entre pares de
pontos. Resistente a outliers, diferente do OLS.

### Autocorrelação serial
Quando um valor da série depende dos anteriores. **Infla artificialmente a significância** do
Mann-Kendall, porque o teste assume observações independentes.

### Pre-whitening (PW) vs. Trend-Free Pre-Whitening (TFPW)
- **PW:** remove a autocorrelação antes do teste. Problema: **remove parte da tendência junto**,
  reduzindo o poder estatístico.
- **TFPW:** remove a tendência primeiro, depois a autocorrelação, e recoloca a tendência —
  proposto justamente para corrigir a perda de poder do PW.

**No projeto:** essa escolha **inverte a conclusão** — PW dá p=0,417 (não significativo), TFPW dá
p=0,00014 (altamente significativo). Ver D-15.

### Correção de variância de Hamed & Rao
Alternativa: em vez de alterar a série, ajusta a variância da estatística do teste para refletir a
autocorrelação. No projeto: p=0,182 (não significativo).

### Seasonal Kendall
Variante do Mann-Kendall que compara cada mês só com o mesmo mês de outros anos, neutralizando
sazonalidade. No projeto: slope 4,67 mg/L/ano, p=0,0038.

### STL — Seasonal-Trend decomposition using Loess
Decompõe a série em tendência + sazonalidade + resíduo, usando suavização local. Base para análises
destendenciadas e detecção de outliers por resíduo.

### Changepoint / quebra estrutural
Ponto no tempo em que o comportamento da série muda de regime. Testes: Chow, CUSUM, Pettitt.
**Central no projeto** para testar se os ciclos identificados (2012, 2015, 2019, 2022) são reais.

---

## 6. Modelagem e avaliação

### Horizonte de previsão
Quantos períodos à frente se prevê. **No projeto: +10, +15 e +20 anos** a partir do último dado
observado — todos maiores que o próprio histórico (~15 anos), o que torna a extrapolação
especulativa por construção.

### Holdout temporal vs. validação cruzada de séries temporais
Em séries temporais **nunca se usa split aleatório** (vazaria futuro para o passado). Usa-se corte
cronológico (holdout) ou janelas expansivas (expanding window CV).

### Backtesting com origem móvel (rolling origin)
Treinar até o ano X e medir o erro real em X+3, X+5, repetindo para vários X. **É o único proxy
honesto de desempenho em extrapolação longa** — o holdout comum não cobre horizontes de 10-20 anos.

### MASE — Mean Absolute Scaled Error
Erro médio absoluto dividido pelo erro de um modelo ingênuo. **MASE < 1 significa que o modelo
vence o naive**; MASE ≥ 1 significa que não vence. Métrica-chave porque impede que um modelo
complexo seja apresentado como bom sem superar o trivial.

### Conformal prediction
Método para gerar intervalos de previsão com cobertura garantida em modelos que não produzem
incerteza nativamente (árvores, ensembles).

### Cobertura empírica do intervalo
Proporção real de observações que caem dentro do IC previsto. Um IC90 que cobre só 60% dos casos
está mal calibrado — por isso a cobertura é reportada junto com a largura.

### WRTDS — Weighted Regressions on Time, Discharge, and Season
Método padrão do USGS para tendência de qualidade de água. **Separa a mudança causada por variação
de vazão da mudança "flow-normalized"** (o que resta depois de descontar a vazão). Responde
diretamente à pergunta central: a subida do TDS é falta de diluição ou mais sal?

**No projeto:** implementação própria (`script_19_wrtds.py`), não o pacote R `EGRET` (sem
equivalente Python maduro) — regressão ponderada localmente (kernel tricúbico em tempo, log(vazão)
e sazonalidade) com janelas fixas, não adaptativas como o EGRET real (simplificação declarada).
Resultado: a tendência flow-normalized não é significativa (p=0,064) — quase toda a tendência
bruta desaparece ao descontar a vazão. Ver D-39.

### Flow-normalização (flow-normalization)
O passo final do WRTDS: em vez de olhar a concentração ajustada no instante `t` com a vazão
realmente observada em `t`, integra (calcula a média de) a predição do modelo sobre **toda a
distribuição histórica de vazão**, mantendo fixos o tempo e a sazonalidade. O resultado é "que
concentração se esperaria em `t` se a vazão tivesse seguido seu padrão histórico normal" — isola o
efeito de tempo/regime do efeito puramente hidrológico.

### Risco de circularidade (em variáveis derivadas)
Quando uma variável explicativa foi calculada a partir da própria variável-alvo (aqui: a vazão
reconstruída via `lb/dia ÷ (mg/L × 8,34)`, D-12, usa o próprio TDS), usá-la para "explicar" o alvo
pode gerar uma relação artificial ou até tautológica (ver `script_20`, onde `TDS = carga_TDS ÷
(vazão_TDS × 8,34)` dá R²=1,000000 exato, por identidade algébrica, não por poder explicativo real).
**Mitigação usada no projeto:** repetir a análise com a vazão derivada de uma série independente
(Cloreto) e comparar — se os resultados coincidirem, a circularidade não invalida o achado (D-39,
D-40).

### Balanço de massa (mass balance)
Em vez de extrapolar a concentração (TDS) diretamente, modela separadamente os dois componentes
físicos que a compõem — carga de sal (massa por tempo, lb/dia) e vazão (volume por tempo, MGD) — e
deriva a concentração pela identidade `TDS = carga ÷ (vazão × 8,34)`. Mais defensável fisicamente
que extrapolar TDS como caixa-preta, mas **herda a fragilidade de cada componente**: se a
extrapolação da vazão ou da carga for instável, a razão entre elas também será (D-40 documenta um
caso concreto: vazão extrapolada linearmente cruza valores negativos em +20 anos).

### LMG (Lindeman, Merenda & Gold) — importância relativa
Método que decompõe o R² de uma regressão múltipla entre as variáveis explicativas, considerando
efeitos diretos e as intercorrelações. Implementado no pacote R `relaimpo`.

**No projeto:** é o método pelo qual o SCSC concluiu que TDS de origem responde por 88% e
conservação por 12%. Reimplementado em Python via fórmula fechada (2 preditores) em `script_18` e
usado de novo internamente em `script_19`/`script_20` para separar os efeitos de vazão e PDSI.

### AR(1) — processo autorregressivo de ordem 1
Modelo estatístico simples em que o valor de uma série no tempo `t` depende linearmente do valor em
`t-1` mais ruído: `X_t = μ + φ(X_{t-1} - μ) + ε_t`. Um processo estacionário (`|φ|<1`) sempre reverte
à média `μ` no longo prazo — é por isso que ele é apropriado para simular o PDSI (índice calibrado
para ser aproximadamente estacionário), mas **não** seria apropriado para simular uma série com
tendência real de longo prazo, que um AR(1) tende a "puxar" de volta à média artificialmente.

**No projeto:** `script_21_cenarios.py` ajusta um único AR(1) no PDSI histórico (1895-2026) e simula
os 4 cenários mudando só a média-alvo `μ` de cada um (não o processo em si).

### Monte Carlo
Técnica de estimar a distribuição de uma quantidade incerta simulando repetidamente o processo que
a gera (aqui: milhares de trajetórias de PDSI + milhares de sorteios do coeficiente da regressão +
ruído), em vez de calcular a distribuição analiticamente. Produz uma distribuição inteira de
resultados possíveis (ex. TDS em +20 anos), da qual se extrai percentis (P5/P50/P95), não um único
número.

### Projeção condicional (vs. previsão)
Uma projeção condicional responde "**se** o clima seguir o padrão do cenário X, o TDS ficaria em
torno de Y" — não afirma qual cenário vai de fato acontecer. Diferente de uma previsão pontual (ex.
"o TDS em 2046 será Z mg/L"), que implicitamente afirma saber o futuro do clima também.

**No projeto:** `script_21` reporta 4 projeções condicionais (seco/normal/úmido/agravamento
climático), nunca um valor único para +20 anos — ver D-41.

---

## 7. Conceitos do estudo SCSC

### TDS de origem (Source TDS)
Concentração de TDS na **água de abastecimento** que entra no sistema urbano. Segundo o SCSC, é o
**determinante dominante** do TDS do esgoto (~88% da importância relativa).

**No projeto:** ausente do nosso dataset — é a lacuna D-30.

### IFU — Increment From Use (incremento de uso)
Diferença entre o TDS do influente e o TDS da água de origem: **o sal adicionado pelo uso doméstico**
(excreção, sabões, abrandadores, água cinza). Faixa típica na literatura: **200-400 mg/L**.

### SML — Salt Mass Load (carga mássica de sal)
Massa de sal adicionada por habitante por dia: ≈ **0,15-0,18 lb/hab/dia** (média 0,17 nas bacias do
SCSC; faixa de 0,04 a 0,4 conforme perfil industrial).

### Modelo determinístico do SCSC
```
TDS_influente = TDS_origem + (SML × população) / (vazão em MGD)
```
Alternativa **fisicamente fundamentada** à extrapolação puramente estatística.

### PDSI / PMDI — Palmer Drought Severity Index (e sua versão modificada)
Índice padronizado de seca (escala de −10 seco a +10 úmido), calculado a partir de temperatura,
precipitação e balanço hídrico. O **PMDI** é a variante operacional, que difere do PDSI apenas nas
transições entre regimes climáticos.

**Limitação relevante:** o PDSI mensal não captura secas com duração menor que ~12 meses.

### 8-Station Index
Índice do DWR californiano que compara a precipitação anual de 8 estações da Sierra Norte com a
média de 50 anos (51,8 polegadas para 1966-2015). Usado na gestão do State Water Project.

### SWP e CRA — State Water Project e Colorado River Aqueduct
As duas principais fontes de água importada para o sul da Califórnia. **A qualidade delas varia com
a seca**: o TDS do CRA oscila ~300 mg/L e o do SWP ~200 mg/L entre anos secos e úmidos — amplitude
suficiente para explicar os ciclos observados no LAGWRP.

---

## 8. Instituições e siglas

| Sigla | Nome | Papel no projeto |
|---|---|---|
| **LAGWRP** | Los Angeles-Glendale Water Reclamation Plant | A estação estudada |
| **LASAN** | LA Sanitation (cidade de Los Angeles) | Opera o LAGWRP e o Tillman |
| **LACSD** | Los Angeles County Sanitation Districts | Opera San Jose Creek, La Cañada, Pomona etc. (é órgão *diferente* do LASAN) |
| **JOS** | Joint Outfall System | Sistema conjunto do LACSD, com outorga compartilhada |
| **MWDSC / MWD** | Metropolitan Water District of Southern California | Fornece a água importada — fonte potencial do TDS de origem |
| **LADWP** | LA Department of Water and Power | Abastece a cidade de LA |
| **EMWD / IEUA** | Eastern Municipal WD / Inland Empire Utilities Agency | Agências mais analisadas no estudo SCSC |
| **SCSC** | Southern California Salinity Coalition | Financiou o estudo de 2018 |
| **DBS&A** | Daniel B. Stephens & Associates | Consultoria que executou o estudo SCSC |
| **DWR** | California Department of Water Resources | Fonte do 8-Station Index |
| **NOAA** | National Oceanic and Atmospheric Administration | Fonte do PDSI/PMDI |
| **USGS** | United States Geological Survey | Origem do método WRTDS |
| **EPA** | Environmental Protection Agency | Mantém o ECHO/DMR |
