# Manutenção Contínua do Artigo Científico do Projeto Aplicado

A pasta:

`C:\Projetos Programação\Cursor\1 - Pós Graduação IA Aplicada\9 - Projeto Aplicado\Artigo`

faz parte integrante deste projeto.

Dentro dela existe o arquivo:

`template.tex`

Esse arquivo é o **documento principal do artigo científico do Projeto Aplicado** da pós-graduação em Inteligência Artificial Aplicada.

## Regra principal

Durante **qualquer execução, análise, desenvolvimento, experimento, alteração metodológica ou produção de resultado relacionada ao Projeto Aplicado**, você deve considerar o `template.tex` como um documento vivo e mantê-lo atualizado.

O artigo **não deve ser deixado para ser preenchido somente ao final do projeto**.

Sempre que uma atividade produzir informação relevante para o artigo, avalie se essa informação deve ser incorporada ao `template.tex` e, quando aplicável, atualize o arquivo imediatamente.

---

## 1. Primeiro: avaliar a estrutura do projeto

Antes de realizar alterações importantes no projeto:

1. Analise a estrutura da pasta do Projeto Aplicado.
2. Identifique os arquivos relacionados a:
   - dados;
   - notebooks;
   - scripts;
   - análises exploratórias;
   - modelos de Machine Learning;
   - resultados;
   - gráficos;
   - tabelas;
   - documentação;
   - referências bibliográficas;
   - configurações;
   - experimentos;
   - versões ou resultados anteriores.
3. Analise também a pasta `Artigo`.
4. Leia integralmente o `template.tex`.
5. Identifique:
   - a estrutura do artigo;
   - títulos e subtítulos existentes;
   - instruções presentes no template;
   - conteúdo esperado em cada seção;
   - campos ainda vazios;
   - placeholders;
   - comentários orientativos;
   - informações que já foram preenchidas.

**Não altere a estrutura acadêmica do template sem necessidade.**

O template deve ser tratado como a estrutura-base oficial do artigo.

---

# 2. O template.tex é a fonte de verdade do artigo

O arquivo:

`C:\Projetos Programação\Cursor\1 - Pós Graduação IA Aplicada\9 - Projeto Aplicado\Artigo\template.tex`

deve permanecer continuamente sincronizado com o estado atual do projeto.

Sempre que houver uma mudança relevante no projeto, verifique seu impacto no artigo.

Exemplos:

- alteração do objetivo;
- alteração da pergunta de pesquisa;
- inclusão ou remoção de dados;
- alteração do período analisado;
- alteração da metodologia;
- inclusão de uma nova variável;
- alteração de técnicas de pré-processamento;
- alteração de modelo;
- criação de novo experimento;
- mudança nos parâmetros do modelo;
- novos resultados;
- novos gráficos;
- novas tabelas;
- descoberta de limitações;
- alteração das conclusões;
- identificação de trabalhos relacionados;
- inclusão de referências;
- mudança na interpretação dos resultados.

Quando uma dessas alterações ocorrer, atualize o artigo na mesma execução, sempre que houver informação suficiente para isso.

---

# 3. Nunca inventar conteúdo científico

O artigo deve refletir **exclusivamente o que foi efetivamente realizado ou demonstrado no projeto**.

Nunca:

- invente resultados;
- invente métricas;
- invente referências;
- invente experimentos;
- invente dados;
- invente conclusões;
- transforme uma hipótese em resultado comprovado;
- afirme que uma metodologia foi utilizada quando ela não foi executada;
- apresente previsões como fatos observados;
- preencha lacunas científicas com informações fictícias.

Quando uma seção ainda não possuir informações suficientes, mantenha-a como pendente ou incompleta, seguindo a estrutura do template.

Se houver dúvida sobre determinada informação, **não assuma**.

---

# 4. Diferenciar claramente três tipos de informação

Ao atualizar o artigo, mantenha distinção entre:

### A. Informações já comprovadas

Resultados efetivamente obtidos pelo projeto.

Exemplo:

- métricas calculadas;
- número de registros;
- período dos dados;
- resultados dos experimentos;
- relações estatísticas encontradas;
- desempenho dos modelos.

Essas informações podem ser incorporadas ao artigo.

### B. Decisões metodológicas

Procedimentos que foram efetivamente escolhidos e executados.

Exemplo:

- método de tratamento dos dados;
- divisão temporal dos dados;
- algoritmo utilizado;
- variáveis utilizadas;
- métricas de avaliação.

Devem ser documentados na metodologia.

### C. Hipóteses, planos ou trabalhos futuros

Aquilo que ainda não foi executado.

Não deve ser apresentado como resultado.

Pode ser registrado como:

- hipótese;
- proposta;
- limitação;
- trabalho futuro;
- etapa pendente.

---

# 5. Atualização seção por seção

Sempre que houver nova informação, determine em qual seção do artigo ela pertence.

Por exemplo:

- **Introdução:** contexto, problema, justificativa e objetivos.
- **Referencial teórico:** conceitos e trabalhos científicos utilizados.
- **Metodologia:** dados, tratamento, variáveis, métodos e modelos efetivamente utilizados.
- **Resultados:** resultados experimentais, métricas, gráficos e tabelas.
- **Discussão:** interpretação dos resultados e comparação com literatura.
- **Conclusão:** síntese dos achados e resposta ao problema de pesquisa.
- **Limitações:** limitações identificadas durante o desenvolvimento.
- **Trabalhos futuros:** etapas ainda não realizadas ou possíveis extensões.

Não coloque informações em uma seção apenas porque ela está disponível; mantenha coerência acadêmica.

---

# 6. Manter consistência entre projeto e artigo

Sempre que atualizar o artigo, verifique a consistência entre:

