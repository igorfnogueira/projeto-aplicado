# Prompt para Claude Code — WRTDS, balanço de massa e cenários (reenquadrado por regime)

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

**Rodar depois de** `prompt_compilar_artigo.md` (para o artigo estar compilável antes de receber
resultados novos).

---

Leia primeiro, nesta ordem:
- `Artigo/DECISOES.md` — **D-37** (ciclos explicados por seca, confirma D-14), **D-31**,
  **D-29** (água de origem domina, não conservação), **D-12** (vazão reconstruída e validada)
- `plano_projeto_TDS.md` — §1.5 (reconstrução da vazão), §3.f.1 a §3.f.3, §4.3 (MLflow)
- `material_apoio_referencias.md` — Tema 9, especialmente §9.1 e §9.5
- `ESCOPO_E_LIMITACOES.md` — §4 e §5

## O problema que esta etapa precisa resolver

A bateria atual de previsão foi construída para **extrapolar tendência monotônica**. Mas D-37
confirmou que a série é dirigida por **ciclos de seca**. Isso cria uma tensão que precisa ser
enfrentada, não contornada:

> Prever TDS em +20 anos, numa série dirigida por seca, equivale a prever a seca em +20 anos —
> o que não é possível. Uma previsão pontual para 2046 não é defensável nesse enquadramento.

Consequências que orientam esta etapa:

1. **A pergunta de tendência mudou.** Não é mais "há tendência de alta?", e sim **"há tendência por
   baixo dos ciclos, depois de descontar o efeito da seca/vazão?"**. É exatamente o que a
   normalização por vazão do WRTDS responde.
2. **A previsão de longo prazo vira cenário, não ponto.** Projetar sob futuros seco/normal/úmido é
   honesto; uma curva única não é.
3. **As previsões pontuais já produzidas não são descartadas** — elas passam a ser apresentadas com
   essa ressalva de enquadramento. Não apague nem reescreva resultados anteriores; contextualize.

## Tarefa 1 — WRTDS / normalização por vazão (`script_19_wrtds.py`)

Objetivo: separar a variação de TDS causada por variação de vazão daquela que resta depois de
descontá-la (a componente "flow-normalized").

Método (Hirsch et al., 2010): regressão ponderada de `log(concentração)` sobre tempo, vazão e
sazonalidade, com pesos por proximidade nas três dimensões; em seguida, normalização por vazão
integrando sobre a distribuição histórica de vazão.

**Ressalvas honestas que precisam ser tratadas, não ignoradas:**

- **Adaptação de contexto.** O WRTDS foi desenhado para rios, onde "discharge" é vazão fluvial
  dirigida por hidrologia. Aqui, a "vazão" é a **vazão do efluente**, dirigida por consumo e
  conservação. A matemática se aplica, mas **a interpretação é diferente** e isso deve ser
  declarado explicitamente na metodologia do artigo.
- **Vazão derivada, não medida.** A vazão vem da identidade `lb/day ÷ (mg/L × 8,34)` (D-12).
  Validada de forma independente por TDS e Cloreto (convergem em 0,015%), mas continua sendo
  estimativa.
- **⚠️ Risco de circularidade — verifique antes de confiar no resultado.** A vazão foi derivada
  *a partir* do TDS. Usar essa vazão como variável explicativa do próprio TDS pode induzir relação
  artificial. **Teste isso explicitamente:** use a vazão derivada do **Cloreto** (série
  independente) como variável explicativa e compare com o resultado obtido usando a vazão derivada
  do TDS. Se os resultados divergirem muito, há circularidade e o achado não se sustenta — reporte
  isso em vez de escolher a versão mais favorável.
- **Tamanho de amostra.** WRTDS costuma ser aplicado a séries de décadas. 182 pontos mensais é
  pouco; se o ajuste ficar instável ou os pesos degenerarem, reporte a limitação.
- **Implementação.** A referência é o pacote R `EGRET`. Em Python não há equivalente maduro —
  avalie implementar a regressão ponderada diretamente ou usar `rpy2`. **Se a implementação
  completa não for viável com confiança, implemente uma versão simplificada de normalização por
  vazão e deixe isso declarado**, em vez de rotular como WRTDS algo que não é.

Entregável: componente flow-normalized da série, tendência estimada sobre ela (com IC), e
comparação explícita com a tendência bruta de 3,906 mg/L/ano.

## Tarefa 2 — Modelo de balanço de massa (`script_20_balanco_massa.py`)

Em vez de extrapolar o TDS diretamente, modele os dois componentes separadamente e derive:

```
TDS = carga de sal (lb/day) ÷ (vazão em MGD × 8,34)
```

