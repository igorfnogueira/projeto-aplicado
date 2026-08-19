# Registro de Decisões — Projeto Aplicado TDS/LAGWRP

> **Propósito:** registrar *por que* cada escolha do projeto foi feita, não só *o que* foi feito.
> O `resultados_comparacao.csv` e o MLflow registram resultados; este arquivo registra o raciocínio.
>
> **Regra de manutenção:** toda decisão metodológica relevante entra aqui **na mesma execução** em
> que é tomada, com motivo e alternativa descartada (regra da seção 2.2 do `plano_projeto_TDS.md`).
> Uma decisão sem alternativa descartada registrada está incompleta.

## Formato de cada entrada

```
### D-XX — Título curto
- **Data:** AAAA-MM-DD
- **Status:** Decidida | Pendente | Revertida | Em verificação
- **Contexto:** o problema que exigiu a decisão
- **Decisão:** o que foi escolhido
- **Alternativas descartadas:** o que foi considerado e por que não
- **Evidência:** arquivo/script/run que embasa
```

---

## Parte 1 — Governança e ferramentas

### D-01 — Descartar o notebook anterior e reconstruir do zero
- **Data:** 2026-08-13 · **Status:** Decidida
- **Contexto:** existia `projeto_aplicado_v1 (1).ipynb` com EDA e Random Forest/GridSearchCV.
- **Decisão:** ignorar o notebook e construir toda a bateria do zero.
- **Alternativas descartadas:** *refatorar o notebook existente* — descartada porque o arquivo estava com JSON truncado/corrompido (ilegível) e porque herdar decisões de pré-processamento não documentadas comprometeria a rastreabilidade exigida pela governança.
- **Evidência:** decisão do usuário; `plano_projeto_TDS.md` §0.

### D-02 — MLflow local como camada de rastreamento de experimentos
- **Data:** 2026-08-13 · **Status:** Decidida
- **Contexto:** bateria de ~10 métodos × 3 horizontes × variantes de CV gera dezenas de execuções; o CSV sozinho não versiona experimentos descartados nem hiperparâmetros.
- **Decisão:** MLflow rodando local (`mlruns/`), sem nuvem. `resultados_comparacao.csv` passa a ser export das runs finais.
- **Alternativas descartadas:** *Weights & Biases* — dashboards melhores, mas cloud por padrão; *DVC* — mais forte para versionar dados, mas curva de aprendizado desproporcional para projeto acadêmico solo; *só o CSV manual* — não guarda histórico de tentativas descartadas.
- **Evidência:** `plano_projeto_TDS.md` §4.3; `utils/experiment_tracking.py`; pasta `mlruns/`.

### D-03 — Notebook único sincronizado com os `.py`
- **Data:** 2026-08-13 · **Status:** Decidida
- **Decisão:** manter `notebook.ipynb` único, atualizado na mesma execução de qualquer alteração em script.
- **Alternativas descartadas:** *um notebook por metodologia* — dificultaria a leitura corrida do projeto no GitHub, que é o objetivo declarado.
- **Evidência:** `plano_projeto_TDS.md` §4.1.

### D-04 — READMEs bilíngues com seletor de idioma
- **Data:** 2026-08-13 · **Status:** Decidida
- **Decisão:** `README.md` (inglês, padrão GitHub) + `README.pt-br.md`, com seletor de idioma no topo de ambos.
- **Evidência:** `plano_projeto_TDS.md` §4.2.

### D-05 — Artigo LaTeX como documento vivo
- **Data:** 2026-08-13 · **Status:** Decidida
- **Decisão:** `Artigo/template.tex` atualizado a cada resultado, não ao final do projeto.
- **Evidência:** `Prompt — Manutenção contínua do artigo científico do Projeto Aplicado.md`.

---

## Parte 2 — Escopo e estrutura dos dados

### D-06 — Unificar `EFF-001` e `EFF-001A` como uma única série
- **Data:** 2026-08-13 · **Status:** Decidida (com ressalva — ver D-13)
- **Contexto:** o código do ponto de monitoramento muda em ~2012.
- **Decisão:** tratar como o mesmo ponto físico, unificando as séries.
- **Justificativa:** mesma latitude/longitude (34,1372 / −118,27422), mesmo método analítico, transição contínua mês a mês (580 → 598 mg/L) sem descontinuidade.
- **Alternativas descartadas:** *tratar como séries separadas* — descartada porque são fisicamente o mesmo efluente; separar reduziria arbitrariamente a série a 14 anos.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `2_quebra_localizacao`.

### D-07 — Pontos de monitoramento secundários apenas como contexto
- **Data:** 2026-08-13 · **Status:** Decidida
- **Contexto:** `R-4`, `R-7`, `RSW-650`, `RSW-654` são água receptora (LA River), não efluente.
- **Decisão:** usar apenas como contexto na introdução/discussão; nenhuma análise dedicada.
- **Alternativas descartadas:** *incluir na bateria de previsão* — descartada porque os objetivos do professor tratam do efluente da estação; incluir água receptora misturaria dois sistemas com dinâmicas diferentes.

### D-08 — Série canônica: `Monthly Average (Mean)` em mg/L
- **Data:** 2026-08-13 · **Status:** Decidida
- **Decisão:** série mensal a partir das linhas `Calculated Method == "Monthly Average (Mean)"`, `Units == "mg/L"`.
- **Alternativas descartadas:** *amostras brutas* — frequência muito desigual entre parâmetros (BOD quase diário, TDS mensal), inviabilizando merge direto.

### D-09 — Usar a média mensal pré-calculada em vez de reagregar
- **Data:** 2026-08-13 · **Status:** Decidida
- **Contexto:** havia risco de a agregação da planta usar critério próprio não documentado.
- **Decisão:** usar a pré-calculada.
- **Justificativa:** a reagregação a partir das amostras brutas produziu **diferença média absoluta de 0,0 mg/L** e slope idêntico (3,9064 mg/L/ano) — as duas são equivalentes, então não há motivo para reagregar.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `4_reagregacao`.

### D-10 — Nenhuma imputação de meses faltantes
- **Data:** 2026-08-13 · **Status:** Decidida
- **Justificativa:** a verificação encontrou **0 meses faltantes** em 182 pontos — a questão não se aplica.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `7_meses_faltantes`.

### D-11 — Tratamento de outliers: manter a série completa
- **Data:** 2026-08-13 · **Status:** Decidida
- **Justificativa:** o resultado é robusto às três variantes — série completa 3,906 mg/L/ano (p=0,0056), winsorizada 5-95% 3,626 (p=0,0055), remoção de 6 pontos por resíduo STL 3σ 3,674 (p=0,0079). Como a conclusão não muda, manter tudo é a opção que menos intervém no dado.
- **Alternativas descartadas:** winsorização e remoção por STL — tecnicamente válidas, mas removem informação sem alterar a conclusão.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `6_outliers`.

---

## Parte 3 — Achados que mudaram o rumo do projeto

