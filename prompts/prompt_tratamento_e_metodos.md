# Prompt para Claude Code — Tratamento de dados robusto + métodos ampliados

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

Ordem recomendada de uso dos prompts do projeto:
1. `prompts/prompt_setup_mlflow.md` (estruturar o rastreamento de experimentos primeiro)
2. **este arquivo** (tratamento de dados + métodos ampliados)

---

Antes de executar qualquer etapa de modelagem, leia com atenção as seções novas de
@plano_projeto_TDS.md:

- **Seção 1.4** — matriz de 9 testes de sensibilidade no tratamento de dados
- **Seção 1.5** — reconstrução da vazão do efluente a partir de `lb/day ÷ (mg/L × 8,34)`
- **Seção 3.e** — análises ano a ano (agregação anual, janela móvel, tendência recursiva, piecewise)
- **Seção 3.f** — 9 métodos adicionais (WRTDS, balanço de massa, cenários, espaço de estados,
  GAM, regressão quantílica, análise de intervenção, SVR, modelos fundacionais)

Leia também @material_apoio_referencias.md como contexto da literatura (não como receita
fechada) e respeite todas as decisões já aprovadas no plano.

## Ordem de execução obrigatória

**ETAPA 1 — Validar a reconstrução da vazão (seção 1.5) antes de tudo**
Pareie as linhas de `mg/L` e `lb/day` por data/parâmetro e calcule a vazão implícita.
Verifique se o resultado é plausível para uma planta de capacidade nominal de 20 MGD.
Se a vazão derivada for implausível ou muito ruidosa, **não force** — reporte que a
identidade não se sustenta nos dados e siga sem ela, ajustando o plano. Se se sustentar,
essa série de vazão vira insumo dos métodos 3.f.1, 3.f.2 e 3.f.3.

**ETAPA 2 — Executar a matriz de sensibilidade (seção 1.4) ANTES de escolher tratamento**
Para cada uma das 9 decisões, rode as variantes e meça o impacto na tendência estimada do TDS
(inclinação, p-valor, sinal). Dê atenção especial a:
- #2 (quebra EFF-001 → EFF-001A) e #3 (mudanças de MDL/método) — são os riscos de degrau
  artificial que podem estar gerando "tendência" que não existe;
- #8 (autocorrelação no Mann-Kendall) — compare MK simples, pre-whitening, TFPW, correção de
  variância e Seasonal Kendall, porque o p-valor pode mudar de significativo para não
  significativo;
- #1 (ND do BOD) — inclua as opções F (Kaplan-Meier), G (ROS) e H (MLE) além de A-E.

Cada variante é uma run separada no MLflow. Ao final, apresente uma tabela consolidada
"decisão de tratamento × efeito na tendência" e **pare para eu decidir** quais tratamentos
adotar como padrão — não escolha sozinho.

**ETAPA 3 — Só depois, rodar a bateria ampliada de métodos**
Priorize nesta ordem: (a) os métodos já planejados nas seções 3.a-3.d; (b) as análises ano a
ano da 3.e; (c) os métodos novos da 3.f, começando por WRTDS, balanço de massa e cenários
(f.1-f.3), que são os que respondem à pergunta causal do trabalho.

## Regras que valem para tudo

- Toda execução logada no MLflow conforme seção 4.3 (params, seed, métricas, artefatos).
- Previsões sempre em +10, +15 e +20 anos a partir do último dado observado, com IC90.
- Nenhum método entra no relatório final sem vencer os baselines (naive, naive sazonal, ETS,
  Theta) — reporte MASE.
- Toda decisão metodológica registrada com motivo + alternativa descartada.
- Ao final de cada etapa: atualizar `notebook.ipynb`, `README.md`/`README.pt-br.md` e avaliar
  impacto em `Artigo/` (metodologia.tex/resultados.tex), compilando o LaTeX quando alterar.
- Nunca inventar resultado. Se um método falhar ou não convergir, isso é resultado e deve ser
  reportado como tal, não escondido.
- Previsão de 20 anos é extrapolação especulativa — apresentar sempre com essa ressalva.

## Entrega desta rodada

1. Relatório da validação da vazão (funcionou ou não, com evidência).
2. Tabela consolidada da matriz de sensibilidade, com recomendação justificada de tratamento
   para cada uma das 9 decisões — mas aguardando minha aprovação antes de fixar.
3. Só após minha aprovação, prosseguir com a bateria de métodos.
