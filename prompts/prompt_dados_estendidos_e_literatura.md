# Prompt para Claude Code — Série estendida, comparadora e literatura internacional

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

Cobre três ações independentes. **A Ação A tem o maior retorno** — se o tempo for curto, faça só ela
e a Ação C.

---

Leia primeiro: `Artigo/DECISOES.md` (especialmente D-14, D-22, D-29, D-30, D-37),
`ESCOPO_E_LIMITACOES.md` (§3 e §6) e `material_apoio_referencias.md` (Tema 9).

## Ação A — Estender a série do LAGWRP para antes de 2011 ⭐ maior prioridade

**Contexto:** a série atual começa em fev/2011 (182 pontos). Isso pode ser um limite da consulta
que gerou o dataset, **não** o limite real dos dados. O formulário mostrado nas instruções do
professor usava data inicial 07/01/2010, o que sugere um recorte de consulta, não ausência de dado.

**Por que importa:** a série tem apenas ~2 ciclos completos de seca. Para um fenômeno cíclico
(D-14/D-37 confirmados), 2 ciclos é base fraca. Cada ciclo adicional fortalece materialmente a
conclusão central.

**Como fazer:**

O portal CIWQS eSMR é um formulário web interativo — provavelmente **você não conseguirá consultar
direto do terminal**. Nesse caso, **não improvise nem invente dados**: monte as instruções exatas
para eu executar manualmente e me entregue por escrito.

URL: `https://ciwqs.waterboards.ca.gov/ciwqs/readOnly/CiwqsReportServlet?inCommand=reset&reportName=esmrAnalytical`

Parâmetros da consulta a montar:
- **Region:** 4 – Los Angeles
- **Facility:** Los Angeles-Glendale WWRP
- **County:** Los Angeles
- **Parameter:** Total Dissolved Solids (TDS) — e depois repetir para Chloride, Ammonia e BOD
- **Sample Date Range:** início **01/01/2000** (proposital: anterior ao provável começo da base,
  para descobrir o limite real), fim = data atual
- **Record Type:** All

**Ressalva honesta a verificar, não assumir:** o reporte eletrônico (eSMR) na Califórnia começou
por volta de 2006-2008. É possível que simplesmente não exista dado antes disso no sistema — e,
nesse caso, o resultado da consulta é a evidência de que 2011 é próximo do limite real. Reporte
isso como achado, não como falha.

**Depois que eu baixar os CSVs:**
1. Verifique quantos meses novos apareceram e qual a data mais antiga real.
2. Se houver dados novos, **reprocesse a série canônica** e reexecute os scripts afetados
   (`script_01`, `script_17`, `script_18`, `script_19`, `script_20`, `script_21` no mínimo).
3. **Compare antes/depois** explicitamente: a tendência muda? A significância muda? Os regimes
   identificados em D-14 continuam nas mesmas datas? A correlação com PDSI melhora com mais ciclos?
4. Grave tudo como linhas novas no `resultados_comparacao.csv` — não sobrescreva as antigas, e
   marque claramente qual versão da série cada linha usa.

## Ação B — Comparadora via eSMR (Tillman e/ou La Cañada)

**Contexto:** D-22 recomendou o Tillman WRP (mesma operadora, mesmo rio receptor, interior, sem
intrusão salina). O estudo SCSC também revelou que **La Cañada WRP tem série desde 1984** — a mais
longa da região, embora seja operada pelo LACSD (agência diferente).

Monte as instruções de consulta ao eSMR (mesmo formato da Ação A) para:
1. **Donald C. Tillman WRP** (NPDES CA0056227), 2000-2026 — comparadora prioritária
2. **La Cañada WRP** (sistema JOS/LACSD), 2000-2026 — se o eSMR tiver, é a série mais longa

**Antes de investir na análise, verifique a densidade de dados.** O Tillman também faz reúso
(Japanese Garden, Sepulveda Basin) e pode ter o mesmo problema do San Jose Creek — muitos registros
"No Discharge". Se vier esparso, reporte e caia para Burbank WRP.

