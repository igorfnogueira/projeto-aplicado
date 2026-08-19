# Plano de Execução — Tendência e Previsão de TDS (LAGWRP)

> Elaborado a partir de `prompt_planejamento_TDS.md`, `AI_Project_Instructions` (instruções originais do professor), `GOVERNANCA_DOCUMENTACAO_TEMPLATE.md`, `Prompt — Manutenção contínua do artigo científico do Projeto Aplicado.md`, da análise estrutural real da pasta `Artigo/` e dos dados reais em `TDS.csv`/`Chloride.csv`/`BOD.csv`/`Ammonia.csv`. Nenhum código foi escrito e nenhum arquivo do artigo foi alterado — este é apenas o plano, para aprovação antes de gerar scripts/subagents ou tocar no `template.tex`.

## 0. Nota sobre o que foi lido/decidido nesta sessão

**Horizontes de previsão:** a bateria passa a prever TDS para **10, 15 e 20 anos** à frente (antes só 10 e 20) — o horizonte intermediário de 15 anos ajuda a mostrar como a incerteza cresce de forma gradual entre o curto e o longo prazo, em vez de um salto direto de 10 para 20. Isso já está refletido nas seções 3 e 4.

**Sobre os CSVs:** você confirmou que apagou todas as outras abas antes de salvar cada uma como CSV, então não seria possível o Excel ter salvo a aba ativa errada. Registro isso, mas a evidência que eu vi (via leitura + `grep`) continua sendo que `Chloride.csv`, `BOD.csv` e `Ammonia.csv` têm exatamente a mesma contagem de linhas por parâmetro (2048 de Chloride, 302 de Ammonia, mesma quantidade de BOD nos três arquivos) e o mesmo conteúdo nas primeiras linhas — então, seja qual for a causa (talvez a mesma aba tenha sido reexportada 3x com nomes diferentes, ou os 3 uploads apontaram para o mesmo arquivo por algum motivo do lado do chat), na prática **não muda nada para o plano**: como cada linha já tem a coluna `Parameter`, vou filtrar por ela em qualquer um dos arquivos — o resultado final é o mesmo estejam eles duplicados ou não. Não é mais um ponto em aberto.

**Sobre o notebook:** decisão sua — **ignorar `projeto_aplicado_v1 (1).ipynb` e começar o projeto do zero**. Isso muda a seção 3.c: o Random Forest deixa de ser "refatorado do notebook existente" e passa a ser construído do zero, junto com os demais métodos da bateria, sem herdar nenhuma decisão de pré-processamento/tuning do notebook anterior.

**Sobre os valores ND do BOD e sobre os pontos secundários de monitoramento:** ver seções 1.3 (opções de tratamento, para você decidir quando eu efetivamente for rodar o `script_00`) e 1.2 (pontos secundários entram só como contexto por enquanto, não como análise dedicada).

**Ampliação de tratamento de dados e metodologia (última atualização):** o plano ganhou (a) a **seção 1.4** — matriz de 9 testes de sensibilidade de tratamento de dados, para evitar que a tendência do TDS seja artefato de uma escolha de pré-processamento; (b) a **seção 1.5** — reconstrução da vazão do efluente a partir da razão `lb/day ÷ mg/L`, que habilita testar diretamente o mecanismo causal (diluição vs. mais sal); (c) a **seção 3.e** — análises ano a ano (agregação anual, janela móvel, tendência recursiva, piecewise); e (d) a **seção 3.f** — 9 métodos novos, com destaque para WRTDS, modelo de balanço de massa e simulação de cenários.

## 1. Objetivos do trabalho (confirmados contra as instruções originais do professor)

Do documento oficial `AI_Project_Instructions`:

> Contexto dado pelo professor: o tratamento convencional de esgoto depende de comunidades microbianas para remover matéria orgânica (BOD) e converter amônia em nitrato. Salinidade alta (TDS alto) pode inibir esses processos biológicos, reduzindo a eficiência do tratamento. Em regiões como Los Angeles, medidas de conservação de água reduzem o uso interno de água, o que pode aumentar involuntariamente a salinidade do esgoto — a mesma massa de sais entra no sistema num volume menor de água.

1. **Análise de tendência:** determinar se as concentrações de TDS aumentaram ao longo do período de 15 anos, usando métodos estatísticos ou de machine learning apropriados, quantificando a taxa de variação.
2. **Modelagem preditiva:** construir um modelo capaz de prever concentrações de TDS **10, 15 e 20 anos** à frente — **contados a partir do último dado observado**. Qualquer abordagem de modelagem é permitida, desde que justificada.
3. **Análise de correlação:** investigar como a salinidade crescente pode afetar o tratamento biológico, analisando a correlação entre TDS e amônia (indicador de desempenho da nitrificação) e entre TDS e BOD (indicador de remoção de matéria orgânica).
4. **Interpretação em contexto real:** discutir como os achados se relacionam com práticas de conservação de água em Los Angeles e as implicações para desempenho do tratamento, planejamento de infraestrutura e gestão ambiental — usando explicitamente o artigo da Nature Sustainability (2020) como guia da discussão.

### 1.1 Referências institucionais adicionais indicadas pelo professor

LASAN — página da LAGWRP; LASAN — página de água reciclada/OWLA; LADWP — conservação de água (fontes institucionais, não artigos revisados por pares). Fonte de dados: portal eSMR do California Water Boards — é exatamente de onde vieram os 4 CSVs (ver 1.2).

### 1.2 Descrição real dos dados

Os arquivos são a exportação bruta do relatório eSMR (Electronic Self-Monitoring Report), uma linha por medição/cálculo. Colunas: `Location; Parameter; Analytical Method; Calculated Method; Qual; Result; Units; MDL; ML; RL; Sampling Date; Sampling Time; Analysis Date; Analysis Time; ...; Latitude; Longitude; Receiving Water Body`.