### D-12 — Reconstrução da vazão do efluente validada ⭐
- **Data:** 2026-08-13 · **Status:** Decidida
- **Contexto:** o dataset não traz vazão explicitamente, mas traz o mesmo parâmetro em mg/L e lb/day.
- **Decisão:** reconstruir a vazão via `vazão(MGD) = lb/day ÷ (mg/L × 8,34)` e promover o `lb/day` de dado secundário a peça central da análise causal.
- **Validação (forte):** as vazões derivadas independentemente de TDS e de Cloreto coincidem — 9,4863 vs 9,4877 MGD de média (diferença de 0,015%). Amônia (8,37) e BOD (9,09) ficam na mesma ordem. Média ~9,5 MGD = 47% da capacidade nominal de 20 MGD, plausível. **0 pontos fora da faixa fisicamente possível.**
- **Alternativas descartadas:** *ignorar o lb/day como secundário* (posição original do plano) — descartada porque a vazão é a variável do mecanismo causal descrito no artigo da Nature.
- **Evidência:** `vazao_reconstruida_resultados.csv`; `script_16_reconstrucao_vazao.py`.

### D-13 — A quebra EFF-001→EFF-001A é artefato de modelagem, não degrau real
- **Data:** 2026-08-13 · **Status:** Decidida (investigação concluída)
- **Contexto:** um modelo OLS com termo de step estimou degrau de +137 mg/L na transição, o que ameaçava invalidar a tendência.
- **Decisão:** rejeitar a hipótese de degrau artificial; o degrau era efeito de forçar uma reta única + step sobre uma série que é **cíclica/por regime**, não monotônica.
- **Justificativa:** transição contínua mês a mês (580 → 598 mg/L), mesmo método analítico, mesmo MDL, mesma coordenada geográfica.
- **⚠️ Achado colateral crítico:** ainda assim, a tendência **desaparece** quando calculada só no período pós-2012: 0,837 mg/L/ano com **p = 0,59** (não significativo), contra 3,906 mg/L/ano com p = 0,0056 na série completa. Ou seja, a tendência de 15 anos depende materialmente do trecho 2011-2012. Isso **precisa constar como limitação no artigo**.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `2_quebra_localizacao`.

### D-14 — Reenquadramento: padrão cíclico por regime, não tendência monotônica
- **Data:** 2026-08-13 · **Status:** **Confirmada** (2026-08-14 — ver D-37 para a evidência quantitativa completa: PDSI explica bem os ciclos)
- **Contexto:** a investigação de D-13 revelou que a série tem estrutura por período, não inclinação constante.
- **Padrão identificado:** 2011 baseline (563 mg/L) → alta 2011-2015 (+46%, coincide com a seca da Califórnia 2012-2016) → queda 2015-2019 (−21%) → alta 2019-2022 (+21%) → estável/leve queda 2022-hoje.
- **Decisão final:** reformular a Etapa 3 em torno de regime/ciclo ligado a seca (PDSI), não conservação isolada — com WRTDS e balanço de massa testando a decomposição água-de-origem × vazão local.
- **Alternativas descartadas:** manter o enquadramento de tendência monotônica — descartada porque a checagem quantitativa (D-37) mostra que um índice de seca independente (PDSI, sem qualquer informação das datas do TDS) explica 68-79% da importância relativa na decomposição LMG e tem changepoints coincidindo com as viradas observadas dentro de ~4-9 meses (3 de 4 séries) a ~15 meses (1 caso).
- **Evidência:** D-37; `pdsi_regimes_resultados.csv`; `script_18_pdsi_regimes.py`.

---

## Parte 4 — Decisões de tratamento ainda pendentes (aguardando o usuário)

### D-15 — Correção de autocorrelação no Mann-Kendall ⚠️ decisão de maior impacto
- **Status:** **Pendente**
- **Contexto:** a significância da tendência **inverte** conforme a correção adotada:

| Variante | Slope (mg/L/ano) | p-valor | Significativo? |
|---|---|---|---|
| MK simples | 3,907 | 0,0056 | Sim |
| Hamed & Rao (correção de variância) | 3,907 | 0,182 | **Não** |
| Pre-whitening | 3,907 | 0,417 | **Não** |
| Trend-free pre-whitening (TFPW) | 3,907 | 0,00014 | Sim (forte) |
| Seasonal Kendall | 4,667 | 0,0038 | Sim |

- **Implicação:** escolher a variante define se o resultado central do trabalho é "tendência significativa" ou "sem evidência de tendência". Não pode ser escolha silenciosa.
- **Recomendação técnica:** reportar **todas as variantes** no artigo como análise de robustez, em vez de escolher uma. A literatura reconhece que pre-whitening simples reduz poder estatístico e TFPW foi proposto justamente para corrigir isso.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `8_autocorrelacao_mk`.

### D-16 — Tratamento dos valores ND do BOD (65% da série)
- **Status:** **Pendente**
- **Resultado dos 5 tratamentos testados** (correlação TDS-BOD destendenciada):

| Variante | Valor substituto | r | p |
|---|---|---|---|
| A — MDL/2 | 1,5 | −0,079 | 0,289 |
| B — Zero | 0,0 | −0,068 | 0,360 |
| F — Kaplan-Meier | 3,0 | −0,126 | 0,090 |
| G — ROS (Helsel) | 2,517 | −0,108 | 0,147 |
| H — MLE lognormal | 2,738 | −0,122 | 0,102 |

- **Achado relevante:** em **todas** as variantes a correlação é **negativa e não significativa** — ou seja, a hipótese do professor (TDS alto piora a remoção de BOD, gerando correlação positiva) **não se confirma** nesses dados. O sinal é inclusive oposto. A escolha do tratamento muda a magnitude, não a conclusão — o que é uma boa notícia para a robustez.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `1_nd_bod`.

### D-17 — Mudanças de MDL ao longo da série
- **Status:** **Pendente**
- **Contexto:** foram identificadas 4 mudanças de MDL, três delas com diferença de nível estatisticamente detectável:

| Mudança | p (Mann-Whitney no nível de TDS) | Preocupante? |
|---|---|---|
| MDL 28 → 25 (2011-06-04) | 0,017 | Sim |
| MDL 25 → 35 (2016-12-19) | 0,052 | Limítrofe |
| MDL 35 → 28 (2021-02-06) | 0,0099 | Sim |
| MDL 28 → 35 (2021-09-01) | 0,618 | Não |
- **Questão em aberto:** essas diferenças de nível são causadas pela mudança de método ou são coincidência temporal com mudanças reais de regime (que D-14 identificou nos mesmos períodos)? Ambos os efeitos se confundem.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `3_mudanca_mdl`.

### D-18 — Agregação anual: não significativa em nenhuma variante
- **Status:** Informativo (não requer decisão, mas requer registro no artigo)
- **Resultado:** média ano civil 4,75 (p=0,379); média ano hidrológico 3,695 (p=0,398); mediana ano civil 4,00 (p=0,435); mediana ano hidrológico 5,262 (p=0,300).
- **Leitura honesta:** nenhuma variante anual atinge significância — esperado, porque n cai de 182 para 15-16 pontos, com perda severa de poder estatístico. Não contradiz a análise mensal, mas também não a corrobora.
- **Evidência:** `matriz_sensibilidade_resultados.csv`, item `5_agregacao_anual`.

