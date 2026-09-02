# Solicitação de dados adicionais — e-mail pronto para envio

---

# PARTE 1 — LEIA ANTES DE ENVIAR

## Contexto

Este e-mail é dirigido a alguém que **já ajudou o projeto antes** (forneceu os dados originais da
LAGWRP) — por isso o tom é diferente do modelo formal para o LASAN (`solicitacao_dados_LASAN.md`):
começa agradecendo e situando o que já foi feito com os dados anteriores, antes de pedir mais.

## Ajustes que você precisa fazer antes de enviar

- [ ] Substituir `[SEU NOME COMPLETO]` e `[SEU E-MAIL]`
- [ ] Substituir `[NOME DA PROFESSORA]` pelo nome real
- [ ] Confirmar/ajustar a frase sobre como os dados originais foram obtidos (o rascunho assume que
      ela forneceu o export do eSMR usado no projeto — ajuste se a história for outra)
- [ ] Decidir se anexa ou resume os achados do projeto (o rascunho oferece enviar o artigo/resumo
      executivo, mas não anexa nada automaticamente)
- [ ] Ajustar a data-limite se seu prazo for diferente do sugerido
- [ ] **Verificar o idioma:** o e-mail abaixo está em português (a pedido do usuário, 2026-09-01).
      Se a professora não lê português, traduza antes de enviar — a versão anterior em inglês fica
      registrada no histórico do arquivo (`git log` ou peça para eu recriá-la, se precisar).

## Atualização importante (2026-09-01/02): conseguimos parte do pedido 1 sozinhos

Depois da versão original deste e-mail, encontramos e lemos **21 relatórios públicos anuais de
qualidade da água da LADWP (2004-2024)**, que trazem o TDS médio por fonte (LA Aqueduct, poços
locais, e as três estações da MWD — Weymouth, Diemer, Jensen) e o percentual de mistura de cada
ano. Construímos uma série de TDS de origem ponderado e comparamos com o TDS de efluente da
LAGWRP: **correlação forte e significativa (r=0,912, p=0,000005)**, mais forte que a que já
tínhamos com o PDSI. Isso já é um resultado real, citável no artigo (D-54 em `Artigo/DECISOES.md`).

**O que isso muda no pedido:** não precisamos mais pedir o dado anual do lado Los Angeles — já o
temos, publicado. O pedido 1 abaixo foi reformulado para focar no que **ainda falta e não
conseguimos sozinhos**: (a) a mesma coisa só que **mensal**, se existir (os relatórios públicos só
trazem médias/faixas anuais); (b) o **peso de cada uma das 3 estações da MWD dentro do total
importado** (hoje assumimos uma média simples das três, por falta desse detalhe); (c) o equivalente
anual/mensal para o **lado Glendale**, que continua sem nenhum dado real. Os três são dados que
temos motivo para acreditar que são internos/não-públicos (não achamos nada com buscas nem tentando
baixar diretamente dos sites oficiais) — por isso a via institucional dela continua sendo o caminho
mais viável.

## Os dois pedidos, em ordem de valor (por que essa ordem)

1. **Refinamento do TDS/condutividade da água de origem** — três pedaços específicos, cada um
   provavelmente exigindo contato direto com LADWP/MWD/Glendale Water & Power (não achamos nada
   assim publicado):
   - **(a) Granularidade mensal**, se existir, para o que já temos anual (LA Aqueduct, poços,
     Weymouth/Diemer/Jensen) — permitiria testar defasagem (quanto tempo a água leva para "chegar"
     no sistema), do jeito que já fizemos com o PDSI.
   - **(b) Peso de cada estação da MWD (Weymouth/Diemer/Jensen) dentro do total importado**, por
     ano — hoje aproximamos por uma média simples das três, o que pode estar distorcendo o
     resultado, já que elas têm TDS bem diferentes entre si (Jensen ~300 mg/L vs. Diemer/Weymouth
     ~600+ mg/L).
   - **(c) O equivalente (anual já ajudaria, mensal seria ideal) para o lado Glendale** — TDS por
     fonte, entregue pela Glendale Water & Power, que ainda não temos em nenhuma granularidade.
2. **TDS de efluente de uma estação comparadora** (Donald C. Tillman WRP ou La Cañada WRP) — testa
   se o padrão cíclico ligado a seca encontrado na LAGWRP se replica em outra estação da região, ou
   é específico dela. Hoje a conclusão do projeto se apoia em dados de uma única estação.

