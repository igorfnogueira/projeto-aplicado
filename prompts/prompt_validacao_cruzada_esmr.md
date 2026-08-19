# Prompt para Claude Code — Validação cruzada do dataset com o export original do eSMR

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

---

## Contexto

Foi feita uma nova consulta ao portal CIWQS eSMR para o LAGWRP, com data inicial 01/01/2000, para
testar se a série poderia ser estendida antes de 2011. O arquivo resultante é
`eSMR_Analytical_Report.xls` (precisa ser colocado na pasta do projeto — se não estiver lá, pare e
me avise).

**Resultado da consulta, já verificado:** **não existe nenhum registro anterior a 2011.** A busca
por datas de 2000 a 2010 retornou zero ocorrências. O arquivo cobre 2011-2026, com 856 linhas de
TDS contra as 848 do `TDS.csv` atual.

**Conclusão:** 2011 é o limite real do eSMR para esta estação, não um recorte da consulta original.
Isso encerra a hipótese de estender a série por via pública.

## ⚠️ Armadilha crítica de formato — leia antes de processar qualquer coisa

O arquivo novo veio no **formato nativo do portal**, enquanto os CSVs atuais do projeto foram
salvos com configuração regional brasileira. As diferenças são silenciosas:

| | CSVs atuais do projeto | `eSMR_Analytical_Report.xls` |
|---|---|---|
| Separador | `;` (ponto e vírgula) | **TAB** (`\t`) |
| Decimal | `,` (vírgula) | **`.`** (ponto) |
| Formato de data | **DD/MM/AAAA** | **MM/DD/AAAA** |
| Extensão | `.csv` | `.xls` — **mas é texto delimitado por tab, não binário Excel** |

**A diferença de data é a mais perigosa.** Foi confirmada comparando o mesmo registro nos dois
arquivos: a linha de `68902 lb/day` do relatório de janeiro/2012 aparece como `04/01/2012` no
`TDS.csv` e como `01/04/2012` no arquivo novo.

Ler o arquivo novo com o parser atual (`sep=';', decimal=','`, DD/MM) **não gera erro** — gera
**corrupção silenciosa**: datas até o dia 12 trocariam de mês, e do dia 13 em diante falhariam.

Leia o arquivo novo com: `sep='\t'`, `decimal='.'`, e parser de data `%m/%d/%Y`.

## Tarefa 1 — Validação cruzada (`script_22_validacao_cruzada.py`)

O arquivo novo não estende a série, mas serve para **validar que a conversão regional feita
originalmente não corrompeu nenhum dado**. Isso nunca foi verificado.

Compare o export nativo contra o `TDS.csv` atual:

1. **Contagem de linhas:** o novo tem 856 linhas de TDS, o atual tem 848. **Explique a diferença de
   8 linhas** — são registros novos (meses recentes adicionados desde o download original),
   duplicatas, ou linhas que se perderam na conversão? Não assuma; identifique quais são.

2. **Pareamento registro a registro:** case as linhas pelas chaves naturais (`Location`,
   `Parameter`, `Calculated Method`/`Analytical Method`, `Sampling Date`, `Units`) e verifique:
   - Todas as datas batem depois de normalizar os dois formatos?
   - Todos os valores de `Result` batem?
   - Os campos `MDL`/`ML`/`RL` batem?
   - Os qualificadores `Qual` (incluindo `ND`) batem?

3. **Verificação específica das datas:** este é o ponto de maior risco. Confirme que nenhuma data
   foi trocada na conversão DD/MM ↔ MM/DD. Um teste eficaz: para todo registro cujo dia ≤ 12,
   verifique se dia e mês não foram invertidos comparado ao par correspondente.

4. **Impacto na série canônica:** se houver divergência, quantifique — quantos pontos da série
   mensal mudam, e a tendência estimada muda?

**Se encontrar divergência real, pare e me avise antes de corrigir qualquer coisa.** Uma correção
silenciosa aqui invalidaria toda a análise já feita sem deixar rastro.

**Se não houver divergência**, isso é um resultado positivo relevante: confirma a integridade do
dataset que sustenta todas as conclusões do projeto.

## Tarefa 2 — Registrar o achado sobre o limite do eSMR

Independente do resultado da validação, registre:

**Em `Artigo/DECISOES.md`** — entrada nova documentando que a tentativa de estender a série foi
executada, com que parâmetros, e que o resultado foi negativo: o eSMR não tem dado do LAGWRP antes
de 2011. Isso fecha a Ação A e reforça que estender a série depende de solicitação direta ao LASAN
(ver `solicitacao_dados_LASAN.md`).

**Em `ESCOPO_E_LIMITACOES.md`** — atualizar a §3 para registrar que os 15 anos são o **máximo
disponível publicamente**, e que isso foi verificado empiricamente (não presumido). Isso fortalece
a limitação: deixa de ser "não buscamos mais dados" e passa a ser "buscamos, e não existe".

**Em `GLOSSARIO.md`** — acrescentar na entrada do eSMR/CIWQS a informação de que o export nativo do
portal usa tab/ponto/MM-DD, diferente dos CSVs do projeto. É exatamente o tipo de detalhe que
causaria erro em quem retomar o projeto depois.

## Regras herdadas

- Logar no MLflow.
- Atualizar `notebook.ipynb` com uma seção sobre a validação (o quê / por quê / como interpretar).
- Atualizar `README.md` e `README.pt-br.md` se o resultado for relevante.
- Compilar o LaTeX se alterar `Artigo/src/` (TeX Live em `C:\texlive\2026\bin\windows\`).
- **Não corrigir divergência silenciosamente** — reportar primeiro.
- Commit e push ao final.

## Entrega

1. Resposta objetiva: **o dataset atual está íntegro em relação ao export nativo do portal?**
2. Explicação da diferença de 8 linhas.
3. `DECISOES.md`, `ESCOPO_E_LIMITACOES.md` e `GLOSSARIO.md` atualizados.