---

## Parte 5 — Estação comparadora (dados externos)

### D-19 — Rejeitar o ECHO DMR como fonte de dados comparativos
- **Data:** 2026-08-14 · **Status:** Decidida
- **Contexto:** buscava-se uma segunda estação para testar se o padrão cíclico se replica.
- **Decisão:** não usar EPA ECHO/DMR; usar o portal **CIWQS eSMR** (mesma fonte dos dados originais do LAGWRP).
- **Justificativa:** o DMR só contém o que a outorga obriga a reportar, em formato de conformidade — janela curta e cobertura irregular. O eSMR entrega formato idêntico ao `TDS.csv` (parsing zero-custo), série desde 2010, colunas MDL/RL/Qual e ambas as unidades (mg/L e lb/day, necessárias para replicar a reconstrução de vazão de D-12).
- **Evidência:** análise dos CSVs baixados (ver D-20, D-21).

### D-20 — Rejeitar Point Loma (CA0107409) como comparadora
- **Data:** 2026-08-14 · **Status:** ⚠️ **Parcialmente revertida em 2026-08-14 — ver D-28**
- **Justificativa original:** o CSV baixado tem 53 medições de TDS, **todas de `Raw Sewage Influent`** — nenhuma de efluente. Valores 1.880-2.160 mg/L (≈3× o LAGWRP), confirmando intrusão de água do mar documentada. Janela de apenas 5 anos (2021-2026).
- **Evidência:** `pont loma wwtp california id ca0107409  august 2021 to august 2026.csv`.

### D-28 — Reversão parcial de D-20: dados de influente são proxy válido de efluente
- **Data:** 2026-08-14 · **Status:** Decidida (revisa D-20)
- **Contexto:** a leitura integral do estudo SCSC/DBS&A (2018) trouxe evidência que contradiz o motivo pelo qual Point Loma foi descartada.
- **Achado:** o estudo afirma explicitamente que "TDS entering a WWTP nearly matched the discharge water quality from the WWTP's effluent. Therefore influent water quality is used as a proxy or surrogate to understand the WWTP effluent water quality." A Tabela 8 reporta R² de influente vs. efluente por planta — e **Point Loma tem R² = 0,98, o mais alto de todas as 14 plantas avaliadas**.
- **Decisão revisada:** o argumento "só tem influente, logo não serve" **não se sustenta**. Os dados de Point Loma já baixados podem ser usados para testar **padrão temporal** (formato do ciclo, timing das viradas), que é justamente o que interessa para validar D-14.
- **O que continua valendo de D-20:** a ressalva do **nível absoluto** permanece — ~2.000 mg/L vs. ~600 mg/L do LAGWRP, por intrusão salina costeira. Comparar amplitude absoluta seria incorreto; comparar forma normalizada da série (ex. z-score ou variação percentual) é legítimo.
- **Limitação remanescente:** janela de 5 anos (2021-2026) cobre apenas o final da nossa série — insuficiente para testar os ciclos de 2011-2019.
- **Evidência:** Estudo SCSC/DBS&A (2018), Tabela 8; `material_apoio_referencias.md` §9.3.

### D-29 — O driver dominante do TDS é a água de origem, não a conservação
- **Data:** 2026-08-14 · **Status:** Decidida (achado de literatura, muda o enquadramento causal)
- **Contexto:** o projeto foi desenhado em torno do mecanismo da Nature (2020): conservação → menos vazão → menos diluição → TDS sobe.
- **Achado do estudo SCSC/DBS&A (2018), com texto completo verificado:** a decomposição de importância relativa (`relaimpo`, método lmg) mostra que o **TDS da água de origem responde por 88% da variabilidade** do TDS de influente (EMWD combinado, R²=0,979), contra apenas **12% do consumo per capita interno**. O padrão se repete: Perris Valley 99%/1%, Moreno Valley 99%/1%, San Jacinto 97%/3%.
- **Magnitudes:** conservação contribui 1,2-1,7 mg/L por 1,0 gpcd de redução. Já o TDS da água importada varia **~300 mg/L (Colorado River Aqueduct)** e **~200 mg/L (State Water Project)** entre anos secos e úmidos, seguindo o PMDI.
- **Implicação:** a amplitude do driver climático é suficiente para explicar sozinha os ciclos observados no LAGWRP. Isso **corrobora independentemente D-14** (reenquadramento cíclico/por regime) e sugere que a variável explicativa correta não é tempo decorrido, mas qualidade da água de origem seguindo ciclos de seca.
- **Consequência para o artigo:** o mecanismo da Nature (2020) continua válido e citável — mas apresentá-lo como *o* mecanismo seria incorreto. Ele é o efeito menor dos dois.
- **Alternativa descartada:** manter o enquadramento exclusivo em conservação — descartada por contradizer evidência quantitativa direta de 26 ETEs da mesma região.
- **Evidência:** `material_apoio_referencias.md` §9.1; `SCSC-TDS-Trends-Study.txt`, seções 4.2 e 5.

### D-30 — Lacuna crítica de dados: falta a série de TDS da água de origem
- **Data:** 2026-08-14 · **Status:** **Pendente de ação**
- **Contexto:** decorre diretamente de D-29 — a variável mais explicativa (TDS da água de origem) **não existe no nosso dataset**.
- **Situação:** temos TDS/Cloreto/Amônia/BOD do efluente e a vazão reconstruída, mas nenhuma medida da qualidade da água que entra no sistema. Isso significa que a variável que a literatura aponta como responsável por ~88% da variabilidade está ausente do modelo.
- **Ação proposta:** buscar séries de TDS dos reservatórios/ETAs da MWDSC que abastecem a região (Castaic Lake, Jensen WTP, Weymouth WTP para SWP/CRA) e/ou o índice PMDI da NOAA como proxy climático.
- **Impacto se não resolvido:** o modelo fica limitado a explicar a variação sem acesso ao seu principal determinante — o que deve, no mínimo, constar como limitação explícita no artigo.

### D-21 — Rejeitar San Jose Creek (CA0053911) como comparadora
- **Data:** 2026-08-14 · **Status:** Decidida
- **Justificativa:** o CSV tem apenas 8 linhas de TDS e **todas marcadas como `No Discharge`** (NODI "C"). Zero valores utilizáveis — é planta de reclamação que recicla praticamente tudo, então descarga superficial é evento raro.
- **Evidência:** `SAN JOSE CREEK WRP California id ca0053911 august 2021 to august 2026.csv`.

