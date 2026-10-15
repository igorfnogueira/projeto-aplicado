# 0003 — Redução da bateria pública para 7 métodos e abandono do conceito de finalista

## Status
Aceita (2026-10-15)

## Contexto
Uma revisão externa do manuscrito reformulou o artigo em 5 frentes analíticas
(tendência/sensibilidade, correlação com PDSI, vazão/carga/balanço de massa,
TDS de origem, correlação destendenciada amônia/BOD), tratando os modelos de
previsão como "verificações auxiliares da dificuldade de previsão" — não mais
como fonte de uma previsão recomendada de longo prazo. Dos 15 métodos então
reportados em `results/resultados_comparacao.csv`, só 7 apareciam com
resultado mostrado nas tabelas dessa revisão: Mann-Kendall/Sen, Theil-Sen,
OLS, SARIMA, Prophet, naive e Detrend+RF.

Sem o híbrido SARIMA+Prophet — um dos dois finalistas recomendados por
`scripts/script_15_sintese_final.py` desde [ADR-0001](0001-remocao-regressao-bayesiana-dos-finalistas.md)
— restaria um único "finalista" (Detrend+RF), o que contradiz a própria
premissa do projeto ("não um único vencedor", critério de comparação
definido desde o plano original).

## Decisão
A bateria pública foi reduzida de 15 para os 7 métodos citados pela revisão
externa. Saíram da bateria pública (arquivados em `scripts/bateria_estendida/`,
nenhum resultado alterado):
- Tendência isolada do STL (`script_02` parcial → `script_33`)
- Random Forest puro (`script_03` parcial → `script_34`)
- Regressão bayesiana (`script_05` parcial → `script_35`)
- Naive sazonal, ETS/Holt-Winters, Theta (`script_08` parcial → `script_36`)
- Detrend+XGBoost (`script_10` parcial → `script_37`)
- Híbrido SARIMA+Prophet (`script_12`, movido inteiro, mesmo número)

`scripts/script_14_diagnostico_residuos.py` e
`scripts/script_31_testes_robustez_avancados.py` foram reescritos para os 3
candidatos remanescentes com tendência explícita (OLS, Detrend+RF, SARIMA).

`scripts/script_15_sintese_final.py` abandonou o conceito de "finalista"
inteiramente — em vez de eleger 1-2 métodos recomendados, passou a reportar
MASE/sMAPE/R²/tendência/IC90 dos 7 métodos do núcleo público, sem apontar
vencedor. Isso não é um ajuste da lista de finalistas (como D-67/ADR-0001
já tinha feito antes) — é a remoção do próprio conceito, porque com 1 método
só remanescente ele deixaria de fazer sentido.

## Consequências
- `results/resultados_comparacao.csv`/`.json` e `results/tabela_sintese_final.csv`
  passam a ter só as linhas dos 7 métodos do núcleo (mais as linhas
  causais/mecanismo — balanço de massa, WRTDS, cenários — que nunca fizeram
  parte dessa contagem). As linhas dos métodos removidos foram movidas para
  `results/bateria_estendida/resultados_comparacao_estendida.csv`/`.json`.
- `README.md`/`README.pt-br.md`/`CLAUDE.md`/`notebooks/notebook.ipynb` foram
  reescritos para refletir os 7 métodos e a ausência de recomendação de
  finalista — a conclusão do artigo não cita mais a convergência de
  finalistas em ~764-781 mg/L como achado do núcleo público (continua
  mencionada como achado histórico, já superado, nas seções que descrevem a
  bateria estendida).
- `scripts/bateria_estendida/` ganhou os scripts 33-37, além do `script_12`
  realocado sem mudança de número.
