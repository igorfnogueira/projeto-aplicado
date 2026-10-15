# 0001 — Remoção da regressão bayesiana da lista de finalistas

## Status
Aceita (2026-10-14)

## Contexto
A bateria de previsão do projeto originalmente recomendava três finalistas em
`scripts/script_15_sintese_final.py`: `detrend_rf`, `hibrido_arima_prophet` e
`regressao_bayesiana`. Esta última foi escolhida por ser o único método com
incerteza "honesta" (IC90 cresce de forma suave e proporcional ao horizonte).

Um teste de Diebold-Mariano (correção HLN de amostra pequena, n=24 meses de
holdout) comparando cada candidato forte contra o baseline naive mostrou que a
regressão bayesiana perde de forma estatisticamente significativa (p=0,0147) —
diferente dos outros dois finalistas, que ficam estatisticamente empatados com
o naive (p=0,81 e p=0,29). Nenhum dos outros quatro candidatos fortes
(OLS, Detrend+RF, SARIMA, híbrido) perde dessa forma.

## Decisão
`FINALISTAS` em `scripts/script_15_sintese_final.py` reduzido de 3 para 2
(`detrend_rf`, `hibrido_arima_prophet`). A regressão bayesiana sai da lista de
finalistas recomendados, mas continua no artigo como um dos métodos originais
que confirmam a tendência clássica — perde apenas o rótulo de finalista. A
faixa de convergência dos finalistas em +10/+15/+20 anos foi recalculada sem
ela: 714,4–743,5 / 738,9–762,2 / 763,5–780,9 mg/L (antes, com os 3 métodos:
faixa mais larga, ~714–806 mg/L).

## Consequências
- `scripts/script_15_sintese_final.py` e `scripts/script_31_testes_robustez_avancados.py`
  foram re-executados; `results/tabela_sintese_final.csv` e as figuras de
  síntese final refletem só os 2 finalistas atuais.
- README.md/README.pt-br.md e `notebooks/notebook.ipynb` foram atualizados
  para citar o teste de Diebold-Mariano como motivo explícito da exclusão —
  reportado como achado, não omitido.
- A regressão bayesiana permanece implementada em `scripts/script_05_prophet_bayesiano.py`
  e segue no comparativo completo de métodos (`results/resultados_comparacao.csv`).