### D-22 — Adotar Tillman WRP (CA0056227) como comparadora prioritária
- **Data:** 2026-08-14 · **Status:** **Em verificação** · *Nota (2026-08-14): a leitura do estudo SCSC confirmou que a cidade de Los Angeles (LASAN) não participa daquele estudo — nem LAGWRP nem Tillman estão entre as 26 estações. A recomendação do Tillman segue válida pelos critérios próprios (mesma operadora, mesmo rio receptor, interior), mas não é corroborada por aquela lista.*
- **Decisão proposta:** puxar TDS do efluente do Donald C. Tillman WRP via CIWQS eSMR, período 2010-2026.
- **Justificativa:** mesma operadora (LA Sanitation), mesma área de serviço (Vale de San Fernando), **mesma água receptora (LA River)**, interior (sem intrusão salina), tratamento terciário. Isso aproxima uma comparação controlada: mesma seca, mesma política estadual, planta diferente.
- **Alternativas em ordem:** Burbank WRP (2ª opção, também LA River); Whittier Narrows/Pomona (3ª, mas mesmo permit do San Jose Creek → mesmo risco de "No Discharge").
- **Verificação pendente:** conferir densidade de dados de TDS no efluente antes de investir — Tillman também faz reúso e pode ter o mesmo problema do San Jose Creek.

---

## Parte 6 — Decisões sobre o artigo

### D-23 — Horizontes de previsão: 10, 15 e 20 anos
- **Status:** Decidida · Contados a partir do último dado observado. O horizonte intermediário de 15 anos foi adicionado para mostrar o crescimento gradual da incerteza.

### D-24 — Incluir Prophet **e** regressão bayesiana
- **Status:** Decidida · Ambos expõem incerteza crescente com o horizonte. **Alternativa descartada:** escolher apenas um — descartada porque a mensagem central do trabalho é a faixa de cenários com incerteza, e ter dois métodos independentes com essa propriedade fortalece o argumento.

### D-25 — Limpeza das imagens de exemplo do template
- **Status:** Decidida · Remover `matrix-de-confusao.png` (órfã, tema não aplicável) e substituir `acurácia-x-epocas.png` quando houver figura real. Aprovada pelo usuário.

### D-26 — Substituir as 3 referências de exemplo do `refs.bib`
- **Status:** Decidida · `vaswani2017attention`, `karimi2024employee` e `bai2020industry` são exemplos de sintaxe do template e saem quando as referências reais entrarem.

### D-27 — Não usar o valor "+50 mg/L" do artigo ACS ES&T Water (2022)
- **Data:** 2026-08-13 · **Status:** Decidida
- **Justificativa:** o número não pôde ser confirmado no texto completo (ACS retorna 403); fontes de terceiros confirmam o desenho do estudo e a direção do efeito, mas não esse valor específico. Citar seria reproduzir um dado não verificado.
- **Evidência:** `material_apoio_referencias.md` §1.3.

---

## Parte 7 — Registro completo da bateria de scripts (preenchido nesta sessão)

### D-31 — Confirmação de D-14 (regime cíclico), com ressalva importante
- **Data:** 2026-08-14 · **Status:** Decidida (confirma D-14, com nuance)
- **Contexto:** D-14 estava "pendente de confirmação" — exigia checar se a vazão reconstruída acompanha os mesmos períodos de virada (2012/2015/2019/2022) identificados na série de TDS.
- **Decisão:** **confirmar o reenquadramento cíclico/por regime**, mas registrar que a vazão sozinha **não explica totalmente** o padrão.
- **Evidência quantitativa:**
  - Correlação mensal TDS×vazão(TDS): r = −0,373, p < 0,001, n = 182 (negativa, como esperado pelo mecanismo de diluição — menos vazão, mais concentração).
  - Correlação anual TDS×vazão(TDS): r = −0,552, p = 0,027, n = 16.
  - Vazão anual (MGD): 13,84 (2011) → declínio quase monotônico até 9,05 (2017) → platô 9-10 (2018-2020) → segunda queda para 7,3-7,5 (2021-2022) → 7,1-8,0 (2023-2026).
  - TDS anual (mg/L): sobe 563→808 (2011-2015), cai para 653 (2017), sobe de novo a 768 (2022), recua para ~700 depois.
- **Leitura honesta:** a correlação é significativa e no sinal esperado (dilução), e os dois grandes picos de TDS (2015, 2022) caem dentro das duas secas oficiais da Califórnia (2012-2016 e 2020-2022/2023) — alinhamento de regime é real. Mas a vazão **não replica** o formato fino da série de TDS: entre 2016 e 2017 a vazão ficou praticamente estável/baixa (9,48→9,05) enquanto o TDS caiu de forma acentuada (778→653), o que a hipótese pura de diluição não explica. Isso é **consistente com D-29** — a vazão/conservação é um driver real, mas parcial; a maior parte da variância (segundo a literatura, ~88%) viria da qualidade da água de origem, que **não está no nosso dataset** (D-30).
- **Alternativas descartadas:** *rejeitar D-14 por falta de correspondência perfeita* — descartada porque a correlação é estatisticamente significativa e o alinhamento com as duas secas é real, só não é suficiente sozinho; *tratar a vazão como explicação completa* — descartada porque contradiz o mismatch observado em 2016-2017 e a evidência de literatura de D-29.
- **Evidência:** `vazao_reconstruida_serie.csv`; cálculo desta sessão (correlação mensal/anual TDS×vazão, ver histórico de execução).

### D-32 — Estratégia de validação padronizada em toda a bateria
- **Data:** 2026-08-14 · **Status:** Decidida
- **Decisão:** todo método de `script_01` em diante usa o mesmo framework (`validacao_utils.py`): holdout fixo dos últimos 24 meses, CV expansiva de 5 folds (horizonte 12 meses, mínimo 60 meses de treino) e backtest de origem móvel em +3/+5 anos (únicos horizontes com dado real disponível para comparar — não é possível validar empiricamente +10/+15/+20 anos, que ficam como extrapolação pura).
- **Alternativas descartadas:** validar diretamente nos horizontes de +10/+15/+20 anos — impossível, não existe dado real futuro nesse alcance; split aleatório — descartado por vazar informação temporal.
- **Nota:** os valores de `n_folds=5`, `min_treino=60`, `horizonte_cv=12`, `passo_origem=6` são defaults fixados na assinatura de `validacao_utils.py`, sem grid search documentado sobre esses números — foram adotados como convenção única para toda a bateria, não otimizados por método.
- **Evidência:** `validacao_utils.py`; uso idêntico em `script_01` a `script_13`.