- **Separador `;`**, decimal `,` (padrão regional do Excel) — `script_00` precisa `sep=';'`, `decimal=','`.
- **Período observado nas amostras lidas:** fevereiro/2011 a fevereiro/2026 (~15 anos, compatível com as instruções) — mínimo/máximo exato do arquivo inteiro só confirmo quando processar tudo (precisa do sandbox).
- **Local principal:** `EFF-001` (até ~2012) e `EFF-001A` (depois) são o **mesmo ponto físico** (mesma lat/long) — efluente da estação, só mudou de código. Tratar como uma série só.
- **Locais secundários** `R-4`, `R-7`, `RSW-650`, `RSW-654` — água receptora (LA River), não o efluente da ETE. **Decisão sua: por enquanto entram só como contexto** (ex. na introdução/discussão, para situar o leitor sobre onde a planta descarrega), não como uma análise dedicada. Se isso mudar mais adiante, atualizo esta seção e a bateria de metodologias.
- **Unidades misturadas:** `mg/L` (concentração — o que os objetivos pedem) vs. `lb/day` (carga mássica). Filtrar `Units == 'mg/L'` para tendência/correlação. **Atualização:** o `lb/day` deixou de ser secundário — ver seção 1.5 (reconstrução da vazão), que o torna peça central da análise causal.
- **Linha "Monthly Average (Mean)" já pré-calculada em mg/L** por parâmetro/mês — é a fonte mais limpa para a série mensal canônica.
- **Frequência bruta desigual entre parâmetros** (TDS/Amônia ~mensal, Chloride bem mais frequente, BOD quase diário) — por isso o merge do `script_00` parte das linhas "Monthly Average (Mean)" de cada parâmetro, não das amostras brutas.
- **Padrão confirmado: cada amostra gera duas linhas.** Uma com `Analytical Method` preenchido — é o resultado bruto de laboratório, em mg/L, sujeito a limite de detecção (por isso tem `MDL`/`ML`/`RL` preenchidos e pode vir com `Qual = ND`). Outra com `Calculated Method` preenchido (ex. "Daily Discharge", "Monthly Average (Mean)") — é um valor derivado (ex. carga mássica em lb/day, calculada a partir da concentração × vazão), por isso não tem `MDL`/`ML`/`RL` e `Qual` é sempre `=`. Não é inconsistência da planilha — é assim que o eSMR estrutura cada medição. Implicação prática para o `script_00`: filtrar por `Analytical Method` não-vazio para pegar a concentração bruta (mg/L, pode ser ND); filtrar por `Calculated Method == "Monthly Average (Mean)"` para pegar o valor mensal já agregado.

### 1.3 Tratamento dos valores não detectados (ND) do BOD — opções a decidir na hora de rodar o `script_00`

Várias linhas de BOD têm `Qual = ND` e `Result` em branco (resultado abaixo do limite de detecção do método). Isso **não será decidido agora** — quando eu for de fato construir o `script_00_preprocessamento.py`, vou apresentar essas opções de novo, já aplicadas aos dados reais (quantos ND existem, em que período se concentram), para você decidir. Registro aqui as opções, com vantagens/desvantagens específicas para este projeto:

**Contexto importante para a decisão:** BOD baixo/não detectado é, em princípio, sinal de tratamento eficiente. Se os ND estiverem concentrados nos anos iniciais (TDS mais baixo) e ficarem mais raros nos anos recentes (TDS mais alto), isso por si só já seria um indício visual da hipótese do projeto (salinidade alta atrapalhando a remoção biológica) — então a forma de tratar o ND pode influenciar diretamente se esse padrão aparece ou desaparece na análise de correlação TDS-BOD. Não é só um detalhe técnico, é uma escolha com peso na conclusão.

| Opção | Como funciona | Vantagem para este projeto | Desvantagem para este projeto |
|---|---|---|---|
| **A. Substituir por MDL/2** | Usa metade do limite de detecção do método como valor estimado | Prática padrão em ciências ambientais para dados censurados à esquerda; simples de implementar; convenção reconhecida na literatura | Introduz um valor arbitrário; se muitos ND, pode distorcer levemente a variância da série |
| **B. Substituir por 0** | Trata ND como ausência de BOD | Simples; conservador (não superestima BOD) | Viés sistemático para baixo — pode mascarar justamente o efeito que o projeto quer detectar (BOD subindo com o TDS) |
| **C. Substituir por MDL (valor cheio)** | Usa o limite de detecção inteiro | Conservador na direção oposta (não subestima) | Superestima sistematicamente; menos usado na literatura que MDL/2 |
| **D. Tratar como dado censurado explícito** (ex. regressão censurada/Tobit, métodos estatísticos para "left-censored data") | Não substitui por um número — modela a censura estatisticamente | Metodologicamente o mais correto, sem viés arbitrário | Bem mais complexo; a maioria dos métodos da bateria (Mann-Kendall, ARIMA, RF, Prophet, bayesiano) não lida nativamente com censura — exigiria adaptação extra |
| **E. Excluir os registros ND** | Remove essas linhas da série | Simples, sem viés de substituição | Quebra a regularidade da série mensal (buracos), complica modelos de série temporal, reduz ainda mais uma amostra já pequena (~15 anos) |

**Pista adicional encontrada por você nos dados brutos:** nas linhas onde a concentração de BOD veio `ND`, a linha correspondente de "Daily Discharge" (carga calculada, lb/day) apareceu como `0`. Se esse padrão se confirmar de forma consistente no arquivo inteiro (todo ND de concentração gera Daily Discharge = 0), é um indício de que a própria metodologia regulatória/da estação já trata ND como zero para efeito de cálculo de carga — o que reforçaria a **Opção B** como a escolha mais alinhada à prática oficial já embutida nos dados, mesmo com a desvantagem (viés para baixo) já registrada na tabela acima. Isso ainda precisa ser verificado sistematicamente no arquivo completo (não só nas 3 linhas de amostra) antes de virar decisão — fica registrado aqui para checar quando o `script_00` for gerado.