## Ponto de honestidade

O e-mail descreve os achados do projeto de forma resumida e precisa (mecanismo de diluição
confirmado, reenquadramento cíclico, limitação da água de origem) — não exagera nem promete mais
do que o projeto de fato mostrou. Se os dados vierem e forem usados, credite a fonte no artigo.

---

# PARTE 2 — MENSAGEM PRONTA PARA ENVIO (em português)

**Assunto sugerido:**
`Atualização do projeto sobre salinidade na LAGWRP — preciso da sua ajuda para conseguir mais dois conjuntos de dados`

---

Prezada [NOME DA PROFESSORA],

Espero que esteja bem. Antes de mais nada, muito obrigado novamente pelos dados originais da LAGWRP
(export do eSMR, TDS/Cloreto/Amônia/DBO, 2011–2026) que tornaram este projeto possível. Escrevo para
contar aonde a análise chegou e pedir sua ajuda para conseguir mais dois conjuntos de dados que
resolveriam a maior limitação que encontramos.

**O que descobrimos**

O TDS do efluente da LAGWRP não segue uma tendência simples de alta — segue um **padrão cíclico
ligado às secas recentes da Califórnia** (2012–2016 e 2020–2022), confirmado estatisticamente com o
índice de seca PDSI da NOAA (não só por inspeção visual). Uma decomposição por balanço de massa
(carga de sal vs. vazão, calculadas de forma independente) confirma que o mecanismo é **diluição**:
a vazão do efluente vem caindo mais rápido que a carga de sal, não o contrário. Como extrapolar
essa série de forma linear por 20 anos se mostrou fisicamente implausível (ela é dirigida por
ciclos, não por uma tendência estável), nossas projeções para +10/+15/+20 anos hoje são apresentadas
como faixas entre cinco cenários climáticos (seco, normal, úmido, agravamento progressivo, e um
fundamentado em projeção climática real de RCP 8.5 via Cal-Adapt) — não mais um número único.

**Onde a análise está travada, e por que preciso da sua ajuda**

Um estudo regional (Southern California Salinity Coalition, 2018, 26 estações de tratamento) achou
que a **qualidade da água de origem explica ~88% da variabilidade do TDS de efluente**, contra
apenas ~12% da conservação local de água. Esse estudo, porém, **não incluiu a cidade de Los
Angeles** — então esse achado é um padrão regional, ainda não confirmado especificamente para a
LAGWRP. Para testar isso com dado real (não só o PDSI como substituto indireto), fomos atrás de
publicações da própria LADWP e encontramos algo bom: **21 relatórios anuais públicos de qualidade da
água (2004-2024)** trazem o TDS médio de cada fonte que abastece Los Angeles — LA Aqueduct, poços
locais, e as três estações de tratamento da MWD (Weymouth, Diemer, Jensen). Construímos uma série de
TDS de origem ponderada por essas fontes e comparamos com o TDS de efluente da LAGWRP: a correlação
é forte e estatisticamente muito significativa (r=0,912, p=0,000005) — mais forte até que a que já
tínhamos com o PDSI.

Esse achado já resolve, sozinho, boa parte do que eu ia pedir. O que sobra, e que não conseguimos
sem ajuda, é mais específico:

1. **Granularidade mensal**, se existir — os relatórios que achamos só publicam médias/faixas
   anuais. Com uma série mensal, daria para testar o tempo de trânsito da água (quantos meses ela
   leva do reservatório até virar esgoto), do jeito que já fizemos com o índice de seca.
2. **O peso de cada uma das 3 estações da MWD (Weymouth/Diemer/Jensen) dentro do total de água
   importada, por ano** — hoje aproximamos isso por uma média simples das três, mas elas têm TDS bem
   diferentes entre si (Jensen ~300 mg/L vs. Diemer/Weymouth ~600+ mg/L), então o peso real
   melhoraria bastante a precisão.
3. **O equivalente para o lado Glendale** (Glendale Water & Power) — a LAGWRP atende tanto Los
   Angeles quanto Glendale, e para o lado Glendale ainda não temos nenhum dado real, nem anual.

Tentamos achar essas três coisas sozinhos (busca online, tentativa de acessar os sites oficiais da
LADWP/Glendale diretamente) e não encontramos nada publicado — acho que são dados mais internos, que
só saem por um contato direto. É exatamente aqui que sua ajuda faria diferença: um contato
institucional ou um caminho de solicitação que você já conheça encurtaria muito esse processo, que
como estudante estrangeiro eu não tenho como percorrer sozinho.