### D-33 — Hiperparâmetros e sementes aleatórias por método
- **Data:** 2026-08-14 · **Status:** Decidida (registro, não decisão nova)
- **Decisão/registro:** `SEED = 42` fixo e logado no MLflow em todo método estocástico (Random Forest `script_03`, XGBoost/LightGBM `script_04`, SVR/GP `script_09`, Detrend+árvore `script_10`, regressão bayesiana `script_05` via `random_seed`, LSTM `script_13` via `torch.manual_seed`).
- **O que teve busca real de hiperparâmetro (GridSearchCV + `TimeSeriesSplit(5)`, nunca split aleatório):** Random Forest (`n_estimators∈{100,300}`, `max_depth∈{None,5,10}`, `min_samples_leaf∈{1,3,5}`), XGBoost (`n_estimators∈{100,300}`, `max_depth∈{3,5,7}`, `learning_rate∈{0.03,0.1}`), LightGBM (mesma grade + `max_depth=-1`), SVR (`C∈{1,10,100}`, `epsilon∈{0.5,1,5}`, `gamma∈{scale,auto}`). SARIMA/SARIMAX: ordem escolhida por menor AIC em grade `p,q∈{0,1,2}`, `P,Q∈{0,1}`, `D∈{0,1}`, `d=1` fixo (série não-estacionária em nível).
- **O que NÃO teve busca sistemática (default ou escolha heurística única, sem sensitivity analysis) — registrado como tal, não inventando justificativa:** Prophet (`changepoint_prior_scale` e demais hiperparâmetros no default da biblioteca); priors da regressão bayesiana (`a~Normal`, `b~Normal`, `sigma~HalfNormal`, escalas calibradas heuristicamente a partir de média/desvio dos dados, sem teste de sensibilidade); LSTM (`JANELA=12, HIDDEN_SIZE=32, EPOCHS=200, LR=0.01`, escolhidos a priori pelo tamanho pequeno do dataset, ~180 pontos, não por tuning); ETS (`error='add', trend='add', damped_trend=False` fixo, alternativas como multiplicativo/damped não testadas); Gaussian Process (forma do kernel e bounds escolhidos manualmente, só os hiperparâmetros internos otimizados via log-marginal-likelihood do scikit-learn, `n_restarts_optimizer=3`).
- **Decisão de escopo comum a RF/XGB/LGBM/SVR/Detrend+árvore:** os hiperparâmetros escolhidos pelo GridSearchCV no ajuste final **não são re-buscados** a cada fold de CV/backtest (custo computacional proibitivo — dezenas de refits) — a mesma combinação vencedora é reaplicada em todos os folds.
- **Alternativas descartadas:** tuning completo (grid search) para Prophet/priors bayesianos/LSTM/ETS — descartado por custo computacional vs. ganho esperado num dataset de ~180 pontos; re-buscar hiperparâmetros por fold de CV — descartado pelo custo (~25 refits por método).
- **Evidência:** `script_03` a `script_05`, `script_09`, `script_10`, `script_13` (linhas citadas no relatório de leitura desta sessão).

### D-34 — Desempenho fraco/negativo no holdout: registrado, não escondido
- **Data:** 2026-08-14 · **Status:** Decidida (registro de resultado negativo)
- **Contexto:** regra do plano (checklist §7): resultado negativo é resultado e deve ser reportado, não omitido.
- **Achado central:** de 21 métodos em `resultados_comparacao.csv`, **apenas `svr` tem R² positivo no holdout de 24 meses (0,039)** — todos os demais têm R² negativo (pior que prever a média constante nesse recorte). Isso é um padrão consistente entre métodos, não um bug isolado — indicativo de que o holdout de 24 meses cai justamente num trecho de reversão de regime (ver D-14/D-31) que nenhum método captura bem fora de amostra.
- **Piores casos específicos:**
  - `gaussian_process` (script_09): RMSE=146,50, R²=−12,65, MASE=2,03 — pior resultado da bateria por larga margem; IC90 em +10/+15/+20a quase idêntico (≈886 mg/L de largura), sinal de que o kernel não captura extrapolação útil.
  - `lstm` (script_13): MASE=0,686 > MASE do `naive` (0,436) — **o próprio script conclui explicitamente que o LSTM não venceu o baseline mais forte**, R²=−2,25.
  - `naive_sazonal`: RMSE=87,83, R²=−3,91 — esperado (é baseline fraco), serve de piso.
  - `theta`: IC90 em +20a com 3.004 mg/L de largura — o mais largo de toda a tabela.
  - `sarima`: IC90 em +20a com 2.509 mg/L de largura — consistente com a limitação já documentada no script (extrapolação de SARIMA além do histórico é frágil).
  - `xgboost`: tendência com p=0,100 — não significativa a 5%.
- **Implicação para a síntese final:** reforça por que `script_15` prioriza MASE e comportamento do IC (largura crescente honesta) em vez de R² no holdout isolado — ver D-35.
- **Evidência:** `resultados_comparacao.csv` (colunas `rmse_holdout`, `r2_holdout`, `mase_holdout`, `ic90_width_*y`).

### D-35 — Critério de escolha dos 3 finalistas na síntese (`script_15`)
- **Data:** 2026-08-14 · **Status:** Decidida (registro)
- **Decisão:** os 3 finalistas escolhidos são `regressao_bayesiana`, `detrend_rf` e `hibrido_arima_prophet`.
- **Justificativa por método (rastreável aos scripts, não inventada agora):**
  - `regressao_bayesiana` — único método com incerteza genuinamente honesta e crescente com o horizonte (propriedade estrutural do modelo, não pós-hoc).
  - `detrend_rf` — melhor MASE no holdout (0,4408) entre os métodos que capturam tendência sem saturar como as árvores puras, e o único dos 5 candidatos sem autocorrelação/heterocedasticidade residual significativa (`script_14_diagnostico_residuos.py`).
  - `hibrido_arima_prophet` — melhor RMSE no holdout (46,40) entre os métodos de série temporal, com IC mais largo que os individuais (envoltória SARIMA+Prophet), lido como cenário mais cauteloso.
- **Alternativas descartadas:** escolher só o de melhor RMSE/MASE isolado — descartada porque nenhum método vence em todos os critérios simultaneamente (ver D-34), e o plano (§5) já previa que a decisão final poderia ser 2-3 métodos complementares, não um vencedor único.
- **Evidência:** `script_15_sintese_final.py`; `resultados_comparacao.csv`; `diagnostico_residuos_resultados.csv`.

### D-36 — Desvios da estrutura de scripts em relação ao plano original (`plano_projeto_TDS.md` §4)
- **Data:** 2026-08-14 · **Status:** Decidida (registro de desvio, não retroativo)
- **Contexto:** o plano original (§4) previa uma bateria de 8 scripts (`script_00` a `script_08`), incluindo `script_00b_sensibilidade_tratamento.py`, `script_01b_analises_anuais.py`, `script_06_wrtds_balanco_massa.py`, `script_07_estruturais_gam_quantilica.py`, `script_08_intervencao_svr_fundacionais.py`.
- **O que de fato existe:** a bateria real vai até `script_17`, com nomes/escopos diferentes dos planejados:
  - A matriz de sensibilidade (§1.4) e a reconstrução de vazão (§1.5), previstas como um único `script_00b`, viraram dois scripts separados no fim da numeração: `script_16_reconstrucao_vazao.py` e `script_17_matriz_sensibilidade.py`.
  - O `script_00b` real (`script_00b_analise_censura_bod.py`) é outro script, não previsto no plano — diagnóstico de censura do BOD.
  - `script_01b_analises_anuais.py` **não foi implementado** como script dedicado; a agregação anual aparece só como item 5 dentro de `script_17`. Janela móvel, tendência recursiva e piecewise (§3.e) **não foram implementados**.
  - `script_06/07/08` do plano (WRTDS/balanço de massa, GAM/DLM/quantílica, ARIMAX de intervenção/SVR/fundacionais) **não foram implementados** com esse conteúdo — os `script_06/07/08` reais são correlação TDS-Amônia-BOD, diagnóstico de estrutura da série e baselines, respectivamente.
  - A bateria ganhou 9 scripts adicionais sem equivalente no plano original (`script_09` a `script_17`: SVR/GP, detrend+árvore, SARIMAX multivariado com Cloreto, híbrido SARIMA+Prophet, LSTM, diagnóstico de resíduos, síntese final, reconstrução de vazão, matriz de sensibilidade).
  - A variante JAX/CUDA da regressão bayesiana, prevista no plano para `script_05`, **não foi configurada** — roda em PyMC/NUTS puro CPU.
