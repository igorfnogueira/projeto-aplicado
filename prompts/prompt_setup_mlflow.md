# Prompt para Claude Code — Estruturar MLflow antes de continuar o projeto

Copie o texto abaixo e cole no Claude Code (terminal, dentro da pasta do projeto).

---

Antes de fazer qualquer uma das alterações do plano atual, leia especificamente a seção 4.3
("Controle de experimentos e histórico de resultados — MLflow") de @plano_projeto_TDS.md.

Sua primeira tarefa é ESTRUTURAR o MLflow no projeto, e só depois disso continuar com o
restante do plano (bateria de metodologias, script_00, notebook, READMEs, artigo). Nesta
primeira etapa:

1. Instalar/configurar o MLflow local (tracking store em pasta local, sem servidor remoto,
   sem conta). Adicionar mlflow ao requirements/ambiente do projeto.
2. Criar um módulo utilitário reutilizável (ex: utils/experiment_tracking.py) com uma função
   padrão que todo script_0X vai chamar para abrir uma run, logar parâmetros, semente
   aleatória, janela de treino/holdout, métricas (RMSE, MAE, MASE, sMAPE, largura do IC90,
   cobertura empírica), tempo de execução, se rodou em CPU ou GPU/CUDA, hash do commit atual
   do Git, e artefatos (gráfico, modelo serializado, tabela de resíduos) — sem duplicar essa
   lógica em cada script.
3. Definir e documentar o padrão de run_id (timestamp + hash do commit + nome do método).
4. Adicionar mlruns/ ao .gitignore do projeto.
5. Escrever a função que exporta as runs finais escolhidas do MLflow para
   resultados_comparacao.csv (formato já definido no plano, seção 4/7) — esse CSV deixa de
   ser escrito manualmente.
6. Validar tudo com um teste simples (uma run de exemplo, ex. rodando OLS no dataset já
   disponível) e confirmar que `mlflow ui` abre e mostra a run corretamente antes de seguir.

Só depois de validar esse setup, continue com o restante do plano normalmente, usando esse
utilitário de tracking em todo script novo que criar — sem contradizer nenhuma decisão já
aprovada em @plano_projeto_TDS.md.
