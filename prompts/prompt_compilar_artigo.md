# Prompt para Claude Code — Compilar e verificar o artigo LaTeX

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

**Contexto:** o TeX Live **está instalado** nesta máquina. Na execução anterior o `pdflatex` não foi
encontrado, o que quase certamente é problema de `PATH` do shell, não de instalação ausente.
As últimas alterações em `Artigo/src/conclusao.tex` e `Artigo/src/resultados.tex` nunca foram
compiladas — o artigo está sem verificação.

---

## Etapa 1 — Localizar o TeX Live

Antes de concluir que não há LaTeX, verifique de fato:

1. Teste `pdflatex --version` e `bibtex --version`.
2. Se não encontrar, procure a instalação do TeX Live no sistema. No Windows costuma ficar em
   `C:\texlive\<ano>\bin\windows\` (versões mais antigas usam `win32`).
3. Se encontrar o executável fora do `PATH`, use o caminho completo nos comandos ou adicione o
   diretório ao `PATH` da sessão.
4. **Só declare que o LaTeX não está disponível depois de procurar de verdade** — e, nesse caso,
   informe exatamente o que foi testado e onde procurou.

## Etapa 2 — Compilar o ciclo completo

A partir de **dentro da pasta `Artigo/`** (o `template.tex` usa caminhos relativos como
`images/...` e `src/...`, então compilar de fora quebra as referências):

```
pdflatex template.tex
bibtex template
pdflatex template.tex
pdflatex template.tex
```

As duas passadas finais são necessárias para resolver referências cruzadas (`\ref`) e citações
(`\cite`). Uma passada só deixa tudo como `?`.

## Etapa 3 — Verificar o resultado (não basta compilar sem erro fatal)

Inspecione o `template.log` procurando especificamente por:

- `Undefined control sequence` — comando LaTeX inexistente ou pacote faltando
- `Citation ... undefined` — `\cite{}` apontando para chave que não existe em `refs.bib`
- `Reference ... undefined` — `\ref{}` apontando para `\label{}` inexistente
- `File ... not found` — imagem ausente ou caminho errado
- `Overfull \hbox` — texto vazando da coluna (não é erro, mas em layout de duas colunas com
  `multicol` costuma indicar tabela larga demais; reporte se for grave)
- `LaTeX Warning` de qualquer tipo

Depois abra/inspecione o **PDF gerado** e confirme:

- As 6 seções aparecem na ordem correta: abstract → introdução → trabalhos relacionados →
  metodologia → resultados → conclusão.
- **Todas as figuras renderizam** — há ~18 imagens em `Artigo/images/`; confirme que as
  referenciadas aparecem e que nenhuma saiu como caixa vazia.
- **A bibliografia aparece** e as citações no texto estão numeradas, não como `[?]`.
- As alterações recentes estão lá: a **seção de limitações** em `conclusao.tex` e a subseção
  **"Tratamento de dados robusto"** em `resultados.tex` (que foi criada para corrigir uma
  referência cruzada quebrada).
- **Atenção especial ao acento:** o arquivo `images/acurácia-x-epocas.png` tem acento no nome.
  Se ele falhar na compilação, esse é o motivo — renomeie para ASCII e atualize a referência no
  `.tex`, registrando a mudança.

## Etapa 4 — Reportar

Reporte objetivamente:
- O ciclo completou? Quantos erros e warnings, e quais?
- O PDF tem quantas páginas? Todas as seções e figuras presentes?
- Há citação ou referência não resolvida?

**Se algo estiver quebrado, conserte e recompile** — mas registre no relatório o que estava
errado e o que foi feito, não corrija silenciosamente.

**Se o PDF sair correto**, confirme que `template.pdf` está atualizado na pasta `Artigo/`.

## Regras herdadas

- Artefatos de compilação (`.aux`, `.log`, `.bbl`, `.blg`, `.out`, `.toc`) devem estar no
  `.gitignore` — confirme. O `template.pdf` pode ser versionado (é o entregável).
- Se alguma correção envolver decisão metodológica ou estrutural, registre em `Artigo/DECISOES.md`.
- Commit e push ao final, com mensagem descrevendo o que foi corrigido.