- **Implicação:** os métodos WRTDS (f.1), balanço de massa (f.2), cenários (f.3) e GAM (f.5) — que motivaram a Etapa 3 desta sessão — **ainda não existem no repositório**, apesar do plano original prevê-los desde `script_06/07`. A Etapa 3 (`prompt_tratamento_e_metodos.md`) parte dessa lacuna real, não de um retrabalho.
- **Alternativas descartadas:** renumerar os scripts existentes para bater com o plano original — descartada por ser puramente cosmética e arriscar quebrar referências já existentes no notebook/MLflow/artigo.
- **Evidência:** comparação direta entre `plano_projeto_TDS.md` §4 e os arquivos `script_*.py` presentes no repositório; relatório de leitura desta sessão.

### D-37 — Os ciclos de TDS são explicados por ciclos de seca (PDSI) ⭐ confirma D-14
- **Data:** 2026-08-14 · **Status:** Decidida (Passo 1 de `prompt_pdsi_regimes.md`)
- **Contexto:** D-14 propôs que os ciclos de TDS acompanham secas, mas não tinha sido testado com uma variável de seca independente. D-29/D-30 apontavam a lacuna (TDS da água de origem ausente do dataset) e sugeriam o PDSI como proxy climático.
- **Dados:** PDSI mensal do NOAA NCEI nClimDiv (`climdiv-pdsidv`/`climdiv-pdsist`, versão `v1.0.0-20260806`, 1895-2026), três séries — California estadual (código `004005`), divisão climática 6/Los Angeles (código `040605`, contém o condado de LA, FIPS 06037 → `county-to-climdivs.txt` linha `06037 04037 0406`) e divisão 2/Sacramento (código `040205`, contém Sacramento e Butte/Oroville — origem do State Water Project, FIPS 06067/06007 → `0402`). Códigos confirmados na documentação oficial (`state-readme.txt`, `divisional-readme.txt`, `county-to-climdivs.txt`), não assumidos. Salvos como `pdsi_california_estadual.csv`, `pdsi_los_angeles_divisao.csv`, `pdsi_sacramento_divisao.csv`.
- **Resultado — desfecho 1 dos 3 possíveis (`prompt_pdsi_regimes.md` Etapa 3): "PDSI explica bem os ciclos"**, com uma ressalva importante:
  - **Correlação com defasagem (0-36 meses), corrigida por graus de liberdade efetivos (Pyper & Peterman 1998, mesma armadilha de D-15):** correlação bruta forte e altamente significativa em defasagem curta — California estadual r=−0,651 (lag=4m, p=0,0003, n_efetivo=26,3 de 178 nominais), LA divisão 6 r=−0,526 (lag=3m, p=0,0126), Sacramento divisão 2 r=−0,563 (lag=4m, p=0,0012). **Ressalva honesta:** a correlação sobre as séries diferenciadas (destendenciadas) cai bastante e **inverte de sinal** (r=+0,15 a +0,19, p entre 0,014 e 0,055) — a relação forte é sobretudo de nível/regime (a mesma informação que já embasa D-14), não uma sincronia mês a mês fina. Isso é reportado como resultado, não escondido.
  - **Changepoints no PDSI, detectados de forma independente (segmentação binária recursiva com o teste de Pettitt de `script_07`, sem informar as datas do TDS ao algoritmo):** das 4 viradas esperadas (2012, 2015, 2019, 2022), a série da divisão de Los Angeles bate as 4 dentro de ~4-6 meses; California estadual bate 3 de 4 dentro de ~7-10 meses (a virada de 2012 fica a ~15 meses, fora do critério de 12 meses); Sacramento bate as 4 dentro de ~3-9 meses. **Nenhum alinhamento foi forçado** — os changepoints vieram de um algoritmo cego às datas do TDS.
  - **Decomposição LMG (PDSI defasado × vazão reconstruída, `TDS ~ PDSI_lag + vazão`):** LMG do PDSI = 79,3% (California estadual), 67,5% (LA divisão 6), 72,6% (Sacramento divisão 2) — mesma ordem de grandeza do benchmark SCSC/DBS&A (~88% água de origem / ~12% consumo per capita, D-29), confirmando que o driver dominante não é a vazão local isolada. Ambos os coeficientes (PDSI e vazão) são significativos (p<0,0001) nas 3 séries — os dois mecanismos contribuem, mas o climático pesa mais.
  - **Regressão por regime (5 dummies de período + PDSI):** o coeficiente do PDSI continua altamente significativo (p<0,0001) mesmo controlando por regime nas 3 séries — o efeito **não é** inteiramente absorvido pelas dummies de período, ou seja, o PDSI carrega informação além de só marcar "qual dos 5 blocos temporais".
- **Interpretação honesta (sem escolher a leitura que "salva" a hipótese):** o padrão cíclico de D-14 tem sustentação empírica real e não-forçada — nível/regime do PDSI explica a maior parte, e o algoritmo de changepoint (cego às datas do TDS) recupera as mesmas viradas. Mas a sincronia fina mês a mês é mais fraca e de sinal invertido, então "seca explica os ciclos" é verdadeiro no nível de regime/período, não como um mecanismo de resposta imediata bem calibrado em alta frequência. Isso é consistente com D-29 (tempo de trânsito/mistura da água importada) e não deve ser lido como mais forte do que os números sustentam.
- **Alternativas descartadas:** usar só a correlação contemporânea (lag=0) — descartada porque subestimaria a relação real (justificativa do próprio prompt: tempo de trânsito da água importada); usar `ruptures` para changepoint — pacote não instalado nesta sessão, optou-se por reaproveitar a implementação de Pettitt já existente em `script_07` via segmentação binária recursiva, evitando dependência nova para um teste que já tinha implementação própria validada no projeto.
- **Evidência:** `script_18_pdsi_regimes.py`; `pdsi_regimes_resultados.csv`/`.json`; `Artigo/images/pdsi-vs-tds-regimes.png`; `Artigo/images/pdsi-tds-correlacao-defasagem.png`; run MLflow `pdsi_regimes`.

## Pendências de registro

- [x] Decisões tomadas dentro de cada `script_01` a `script_17` (escolha de hiperparâmetros, ordem SARIMA, features, seeds) — ver D-33.
- [x] Justificativa da escolha de holdout/CV adotada — ver D-32.
- [x] Métodos que falharam ou não convergiram (resultado negativo também é resultado) — ver D-34.
- [x] Decisão sobre quais modelos entram como finalistas na síntese — ver D-35.
- [x] Confirmação ou reversão de D-14 (regime cíclico) após a checagem vazão-vs-seca — ver D-31 (confirmada, com ressalva).
- [x] Desvios da estrutura de scripts em relação ao plano original — ver D-36 (não previsto na lista original de pendências, mas descoberto durante o preenchimento desta seção).

