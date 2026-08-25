# Escopo e Limitações — Projeto Aplicado TDS/LAGWRP

> **Para que serve:** delimitar explicitamente a fronteira deste estudo — o que está dentro, o que
> ficou de fora por escolha, o que ficou de fora por indisponibilidade, e quais fragilidades os
> resultados têm. Alimenta diretamente a seção de limitações do artigo científico.
>
> **Princípio:** declarar limitação não enfraquece um trabalho científico — esconder limitação sim.
> Um resultado apresentado sem suas ressalvas é menos confiável que o mesmo resultado com elas.
>
> **Regra de manutenção:** atualizar sempre que uma nova fronteira ou fragilidade for identificada.
> Decisões que geram limitação também entram no `Artigo/DECISOES.md` com o raciocínio completo.

---

## 1. O que está dentro do escopo

- **Série mensal de TDS do efluente do LAGWRP**, 182 pontos, fev/2011 a fev/2026 (~15 anos).
- Séries mensais de **Cloreto, Amônia e BOD** do mesmo ponto, para as análises de correlação.
- **Vazão do efluente reconstruída** a partir da razão `lb/day ÷ (mg/L × 8,34)` — não estava no
  dataset original, foi derivada e validada (D-12).
- Análise de tendência, previsão a +10/+15/+20 anos, e correlações TDS-amônia e TDS-BOD, conforme
  os quatro objetivos definidos pelo professor.

---

## 2. Deliberadamente fora do escopo (escolhas, não falhas)

### 2.1 Pontos de monitoramento de água receptora
`R-4`, `R-7`, `RSW-650` e `RSW-654` medem a qualidade do Rio Los Angeles, não o efluente da
estação. Mantidos apenas como contexto. **Motivo:** os objetivos do trabalho tratam do efluente;
incluir a água receptora misturaria dois sistemas com dinâmicas distintas.
→ Ver D-07. *Se essa decisão mudar, este arquivo e a bateria de metodologias precisam ser revistos.*

### 2.2 Carga mássica (lb/day) como série de análise própria
O `lb/day` é usado **como insumo para derivar a vazão**, não analisado como série-alvo. **Motivo:**
os objetivos pedem concentração (mg/L). Uma análise de tendência da carga total de sal descarregada
seria legítima, mas é outro trabalho.

### 2.3 Notebook e análises anteriores
`projeto_aplicado_v1 (1).ipynb` foi descartado; o projeto foi reconstruído do zero. **Motivo:**
arquivo corrompido e impossibilidade de rastrear as decisões de pré-processamento embutidas nele.
→ Ver D-01.

### 2.4 Modelagem de processo da estação
Não modelamos a operação interna da ETE (aeração, tempo de retenção, biomassa). O trabalho trata a
estação como caixa-preta entre influente e efluente. **Motivo:** os dados disponíveis são de
monitoramento regulatório de saída, não de processo.

---

## 3. Fora do escopo por indisponibilidade (não foi escolha)

### 3.1 ⚠️ TDS da água de origem — a lacuna mais importante
A literatura (SCSC/DBS&A 2018) identifica o **TDS da água de abastecimento como responsável por
~88% da variabilidade** do TDS do esgoto — mais que qualquer outro fator, incluindo conservação.
**Essa variável não existe no nosso dataset.**

**Impacto:** o modelo explica a série sem acesso ao seu principal determinante. Qualquer conclusão
causal precisa registrar essa ausência.
**Mitigação possível:** buscar séries da MWDSC/LADWP, ou usar o PDSI como proxy climático.
→ Ver D-30.

### 3.2 Vazão medida diretamente
Só temos vazão **derivada** por identidade algébrica, não medida. A derivação foi validada de forma
independente por dois parâmetros (TDS e Cloreto convergem em 0,015%), mas continua sendo uma
estimativa, não um medidor.

### 3.3 Dados populacionais da bacia de esgotamento
Sem população, não é possível calcular consumo per capita (gpcd) nem replicar diretamente o modelo
determinístico do SCSC (`TDS = origem + SML × pop / vazão`). **Adaptação usada em vez disso**
(`script_20_balanco_massa.py`, D-40): a identidade física direta `TDS = carga/(vazão×8,34)`, sem o
termo per-capita — mais simples, mas não separa quanto da carga vem de água de origem vs. de uso
doméstico.

