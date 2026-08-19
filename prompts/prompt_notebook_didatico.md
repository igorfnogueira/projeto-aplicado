# Prompt para Claude Code — Tornar o notebook didático e integrar a nova documentação

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

---

Foram criados dois documentos novos na raiz do projeto:

- **`GLOSSARIO.md`** — todos os termos técnicos do projeto explicados (domínio sanitário,
  regulatório/dados, unidades e a conversão 8,34, estatística de dados censurados, estatística de
  tendência, modelagem, conceitos do estudo SCSC, instituições). Criado por exigência da própria
  governança (`GOVERNANCA_DOCUMENTACAO_TEMPLATE.md` prevê `GLOSSARY.md` como gatilho obrigatório).
- **`ESCOPO_E_LIMITACOES.md`** — fronteira do estudo: o que está dentro, o que ficou de fora por
  escolha, o que ficou de fora por indisponibilidade, e as fragilidades conhecidas dos resultados
  com os números reais.

Leia os dois integralmente antes de começar. Leia também `Artigo/DECISOES.md` (raciocínio por trás
de cada escolha) e `plano_projeto_TDS.md`.

## Tarefa 1 — Tornar o `notebook.ipynb` didático

Hoje o notebook mostra **o que** foi feito. Ele precisa passar a explicar **por que** — de forma que
alguém sem background em engenharia sanitária consiga ler de cima a baixo e entender o projeto
inteiro, inclusive na defesa da banca.

Para **cada seção** do notebook, adicione uma célula markdown *antes* do código contendo:

1. **O que esta etapa faz**, em uma frase.
2. **Por que ela é necessária** — qual pergunta ela responde ou qual problema ela resolve.
3. **Quais termos técnicos aparecem aqui**, com explicação de uma linha e link para o
   `GLOSSARIO.md` (ex.: "*Mann-Kendall*: teste não paramétrico de tendência monotônica — ver
   [Glossário](GLOSSARIO.md#mann-kendall)").
4. **Como interpretar o resultado** que vem logo abaixo — o que seria um bom resultado, o que seria
   um resultado ruim, e o que **não** se pode concluir dele.
5. Quando a etapa envolver uma decisão registrada, **referencie a decisão** (ex.: "a escolha de
   tratamento dos ND está documentada em D-16").

Adicione também, no notebook:

- **Uma célula de abertura** com: o problema em linguagem simples (por que a salinidade do esgoto
  de Los Angeles importa), a pergunta de pesquisa, um mapa do que o notebook cobre, e links para
  `GLOSSARIO.md`, `ESCOPO_E_LIMITACOES.md`, `Artigo/DECISOES.md` e `plano_projeto_TDS.md`.
- **Uma seção de limitações antes da conclusão**, resumindo as fragilidades de
  `ESCOPO_E_LIMITACOES.md` §4 — especialmente: a tendência que não sobrevive ao recorte pós-2012,
  a significância que inverte conforme a correção de autocorrelação, e a correlação TDS-BOD que
  contraria a hipótese inicial.
- **Uma célula de encerramento** com a leitura honesta do que o trabalho mostrou e do que ficou em
  aberto.

Regras ao escrever o texto didático:
- Linguagem clara, sem jargão não explicado. Se um termo aparece, ou é explicado ali ou aponta para
  o glossário.
- **Nunca suavizar resultado negativo.** A correlação TDS-BOD não confirma a hipótese do professor —
  isso deve estar escrito com todas as letras, como resultado legítimo, não escondido em nota de
  rodapé.
- Não inventar interpretação que os números não sustentam.
- Manter o notebook leve o suficiente para renderizar bem no GitHub.

## Tarefa 2 — Integrar os documentos novos ao restante do projeto

**`README.md` e `README.pt-br.md`:** adicionar `GLOSSARIO.md` e `ESCOPO_E_LIMITACOES.md` à estrutura
do projeto, com uma linha explicando para que serve cada um. Manter os dois idiomas espelhados.

**`plano_projeto_TDS.md`:** registrar os dois arquivos como documentos de manutenção contínua —
mesmo status já dado ao notebook, aos READMEs e ao artigo (§4.1-4.3).

**Checklist de saída (§7 do plano):** incluir dois itens novos:
```
[ ] Algum termo técnico novo foi introduzido? Entrou no GLOSSARIO.md?
[ ] A execução revelou alguma limitação ou fronteira nova? Entrou em ESCOPO_E_LIMITACOES.md?
```

**`Artigo/src/conclusao.tex`:** avaliar se a seção de limitações do artigo deve ser escrita ou
atualizada a partir de `ESCOPO_E_LIMITACOES.md` §4 e §5. Se sim, escreva em linguagem acadêmica
formal (o arquivo `.md` é o rascunho de trabalho, o `.tex` é o texto final) e compile o LaTeX
depois — ciclo completo `pdflatex → bibtex → pdflatex → pdflatex`, checando o `.log`.

## Tarefa 3 — Verificação

Antes de dar por concluído:
- Confirme que todos os links relativos entre os `.md` funcionam.
- Confirme que os números citados no notebook batem com os arquivos de resultado
  (`matriz_sensibilidade_resultados.csv`, `vazao_reconstruida_resultados.csv`,
  `resultados_comparacao.csv`) — não reproduza número de memória.
- Se encontrar divergência entre o que a documentação afirma e o que os resultados mostram,
  **pare e me avise** em vez de ajustar silenciosamente qualquer um dos lados.

## Regras herdadas

- Registrar em `Artigo/DECISOES.md` qualquer decisão metodológica tomada nesta execução.
- Logar no MLflow se algum script for reexecutado.
- Nunca inventar conteúdo — se faltar informação para explicar alguma etapa, marque como pendente
  em vez de preencher com texto genérico.