- objetivos;
- metodologia;
- dados;
- variáveis;
- experimentos;
- resultados;
- discussão;
- conclusões.

Por exemplo:

Se um modelo for removido do projeto, ele não deve continuar sendo apresentado no artigo como modelo utilizado.

Se uma variável for adicionada à análise, avalie se ela precisa aparecer também na metodologia, resultados e discussão.

Se um resultado mudar, verifique se a interpretação e a conclusão continuam válidas.

---

# 7. Resultados devem ser rastreáveis

Sempre que possível, os resultados apresentados no artigo devem poder ser relacionados aos arquivos, notebooks, scripts ou experimentos que os produziram.

Não copie resultados manualmente sem verificar sua origem.

Para cada resultado importante, procure identificar:

- qual experimento o produziu;
- qual arquivo contém o resultado;
- qual conjunto de dados foi utilizado;
- quais parâmetros foram utilizados;
- qual método foi aplicado.

O objetivo é que o artigo seja **reprodutível e auditável**.

---

# 8. Gráficos e tabelas

Quando um gráfico ou tabela produzido pelo projeto for relevante para o artigo:

1. Verifique se ele já existe.
2. Identifique sua origem.
3. Avalie se deve ser incluído no artigo.
4. Caso seja necessário, atualize o `template.tex` para referenciá-lo.
5. Mantenha legenda, numeração e referência no texto consistentes.

Não crie artificialmente gráficos ou tabelas apenas para preencher o artigo.

---

# 9. Referências bibliográficas

Quando uma fonte científica for efetivamente utilizada para fundamentar o artigo:

- registre a referência de maneira adequada;
- utilize o mecanismo bibliográfico já adotado pelo template;
- cite a fonte no ponto correspondente do texto;
- não invente DOI, autores, títulos ou dados bibliográficos.

Não adicione referências apenas para aumentar a quantidade de citações.

---

# 10. Qualidade acadêmica

O artigo deve evoluir progressivamente em direção a um artigo científico completo.

Ao atualizar o `template.tex`, procure manter:

- linguagem acadêmica;
- clareza;
- precisão técnica;
- coerência metodológica;
- distinção entre resultado e hipótese;
- citações adequadas;
- ausência de afirmações sem evidência;
- consistência terminológica;
- coerência entre objetivos, métodos e conclusões.

Evite linguagem promocional ou afirmações exageradas sobre os resultados.

---

# 11. Não apagar informações importantes sem verificar

Antes de remover conteúdo existente do artigo:

1. Verifique se ele ainda é válido.
2. Verifique se alguma outra seção depende dele.
3. Caso tenha sido substituído por uma nova abordagem, atualize todas as partes relacionadas.

Não simplesmente sobrescreva informações anteriores sem avaliar os impactos.

---

# 12. Ao finalizar cada execução

Antes de considerar uma execução do projeto concluída, faça uma verificação específica do artigo:

### Checklist

- [ ] O `template.tex` foi analisado em relação às alterações realizadas?
- [ ] Novos resultados relevantes foram incorporados?
- [ ] Alterações metodológicas foram refletidas?
- [ ] Variáveis e dados estão atualizados?
- [ ] Objetivos continuam coerentes com o trabalho realizado?
- [ ] Resultados apresentados correspondem aos resultados realmente obtidos?
- [ ] Não foram inventadas informações?
- [ ] Gráficos e tabelas relevantes foram avaliados?
- [ ] Referências novas foram incorporadas quando necessário?
- [ ] Discussão e conclusões continuam coerentes com os resultados?
- [ ] Limitações ou etapas pendentes foram registradas quando necessário?
- [ ] O artigo continua compilável em LaTeX?

---

# 13. Regra para mudanças futuras

Sempre que eu solicitar qualquer atividade relacionada ao Projeto Aplicado, **não trate a solicitação como isolada do artigo**.

Antes de finalizar a tarefa, pergunte internamente:

> "O que foi alterado ou descoberto nesta execução precisa ser refletido no artigo?"

Se a resposta for sim, atualize o `template.tex`.

Se a resposta for não, não faça alterações desnecessárias no artigo.

---

# 14. Prioridade

A prioridade é:

**Projeto real → evidências/resultados → documentação → artigo científico.**

O artigo deve documentar fielmente a evolução real do projeto.

Não faça o projeto se adaptar artificialmente ao artigo.

O artigo deve se adaptar ao projeto conforme o projeto evolui.

---

# 15. Estado atual do Projeto Aplicado

O Projeto Aplicado está relacionado à análise de tendências de longo prazo da salinidade em águas residuárias da **Los Angeles–Glendale Water Reclamation Plant (LAGWRP)**.

O trabalho envolve, entre outros aspectos:

- análise histórica de aproximadamente 15 anos de dados;
- TDS (Total Dissolved Solids);
- cloreto;
- amônia;
- BOD;
- análise de tendências temporais;
- investigação das relações entre as variáveis;
- aplicação de métodos de Inteligência Artificial/Machine Learning;
- avaliação de possibilidades de previsão de longo prazo;
- interpretação das implicações ambientais e operacionais.

Essas informações devem ser consideradas como contexto inicial, mas **não devem ser tratadas como definitivas caso os arquivos e experimentos atuais do projeto indiquem alterações**.

A versão atual dos arquivos, dados, notebooks, scripts e resultados do projeto deve sempre prevalecer sobre informações antigas.

---

## Regra final

O `template.tex` não é apenas um arquivo para ser preenchido no final.

Ele é o **registro acadêmico vivo do Projeto Aplicado**.

Portanto, durante todo o desenvolvimento:

**desenvolver → analisar → obter resultado → documentar → atualizar o artigo → continuar o projeto.**

Ao final de cada execução relevante, o artigo deve refletir o estado mais atual e comprovado do projeto.