Quando o `script_00` for gerado, essa tabela (com os números reais de quantos ND existem, em que período, e a verificação da pista acima) volta para você decidir antes de eu codificar a escolha padrão.

**Opções adicionais vindas do material de apoio (Tema 8):** além de A-E, avaliar os métodos de Helsel para dados censurados — **F. Kaplan-Meier** (indicado como melhor técnica para séries com <70% de censura; nosso BOD tem ~65% ND), **G. ROS (Regression on Order Statistics)** e **H. MLE**. A literatura de estatística ambiental é explícita em que substituições simples (A, B, C) produzem estatísticas enviesadas — então F/G/H provavelmente são superiores, mas exigem verificação no nosso caso concreto.

### 1.4 Matriz de testes de sensibilidade no tratamento de dados (obrigatória antes de fechar qualquer resultado)

O tratamento do ND do BOD não é a única escolha capaz de enviesar o resultado. Existem pelo menos 9 decisões de pré-processamento que afetam diretamente a **tendência do TDS** — que é o resultado central do trabalho. Cada uma deve virar um **teste de sensibilidade**: rodar a análise com as variantes e reportar se a conclusão muda. Um resultado que só aparece sob uma escolha específica de tratamento não é um resultado robusto, e isso precisa ser dito no artigo.

| # | Decisão de tratamento | Risco de viés | Variantes a testar |
|---|---|---|---|
| 1 | **ND do BOD** | Alto — na correlação TDS-BOD | Opções A-E + F (Kaplan-Meier), G (ROS), H (MLE) da seção 1.3 |
| 2 | **Quebra EFF-001 → EFF-001A (~2012)** | **Alto e ainda não tratado** — se houve mudança de método/laboratório junto com a troca de código, unificar as séries cria um degrau artificial que a análise lê como "tendência" | Teste de mudança de nível no ponto de transição (Chow/Pettitt); calcular a tendência só em EFF-001A (2012-2026) e comparar com a série completa |
| 3 | **Mudanças de MDL / método analítico ao longo do tempo** | Alto — observado MDL 28 → 25 já em 2011; mudanças de método criam degraus | Mapear todas as mudanças de `Analytical Method`/`MDL`/`RL` na série e testar se coincidem com saltos de nível |
| 4 | **Usar o "Monthly Average (Mean)" pronto vs. reagregar das amostras brutas** | Médio — a agregação da planta pode incluir/excluir amostras por critério próprio, não documentado | Calcular a média mensal a partir das amostras brutas e comparar com a pré-calculada; divergências sistemáticas precisam ser entendidas antes de escolher |
| 5 | **Média vs. mediana mensal; ano civil vs. ano hidrológico** (out–set, padrão na Califórnia) | Médio — afeta sazonalidade e agregação anual | Rodar as duas versões de cada |
| 6 | **Outliers** | Alto — remover outliers pode achatar ou acentuar artificialmente a tendência | Comparar: manter tudo / winsorizar / remover por Hampel ou por resíduo do STL |
| 7 | **Meses faltantes** | Médio — interpolação inventa dados | Comparar: deixar NaN / interpolação linear / suavização de Kalman |
| 8 | **Autocorrelação no Mann-Kendall** | **Alto no p-valor** — série mensal autocorrelacionada infla a significância e pode "criar" tendência significativa onde não há | Comparar: MK simples / pre-whitening (PW) / trend-free pre-whitening (TFPW) / correção de variância (Hamed & Rao) / **Seasonal Kendall** |
| 9 | **Escala bruta vs. log** | Médio | Tendência em mg/L/ano (bruta) vs. %/ano (log) — a segunda é mais comparável com a literatura e estabiliza variância |

**Como reportar:** cada variante roda como uma run separada no MLflow (seção 4.3), e o artigo deve conter uma tabela ou parágrafo de robustez — "a tendência estimada varia entre X e Y mg/L/ano conforme o tratamento adotado, mantendo (ou não) o sinal e a significância". Isso é mais defensável academicamente do que apresentar um único número sem contexto.

### 1.5 Reconstrução da vazão do efluente a partir dos dados existentes ⭐ oportunidade encontrada nos dados

O dataset traz o **mesmo parâmetro em duas unidades**: `mg/L` (concentração) e `lb/day` (carga mássica). Essas grandezas se relacionam pela identidade padrão do setor:

```
lb/day = mg/L × vazão(MGD) × 8,34
  ⇒  vazão(MGD) ≈ lb/day ÷ (mg/L × 8,34)
```

Ou seja, **é possível reconstruir a série de vazão do efluente da estação**, que não aparece explicitamente no dataset. Isso muda o status do `lb/day`: ele deixa de ser "dado secundário" (como estava registrado na seção 1.2) e vira peça central da análise.

**Por que isso importa tanto:** a vazão é *a variável do mecanismo* descrito no artigo da Nature (conservação → menos água → menos diluição → TDS sobe). Com a vazão reconstruída, o projeto consegue responder à pergunta que efetivamente fecha o argumento causal:

- Se a **carga de sal (lb/day) está estável ou caindo** e o TDS sobe → é a vazão que caiu; confirma a hipótese da diluição (mesma massa de sal em menos água).
- Se a **carga de sal também está subindo** → há mais sal entrando no sistema; o mecanismo é outro (ou adicional), e a conclusão do trabalho muda.