**O que ajudaria, em ordem de valor**

1. **Qualquer um dos três itens acima** (mensal, peso por estação da MWD, ou dado da Glendale) —
   qualquer um já ajudaria; não precisa ser os três.
2. **TDS mensal de efluente de uma estação de tratamento comparável** — idealmente o Donald C.
   Tillman WRP ou o La Cañada WRP — para testar se o padrão cíclico ligado à seca que encontramos na
   LAGWRP se repete em outro lugar, ou é específico dela.

Qualquer formato legível por máquina (CSV, Excel) funciona bem, e sei que são pedidos difíceis —
qualquer parte que você conseguir já ajuda.

**Compartilhando os resultados**

Terei prazer em compartilhar a versão atual do artigo, o notebook de análise, ou um resumo curto dos
achados — o que for mais útil para você. É uma pesquisa acadêmica sem fins comerciais, para um
trabalho de conclusão de pós-graduação, e qualquer dado recebido será devidamente creditado.

Muito obrigado novamente pelo apoio a este projeto — me avise se houver um contato ou canal melhor
para qualquer um dos dois pedidos.

Atenciosamente,

[SEU NOME COMPLETO]
Estudante de Pós-Graduação em Inteligência Artificial Aplicada
UniSENAI — Brasil
[SEU E-MAIL]

---

# PARTE 3 — VERSÃO CURTA (mesmo conteúdo, bem mais resumida)

Use esta versão se preferir um e-mail mais direto, sem o passo a passo dos achados — mantém só o
essencial: o que descobrimos em uma frase, por que falta um dado, e o pedido.

**Assunto sugerido:**
`Preciso da sua ajuda para conseguir dois conjuntos de dados para o projeto da LAGWRP`

---

Prezada [NOME DA PROFESSORA],

Espero que esteja bem. Obrigado novamente pelos dados da LAGWRP que você nos passou — o projeto
avançou bastante desde então, e agora esbarrei numa limitação que só resolvo com sua ajuda.

Descobrimos que o TDS do efluente segue um padrão cíclico ligado às secas da Califórnia (confirmado
com o índice PDSI), causado por diluição — menos vazão de efluente, não mais sal entrando no
sistema. A literatura da região mostra que o fator que mais explica o TDS é a **qualidade da água de
origem** (~88% da variação, contra ~12% de conservação local) — e fomos atrás disso sozinhos: achamos
21 relatórios anuais públicos da LADWP (2004-2024) com o TDS por fonte de abastecimento, e a
correlação com o efluente da LAGWRP é forte (r=0,912, p=0,000005).

O que sobra, e que não consigo sozinho, é mais específico: (a) essa mesma série **mensal**, se
existir, em vez de só anual; (b) o **peso de cada estação da MWD** (Weymouth/Diemer/Jensen) dentro do
total importado, que hoje aproximo por média simples; (c) o mesmo dado para o **lado Glendale**, que
ainda não tenho de forma nenhuma. São registros que parecem internos (não achei nada publicado,
mesmo tentando os sites oficiais diretamente) — por isso peço sua ajuda, em ordem de valor:

1. **Qualquer um dos três itens acima** (mensal, peso por estação da MWD, ou dado da Glendale) — não
   precisa ser todos.
2. **TDS mensal de efluente de outra estação comparável** — Donald C. Tillman WRP ou La Cañada WRP —
   para testar se o padrão que achamos na LAGWRP se repete em outro lugar.

Sei que são pedidos difíceis — qualquer parte que você conseguir já ajuda. Posso compartilhar o
artigo, o notebook ou um resumo dos achados, o que for mais útil. É pesquisa acadêmica sem fins
comerciais, e qualquer dado recebido será devidamente creditado.

Muito obrigado pelo apoio — me avise se houver um caminho melhor para pedir isso.

Atenciosamente,

[SEU NOME COMPLETO]
Estudante de Pós-Graduação em Inteligência Artificial Aplicada
UniSENAI — Brasil
[SEU E-MAIL]

---

# PARTE 4 — REFERÊNCIAS DE CADA AFIRMAÇÃO DO E-MAIL (Partes 2 e 3)