### 3.4 Perris Valley WWTP como comparadora
Estação sem outorga NPDES federal (`CAU001102`, "Unpermitted"), opera sob licença estadual por focar
em reúso/descarte no solo. **Consequência:** o sistema ECHO da EPA não gera dados de efluente para
ela.

### 3.5 Dados brutos do estudo SCSC
As séries das 26 estações não são públicas — foram fornecidas pelas agências diretamente aos
consultores. Só temos os resultados agregados publicados no relatório.

### 3.6 Texto completo do artigo ACS ES&T Water (2022)
O portal ACS retorna 403. Por isso o valor "+50 mg/L" citado por fontes de terceiros **não foi
verificado e não será usado** no artigo.
→ Ver D-27.

### 3.7 Point Loma e San Jose Creek como comparadoras diretas
- **San Jose Creek:** 8 registros de TDS, todos "No Discharge" — planta de reúso, descarga
  superficial é evento raro (D-21).
- **Point Loma:** apenas influente, com intrusão salina (~2.000 mg/L) e janela de 5 anos. *Reversão
  parcial:* o estudo SCSC mostra R²=0,98 entre influente e efluente nessa planta, então os dados
  servem para comparar **forma temporal**, não nível absoluto (D-28).

### 3.8 TimeGPT e TimesFM como modelos fundacionais adicionais
`plano_projeto_TDS.md` §3.f.9 sugeria testar múltiplos modelos fundacionais. **TimeGPT (Nixtla)**
não foi testado — é um serviço de API paga, sem chave de acesso disponível nesta sessão.
**TimesFM (Google)** não foi testado — decisão de escopo, não indisponibilidade: seria redundante
com o Chronos-Bolt já testado para responder à mesma pergunta de pesquisa (um modelo zero-shot
generalista supera os métodos clássicos aqui?), sem ganho de informação proporcional ao custo. →
Ver D-49.

---

## 4. Fragilidades conhecidas dos resultados

Esta seção é o núcleo da futura seção de limitações do artigo. Todos os números vêm de
`matriz_sensibilidade_resultados.csv`.

### 4.1 ⚠️ A tendência não sobrevive ao recorte pós-2012
| Recorte | Inclinação | p-valor |
|---|---|---|
| Série completa (2011-2026) | 3,906 mg/L/ano | 0,0056 |
| Somente pós-2012 | 0,837 mg/L/ano | **0,59** |

A tendência de 15 anos **depende materialmente do trecho 2011-2012**. Isso não invalida o
resultado, mas exige que ele seja apresentado com essa ressalva.
→ Ver D-13.

### 4.2 ⚠️ A significância inverte conforme a correção de autocorrelação
| Variante | p-valor | Significativo? |
|---|---|---|
| Mann-Kendall simples | 0,0056 | Sim |
| Hamed & Rao | 0,182 | **Não** |
| Pre-whitening | 0,417 | **Não** |
| Trend-free pre-whitening | 0,00014 | Sim |
| Seasonal Kendall | 0,0038 | Sim |

Escolher uma variante isoladamente definiria a conclusão central do trabalho. **Decisão adotada:**
reportar todas como análise de robustez, em vez de escolher uma.
→ Ver D-15.

### 4.3 A hipótese TDS-BOD não se confirma
Em **todas as cinco** variantes de tratamento de dados censurados, a correlação TDS-BOD é
**negativa e não significativa** (r entre −0,068 e −0,126; p entre 0,090 e 0,360) — sinal oposto ao
previsto pela hipótese do professor.

**Leitura honesta:** ausência de evidência do efeito esperado é um resultado legítimo, não uma
falha do trabalho. A robustez é boa notícia: a conclusão não depende do tratamento escolhido.

### 4.4 65% do BOD é censurado
A maioria dos meses tem BOD abaixo do limite de detecção. Isso é bom para a estação (tratamento
eficiente), mas reduz drasticamente a variação disponível para correlacionar com o TDS.

### 4.5 Agregação anual não atinge significância em nenhuma variante
Média ano civil p=0,379; média ano hidrológico p=0,398; mediana ano civil p=0,435; mediana ano
hidrológico p=0,300. **Esperado:** n cai de 182 para 15-16 pontos, com perda severa de poder. Não
contradiz a análise mensal, mas também não a corrobora.