Passos:
1. Modelar a série de **carga de sal** (lb/day) — tendência e ciclo próprios.
2. Modelar a série de **vazão** (MGD) — tendência e ciclo próprios.
3. Derivar TDS previsto e comparar com o observado (validação do modelo no período histórico).
4. Projetar cada componente separadamente e derivar o TDS futuro.

**Pergunta central a responder com números:** a carga de sal está estável/caindo enquanto a vazão
cai (→ confirma o mecanismo de diluição), ou a carga também sobe (→ há mais sal entrando, mecanismo
diferente)? Essa decomposição é uma das contribuições mais fortes disponíveis para o artigo.

**Referência de comparação:** o SCSC usa a forma `TDS_influente = TDS_origem + (SML × população) /
vazão`, com SML ≈ 0,15-0,18 lb/hab/dia. Não temos população nem TDS de origem (D-30), então a
forma acima é a adaptação possível — declare a adaptação e o que ela impede de fazer.

## Tarefa 3 — Projeção por cenários (`script_21_cenarios.py`)

Substituir a previsão pontual de longo prazo por **projeção sob cenários climáticos**, usando o
PDSI já baixado no `script_18`.

1. Caracterize a distribuição histórica do PDSI e a relação PDSI → TDS estabelecida em D-37
   (incluindo a defasagem identificada).
2. Defina pelo menos três cenários para os horizontes de +10, +15 e +20 anos:
   - **Seco:** PDSI persistentemente negativo (equivalente a seca prolongada)
   - **Normal:** PDSI oscilando em torno da média histórica
   - **Úmido:** PDSI persistentemente positivo
   - Opcionalmente, um cenário de **agravamento climático** com secas mais frequentes/intensas
3. Rode **simulação de Monte Carlo** sobre a incerteza dos parâmetros e a variabilidade do PDSI,
   produzindo uma distribuição de TDS por horizonte e cenário — não um número.
4. Gráfico: série histórica + leque de cenários com bandas de incerteza para +10/+15/+20 anos.

**Não apresente um valor único de TDS para 2046.** Apresente a faixa por cenário, com a ressalva
de que cenários não são previsões — são projeções condicionais.

## Reconciliação com o que já existe

- Os métodos já rodados (`script_01` a `script_18`) e o `resultados_comparacao.csv`
  **permanecem**. Adicione linhas novas, não sobrescreva.
- Na síntese, deixe claro o que cada família responde:
  - Métodos de tendência/ML → desempenho preditivo de curto prazo e magnitude da tendência bruta
  - WRTDS → há tendência *sob* os ciclos?
  - Balanço de massa → o mecanismo é diluição ou mais sal?
  - Cenários → faixa plausível de longo prazo, condicionada ao clima
- Se algum resultado novo contradisser um anterior, **registre a contradição** em `DECISOES.md` em
  vez de escolher qual manter.

## Regras herdadas (obrigatórias)

- Logar tudo no MLflow (§4.3): params, seed, métricas, artefatos, tempo, CPU/GPU.
- Figuras em `Artigo/images/` com nome ASCII (ex. `wrtds-flow-normalized.png`,
  `balanco-massa-decomposicao.png`, `cenarios-pdsi-horizontes.png`).
- Atualizar `notebook.ipynb` com seções didáticas no mesmo padrão já adotado (o quê / por quê /
  termos do glossário / como interpretar / decisão vinculada).
- Atualizar `GLOSSARIO.md` com os termos novos (WRTDS, flow-normalization, balanço de massa,
  Monte Carlo, projeção condicional).
- Atualizar `ESCOPO_E_LIMITACOES.md` com as limitações novas (adaptação do WRTDS, risco de
  circularidade, ausência de população/TDS de origem para o balanço completo).
- Atualizar `Artigo/src/metodologia.tex` e `resultados.tex`; **compilar o LaTeX** e checar o `.log`.
- Registrar em `Artigo/DECISOES.md` cada decisão metodológica desta etapa.
- **Nunca inventar resultado.** Se o WRTDS não convergir, se a circularidade se confirmar, ou se o
  balanço de massa não fechar, isso é resultado e deve ser reportado como tal.
- Commit e push ao final.

## Entrega

1. Os três scripts funcionando e logados no MLflow.
2. Resposta objetiva a três perguntas, com números:
   - **Há tendência de TDS depois de descontar o efeito da vazão?**
   - **A subida do TDS é falta de diluição ou aumento de carga de sal?**
   - **Qual a faixa plausível de TDS em +10/+15/+20 anos por cenário climático?**
3. `DECISOES.md`, `GLOSSARIO.md` e `ESCOPO_E_LIMITACOES.md` atualizados.
4. Artigo recompilado e verificado.