Essa decomposição (TDS = carga ÷ vazão) também habilita os métodos novos 3.f.1 (WRTDS), 3.f.2 (balanço de massa) e 3.f.3 (cenários) descritos adiante.

**Ressalvas honestas:** (a) a identidade acima assume que ambas as medidas se referem à mesma amostra/período — precisa ser validado pareando as linhas por data antes de confiar na vazão derivada; (b) o fator 8,34 (lb por milhão de galões por mg/L) é a convenção americana padrão, mas deve ser confirmado contra os próprios dados (checar se `lb/day ÷ mg/L` dá um valor de vazão plausível para uma planta de 20 MGD de capacidade nominal, conforme o brochure institucional); (c) se a vazão derivada apresentar ruído irreal ou valores impossíveis, isso indica que as duas linhas não são pareáveis daquela forma — e a ideia deve ser abandonada ou ajustada, não forçada.

## 2. Estrutura real do artigo científico e fluxo de atualização

### 2.A Mapa da estrutura (validado arquivo por arquivo)

```
Artigo/
├── template.tex          ← ARQUIVO RAIZ (o que se compila)
├── refs.bib               ← base bibliográfica (BibTeX clássico)
├── images/
│   ├── acurácia-x-epocas.png     ← usada (figura de exemplo em resultados.tex)
│   └── matrix-de-confusao.png    ← ÓRFÃ: existe no disco, não é referenciada em nenhum .tex
└── src/
    ├── abstract.tex               ← \input pelo template.tex
    ├── introducao.tex             ← \input pelo template.tex
    ├── trabalhos-relacionados.tex ← \input pelo template.tex
    ├── metodologia.tex            ← \input pelo template.tex
    ├── resultados.tex             ← \input pelo template.tex
    └── conclusao.tex              ← \input pelo template.tex
```

Não existem `.sty`/`.cls` customizados, não existe `Makefile`/`latexmkrc`, não existe subpasta dedicada a "resultados"/"tabelas"/"referências" separada de `refs.bib`, e não há `.gitignore`. Não há PDF compilado na pasta.

### 2.B Como o LaTeX está estruturado

- **Arquivo raiz:** `template.tex`. Os `.tex` de `src/` não compilam sozinhos.
- **Inclusão:** `\input{src/<arquivo>.tex}`, ordem fixa: `abstract` → `introducao` → `trabalhos-relacionados` → `metodologia` → `resultados` → `conclusao`.
- **Classe:** `article` padrão (a4paper, 12pt); duas colunas via `multicol`.
- **Pacotes:** `multicol`, `graphicx`, `xcolor` (marca texto-instrução em vermelho vs. conteúdo real em preto), `fancyhdr`, `tikz`, `pgfplots`, `pgfplotstable`, `subcaption`, `authblk`, `abstract`, `float`. `fancyhdr`/`tikz`/`pgfplots` ainda não usados — `pgfplots` permite plotar as séries de TDS direto em LaTeX.
- **Macros:** nenhuma customizada. Convenção: `\color{red} ... \color{black}` marca texto-instrução.
- **Imagens/tabelas:** `\includegraphics{images/<nome>.png}` em `figure[H]`; `tabular` em `table[H]`, sem importação automática de CSV.
- **Bibliografia:** BibTeX clássico — `\bibliographystyle{plain}` + `\bibliography{refs.bib}`.
- **Compilação:** `pdflatex template.tex` → `bibtex template` → `pdflatex template.tex` → `pdflatex template.tex`.

### 2.C Fluxo correto de atualização (onde cada coisa entra)

| Tipo de conteúdo novo | Vai para |
|---|---|
| Objetivo, pergunta de pesquisa, motivação, contribuições | `Artigo/src/introducao.tex` |
| Trabalhos relacionados / literatura | `Artigo/src/trabalhos-relacionados.tex` (hoje vazio) |
| Descrição dos dados, métodos testados, setup experimental | `Artigo/src/metodologia.tex` |
| Resultados numéricos, gráficos, tabelas, análise dos experimentos | `Artigo/src/resultados.tex` |
| Nova imagem/gráfico | `Artigo/images/`, nome ASCII sem espaço/acento, referenciada em `resultados.tex` |
| Nova tabela (ex. `resultados_comparacao.csv`) | transcrita como `tabular` em `resultados.tex` |
| Nova referência bibliográfica real | `Artigo/refs.bib` + `\cite{chave}` no `.tex` correspondente |
| Conclusão / limitações / trabalhos futuros | `Artigo/src/conclusao.tex` |
| Resumo final (só com o resto já real) | `Artigo/src/abstract.tex` |

### 2.D Estado atual de preenchimento

**100% do artigo ainda é placeholder/template** — todas as seções com texto de instrução ou exemplo. `refs.bib` só tem as 3 referências de exemplo. Tudo deve ser **substituído** (não complementado).

### 2.E Problemas encontrados (análise estática — compilação real ainda não executada)

Sem erro óbvio de referência quebrada. Pontos de atenção: nome de arquivo com acento (`acurácia-x-epocas.png`); imagem órfã `matrix-de-confusao.png` (remoção já aprovada); nenhum `.gitignore`; compilação real ainda não executada (sandbox indisponível).

### 2.F Sequência de atualização do artigo

1. Executar a análise/script de metodologia. 2. Validar o resultado. 3. Gravar em `resultados_comparacao.csv`/`.json`. 4. Gerar gráfico/figura se fizer sentido. 5. Salvar em `Artigo/images/` (ASCII, sem espaço/acento). 6. Editar só o `.tex` certo (tabela 2.C). 7. Inserir `\includegraphics`/tabela. 8. Referência real → `refs.bib` + `\cite{}`, nunca inventada. 9. Compilar ciclo completo. 10. Checar PDF/log. 11. Só então marcar como documentado.

### 2.G Regras operacionais para evitar erros futuros

