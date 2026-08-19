# Solicitação de dados a LA Sanitation (LASAN) — instruções + mensagem pronta

---

# PARTE 1 — LEIA ANTES DE ENVIAR

## Expectativa realista

Isso é uma **aposta de baixo custo e retorno incerto**. Custa um e-mail; pode não ser respondido.
Não construa o cronograma do projeto contando com essa resposta — se chegar, é bônus. Prazo típico
de agências públicas americanas: de duas semanas a alguns meses.

## Por que vale tentar mesmo assim

Foi exatamente assim que o estudo SCSC/DBS&A obteve série de 1984-2016 para La Cañada: as agências
forneceram os dados diretamente aos consultores, e essas séries **não são públicas**. O portal
eSMR só cobre a era de reporte eletrônico (~2006 em diante).

## Para quem enviar

**Alvo principal — LA Sanitation (LASAN)**, operadora do LAGWRP:
- Helpline geral: **1-800-773-2489**
- Contato do LAGWRP (visitas/informações): **818-778-4226**
- Site: `lacitysan.org` — procure "Contact Us" ou o formulário de Public Records Request

**Duas vias possíveis, e a diferença importa:**

1. **Via informal (recomendada primeiro):** e-mail direto à equipe técnica/qualidade da água,
   apresentando-se como estudante. Costuma ser mais rápido e as pessoas respondem bem a pedido
   acadêmico específico.
2. **Via formal (CPRA):** o California Public Records Act garante a qualquer pessoa — inclusive
   estrangeiro — o direito de solicitar registros de agência pública. Mais garantido juridicamente,
   porém mais lento e burocrático. **Use só se a via informal não responder** em ~3 semanas.

## O que você está pedindo, em ordem de valor

A mensagem foi escrita nessa ordem **de propósito** — se eles só puderem atender parte, você recebe
o mais importante primeiro:

1. **Vazão do efluente (MGD), mensal, histórico completo** — é o item mais valioso. Hoje sua vazão
   é *derivada* pela identidade `lb/day ÷ (mg/L × 8,34)` (D-12). Ter a vazão medida validaria a
   reconstrução e removeria uma limitação declarada (§3.2 do `ESCOPO_E_LIMITACOES.md`).
2. **Volumes de água reciclada / desviada para reúso** — resolve a explicação alternativa que ainda
   está em aberto: a vazão caiu por conservação ou por desvio para reúso? Isso afeta diretamente o
   argumento causal do artigo.
3. **TDS, cloreto, amônia e BOD do efluente anteriores a 2011** — estende a série primária e dá
   mais ciclos de seca para testar D-14/D-37.
4. **TDS da água de abastecimento** — a lacuna D-30. Provavelmente o LASAN **não** tem (é o LADWP
   quem abastece), mas custa nada perguntar e eles podem encaminhar.

## Ajustes que você precisa fazer antes de enviar

- [ ] Substituir `[SEU NOME COMPLETO]` e `[SEU E-MAIL]`
- [ ] Confirmar o nome oficial do curso e da instituição (está como "UniSENAI, Brazil")
- [ ] Se seu orientador autorizar, incluir o nome dele — pedido acadêmico com orientador
      identificado tem taxa de resposta melhor
- [ ] Ajustar a data-limite se seu prazo for diferente de 30 dias

## Ponto de honestidade

A mensagem diz que é pesquisa acadêmica sem fins comerciais e oferece citar a fonte. **Cumpra isso.**
Se os dados vierem e forem usados, credite o LASAN no artigo e considere enviar uma cópia do
trabalho finalizado — foi oferecido no texto.

---

# PARTE 2 — MENSAGEM PRONTA PARA ENVIO (em inglês)

**Assunto sugerido:**
`Academic data request — historical effluent monitoring data, LA-Glendale Water Reclamation Plant`

---

Dear LA Sanitation Water Quality Team,

My name is [SEU NOME COMPLETO], and I am a graduate student in Applied Artificial Intelligence at
UniSENAI, Brazil. I am writing to request historical monitoring data for the Los Angeles–Glendale
Water Reclamation Plant (LAGWRP) for an academic research project.

**About the research**

My project analyzes long-term trends in effluent salinity (Total Dissolved Solids) at LAGWRP,
using the monthly eSMR record from February 2011 to February 2026 obtained through the CIWQS
portal. The study applies statistical and machine-learning methods to assess whether TDS
concentrations have been rising, and to identify the underlying drivers.

Our preliminary findings are that the observed rise in TDS concentration is explained almost
entirely by declining effluent flow rather than by an increase in salt mass load — the salt load
itself has been decreasing. We would like to strengthen and validate these findings with
additional data that is not available through the public eSMR portal.

**Data requested (in order of importance)**

1. **Monthly effluent flow (MGD)** for the full available period of record.
   *Why:* our current flow series is derived algebraically from paired concentration and mass-load
   values (mg/L and lb/day). Measured flow data would allow us to validate that reconstruction.

2. **Monthly volumes of recycled water produced or diverted** (i.e., effluent not discharged to the
   Los Angeles River) for the full available period of record.
   *Why:* this would let us distinguish whether the observed decline in discharge flow reflects
   reduced influent volume (water conservation) or increased diversion to reuse — an important
   distinction for our conclusions.

3. **Monthly effluent concentrations of Total Dissolved Solids, Chloride, Ammonia, and BOD prior
   to 2011**, as far back as records permit.
   *Why:* the electronic eSMR record appears to begin around 2011. A longer series would let us
   evaluate more complete drought cycles.

4. **Source (supply) water TDS concentrations** for the plant's service area, if LASAN holds such
   records.
   *Why:* regional literature identifies source water quality as the dominant driver of wastewater
   salinity. If this information is held by LADWP rather than LASAN, I would be grateful for a
   referral.

**Format and scope**

Any machine-readable format (CSV, Excel) would be ideal, but I am glad to work with whatever format
is convenient — including scanned reports. Monthly resolution is sufficient; daily data is not
necessary. If only part of this request can be accommodated, items 1 and 2 would be the most
valuable.

**Purpose and attribution**

This is non-commercial academic research for a graduate thesis. Any data provided would be cited
with full attribution to LA Sanitation, and I would be happy to share the completed study with your
team.

If a formal California Public Records Act request is the appropriate channel for this, please let
me know and I will submit one accordingly.

Thank you very much for your time and for the work your team does. I appreciate any assistance you
can offer.

Sincerely,

[SEU NOME COMPLETO]
Graduate Student, Applied Artificial Intelligence
UniSENAI — Brazil
[SEU E-MAIL]

---

# PARTE 3 — VARIANTE PARA O LACSD (opcional)

Se quiser tentar também a série de **La Cañada WRP (1984-2016)**, que o estudo SCSC identificou como
a mais longa da região, o destinatário é outro: **Los Angeles County Sanitation Districts (LACSD)** —
agência **diferente** do LASAN, apesar do nome parecido.

Adapte a mensagem acima trocando:
- Destinatário: `Dear Los Angeles County Sanitation Districts Water Quality Team,`
- O pedido central passa a ser: *monthly effluent TDS for the La Cañada WRP, and if available for
  other Joint Outfall System facilities (Long Beach, Los Coyotes, Pomona, San Jose Creek, Whittier
  Narrows), for the full period of record.*
- Justificativa a acrescentar: *"This request follows the 2018 Southern California Salinity
  Coalition study prepared by Daniel B. Stephens & Associates, which reported that LACSD provided
  effluent TDS records extending back to 1984 for these facilities."*

Citar o estudo SCSC é útil: mostra que você sabe que esses dados existem e que já foram
compartilhados antes para fim de pesquisa.