**O que fazer com os dados que vierem:**
- Aplicar a mesma reconstrução de vazão (D-12) se houver mg/L e lb/day.
- Testar se o **padrão cíclico se replica**: as viradas de regime caem nas mesmas datas
  (2012, 2015, 2019, 2022)?
- Testar se a **conclusão do balanço de massa se replica**: carga de sal caindo, vazão caindo mais
  rápido?
- **Comparar forma normalizada** (z-score ou variação percentual), não nível absoluto — plantas
  diferentes têm níveis diferentes por motivos que não são o objeto do estudo.

Se o padrão se replicar em outra planta, é evidência forte de que o mecanismo é regional e não
particular do LAGWRP. Se não se replicar, isso também é resultado e deve ser reportado.

## Ação C — Levantamento de literatura internacional

**Contexto e enquadramento (importante, não é "comparar por comparar"):** o achado do projeto se
decompõe em duas partes de natureza diferente:

- A **diluição** (carga de sal caindo, vazão caindo mais rápido → concentração sobe) é **física** —
  deveria valer em qualquer lugar onde haja conservação, independente de geografia.
- O **efeito da água de origem** (88% segundo o SCSC, seca → qualidade da água importada) é
  **regional** — depende do portfólio californiano de SWP/Colorado.

Uma comparação internacional testa **qual parte do achado é universal e qual é local**. É isso que
deve orientar a busca — não acumular referências.

**Regiões prioritárias** (por ordem de similaridade ao caso californiano):
1. **Austrália** — Millennium Drought (1997-2009): seca longa, conservação agressiva, dados
   documentados em Melbourne, Adelaide, Perth. É o análogo mais próximo.
2. **África do Sul** — Cape Town "Day Zero" (2018): choque de conservação abrupto, funciona quase
   como experimento natural.
3. **Israel** — 86% de reúso, e desde 2010 tem **padrões regulatórios explícitos de salinidade** no
   efluente tratado, justamente por causa desse problema.
4. **Espanha** — segundo maior reúso mundial, contexto mediterrâneo.
5. Opcional: Singapura (NEWater), Chile, Irã.

**Para cada estudo encontrado, registre:** região, período, se houve tendência de alta de
salinidade no efluente, qual mecanismo os autores atribuem (conservação/diluição vs. qualidade da
água de origem vs. outro), métodos usados, e magnitude do efeito quando houver número.

**Onde registrar:** crie um **Tema 10 — Comparação internacional** em
`material_apoio_referencias.md`, no mesmo formato dos temas existentes, incluindo o aviso de
honestidade sobre quais foram lidos na íntegra e quais só pelo abstract.

**Regra crítica:** não invente conclusão de artigo que você não leu. Se só o abstract estiver
acessível, diga isso explicitamente na entrada, como já é feito nos outros temas.

## Regras herdadas (valem para as três ações)

- Logar no MLflow qualquer reprocessamento (§4.3 do plano).
- Atualizar `notebook.ipynb`, `README.md`, `README.pt-br.md`, `GLOSSARIO.md` (termos novos) e
  `ESCOPO_E_LIMITACOES.md` (se alguma limitação for resolvida ou criada).
- Registrar em `Artigo/DECISOES.md`: atualizar D-22 e D-30 conforme o resultado, e criar entradas
  novas para as decisões desta etapa.
- Avaliar impacto em `Artigo/src/` e **compilar o LaTeX** (o TeX Live está em
  `C:\texlive\2026\bin\windows\`, pode não estar no PATH).
- **Se a série estendida mudar alguma conclusão, isso é resultado importante** — reporte com
  destaque, não silenciosamente.
- Commit e push ao final.

## Entrega

1. Instruções de consulta prontas para eu executar no portal (Ações A e B), ou os dados já baixados
   se você conseguir acessar.
2. Se novos dados chegarem: comparação antes/depois das conclusões centrais.
3. `material_apoio_referencias.md` com o Tema 10 preenchido.
4. `DECISOES.md` atualizado.