Editar sempre o `src/` certo; imagens só em `Artigo/images/` (ASCII); tabelas transcritas manualmente do CSV, conferindo números; citação nova exige entrada real em `refs.bib` antes; remover bloco `\color{red}` ao preencher uma seção; nunca escrever resultado não rastreável a um script; não renomear/mover a estrutura sem necessidade comprovada; sempre rodar o ciclo de compilação completo antes de dar por concluído.

### 2.H Decisões já aprovadas sobre o artigo (ainda não executadas)

- Remover `matrix-de-confusao.png` quando a primeira figura real entrar; substituir `acurácia-x-epocas.png` só quando houver uma figura real para seu lugar.
- Ao citar de fato um dos artigos da seção 6 pela primeira vez, criar a entrada real em `refs.bib` e remover as 3 de exemplo (`vaswani2017attention`, `karimi2024employee`, `bai2020industry`) nesse momento.

## 3. Bateria de metodologias a testar (construída do zero — notebook anterior não será reaproveitado)

### a) Estatística clássica de tendência
- **Mann-Kendall** + **Sen's slope**, **Theil-Sen**, **OLS** — sobre a série mensal (`Monthly Average (Mean)`, mg/L, `EFF-001`+`EFF-001A` unificados).
- **Limitações:** taxa assumida constante; sensível a autocorrelação serial; ~15 anos é pouco para validar linearidade no longo prazo.

### b) Séries temporais clássicas
- **Decomposição STL** e **ARIMA/SARIMA** sobre a série mensal.
- **Limitações:** horizontes de 10, 15 e 20 anos, todos bem maiores que o histórico (~15 anos) — IC tende a crescer (e no caso de 20 anos, explodir); SARIMA extrapola de forma quase determinística além de poucos passos, então o horizonte de 15 anos já é o limite de confiança razoável e o de 20 é essencialmente especulativo.

### c) Modelos baseados em árvore
- **Random Forest** e **XGBoost/LightGBM** — construídos do zero (decisão de ignorar o notebook anterior), sem herdar tuning/pré-processamento de versões antigas.
- **Limitações:** árvores não extrapolam bem fora do range de treino — problema sério para tendência crescente nos horizontes de 10, 15 e 20 anos à frente (a previsão tende a saturar, especialmente nos dois últimos).

### d) Abordagem adicional — **Prophet e regressão bayesiana** (aprovado incluir as duas)
- Ambas expõem incerteza crescente com o horizonte — mais honesto para extrapolar 15 anos de dados para 20 anos à frente. Instruções do professor endossam liberdade metodológica.

### e) Análises ano a ano (complementares à série mensal)

A série mensal é a base, mas a agregação anual responde perguntas que a mensal esconde — e é como a maioria dos relatórios regulatórios reporta:

- **Agregação anual** — 15 pontos anuais em vez de ~180 mensais: menos ruído, Mann-Kendall mais limpo, sem necessidade de correção sazonal.
- **Tendência em janela móvel** (ex. janelas de 5 anos) — mostra se a tendência está **acelerando ou desacelerando**, muito mais informativo do que uma taxa única para todo o período.
- **Tendência recursiva/expansiva** — recalcular a inclinação usando dados até cada ano e plotar a evolução da estimativa: evidencia se o resultado é estável ou se depende de poucos anos específicos.
- **Regressão por partes (piecewise) com detecção de breakpoints** — testa se houve mudança de regime (ex. seca 2012-2016) em vez de assumir uma tendência linear única ao longo dos 15 anos.

### f) Métodos adicionais ainda não contemplados — por ordem de valor para este projeto

**f.1 WRTDS (Weighted Regressions on Time, Discharge, and Season)** ⭐ maior valor
Método padrão do USGS para tendência de qualidade de água. Separa explicitamente a mudança causada por variação de vazão da mudança "flow-normalized" (o que sobrou depois de descontar a vazão). Só se torna viável por causa da reconstrução de vazão da seção 1.5 — e responde diretamente à pergunta central do trabalho (a subida do TDS é diluição ou mais sal?). Provavelmente a adição metodológica mais forte disponível.

**f.2 Modelo de balanço de massa / mecanístico**
Em vez de extrapolar o TDS diretamente por 20 anos (estatisticamente frágil), modelar **separadamente** a carga de sal (lb/day) e a vazão (MGD), cada uma com sua própria tendência, e derivar `TDS = carga ÷ vazão`. Previsão fisicamente fundamentada — muito mais defensável em horizonte longo do que qualquer modelo caixa-preta extrapolando 20 anos além do histórico.

**f.3 Simulação de cenários (Monte Carlo)**
Em vez de um número único para +20 anos, projetar sob cenários de conservação (vazão −0%, −10%, −20%), como faz o estudo da bacia do LA River no material de apoio. Para horizonte longo, apresentar um leque de cenários é mais honesto do que uma previsão pontual — e alinha com a mensagem central já definida no plano (faixa de cenários com incerteza quantificada).

**f.4 Modelos estruturais de espaço de estados (Unobserved Components / DLM, via filtro de Kalman)**
Tendência local + componente sazonal, com incerteza nativa e tendência **variável no tempo** extraível como componente explícito. Costuma se comportar melhor que ARIMA em extrapolação longa, porque a tendência é modelada como estado e não como diferenciação. Disponível em `statsmodels` (`UnobservedComponents`).

**f.5 GAM (Modelo Aditivo Generalizado)**
Tendência suave (spline) + termo sazonal cíclico, com banda de confiança. Padrão em trabalhos ambientais/ecológicos, altamente interpretável — bom candidato a figura principal do artigo. Disponível em `pyGAM`.

