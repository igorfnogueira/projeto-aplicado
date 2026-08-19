# Resumo Executivo — As Decisões que Mudaram o Rumo Deste Trabalho

> **Para que serve:** `Artigo/DECISOES.md` tem 40+ entradas — completo e rastreável, mas longo
> demais para alguém entender o projeto em 5 minutos. Este documento aponta só as decisões que
> **mudaram uma conclusão**, não as que só documentam uma escolha técnica sem consequência no
> resultado final. Para o raciocínio completo de qualquer item abaixo, siga o link `D-XX`.
>
> **Regra de manutenção:** atualizar só quando uma decisão nova muda o rumo do trabalho (não a
> cada entrada nova do ADR — a maioria das entradas é detalhe de implementação, não guinada).

**Classificação do projeto (Fase 1 do kickoff crítico, `inicio-de-projeto`):** **acadêmico** —
2026-08-19. Não se encaixa em N0-N3 (que presumem produto de software com usuários/deploy): é um
TCC de pós-graduação com dois entregáveis fixos (pipeline reprodutível + artigo científico), então
os gatilhos de subida de nível N0→N1→N2→N3 não se aplicam a este projeto. Revisitar essa
classificação só se o escopo mudar para além de um trabalho de defesa (ex. virar produto/serviço
real).

---

## 1. A hipótese central mudou — e a mudança é o resultado mais importante do projeto

O trabalho começou com a hipótese padrão da literatura (conservação de água → menos diluição →
TDS sobe de forma monotônica). Essa hipótese **não sobreviveu ao teste dos próprios dados**:

- A "tendência de alta" inicial (3,91 mg/L/ano, p=0,0056) **desaparece** quando restrita ao período
  pós-2012 (0,84 mg/L/ano, p=0,59) — [D-13](Artigo/DECISOES.md#d-13--a-quebra-eff-001eff-001a-é-artefato-de-modelagem-não-degrau-real).
- Investigando por quê, a série revelou um **padrão cíclico por regime** (alta 2011-2015, queda
  até 2019, alta até 2022), não uma reta — [D-14](Artigo/DECISOES.md#d-14--reenquadramento-padrão-cíclico-por-regime-não-tendência-monotônica).
- Esse padrão foi **testado contra uma variável externa independente** (o índice de seca PDSI do
  NOAA, sem nenhuma informação das datas do TDS) e confirmado: os *changepoints* do PDSI coincidem
  com as viradas de regime observadas — [D-37](Artigo/DECISOES.md#d-37--os-ciclos-de-tds-são-explicados-por-ciclos-de-seca-pdsi--confirma-d-14).

**Consequência prática:** o projeto não responde mais "o TDS está subindo?" com uma reta — responde
"o TDS sobe e desce em ciclos ligados à seca da Califórnia", uma afirmação mais defensável e mais
fiel aos dados.

## 2. O mecanismo é diluição, não mais sal — respondido diretamente, não por analogia

A literatura de referência (Nature Sustainability, 2020) propõe conservação→diluição como
mecanismo. Em vez de só citar esse mecanismo, o projeto o testou com os próprios dados da LAGWRP:

- A vazão do efluente foi **reconstruída** a partir de uma identidade física já presente no dataset
  (`lb/dia = mg/L × vazão × 8,34`) — [D-12](Artigo/DECISOES.md#d-12--reconstrução-da-vazão-do-efluente-validada-).
- O balanço de massa mostrou que a **carga de sal caiu** (−3,20%/ano) enquanto a **vazão caiu mais
  rápido ainda** (−3,85%/ano) — confirma diluição, não mais sal entrando no sistema —
  [D-40](Artigo/DECISOES.md#d-40--balanço-de-massa-confirma-diluição-não-mais-sal--mas-extrapolação-linear-dos-componentes-é-fisicamente-implausível).
- O WRTDS (normalização por vazão) confirmou de outro ângulo: **quase não sobra tendência**
  depois de descontar o efeito da vazão (p=0,064, não significativo) —
  [D-39](Artigo/DECISOES.md#d-39--wrtds-confirma-não-há-tendência-de-tds-depois-de-descontar-a-vazão).

## 3. A previsão de longo prazo virou uma faixa, não um número

Extrapolar linearmente carga e vazão por 20 anos produz vazão **negativa** em +20 anos —
fisicamente impossível — [D-40](Artigo/DECISOES.md#d-40--balanço-de-massa-confirma-diluição-não-mais-sal--mas-extrapolação-linear-dos-componentes-é-fisicamente-implausível).
A resposta não foi forçar um piso arbitrário: foi substituir o número único por uma **projeção
condicional a cenários climáticos** (seco/normal/úmido/agravamento), via Monte Carlo sobre o PDSI —
faixa de 594 a 721 mg/L em +20 anos, dependendo do cenário —
[D-41](Artigo/DECISOES.md#d-41--projeção-por-cenários-climáticos-substitui-a-previsão-pontual-de-longo-prazo).

## 4. Um resultado que contraria a hipótese do professor foi mantido, não escondido

A correlação TDS↔BOD saiu **negativa e não significativa** em todos os tratamentos de dado testado
— o oposto do que a hipótese do professor previa (salinidade alta prejudicando a remoção de matéria
orgânica). Isso está escrito com todas as letras no artigo, não suavizado —
[D-16](Artigo/DECISOES.md#d-16--tratamento-dos-valores-nd-do-bod-65-da-série).

## 5. O que ainda está em aberto

- GAM e os demais métodos da seção 3.f do plano original não foram implementados —
  <!-- PENDENTE: existe uma decisão explícita de não implementar (e por quê), ou é só falta de
  tempo? Ver entrada nova em Artigo/DECISOES.md para registrar a resposta real. -->
- A página de título do artigo (`Artigo/template.tex`) ainda tem os placeholders `Título do
  documento` / `Autor A, Autor B, Autor C` —
  <!-- PENDENTE: título real do trabalho e nomes reais dos autores, para preencher antes da entrega. -->

---

**Como usar este documento:** leia isto primeiro. Se precisar do raciocínio completo de qualquer
item (dados usados, alternativas descartadas, evidência numérica), siga o link para a entrada
correspondente em `Artigo/DECISOES.md`. Para o vocabulário técnico usado acima, ver `GLOSSARIO.md`.
Para as fronteiras e fragilidades conhecidas do trabalho, ver `ESCOPO_E_LIMITACOES.md`.