### 4.6 Mudanças de MDL se confundem com mudanças de regime
Quatro mudanças de limite de detecção ao longo da série; três coincidem com diferenças de nível
estatisticamente detectáveis (p=0,017; p=0,052; p=0,0099). **Não é possível separar**, com os dados
disponíveis, o que é efeito de método e o que é mudança real — especialmente porque as datas caem
perto das viradas de regime identificadas.
→ Ver D-17.

### 4.7 Extrapolação de 20 anos a partir de 15 de histórico
Prever além do próprio comprimento da série é **especulativo por construção**. Nenhum método
resolve isso; a mitigação adotada é apresentar faixas de incerteza e cenários, nunca um número
único, e declarar essa ressalva sempre que o horizonte de 20 anos for citado.

### 4.8 Amostra pequena para métodos de alta capacidade
~180 pontos mensais é pouco para deep learning. A expectativa (a ser verificada, não assumida) é
que modelos clássicos superem LSTM/N-BEATS — e um resultado negativo aqui deve ser reportado, não
omitido.

### 4.9 ⚠️ WRTDS: adaptação de contexto e implementação simplificada
O WRTDS (Hirsch et al., 2010) foi desenhado para vazão **fluvial** (dirigida por hidrologia); aqui
a "vazão" é vazão de **efluente** (dirigida por consumo/conservação) — a matemática se aplica, a
interpretação é diferente. Além disso, a implementação usada (`script_19_wrtds.py`) é própria, não
o pacote R `EGRET` (sem equivalente Python maduro): usa janelas de meia-largura **fixas**, sem a
expansão adaptativa do EGRET real quando poucos pontos têm peso não-nulo. O risco de circularidade
(a vazão padrão foi derivada do próprio TDS) foi testado explicitamente comparando com a vazão de
Cloreto (independente) — as duas convergem (diferença de 0,024 pontos percentuais/ano), então a
circularidade não invalida o achado, mas o teste precisa ser refeito se a vazão padrão do projeto
mudar. → Ver D-39.

### 4.10 ⚠️ Balanço de massa: extrapolação linear dos componentes é fisicamente implausível
Extrapolar carga de sal e vazão linearmente (Theil-Sen) por 10-20 anos cruza valores fisicamente
impossíveis: a vazão projetada cai para 14% da capacidade nominal em +10a, 5% em +15a, e **fica
negativa** em +20a. O TDS derivado dessas projeções (993 → 1.724 → 1.557 mg/L) não é uma previsão
confiável — é reportado para expor a fragilidade, não escondê-la. A mitigação adotada foi substituir
a extrapolação linear por cenários condicionados a faixas historicamente observadas de PDSI
(`script_21_cenarios.py`), não por um piso arbitrário na vazão. → Ver D-40.

### 4.11 Espaço de estados: sem evidência de tendência genuinamente variável no tempo
A promessa teórica do modelo (`UnobservedComponents`) é uma tendência que pode mudar ao longo da
série. Na prática, a variância estimada do estado de tendência ficou ~0 — o modelo convergiu para
uma inclinação efetivamente constante, não encontrando evidência de que a tendência realmente varie
além do que uma reta já captura. Resultado negativo, reportado como tal. → Ver D-45.

### 4.12 ⚠️ GAM: extrapolação explosiva sob o critério de ajuste padrão (GCV irrestrito)
Minimizar GCV sem restrição no termo de tendência escolhe uma spline pouco suavizada que prevê
1.910 mg/L em +10 anos (quase 3× o último valor observado). Corrigido com um piso na suavização do
termo de tendência (λ≥1,0, ainda escolhido por GCV dentro dessa faixa) — decisão declarada, não uma
correção invisível. Sem esse piso, o método não seria utilizável para extrapolação de longo prazo.
→ Ver D-46.

### 4.13 Regressão quantílica: cruzamento de quantis ao extrapolar
Q10, Q50 e Q90 são ajustados de forma independente. Como a inclinação do Q90 é negativa e a do
Q10/Q50 é positiva, a extrapolação **cruza** nos três horizontes testados (ex. Q90 previsto abaixo
de Q50 em +20a) — violação da ordem Q10≤Q50≤Q90 que só vale por definição no período histórico. Não
foi corrigido reordenando os valores (isso esconderia o problema, não o resolveria). → Ver D-47.