**f.6 Regressão quantílica**
A tendência da **mediana** pode ser diferente da tendência do **percentil 90**. Como limites regulatórios incidem sobre valores máximos (não médias), saber se os picos de TDS sobem mais rápido que a média tem valor prático e regulatório real — e é um ângulo que a maioria dos trabalhos não cobre.

**f.7 Análise de intervenção / ARIMAX com regressores de evento**
Usar eventos conhecidos como variáveis exógenas: seca de 2012-2016 e a ordem estadual da Califórnia de redução obrigatória de 25% no consumo (2015). Liga a estatística diretamente à causa hipotetizada, em vez de deixar a associação implícita.

**f.8 SVR (Support Vector Regression)**
Aparece com frequência na literatura de previsão de TDS (material de apoio, Tema 2) e ainda não está na bateria — barato de adicionar como ponto de comparação com a literatura.

**f.9 Modelos fundacionais de séries temporais** (Chronos, TimesFM, TimeGPT)
Previsão zero-shot com modelos pré-treinados. Custo baixo de testar e é um diferencial interessante para um trabalho de pós-graduação em IA aplicada. Expectativa honesta: com ~180 pontos é improvável que superem os clássicos — mas o teste em si, com resultado negativo reportado, tem valor científico.

### g) Uso de GPU (CUDA) — decisão sua: aproveitar a RTX 4060 Ti 16GB

Nem todo método da bateria se beneficia de GPU — o dataset canônico é pequeno (~180 pontos mensais em 15 anos), então CUDA ajuda principalmente onde há busca de hiperparâmetros ou muitas iterações, não nos métodos estatísticos leves. Mapeamento honesto por método:

| Método | Roda em GPU/CUDA? | Como habilitar |
|---|---|---|
| Mann-Kendall, Theil-Sen, OLS | Não precisa — cálculo leve, dataset pequeno | CPU mesmo; forçar GPU aqui só adicionaria overhead |
| ARIMA/SARIMA (`statsmodels`) | Não — sem implementação GPU madura | CPU |
| Random Forest | Só com `cuML` (RAPIDS), não com `scikit-learn` puro | Exigiria instalar RAPIDS (Linux nativo ou WSL2 no Windows — não roda nativo no Windows) |
| XGBoost / LightGBM | **Sim, nativamente, inclusive no Windows** | XGBoost: `tree_method='hist', device='cuda'`; LightGBM: `device='gpu'` (build com suporte a GPU) |
| Prophet | Não — usa Stan/CmdStan, sem backend CUDA | CPU |
| Regressão bayesiana | Sim, se implementada com PyMC + backend JAX/Numpyro | Precisa `jax[cuda12]` compatível com o driver instalado |

**Onde a RTX 4060 Ti 16GB entra de fato:** `script_04_xgboost_lightgbm.py` (GPU nativa, ganho real no `GridSearchCV`) e, se optarmos pela variante JAX da regressão bayesiana em `script_05`, também acelera a amostragem MCMC. Random Forest só ganha GPU se o ambiente do usuário tiver RAPIDS configurado (WSL2) — caso contrário roda em CPU normalmente via `scikit-learn`, sem quebrar o pipeline.

**Pré-requisito de ambiente (fora do escopo desta sessão):** essa parte só roda na sua máquina local, com driver NVIDIA + CUDA Toolkit instalados (a RTX 4060 Ti é Ada Lovelace, compute capability 8.9 — compatível com CUDA 11.8+ e 12.x). O sandbox usado nesta sessão de planejamento não tem GPU, então a habilitação de CUDA será testada quando os scripts rodarem localmente, não aqui.

## 4. Estrutura de execução em paralelo

```
script_00_preprocessamento.py
  # lê TDS.csv/Chloride.csv/BOD.csv/Ammonia.csv com sep=';' decimal=','
  # filtra Location em {EFF-001, EFF-001A} (mesmo ponto físico, unificar)
  # filtra Calculated Method == "Monthly Average (Mean)" e Units == "mg/L"
  # APRESENTA as opções de tratamento de ND (seção 1.3) com números reais, aguarda decisão
  # uma linha por parâmetro/mês -> merge dos 4 parâmetros num dataset canônico
  # salva csv/parquet canônico
script_00b_sensibilidade_tratamento.py  # matriz de testes da seção 1.4 + reconstrução da vazão (1.5)
script_01_mann_kendall_theilsen.py      # inclui correções de autocorrelação e Seasonal Kendall (1.4 #8)
script_01b_analises_anuais.py           # agregação anual, janela móvel, tendência recursiva, piecewise (3.e)
script_02_arima_sarima.py
script_03_random_forest_gridsearch.py   # construído do zero
script_04_xgboost_lightgbm.py           # usa CUDA (tree_method/device='cuda') na RTX 4060 Ti
script_05_prophet_bayesiano.py          # bayesiano via JAX/CUDA se essa variante for escolhida
script_06_wrtds_balanco_massa.py        # WRTDS + modelo de balanço de massa + cenários (3.f.1-f.3)
script_07_estruturais_gam_quantilica.py # espaço de estados/DLM, GAM, regressão quantílica (3.f.4-f.6)
script_08_intervencao_svr_fundacionais.py # ARIMAX com eventos, SVR, modelos fundacionais (3.f.7-f.9)
```

Cada script de metodologia: lê o dataset canônico → split temporal (holdout ou walk-forward) → previsão pontual + IC para **+10, +15 e +20 anos** a partir do último dado observado → RMSE/MAE/R² no holdout, tendência (mg/L/ano), p-valor, previsão e IC90 para os 3 horizontes → grava uma linha em `resultados_comparacao.csv`/`.json` sem sobrescrever as demais.

Os scripts de metodologia rodam em paralelo (só dependem do dataset comum); a sincronização com o artigo roda depois, sobre os resultados consolidados.

### 4.1 Notebook único do projeto (`notebook.ipynb`) — obrigatório a partir de agora

