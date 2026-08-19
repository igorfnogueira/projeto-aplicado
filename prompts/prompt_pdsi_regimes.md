# Prompt para Claude Code — Testar se os ciclos de TDS são explicados por seca (PDSI)

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

Este é o **Passo 1** da nova etapa: o teste mais barato e mais informativo disponível agora.
Ele decide se o reenquadramento cíclico (D-14) se sustenta antes de investir em WRTDS,
balanço de massa ou busca de estação comparadora.

---

Leia primeiro, nesta ordem:
- `Artigo/DECISOES.md` — em especial **D-13** (quebra EFF-001 é artefato), **D-14** (reenquadramento
  cíclico, pendente de confirmação), **D-29** (driver dominante é a água de origem, não a
  conservação) e **D-30** (lacuna: falta a série de TDS de origem)
- `material_apoio_referencias.md` — **Tema 9**, especialmente §9.1 e §9.5
- `plano_projeto_TDS.md` — seções 1.5 (reconstrução da vazão) e 4.3 (MLflow)

## Objetivo

Testar quantitativamente a hipótese de D-14: **os ciclos de TDS do LAGWRP são dirigidos por ciclos
de seca**, e não por uma tendência monotônica de conservação.

Padrão a explicar (já identificado no projeto):
2011 baseline ~563 mg/L → alta 2011-2015 (+46%) → queda 2015-2019 (−21%) → alta 2019-2022 (+21%)
→ estável/leve queda 2022-hoje. Pontos de virada aproximados: **2012, 2015, 2019, 2022**.

## Etapa 1 — Obter os dados de seca

Baixe o **PDSI mensal** do NOAA NCEI (nClimDiv), que é o índice usado pelo estudo SCSC/DBS&A:

- Interface: https://www.ncei.noaa.gov/access/monitoring/historical-palmers/
- Arquivos legíveis por máquina: https://www.ncei.noaa.gov/pub/data/cirs/climdiv/
  (procure o arquivo `climdiv-pdsidv-*` — PDSI por divisão climática)

**Confirme na documentação** (não assuma): o código de estado da Califórnia e qual divisão
climática cobre a área de Los Angeles/Vale de San Fernando. Se a documentação for ambígua,
registre a ambiguidade em vez de chutar.

Baixe **três séries**, porque elas testam mecanismos diferentes:
1. **PDSI estadual da Califórnia** — é o que o SCSC usou, como generalização.
2. **PDSI da divisão climática de Los Angeles** — seca local.
3. Se disponível sem esforço desproporcional: PDSI da **Sierra Norte / bacia do Sacramento**
   (origem da água do State Water Project).

**Por que três:** o mecanismo de D-29 diz que a seca afeta o TDS da **água de origem**, que vem
importada do SWP (norte da Califórnia) e do Colorado River. Logo, a seca *no norte* pode explicar
melhor o TDS de LA do que a seca *local*. Se a série do norte explicar mais que a local, isso é
evidência forte a favor do mecanismo de água de origem. Teste e reporte as três.

Salve como CSV na pasta do projeto, com nome descritivo (ex. `pdsi_california_estadual.csv`).

## Etapa 2 — Análises a executar

Crie `script_18_pdsi_regimes.py`. Ele deve:

**2.1 Alinhamento e inspeção**
- Alinhar o PDSI mensal com a série canônica de TDS (mesma grade mensal, período comum).
- Gráfico sobreposto: TDS (eixo esquerdo) × PDSI invertido (eixo direito) — a hipótese prevê
  espelhamento (PDSI baixo = seca = TDS alto).

**2.2 Correlação com defasagem (obrigatório, não opcional)**
- Função de correlação cruzada para **defasagens de 0 a 36 meses**.
- Justificativa: água importada tem tempo de trânsito e mistura em reservatório; o TDS do efluente
  não responde à seca no mesmo mês. Testar só a correlação contemporânea provavelmente
  subestimaria a relação real.
- Reporte a defasagem de correlação máxima e o valor.

**⚠️ Cuidado estatístico obrigatório:** ambas as séries são autocorrelacionadas e possivelmente
não estacionárias — correlacioná-las diretamente gera **correlação espúria**. Isso é o mesmo tipo
de armadilha já documentada em D-15. Portanto:
- Reporte a correlação bruta **e** a correlação sobre as séries diferenciadas/destendenciadas.
- Use graus de liberdade efetivos ajustados por autocorrelação para o p-valor.
- Se a correlação sobrevive só na versão bruta e desaparece na destendenciada, diga isso
  claramente — é resultado, não falha.

