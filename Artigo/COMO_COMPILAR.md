# Como Compilar o Artigo — Pré-requisitos de Ambiente

> **Por que este arquivo existe:** o `requirements.txt` na raiz do projeto cobre só as dependências
> Python do pipeline de análise — **não cobre o que é preciso para compilar o artigo em PDF**.
> Numa sessão anterior deste projeto, a ausência do LaTeX no `PATH` do shell foi erroneamente
> interpretada como "LaTeX não está instalado", e o artigo ficou sem ser recompilado por um tempo
> mesmo com o TeX Live já presente na máquina (ver `DECISOES.md`, nota de troubleshooting em D-38).
> Este documento existe para que isso não se repita.

## Pré-requisito

**TeX Live** (qualquer distribuição completa que inclua `pdflatex` e `bibtex`). Neste projeto, a
instalação de referência ficou em:

```
C:\texlive\2026\bin\windows\
```

**Antes de concluir que o LaTeX não está instalado, verifique de fato** (não assuma pelo `PATH`
padrão do shell):

```bash
pdflatex --version
bibtex --version
```

Se os comandos não forem encontrados, procure a instalação antes de desistir — no Windows costuma
ficar em `C:\texlive\<ano>\bin\windows\` (versões mais antigas usam `win32`). Se encontrar fora do
`PATH`, adicione o diretório à sessão do shell:

```bash
export PATH="/c/texlive/2026/bin/windows:$PATH"
```

(ajuste o ano/caminho conforme a instalação real da máquina).

## Ciclo de compilação completo

Sempre a partir de **dentro da pasta `Artigo/`** (o `template.tex` usa caminhos relativos como
`images/...` e `src/...` — compilar de fora quebra as referências):

```bash
cd Artigo
pdflatex -interaction=nonstopmode template.tex
bibtex template
pdflatex -interaction=nonstopmode template.tex
pdflatex -interaction=nonstopmode template.tex
```

As duas passadas finais do `pdflatex` são necessárias para resolver referências cruzadas (`\ref`)
e citações (`\cite`) — uma passada só deixa tudo como `?`.

## Checklist de verificação pós-compilação

Não basta "compilou sem erro fatal". Inspecione o `template.log` (gerado na própria pasta
`Artigo/`, ignorado pelo Git) procurando por:

```
[ ] "Undefined control sequence" -- comando LaTeX inexistente ou pacote faltando
[ ] "Citation ... undefined" -- \cite{} apontando para chave que não existe em refs.bib
[ ] "Reference ... undefined" -- \ref{} apontando para \label{} inexistente
[ ] "File ... not found" -- imagem ausente ou caminho errado
[ ] Qualquer "LaTeX Warning"
```

E confira o **PDF gerado**:

```
[ ] As 6 seções aparecem na ordem: abstract -> introdução -> trabalhos relacionados ->
    metodologia -> resultados -> conclusão
[ ] Todas as figuras referenciadas em Artigo/images/ renderizam (nenhuma caixa vazia)
[ ] A bibliografia aparece e as citações no texto estão numeradas, não como [?]
[ ] A página de título tem o título e os autores reais, não os placeholders do template
```

## Armadilha recorrente: acento dentro de modo matemático

Palavra acentuada dentro de `\mathrm{}`, `\text{}` ou `\log(\mathrm{})` em modo matemático
(`$...$`) quebra a compilação, mesmo com `amsmath` carregado (ver `DECISOES.md`, D-38). Ao escrever
uma fórmula nova, use a forma sem acento só dentro do `$...$` (ex. `vazao`, não `vazão`) — o texto
em prosa ao redor pode continuar acentuado normalmente. Isso já se repetiu duas vezes no projeto;
uma varredura pontual não previne reincidência, só a atenção ao escrever cada fórmula nova.

## O que é seguro versionar no Git

`Artigo/template.pdf` é o entregável e **deve** ser versionado. Os artefatos intermediários de
compilação (`*.aux`, `*.log`, `*.bbl`, `*.blg`, `*.out`, `*.toc`) já estão no `.gitignore` da raiz
do projeto — não precisam de atenção manual.