Toda vez que eu criar ou alterar os scripts `.py` da bateria, também crio/atualizo um **notebook único** (`notebook.ipynb`, na raiz do projeto) reunindo o projeto inteiro: pré-processamento, análise exploratória, experimentação de cada metodologia, visualizações e apresentação final dos resultados/comparação. Esse notebook é o que você abre para ver tudo de forma simples, e é o que fica bonito ao ser renderizado direto no GitHub.

Regras para manter isso real, não decorativo:
- **Qualquer alteração num `.py`** (novo método, mudança de parâmetro, novo tratamento de dado, etc.) **precisa refletir no `notebook.ipynb` na mesma execução** — mesmo princípio já aplicado ao `Artigo/template.tex` (seção 2), agora estendido ao notebook.
- O notebook não duplica lógica "à mão" — ele importa/chama as funções dos `.py` (ou replica exatamente a mesma lógica de forma explícita célula a célula), para nunca divergir do que os scripts realmente fazem.
- Saídas (gráficos, tabelas) ficam nas células, mas sem embutir arquivos binários gigantes desnecessários — o notebook precisa continuar leve o suficiente para renderizar bem no GitHub.
- Estrutura sugerida do notebook (uma seção Markdown por bloco): 1) Objetivo do projeto (resumo), 2) Carregamento e pré-processamento dos dados (chama `script_00`), 3) Análise exploratória, 4) Testes de sensibilidade de tratamento (seção 1.4) e reconstrução da vazão (seção 1.5), 5) Uma seção por metodologia da bateria (3.a-3.f), cada uma com o resultado e o gráfico correspondente, 6) Tabela comparativa final (`resultados_comparacao.csv`), 7) Conclusão/discussão resumida.
- Este item entra também no checklist de saída (seção 7).

### 4.2 READMEs bilíngues (`README.md` e `README.pt-br.md`) — obrigatório a partir de agora

Criar e manter dois READMEs na raiz do projeto:
- `README.md` — completo, em inglês, no padrão GitHub (descrição do projeto, dados, metodologia, como rodar, estrutura de pastas, resultados principais, link para o notebook e para o artigo).
- `README.pt-br.md` — o mesmo conteúdo, em português.

No topo dos dois arquivos, o seletor de idioma:
- Em `README.md`: `Language / Idioma: **English** | [Português](README.pt-br.md)`
- Em `README.pt-br.md`: `Language / Idioma: [English](README.md) | **Português**`

Assim como o notebook e o artigo, **os READMEs são atualizados continuamente** — qualquer mudança relevante no projeto (novo dado, nova metodologia, novo resultado, mudança de conclusão) deve se refletir nos dois READMEs na mesma execução, não só no fim. Este item também entra no checklist de saída (seção 7).

### 4.3 Controle de experimentos e histórico de resultados (MLflow) — obrigatório a partir de agora

Com uma bateria de ~8-10 métodos rodando em 3 horizontes, cada um gerando várias execuções via CV/GridSearchCV, o `resultados_comparacao.csv` sozinho não dá controle fino o suficiente (não versiona execuções descartadas, não guarda hiperparâmetros/artefatos por tentativa). Passa a valer:

- **MLflow rodando localmente** (`mlflow ui`, sem nuvem, sem conta) como camada de rastreamento de experimentos, complementar ao `resultados_comparacao.csv` — não o substitui, alimenta ele.
- **Cada execução de um script (`script_0X`) é uma "run" do MLflow.** Buscas de hiperparâmetro (GridSearchCV/Optuna) geram runs "filhas" dentro da run principal, todas comparáveis lado a lado no dashboard.
- **Cada run registra:** hiperparâmetros usados, semente aleatória, janela de treino/holdout, métricas (RMSE, MAE, MASE, sMAPE, largura do IC90, cobertura empírica do IC), tempo de execução, se rodou em CPU ou GPU/CUDA, hash do commit do Git, e artefatos (gráfico da previsão, modelo serializado, tabela de resíduos).
- **`run_id` padronizado:** timestamp + hash do commit + nome do método — nunca há dúvida de qual versão de qual script gerou qual resultado.
- **Semente aleatória fixa e logada** em todo método estocástico (Random Forest, XGBoost/LightGBM, regressão bayesiana) — reprodutibilidade.
- **O `resultados_comparacao.csv` passa a ser um export/resumo** das runs finais escolhidas no MLflow (não mais escrito manualmente) — mantém o CSV como fonte enxuta para o notebook e o artigo, enquanto o histórico completo (inclusive experimentos descartados) fica rastreável no MLflow.
- A pasta local de tracking (`mlruns/`) entra no `.gitignore` (mesma recomendação leve já registrada na seção 2.E) — não é para versionar no Git, é um histórico local de experimentação.
- Este item entra também no checklist de saída (seção 7).

## 5. Critérios de comparação

Desempenho no holdout (RMSE/MAE/R²) sem ser o único critério; largura/comportamento do IC de longo prazo (IC largo e crescente > falsa confiança); significância estatística da tendência; coerência com a literatura (Nature 2020, DBS&A/SCSC 2018); robustez a diferentes janelas de treino; **robustez às variantes de tratamento da matriz de sensibilidade (seção 1.4) — um método cujo resultado só se sustenta sob uma escolha específica de pré-processamento é menos confiável que um estável entre variantes**; decisão final pode ser 2-3 métodos complementares, não um vencedor único.

## 6. Como as referências entram na discussão final