**2.3 Coincidência dos pontos de virada**
- Rode detecção de pontos de mudança (changepoint) **na série de PDSI de forma independente**,
  sem informar as datas do TDS ao algoritmo.
- Compare as datas detectadas com 2012, 2015, 2019, 2022.
- Reporte a diferença em meses para cada par. Coincidência dentro de ~6-12 meses é
  substantivamente relevante (dado o tempo de trânsito da água).
- **Não force o alinhamento**: se as datas não baterem, reporte a divergência.

**2.4 Decomposição dos dois mecanismos** (esta é a parte mais valiosa)
Com a vazão reconstruída (D-12) já disponível, teste os dois caminhos causais separadamente:
- **Caminho A (água de origem, dominante segundo o SCSC):** PDSI → TDS do efluente
- **Caminho B (conservação/diluição, mecanismo da Nature 2020):** PDSI → vazão → TDS do efluente

Rode uma regressão múltipla `TDS ~ PDSI(defasado) + vazão` e decomponha a importância relativa
das duas variáveis (método LMG, equivalente ao pacote R `relaimpo` usado pelo SCSC — em Python,
implemente via `statsmodels` ou biblioteca equivalente).

**Compare o resultado com o benchmark do SCSC:** eles acharam ~88% para água de origem e ~12%
para consumo per capita. Nossa decomposição bate na mesma ordem de grandeza? Reporte a comparação
explicitamente.

**2.5 Regressão por regime**
- Ajuste um modelo com variável indicadora de regime (os 5 períodos) e verifique se o PDSI ainda
  tem poder explicativo *dentro* dos regimes, ou se o efeito é todo absorvido pelas dummies.

## Etapa 3 — Interpretação honesta

Três desfechos possíveis, todos legítimos:

1. **PDSI explica bem os ciclos** → D-14 confirmado; seguir com WRTDS/balanço de massa/regime,
   e reescrever o enquadramento causal do artigo em torno de água de origem + seca.
2. **PDSI explica parcialmente** → registrar a fração explicada e o que resta sem explicação;
   o TDS de origem real (D-30) provavelmente explicaria o resto.
3. **PDSI não explica** → D-14 fica sem sustentação empírica com os dados disponíveis, e isso
   **deve ser reportado como resultado negativo**, não escondido. Nesse caso, reavaliar se o
   reenquadramento cíclico deve ser mantido.

Não escolha a interpretação que "salva" a hipótese. O objetivo é saber se ela se sustenta.

## Regras herdadas (obrigatórias)

- Logar tudo no MLflow conforme §4.3 do plano (params, seed, métricas, artefatos, tempo).
- Gravar resultados em `pdsi_regimes_resultados.csv`/`.json`; linha nova em
  `resultados_comparacao.csv` se gerar métrica comparável.
- Figura em `Artigo/images/` com nome ASCII (ex. `pdsi-vs-tds-regimes.png`).
- Atualizar `notebook.ipynb`, `README.md`, `README.pt-br.md` na mesma execução.
- Avaliar impacto em `Artigo/src/metodologia.tex` e `resultados.tex`; compilar o LaTeX se alterar.
- **Registrar em `Artigo/DECISOES.md`**: atualizar o status de D-14 (confirmada / parcialmente
  confirmada / não sustentada) com a evidência, e criar entrada nova para qualquer decisão
  metodológica tomada aqui (ex. qual defasagem foi adotada e por quê).
- Nunca inventar resultado. Se o download do PDSI falhar ou a documentação do NOAA estiver
  ambígua, pare e me avise em vez de improvisar com dados de outra fonte.

## Entrega

1. As três séries de PDSI baixadas, como CSV na pasta do projeto.
2. `script_18_pdsi_regimes.py` funcionando e logado no MLflow.
3. Relatório objetivo respondendo: **os ciclos de TDS do LAGWRP são explicados por ciclos de seca?**
   Com números (correlação, defasagem, importância relativa, coincidência de datas) e um dos três
   desfechos da Etapa 3 declarado explicitamente.
4. `DECISOES.md` atualizado com o status de D-14.
