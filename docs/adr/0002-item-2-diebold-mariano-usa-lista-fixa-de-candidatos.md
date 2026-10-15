# 0002 — Item 2 do script_31 (Diebold-Mariano) passa a usar uma lista fixa de candidatos

## Status
Aceita (2026-10-14)

## Contexto
Depois de [ADR-0001](0001-remocao-regressao-bayesiana-dos-finalistas.md) reduzir
`FINALISTAS` de 3 para 2 métodos em `scripts/script_15_sintese_final.py`, uma
auditoria encontrou que a rotina do item 2 de
`scripts/script_31_testes_robustez_avancados.py` (Diebold-Mariano) montava a
lista de métodos comparados a partir de `FINALISTAS + [runner_up, "naive"]` —
ou seja, lendo a mesma constante que a ADR-0001 acabou de reduzir — em vez de
uma lista fixa e independente, como já faziam os itens 1, 3 e 4 do mesmo
script.

Como consequência, rodar `script_31` de novo depois da ADR-0001 deixava de
gerar a comparação `regressao_bayesiana_vs_naive` — exatamente o teste
(estatística=2,638, p=0,0147) que motivou a própria ADR-0001, e que é citado
publicamente em `README.md`, `README.pt-br.md` e `notebooks/notebook.ipynb`.
Rodar a bateria de robustez de novo teria silenciosamente tornado essa
evidência irreprodutível.

## Decisão
O item 2 de `scripts/script_31_testes_robustez_avancados.py` passa a usar a
mesma constante `CANDIDATOS` (lista fixa dos 5 candidatos fortes + naive) já
usada pelos itens 1, 3 e 4 do script, em vez de derivar a lista de
`script_15.FINALISTAS`. O conjunto comparado no Diebold-Mariano agora é
estável e independente de qual subconjunto é recomendado como finalista em um
dado momento.

## Consequências
- `results/testes_robustez_resultados.csv`/`.json` voltam a incluir a
  comparação `regressao_bayesiana_vs_naive` em toda execução futura de
  `script_31`, preservando a evidência citada no artigo e no README.
- Este padrão (usar uma lista fixa, não derivada de `FINALISTAS`) deve ser
  mantido em qualquer novo item adicionado ao script de robustez.