Não faz parte do texto do e-mail — é para você ter à mão se a professora questionar algum número ou
afirmação específica. Cada linha abaixo aponta exatamente de onde veio o dado, incluindo o arquivo
do projeto onde a afirmação está documentada com mais detalhe (`Artigo/DECISOES.md` = nosso log de
decisões metodológicas, em formato ADR).

| Afirmação no e-mail | Fonte | Documentação interna |
|---|---|---|
| Dados originais de efluente da LAGWRP (TDS/Cloreto/Amônia/DBO, 2011–2026) | Portal CIWQS eSMR (California Water Boards), export original fornecido pela professora | `plano_projeto_TDS.md` §1 |
| Padrão cíclico do TDS ligado às secas de 2012-2016 e 2020-2022 | Índice PDSI (Palmer Drought Severity Index), NOAA NCEI nClimDiv — `climdiv-pdsidv`/`climdiv-pdsist`, série 1895-2026: https://www.ncei.noaa.gov/pub/data/cirs/climdiv/ | `Artigo/DECISOES.md`, D-14 e D-37 |
| Mecanismo de diluição (vazão caindo mais rápido que carga de sal) | Balanço de massa com carga de sal (lb/dia, direto do dataset) e vazão reconstruída de forma independente (a partir do Cloreto) — análise própria do projeto | `Artigo/DECISOES.md`, D-39 (WRTDS) e D-40 (balanço de massa) |
| Os 5 cenários climáticos (seco/normal/úmido/agravamento + RCP 8.5) | Simulação Monte Carlo própria (AR(1) sobre PDSI histórico) + projeção real de precipitação futura da API pública do Cal-Adapt (RCP 8.5, downscaling LOCA): historical https://api.cal-adapt.org/media/img/30698/pr_30yavg_ens32avg_historical_1961-1990.LOCA_2016-04-02.16th.CA_NV.tif · RCP8.5 https://api.cal-adapt.org/media/img/30700/pr_30yavg_ens32avg_rcp85_2035-2064.LOCA_2016-04-02.16th.CA_NV.tif | `Artigo/DECISOES.md`, D-51 |
| Água de origem explica ~88% da variação do TDS, conservação ~12% | Daniel B. Stephens & Associates, Inc. (2018). *Study to Evaluate Long-Term Trends and Variations in the Average Total Dissolved Solids Concentration in Wastewater and Recycled Water*. Southern California Salinity Coalition, 30 mar. 2018, Costa Mesa, CA. Número exato (88,17%/11,83%, sewershed "EMWD Combined") na **Tabela 11**, **p. 55 do relatório impresso = p. 70 do arquivo PDF**. | `material_apoio_referencias.md` Tema 9; `Artigo/DECISOES.md`, D-29 |
| "Volume-weighted source water TDS... is the significant determiner of influent TDS"; variação de 300 mg/L (CRA) e 200 mg/L (SWP) entre anos secos/úmidos; conservação = 1,2-1,7 mg/L por 1,0 gpcd | Mesmo relatório, seção 5 "Summary", lista de *key findings* — **p. 57 do relatório impresso = p. 72 do PDF** | `material_apoio_referencias.md` Tema 9 |
| "Influent water quality... used as a proxy or surrogate to understand the WWTP effluent water quality" | Mesmo relatório, Resumo Executivo — **p. 13 do PDF** (Resumo Executivo usa paginação própria "ES-x", não numerada como o corpo do relatório) | `Artigo/DECISOES.md`, D-28 |
| Tabela de R² influente vs. efluente por estação (Point Loma R²=0,98) | Mesmo relatório, **Tabela 8**, próximo à **p. 36-37 do relatório impresso = p. 52 do PDF** | `Artigo/DECISOES.md`, D-28 |
| Lista das agências participantes (8 membros oficiais da SCSC) | Mesmo relatório, página de rosto/missão — **p. 1 do PDF** (EMWD, IEUA, MWDSC, OCSD, OCWD, SDCWA, LACSD, SAWPA) | `material_apoio_referencias.md` Tema 9, nota |
| San Bernardino e Riverside Public Utilities como estudos de caso adicionais (não membros oficiais) | Mesmo relatório, Seção 2.7 e 2.8 — **p. 21-22 do relatório impresso = p. 36-37 do PDF** | `material_apoio_referencias.md` Tema 9, nota |
| Esse estudo (SCSC 2018) não incluiu a cidade de Los Angeles | Conclusão própria, cruzando a lista de agências acima (nenhuma delas é LASAN/cidade de Los Angeles) — não é uma frase textual do relatório, é uma inferência nossa a partir da lista | `material_apoio_referencias.md` Tema 9, nota |
| Portfólio de abastecimento de Los Angeles (LADWP: LA Aqueduct 41%, MWD 50%, subterrânea 7%, reciclada 2%) | LADWP — Sources of Supply: https://www.ladwp.com/who-we-are/water-system/sources-supply · MWD subpágina: https://www.ladwp.com/who-we-are/water-system/sources-supply/metropolitan-water-district-southern-california — páginas web institucionais, sem numeração de página aplicável. **Nota:** esse percentual é a média FY2020-2024; o relatório de 2024 específico tem 59%/36%/2%/3% — o mix varia ano a ano (ver linha seguinte). | `Artigo/DECISOES.md`, D-30 (atualização 2026-08-27) |
| **TDS de origem ponderado (LADWP) × TDS de efluente LAGWRP: r=0,912 (p=0,000005, n=14 anos)** | 21 relatórios anuais de qualidade da água da LADWP (2004-2024), pasta local `ladwp las drinking water quality report/`, Tabela II ("Aesthetic-based Secondary Standards") de cada um — TDS médio por fonte (LA Aqueduct, poços, Weymouth/Diemer/Jensen) e % de mistura anual. Todos os 21 anos conferidos célula a célula contra o PDF original (auditoria de 100%, zero discrepâncias). Cálculo em `script_28_ladwp_tds_origem.py`, saída em `ladwp_tds_por_fonte_historico.csv`/`ladwp_tds_origem_vs_efluente.csv`. | `Artigo/DECISOES.md`, D-54; `Artigo/src/resultados.tex` |
| Portfólio de abastecimento de Glendale (MWD 60-70%, subterrânea 30-40%) | City of Glendale — Water Quality Reports: https://www.glendaleca.gov/government/departments/glendale-water-and-power/reports-plans/water-quality-reports · WQR.20: https://www.glendaleca.gov/home/showpublisheddocument/57795/637285835714100000 — o WQR.20 é um PDF, mas a página exata do trecho citado **ainda não foi verificada** (só o resumo do texto foi lido via busca web, não o PDF completo) | `Artigo/DECISOES.md`, D-30 (atualização 2026-08-27) |
| Jensen e Weymouth como ETAs que abastecem a região/Glendale | ARCS LA Chapter — Water Treatment Plants Fact Sheet: https://orange-county.arcsfoundation.org/files/civicrm/persist/contribute/images/ARCS%20LA%20Chapter%20FT%20Water%20Treatment%20Plants%20Fact%20Sheet%20FINAL_web.pdf — é um PDF curto (fact sheet, 1-2 páginas), mas a página exata **ainda não foi verificada** (mesmo motivo acima) | `Artigo/DECISOES.md`, D-30 (atualização 2026-08-27) |
| Tillman WRP e La Cañada WRP como comparadoras recomendadas | Análise própria (mesma operadora/bacia que a LAGWRP para o Tillman; série mais longa da região para o La Cañada) — ainda **não obtidos**, é o pedido 2 do e-mail | `Artigo/DECISOES.md`, D-22 |

**Nota sobre como as páginas do relatório SCSC foram conferidas:** o relatório tem sua própria
numeração impressa no rodapé de cada página (ex. "...docx 55"), que **não é igual** ao número de
página do arquivo PDF em si (o PDF tem ~15 páginas de capa/sumário antes do corpo numerado como
"página 1"). As duas colunas acima citam os dois números para evitar ambiguidade — "p. 55 do
relatório impresso" é o que aparece no rodapé da página; "p. 70 do PDF" é a página que você vê no
contador do seu leitor de PDF (Adobe, Preview, etc.), a que realmente importa se ela for abrir o
arquivo digital.

**Sobre as fontes só verificadas por resumo web (Glendale WQR.20 e o fact sheet da ARCS):** essas
duas eu ainda não abri o PDF completo, só o resumo que apareceu na busca — se quiser que eu confirme
a página exata antes de você enviar o e-mail, posso baixar e ler os dois na íntegra.

**Se ela pedir para ver o projeto:** o repositório é público no GitHub
(`github.com/igorfnogueira/projeto-aplicado`) — todo o `Artigo/DECISOES.md` fica lá, com o
raciocínio completo de cada decisão, alternativas descartadas e evidência.
