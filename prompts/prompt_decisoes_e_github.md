# Prompt para Claude Code — Completar o DECISOES.md e publicar no GitHub

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

---

## Parte 1 — Completar o registro de decisões

Foi criado o arquivo `Artigo/DECISOES.md` — um registro no estilo ADR (decisão + alternativa
descartada + motivo + evidência) com 27 decisões já documentadas, cobrindo governança, escopo
dos dados, achados que mudaram o rumo do projeto (reconstrução da vazão, quebra EFF-001,
reenquadramento cíclico), decisões pendentes de tratamento, escolha de estação comparadora e
decisões sobre o artigo.

Leia `Artigo/DECISOES.md` inteiro primeiro. Depois **complete a seção "Pendências de registro"**
com o que só você tem contexto para documentar, seguindo exatamente o mesmo formato das entradas
existentes (D-XX, com Data/Status/Contexto/Decisão/Alternativas descartadas/Evidência):

1. **Decisões internas de cada script** (`script_01` a `script_17`): escolha de hiperparâmetros,
   ordem SARIMA selecionada e critério (AIC/BIC), features construídas, sementes aleatórias,
   e por que cada uma foi escolhida em vez das alternativas.
2. **Estratégia de validação adotada**: qual split temporal/CV foi usado, quantos folds, e por
   que essa configuração e não outra.
3. **Métodos que falharam, não convergiram ou tiveram desempenho ruim** — resultado negativo é
   resultado e deve ser registrado, não omitido. Inclua o motivo provável.
4. **Critério de escolha dos modelos finalistas** na síntese final (`script_15`).
5. **Qualquer decisão tomada durante a execução que não esteja no plano** — se você desviou do
   `plano_projeto_TDS.md` em algum ponto, registre o desvio e o motivo.

Regras ao preencher:
- **Nunca invente** um motivo que você não tem. Se uma escolha foi feita por padrão da biblioteca
  ou sem deliberação explícita, registre exatamente isso ("adotado o default de X porque não
  houve avaliação explícita de alternativas") — é mais honesto e mais útil que uma justificativa
  fabricada a posteriori.
- Toda entrada precisa apontar a **evidência** (script, arquivo de resultado ou run do MLflow).
- Não altere nem reescreva as decisões D-01 a D-27 já existentes, exceto se encontrar um **erro
  factual** — nesse caso, corrija e sinalize claramente o que estava errado.
- Se discordar de alguma decisão registrada, **não a apague**: adicione uma entrada nova com
  status "Revertida" ou "Em revisão" explicando o motivo, preservando o histórico.

Ao terminar, marque os itens da seção "Pendências de registro" como concluídos.

## Parte 2 — Inicializar o Git e publicar no GitHub

O projeto ainda **não tem repositório Git inicializado**. Isso é uma lacuna real: a especificação
do MLflow (`plano_projeto_TDS.md` §4.3) manda logar o hash do commit em cada run, e sem Git esse
campo de rastreabilidade fica vazio.

Repositório remoto já criado: **https://github.com/igorfnogueira/projeto-aplicado**

Execute:

1. **Antes de qualquer coisa, revise o `.gitignore`** e confirme que ele exclui:
   - `.venv/` (ambiente virtual — nunca versionar)
   - `mlruns/` (histórico local de experimentos)
   - `__pycache__/`, `*.pyc`
   - Artefatos de compilação LaTeX: `*.aux`, `*.log`, `*.bbl`, `*.blg`, `*.out`, `*.toc`
   - Arquivos temporários/scratch (ex.: `scratch_update_notebook6.py`, se for descartável)

   Confirme também que **os dados brutos e os CSVs de resultado devem ser versionados** (eles são
   pequenos e essenciais para reprodutibilidade) — a menos que algum ultrapasse 100 MB, limite do
   GitHub. Verifique os tamanhos antes: `Chloride.csv`, `BOD.csv` e `Ammonia.csv` têm ~5,6 MB cada,
   o que está OK.

2. `git init` (se o branch padrão vier como `master`, renomeie para `main`).

3. `git add` + primeiro commit com mensagem descritiva, por exemplo:
   `"Projeto Aplicado TDS/LAGWRP: pipeline completo, bateria de metodologias, artigo LaTeX e registro de decisões"`

4. Adicionar o remoto e fazer push:
   ```
   git remote add origin https://github.com/igorfnogueira/projeto-aplicado.git
   git branch -M main
   git push -u origin main
   ```

5. **Se o push pedir autenticação**, pare e me avise — não tente contornar. O GitHub não aceita
   mais senha de conta via HTTPS; será necessário um Personal Access Token ou SSH configurado por
   mim.

6. Depois do push bem-sucedido, **verifique no navegador** se o `notebook.ipynb` está renderizando
   corretamente no GitHub e se os dois READMEs aparecem com o seletor de idioma funcionando. Se o
   notebook estiver pesado demais para renderizar, me avise antes de tentar qualquer solução.

## Parte 3 — Ao final

Atualize, conforme a governança já estabelecida:
- `README.md` e `README.pt-br.md` — adicionar menção ao `Artigo/DECISOES.md` e ao repositório GitHub
- `plano_projeto_TDS.md` — registrar que o Git foi inicializado e que o `DECISOES.md` passa a ser
  documento de manutenção contínua (mesmo status do notebook, READMEs e artigo)
- O checklist de saída (§7 do plano) — incluir o item "a decisão tomada nesta execução foi
  registrada em `Artigo/DECISOES.md` com motivo e alternativa descartada?"