### D-38 — Primeira compilação real do artigo: `\text{}`/`\mathrm{}` com acento quebra o PDF (amsmath ausente)
- **Data:** 2026-08-14 · **Status:** Decidida (correção de bug de compilação, não decisão metodológica)
- **Contexto:** `prompt_compilar_artigo.md` — TeX Live estava instalado (`C:\texlive\2026\bin\windows\`, fora do `PATH` do shell), não ausente como a sessão anterior concluiu por engano; essa foi a primeira compilação real desde as edições em D-13/D-14/D-31/D-37 (fórmula da identidade `lb/dia = mg/L × vazão × 8,34` inserida em `conclusao.tex`, `metodologia.tex` e `resultados.tex`).
- **Erro encontrado:** `template.tex` nunca carregou `\usepackage{amsmath}` — então `\text{}` (usado em `conclusao.tex`) é um comando indefinido (`Undefined control sequence`), e mesmo `\mathrm{}` (usado em `metodologia.tex`/`resultados.tex`) falha ao conter a palavra acentuada `vazão` dentro de modo matemático (`Please use \mathaccent for accents in math mode` — CM/OT1 não compõe `ã` corretamente dentro de fórmula).
- **Decisão:** (1) adicionar `\usepackage{amsmath}` a `template.tex`; (2) remover o acento nas 3 ocorrências de `vazão` dentro de `$...$`/`\mathrm{}`/`\text{}` (viraram `vazao`, sem acento, só dentro da fórmula — o texto em prosa ao redor continua acentuado normalmente).
- **Alternativas descartadas:** envolver a palavra em `\text{}` sem `amsmath` carregado — não resolve, é a própria causa; usar `\mbox{}` em vez de corrigir o acento — mais invasivo, a correção mínima (remover o acento só dentro da fórmula) resolve sem mudar a leitura da equação.
- **Resultado da recompilação:** ciclo completo (`pdflatex → bibtex → pdflatex → pdflatex`) roda limpo — 0 `Undefined control sequence`, 0 citação/referência não resolvida, as 17 figuras referenciadas em `resultados.tex` todas embutidas, bibliografia com 3 referências numeradas (nenhum `[?]`), 22 páginas, 6 seções na ordem correta (abstract → introdução → trabalhos relacionados → metodologia → resultados → conclusão). `Overfull \hbox` presentes (esperado em layout de duas colunas com tabelas largas) mas não impedem a compilação nem cortam conteúdo visível.
- **Achado colateral, fora do escopo desta correção:** a página de título ainda tem os placeholders `Título do documento` / `Autor A1, Autor B1 e Autor C1` (nunca preenchidos com o título real e os autores reais) — registrado aqui para não ser esquecido, não corrigido nesta execução por não ter essa informação.
- **Evidência:** `Artigo/template.tex`, `Artigo/src/conclusao.tex`, `Artigo/src/resultados.tex`, `Artigo/template.pdf` (recompilado), `Artigo/template.log`.
- **Nota de troubleshooting (2026-08-14, pós-D-38):** o mesmo bug se repetiu uma segunda vez nesta sessão — depois de corrigido em `conclusao.tex`/`resultados.tex` e de uma varredura por regex, novas ocorrências apareceram em `metodologia.tex`/`resultados.tex` (linhas 69, 75, 393) porque foram **escritas depois** da varredura, ao redigir as seções de WRTDS/balanço de massa (D-39/D-40). A causa raiz não é um arquivo específico, é um padrão de escrita: **qualquer palavra acentuada dentro de `\mathrm{}`, `\text{}` ou `\log(\mathrm{})` em modo matemático (`$...$`) quebra a compilação**, mesmo com `amsmath` carregado. Regra prática para evitar uma terceira ocorrência: ao escrever uma fórmula nova, usar sempre a forma sem acento dentro do `$...$` (ex. `vazao`, não `vazão`) — o texto em prosa ao redor pode continuar acentuado normalmente. Não é algo que uma varredura pontual resolve de vez, porque cada nova fórmula escrita no futuro pode reintroduzir o problema.

### D-39 — WRTDS confirma: não há tendência de TDS depois de descontar a vazão
- **Data:** 2026-08-14 · **Status:** Decidida (`prompt_wrtds_balanco_cenarios.md`, Tarefa 1)
- **Contexto:** D-37 mudou a pergunta de tendência de "há tendência de alta?" para "há tendência POR BAIXO dos ciclos, depois de descontar o efeito da vazão?" — exatamente o que a normalização por vazão do WRTDS responde.
- **Implementação:** própria (`script_19_wrtds.py`), não o pacote R `EGRET` (sem equivalente Python maduro) — regressão ponderada localmente de `log(TDS)` sobre tempo, `log(vazão)` e sazonalidade (kernel tricúbico, janelas fixas: tempo±7a, log(vazão)±2, sazonal±0,5 — mesmos defaults do EGRET, exceto que aqui as janelas **não** se expandem adaptativamente quando poucos pontos têm peso, simplificação declarada). Flow-normalização = média da predição sobre toda a distribuição histórica de vazão em cada instante.
- **Resultado:** tendência bruta (log TDS) = +0,582%/ano (p=0,0056, significativa) → tendência **flow-normalized** = −0,133%/ano (**p=0,064, não significativa**). Ou seja: quase toda a "tendência" aparente desaparece ao descontar o efeito da vazão — consistente com D-37/D-31 (o padrão é dirigido por ciclos de vazão/seca, não por uma tendência de longo prazo independente).
- **Checagem de circularidade (obrigatória, feita antes de aceitar o resultado):** a vazão padrão (`vazao_mgd_TDS`) foi derivada do próprio TDS (D-12) — repetiu-se todo o procedimento com `vazao_mgd_Chloride` (série independente). Resultado: −0,158%/ano (p=0,033), correlação entre as duas séries flow-normalized r=0,998 (p≈5×10⁻²²⁰), diferença de apenas 0,024 pontos percentuais/ano entre as duas versões. **A circularidade não invalida o achado** — as duas vazões (dependente e independente do TDS) levam à mesma conclusão qualitativa.
- **Adaptação de contexto declarada:** WRTDS foi desenhado para rios (vazão = hidrologia); aqui "vazão" é vazão de efluente (dirigida por consumo/conservação). A matemática se aplica, a interpretação é diferente — registrado explicitamente na metodologia do artigo.
- **Alternativas descartadas:** usar `rpy2` para chamar o `EGRET` real em R — descartado por adicionar uma dependência de sistema pesada (R + pacotes) para um ganho marginal sobre a implementação própria, que já reproduz o mecanismo central (regressão ponderada 3D + integração sobre a distribuição de vazão) e foi validada contra circularidade.
- **Evidência:** `script_19_wrtds.py`; `wrtds_resultados.csv`/`.json`; `Artigo/images/wrtds-flow-normalized.png`, `wrtds-circularidade.png`; linha `wrtds_flow_normalized` em `resultados_comparacao.csv`.

### D-40 — Balanço de massa confirma diluição, não mais sal — mas extrapolação linear dos componentes é fisicamente implausível
- **Data:** 2026-08-14 · **Status:** Decidida (`prompt_wrtds_balanco_cenarios.md`, Tarefa 2)
- **Contexto:** pergunta central — a carga de sal está estável/caindo enquanto a vazão cai (diluição) ou a carga também sobe (mais sal)?
- **Dados:** carga de sal (lb/dia) obtida **diretamente** da linha "Monthly Average (Mean)" em lb/dia do `TDS.csv` (não derivada de vazão alguma — evita um segundo ponto de circularidade). Vazão usada no modelo principal: `vazao_mgd_Chloride` (independente do TDS), pelo mesmo motivo de D-39.
- **Resultado:** carga de sal cai −3,20%/ano (p<0,0001); vazão cai −3,85%/ano (p<0,0001) → **confirma o mecanismo de diluição** (menos água, carga de sal estável/em leve queda, não mais sal entrando no sistema).
- **Validação histórica (não-circular):** `TDS_previsto = carga ÷ (vazão_Cloreto × 8,34)` vs. TDS observado: RMSE=19,1 mg/L, r=0,973, R²=0,941 — forte.
- **Checagem de tautologia (exigida pelo prompt, feita explicitamente):** repetindo com `vazao_mgd_TDS` (a vazão derivada do próprio TDS), R²=1,000000 exato — confirma que essa versão é uma identidade algébrica por construção (`vazão_mgd_TDS ≡ carga_TDS/(TDS_mgL×8,34)`), **não uma validação**. Reportado como checagem, não como resultado.
- **⚠️ Achado negativo, registrado e não escondido:** a extrapolação linear (Theil-Sen) de carga e vazão para +10/+15/+20 anos cruza valores fisicamente implausíveis — a vazão projetada cai para 14% da capacidade nominal em +10a, 5% em +15a, e **fica negativa** em +20a. O TDS derivado dessas projeções (993 → 1.724 → 1.557 mg/L, não-monotônico) não deve ser lido como previsão confiável. Isso não contradiz o achado da diluição (que é sobre o período histórico, robusto); contradiz apenas a ideia de extrapolar essa reta por décadas.
- **Decisão:** não forçar um piso arbitrário "razoável" na vazão projetada (seria inventar um número) — reportar a implausibilidade como está, e resolver com cenários condicionados a faixas historicamente observadas (D-41/`script_21`), não com uma correção ad-hoc da extrapolação linear.
- **Adaptação da forma do SCSC:** sem população nem TDS de origem (D-30), a forma usada é a identidade física direta `TDS = carga/(vazão×8,34)`, sem o termo per-capita do modelo do SCSC (`TDS_origem + SML×pop/vazão`) — declarado como adaptação, não substituição equivalente.
- **Evidência:** `script_20_balanco_massa.py`; `balanco_massa_resultados.csv`/`.json`; `Artigo/images/balanco-massa-decomposicao.png`, `balanco-massa-validacao.png`; linha `balanco_massa` em `resultados_comparacao.csv`.

### D-41 — Projeção por cenários climáticos substitui a previsão pontual de longo prazo
- **Data:** 2026-08-14 · **Status:** Decidida (`prompt_wrtds_balanco_cenarios.md`, Tarefa 3)
- **Contexto:** decorre diretamente de D-40 — extrapolar componentes linearmente por 20 anos não é sustentável fisicamente numa série dirigida por ciclos de seca (D-37/D-14).
- **Método:** AR(1) ajustado no PDSI histórico completo (1895-2026, série California estadual, a de maior LMG% em D-37): μ=−0,31, φ=0,894, resid\_std=1,08. Regressão `TDS ~ PDSI(lag=4 meses, mesmo lag de D-37)`: coef=−20,4 (se=1,70), R²=0,445. Quatro cenários simulados pelo **mesmo** AR(1) ajustado, só mudando a média-alvo: seco (P10 histórico), normal (média histórica), úmido (P90 histórico), agravamento climático (média deslizando linearmente de histórica para P10 ao longo de 20 anos). Monte Carlo com 2.000 simulações por cenário, propagando incerteza do coeficiente da regressão + ruído residual + variabilidade do PDSI simulado.
- **Resultado — faixas de TDS por cenário em +20 anos (mediana [P5, P95], mg/L):** seco 718 [588, 846]; normal 658 [529, 783]; úmido 594 [462, 721]; agravamento climático 714 [591, 842] (converge para perto do cenário seco, como esperado pela definição da rampa). Todas as faixas são fisicamente plausíveis (diferente da extrapolação linear de D-40) porque o PDSI é limitado à distribuição historicamente observada, não extrapolado ao infinito.
- **Alternativas descartadas:** projetar PDSI com tendência própria (ao contrário de mean-reverting) — descartada porque o PDSI é calibrado para ser aproximadamente estacionário por construção (Palmer, 1965); assumir independência entre meses (sem AR(1)) — descartada porque subestimaria a persistência real de secas/períodos úmidos, já documentada na literatura (PDSI mensal não captura secas com duração menor que ~12 meses, ver `GLOSSARIO.md`).
- **Limitação declarada:** a incerteza de reconstrução do próprio PDSI (erro de medição/interpolação do nClimDiv) não é propagada — só incerteza do coeficiente da regressão, ruído residual e variabilidade do PDSI simulado.
- **Evidência:** `script_21_cenarios.py`; `cenarios_resultados.csv`/`.json`; `Artigo/images/cenarios-pdsi-fanchart.png`, `cenarios-pdsi-horizontes.png`; linhas `cenario_pdsi_*` em `resultados_comparacao.csv`.

### D-42 — Reconciliação: o que cada família de método responde (não há contradição a registrar)
- **Data:** 2026-08-14 · **Status:** Decidida
- **Contexto:** `prompt_wrtds_balanco_cenarios.md` pedia registrar explicitamente se algum resultado novo contradissesse um anterior.
- **Verificação:** os métodos de tendência/ML de `script_01`-`script_15` (finalistas ~760-800 mg/L em +20a, Seção "Síntese final") **não são substituídos** por D-39/D-40/D-41 — respondem a uma pergunta diferente (desempenho preditivo de curto prazo e magnitude da tendência bruta, sem descontar vazão). WRTDS (D-39) responde "há tendência sob os ciclos?" (não, uma vez descontada a vazão). Balanço de massa (D-40) responde "diluição ou mais sal?" (diluição). Cenários (D-41) respondem "faixa plausível condicionada ao clima?" (594-721 mg/L em +20a, dependendo do cenário). **Não há contradição factual entre as famílias** — os finalistas de `script_15` preveem a série bruta (que inclui o efeito da vazão); D-39-D-41 decompõem essa mesma série. As faixas de cenário (594-721) ficam **abaixo** dos finalistas de tendência bruta (~760-800) porque a vazão média projetada pelos cenários (baseada em PDSI historicamente plausível) é mais alta do que a implícita numa extrapolação linear de tendência — coerente com D-40 ter descartado a extrapolação linear por implausibilidade física.
- **Evidência:** `resultados_comparacao.csv` (todas as linhas coexistem, nenhuma sobrescrita).