### 4.14 Análise de intervenção: instabilidade na componente sazonal MA do SARIMAX
O termo `ma.S.L12` do modelo convergiu para o limite do espaço admissível (−1,0000, quase
não-invertível) com erro-padrão de 404 — sinal de instabilidade de estimação nessa componente
específica. Os coeficientes dos regressores de evento (seca, ordem de conservação) continuam
interpretáveis, mas a incerteza dessa componente sazonal deve ser lida com cautela. → Ver D-48.

### 4.15 Modelo fundacional zero-shot: incerteza que não cresce com o horizonte
O IC80 (não IC90 — limite nativo do Chronos-Bolt) do Chronos-Bolt-Small **diminui** com o
horizonte (216,7 mg/L de largura em +10a → 137,8 em +20a) — o oposto do comportamento de todos os
outros métodos da bateria. Característica de cabeças de previsão diretas/multi-horizonte, não um
bug: os quantis de cada horizonte são preditos conjuntamente a partir do mesmo contexto fixo, sem
composição autorregressiva de incerteza. → Ver D-49.

---

## 5. Limitações do enquadramento causal

### 5.1 O mecanismo assumido inicialmente é o efeito menor
O projeto foi desenhado sobre o mecanismo da Nature (2020): conservação → menos vazão → menos
diluição → TDS sobe. A leitura integral do estudo SCSC mostra que esse mecanismo responde por
apenas **~12%** da variabilidade, enquanto o TDS da água de origem responde por **~88%**.

O mecanismo da Nature continua válido e citável — mas apresentá-lo como *o* mecanismo seria
incorreto.
→ Ver D-29.

### 5.2 Associação não é causalidade
Mesmo que o PDSI se correlacione com os ciclos de TDS, isso é evidência de associação temporal
compatível com o mecanismo — não prova causal. O desenho é observacional, sem controle nem
intervenção.

### 5.3 O reenquadramento cíclico está confirmado, mas com sincronia fina mais fraca do que o nível/regime
**Atualização (2026-08-14):** o teste pendente foi executado (`script_18_pdsi_regimes.py`) e D-14
está **confirmado** — o PDSI (independente, cego às datas do TDS) explica 68-79% da importância
relativa na decomposição LMG, e seus *changepoints* coincidem com as 4 viradas de regime observadas
dentro de poucos meses. A ressalva que permanece: a correlação sobre as séries destendenciadas
(sincronia mês a mês) é mais fraca e muda de sinal — a seca explica principalmente o *nível* de cada
regime, não sua oscilação fina. `script_19_wrtds.py` reforça essa leitura: a tendência
flow-normalized (que descontaria justamente esse tipo de efeito de nível) não é significativa
(p=0,064). → Ver D-14, D-37, D-39.

---

## 6. Limitações de generalização

- **Uma única estação.** Conclusões valem para o LAGWRP; extensão a outras plantas exige
  verificação.
- **Contexto regional específico.** Sul da Califórnia, com água importada de SWP/CRA e política de
  conservação estadual particular. Não transferível diretamente a outras regiões.
- **A LAGWRP não faz parte dos estudos de referência.** Nem do painel de 34 ETEs da Nature (2020) —
  o que só pode ser suposto, não confirmado — nem das 26 do SCSC (confirmado: a cidade de LA não
  participa daquele estudo). As comparações com a literatura são, portanto, entre plantas
  diferentes da mesma região.
- **Comparação internacional é necessariamente qualitativa, não numérica.** Duas buscas dedicadas
  (`material_apoio_referencias.md` Tema 10, incluindo download e inspeção real do arquivo UNEP
  GEMS/Water) não localizaram nenhum dataset aberto e baixável de TDS/condutividade especificamente
  de **efluente de ETE** (não rio, não água potável) fora da Califórnia, com série temporal
  multi-ano. O eSMR/CIWQS californiano é excepcional nesse aspecto, não a norma — então qualquer
  afirmação sobre o mecanismo de diluição valer "internacionalmente" só pode se apoiar em literatura
  publicada (com suas próprias magnitudes, não replicadas aqui), nunca em replicação direta dos
  dados.

---

## 7. Limitações de infraestrutura do próprio trabalho

- Parte das análises exploratórias desta fase foi conduzida em ambiente sem sandbox de execução,
  o que limitou verificações diretas em arquivos binários (`.docx`, `.xlsx`, PDFs protegidos) e
  exigiu conversão manual para formatos texto.
- O artigo LaTeX e o notebook dependem de manutenção contínua manual (não há CI que valide se estão
  sincronizados com os scripts).
