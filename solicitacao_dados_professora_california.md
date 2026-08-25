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

## Os dois pedidos, em ordem de valor (por que essa ordem)

1. **TDS/condutividade da água de origem (State Water Project e/ou Colorado River Aqueduct)** — é o
   item de maior valor. A literatura de referência do projeto (relatório da Southern California
   Salinity Coalition, 2018) mostra que a qualidade da água de origem explica ~88% da variabilidade
   do TDS de efluente nas estações estudadas, contra ~12% de conservação local — e essa variável
   está **ausente** do nosso dataset. Hoje usamos o índice de seca PDSI como *proxy* indireto; ter
   o dado real substituiria uma aproximação por uma medida direta.
2. **TDS de efluente de uma estação comparadora** (Donald C. Tillman WRP ou La Cañada WRP) — testa
   se o padrão cíclico ligado a seca encontrado na LAGWRP se replica em outra estação da região, ou
   é específico dela. Hoje a conclusão do projeto se apoia em dados de uma única estação.

## Ponto de honestidade

O e-mail descreve os achados do projeto de forma resumida e precisa (mecanismo de diluição
confirmado, reenquadramento cíclico, limitação da água de origem) — não exagera nem promete mais
do que o projeto de fato mostrou. Se os dados vierem e forem usados, credite a fonte no artigo.

---

# PARTE 2 — MENSAGEM PRONTA PARA ENVIO (em inglês)

**Assunto sugerido:**
`Follow-up request — additional data for the LAGWRP salinity study`

---

Dear [NOME DA PROFESSORA],

I hope this message finds you well. Thank you again for providing the original LAGWRP effluent
monitoring data (eSMR export, TDS/Chloride/Ammonia/BOD, 2011–2026) that made this project possible.
I wanted to share where the analysis has led and ask for two additional pieces of data that would
meaningfully strengthen it.

**What we found so far**

The data show that effluent TDS at LAGWRP does not follow a simple upward trend — it follows a
**cyclical pattern tied to California's recent droughts** (2012–2016 and 2020–2022), confirmed
independently using NOAA's Palmer Drought Severity Index. A mass-balance decomposition (salt load
vs.\ flow, both derived from the same dataset) confirms the mechanism is **dilution**: effluent flow
has been declining faster than salt load, not the reverse. Because long-term extrapolation proved
physically unstable in this drought-driven series, our +10/+15/+20-year projections are now
presented as climate-scenario ranges (dry/normal/wet) rather than a single forecast number.

**Where the analysis is currently limited**

Regional literature (a 2018 study by the Southern California Salinity Coalition, covering 26
treatment plants) found that **source (supply) water TDS explains roughly 88% of effluent TDS
variability**, versus about 12% from local water conservation. We do not have a source-water TDS
series, so our drought index (PDSI) is only an indirect proxy for this dominant driver — and our
conclusions are based on a single treatment plant.

**What would help, in order of value**

1. **Monthly TDS or electrical conductivity of the source water supplied to the LAGWRP service
   area** (State Water Project and/or Colorado River Aqueduct deliveries, e.g.\ from MWDSC), for as
   long a period as available. This is the single most valuable addition — it would let us replace
   our drought-index proxy with the actual dominant driver identified in the literature.
2. **Monthly effluent TDS (or chloride/conductivity) from a comparable treatment plant** — ideally
   Donald C. Tillman WRP or La Cañada WRP — to test whether the cyclical, drought-linked pattern we
   found at LAGWRP replicates elsewhere, or is specific to this plant.

Any machine-readable format (CSV, Excel) works well, and any subset of this request is genuinely
useful — item 1 alone would already be a significant improvement.

**Sharing results**

I would be glad to share the current draft of the article, the analysis notebook, or a short
summary of findings — whichever is more useful to you. This is non-commercial academic research for
a graduate thesis, and any data provided would be properly credited.

Thank you again for your support with this project — please let me know if there's a better contact
or channel for either request.

Warm regards,

[SEU NOME COMPLETO]
Graduate Student, Applied Artificial Intelligence
UniSENAI — Brazil
[SEU E-MAIL]