| Fonte | Tipo | Uso na discussão |
|---|---|---|
| Nature Sustainability (2020) | Artigo científico | Referência obrigatória — explica por que o TDS pode estar subindo. |
| DBS&A / Southern California Salinity Coalition (2018) | Relatório técnico | Estudo-irmão — comparar magnitude da tendência com outras ETEs. |
| Sustainable and Resilient Infrastructure / Tandfonline (2023) | Artigo científico | Implicações/recomendações de adaptação. |
| Ambiente & Água (2015) | Artigo científico | Fundamenta correlação TDS-amônia. |
| PMC5006585 (2016) | Artigo científico | Contextualiza correlação TDS-BOD. |
| ScienceDirect S0141022903003661 — Uygur & Kargı (2004) | Artigo científico | Reforça mecanismo de inibição salina. |
| LASAN — LAGWRP/OWLA, LADWP conservação de água | Fonte institucional | Contexto operacional e de política pública. |

## 7. Checklist de saída (a cada execução relevante do projeto)

```
[ ] O resultado gerado foi validado antes de ir para resultados_comparacao.csv?
[ ] Alguma figura/tabela nova precisa entrar em Artigo/images/ ou em resultados.tex?
[ ] O .tex certo foi identificado pela tabela da seção 2.C?
[ ] Alguma referência real nova foi adicionada a refs.bib (sem inventar dados)?
[ ] O bloco \color{red} de instrução foi removido da seção que ganhou conteúdo real?
[ ] O ciclo completo de compilação foi rodado (pdflatex → bibtex → pdflatex → pdflatex)?
[ ] O PDF e o .log foram checados por referência/citação/imagem quebrada?
[ ] Metodologia, objetivos e dados no artigo continuam coerentes com o que foi executado?
[ ] Nada foi inventado (resultado, métrica, citação, conclusão)?
[ ] O notebook.ipynb foi atualizado para refletir a mudança nos .py (seção 4.1)?
[ ] README.md e README.pt-br.md foram atualizados, mantendo o conteúdo espelhado entre os dois (seção 4.2)?
[ ] A execução foi logada no MLflow (params, métricas, seed, artefatos) antes de virar linha no resultados_comparacao.csv (seção 4.3)?
[ ] O resultado foi verificado contra a matriz de sensibilidade de tratamento (seção 1.4) — a conclusão se mantém sob as variantes testadas?
[ ] Se a conclusão muda conforme o tratamento adotado, isso foi reportado explicitamente no artigo como limitação/robustez?
[ ] A decisão tomada nesta execução foi registrada em `Artigo/DECISOES.md` com motivo e alternativa descartada?
[ ] Algum termo técnico novo foi introduzido? Entrou no GLOSSARIO.md?
[ ] A execução revelou alguma limitação ou fronteira nova? Entrou em ESCOPO_E_LIMITACOES.md?
```

## 9. Controle de versão (Git/GitHub)

**Git foi inicializado em 2026-08-14** (`prompt_decisoes_e_github.md`, Parte 2) — o projeto não tinha repositório antes disso. Branch padrão `main`, remoto em `https://github.com/igorfnogueira/projeto-aplicado`, primeiro commit com o pipeline completo (scripts 00-17, notebook, artigo, `Artigo/DECISOES.md`, READMEs). `.gitignore` exclui `.venv/`, `mlruns/`, `mlflow.db`, `__pycache__/`, artefatos de compilação LaTeX (`*.aux/.log/.bbl/.blg/.out/.toc`) e o scratch descartável da sessão; os CSVs brutos e de resultado são versionados (todos abaixo do limite de 100 MB do GitHub).

**`Artigo/DECISOES.md`** passa a ser documento de manutenção contínua com o mesmo status do notebook, dos READMEs e do artigo (seção 2.C-2.G, 4.1, 4.2 já estabeleciam essa regra para os demais; agora estende-se explicitamente ao registro de decisões) — toda decisão metodológica relevante entra lá na mesma execução em que é tomada, com motivo e alternativa descartada, nunca só ao final.

**`GLOSSARIO.md`** (criado em 2026-08-14, por exigência de `GOVERNANCA_DOCUMENTACAO_TEMPLATE.md`) e **`ESCOPO_E_LIMITACOES.md`** (mesma data) entram com o mesmo status de manutenção contínua do notebook/READMEs/artigo/`DECISOES.md`: todo termo técnico novo introduzido no projeto entra no glossário na mesma execução; toda fronteira ou fragilidade de resultado nova identificada entra em `ESCOPO_E_LIMITACOES.md`. Ver checklist §7.

**`RESUMO_EXECUTIVO_DECISOES.md`** (criado em 2026-08-19, saída da Fase 1/2 do kickoff crítico do projeto) resume em 1 página só as decisões que **mudaram uma conclusão** do trabalho, com link para a entrada completa em `Artigo/DECISOES.md` — não substitui o ADR completo, é uma camada de navegação para quem (incluindo a banca) precisa entender o projeto rápido. Atualizar só quando uma decisão nova mudar o rumo do trabalho, não a cada entrada nova do ADR.

**`Artigo/COMO_COMPILAR.md`** (mesma data) documenta os pré-requisitos de ambiente para compilar o artigo (TeX Live/`pdflatex`/`bibtex`, fora do `requirements.txt` Python) e o checklist de verificação pós-compilação — criado depois de uma sessão anterior ter concluído erroneamente que o LaTeX "não estava instalado" só porque não estava no `PATH` do shell (ver `Artigo/DECISOES.md`, nota de troubleshooting em D-38).

## 8. Pontos ainda em aberto

Nenhuma pergunta bloqueante restante. O único item que volta a aparecer é a decisão de tratamento de ND (seção 1.3), mas só na hora em que o `script_00` for de fato construído — não bloqueia a aprovação deste plano.

## Próximos passos

Plano pronto para aprovação. Ao aprovar, começo pelo `script_00_preprocessamento.py` (dataset canônico) e, quando chegar no tratamento dos ND do BOD, paro e apresento as opções da seção 1.3 com os números reais antes de continuar.
