# Governança de Documentação — [Nome do Projeto]

> **Este documento é uma instrução de projeto, não uma referência opcional.**
> Toda IA ou desenvolvedor que implementar mudanças neste projeto deve
> consultar as regras abaixo ANTES de considerar uma tarefa concluída.
>
> Este arquivo deve ser referenciado no documento de contexto principal
> do projeto (ex: `CLAUDE.md`, `AGENTS.md`, `.cursorrules` ou equivalente)
> para ser carregado automaticamente em toda sessão de trabalho. Ver
> seção "Como ativar este documento" ao final.

---

## Princípio

Documentação não é um evento único no início do projeto — é um artefato
que evolui junto com o código. Cada tipo de mudança tem um "gatilho"
que aciona a obrigação de criar ou atualizar um documento específico.

**Regra de ouro:** se você mudou o comportamento, a arquitetura, a
superfície de dados ou a segurança do sistema, e nenhum `.md` mudou
junto, a tarefa não está completa — só o código está.

---

## Estrutura mínima de documentos (criar no início do projeto)

Antes de qualquer linha de código, garantir que existam pelo menos:

| Documento | Propósito |
|---|---|
| `README.md` | O que o projeto faz, como rodar, stack usada |
| `SECURITY.md` | Como reportar vulnerabilidade, política de segredos |
| `LICENSE` | Termos de uso e distribuição do código |
| `.env.example` | Lista de variáveis de ambiente necessárias, sem valores reais |
| `CHANGELOG.md` | Histórico de mudanças por versão/data |
| `DECISOES_ARQUITETURA.md` | Registro de decisões técnicas (ADR) |

Os demais documentos abaixo são criados **sob demanda**, conforme os
gatilhos da tabela seguinte — não é necessário criar tudo de uma vez.

---

## Tabela de gatilhos — condição → documento obrigatório

### Segurança

| Se você... | Deve atualizar |
|---|---|
| Adicionar/trocar mecanismo de autenticação | `SECURITY.md` + `DECISOES_ARQUITETURA.md` |
| Adicionar uma nova chave de API, token ou segredo (mesmo em variável de ambiente) | `SECURITY.md` (documentar o nome da variável, nunca o valor) + `.env.example` |
| Expor um novo endpoint, função pública ou rota de API | `SECURITY.md` (avaliar superfície de ataque) + `TECHNICAL_DOCS.md` |
| Corrigir uma vulnerabilidade encontrada (própria ou de auditoria) | `SECURITY.md` (registrar o achado e a correção) + `CHANGELOG.md` |
| Alterar regras de acesso (permissões, papéis, políticas de autorização) | `SECURITY.md` |

### Privacidade / Dados pessoais (LGPD, GDPR ou equivalente)

| Se você... | Deve atualizar |
|---|---|
| Adicionar um novo campo que armazena dado pessoal (nome, telefone, CPF/CNPJ, e-mail, endereço, dado biométrico, etc.) | `DATA_PRIVACY.md` (o quê é coletado, onde fica, por quê) |
| Criar uma funcionalidade ou tool de IA que lê/agrega dados de usuários | `DATA_PRIVACY.md` (confirmar que dado sensível não vaza em agregações ou respostas) |
| Integrar um novo serviço terceiro que processa dados (provedor de IA, analytics, e-mail transacional, pagamento) | `DATA_PRIVACY.md` (base legal) + `DPA.md` se aplicável |
| Mudar por quanto tempo um dado é retido ou como é excluído a pedido do titular | `DATA_PRIVACY.md` |

### Arquitetura

| Se você... | Deve atualizar |
|---|---|
| Trocar ou adicionar uma tecnologia (banco de dados, framework, provedor de nuvem, linguagem) | `DECISOES_ARQUITETURA.md` (registrar como ADR: decisão + alternativas descartadas + motivo) |
| Mudar um fluxo de dados existente (de onde algo lê, para onde algo escreve) | `TECHNICAL_DOCS.md` (fluxo numerado, passo a passo) |
| Adicionar uma nova integração externa (webhook, API de terceiro) | `API_CONTRACT.md` (contrato formal do que é prometido e não deve quebrar) |
| Criar um mecanismo de fallback, cache ou redundância | `DECISOES_ARQUITETURA.md` + `INCIDENT_RESPONSE.md` (o que fazer se o fallback também falhar) |

### Funcionalidade / Produto

| Se você... | Deve atualizar |
|---|---|
| Adicionar uma funcionalidade nova visível ao usuário | `README.md` (seção de funcionalidades) + `CHANGELOG.md` |
| Mudar um fluxo que o usuário já usa | `CHANGELOG.md` + `TROUBLESHOOTING.md` se envolveu debugging não trivial |
| Adicionar uma nova variável de ambiente/configuração necessária | `.env.example` + `README.md` (seção de setup) |
| Adicionar uma nova ferramenta (tool) a um agente de IA | Documento de prompts/tools do projeto (tabela de tools) + system prompt correspondente |

### Processo / Time

| Se você... | Deve atualizar |
|---|---|
| Mudar convenção de código, nomenclatura ou padrão de commit | `CONTRIBUTING.md` |
| Descobrir uma falha que exigiu investigação não óbvia | `TROUBLESHOOTING.md` (causa raiz + tentativas + solução) |
| Mudar o processo de deploy ou a plataforma de hospedagem | `DEPLOY.md` (ou seção equivalente no README) |
| Introduzir um termo de domínio novo específico do negócio | `GLOSSARY.md` |

---

## Checklist de saída — rodar antes de finalizar QUALQUER tarefa

Antes de dizer que uma tarefa está concluída, responda:

```
[ ] Esta mudança tocou em autenticação, segredo ou permissão?
    → Se sim: SECURITY.md foi atualizado?

[ ] Esta mudança tocou em dado pessoal de usuário/cliente em qualquer
    camada (banco, IA, log, exportação)?
    → Se sim: DATA_PRIVACY.md foi atualizado?

[ ] Esta mudança trocou ou adicionou uma tecnologia, framework,
    provedor ou padrão arquitetural?
    → Se sim: DECISOES_ARQUITETURA.md tem uma entrada nova (ADR)?

[ ] Esta mudança alterou um fluxo de dados ou contrato de função
    já documentado?
    → Se sim: TECHNICAL_DOCS.md reflete o novo comportamento?

[ ] Esta mudança é visível ao usuário final (nova tela, novo botão,
    novo comportamento)?
    → Se sim: README.md e CHANGELOG.md foram atualizados?

[ ] Esta mudança exigiu debugging não trivial (mais de uma tentativa
    para achar a causa raiz)?
    → Se sim: TROUBLESHOOTING.md tem o registro?

[ ] Alguma variável de ambiente nova foi introduzida?
    → Se sim: .env.example foi atualizado com o NOME (nunca o valor)?

Se todas as respostas "se sim" acima foram tratadas (ou não se aplicam),
a tarefa está completa. Se alguma ficou pendente, a tarefa NÃO está
completa — o código funciona, mas a documentação está desalinhada
com a realidade do sistema.
```

---

## Regras de qualidade para as atualizações

Não basta tocar no arquivo — a atualização precisa ser útil:

```
1. ADRs em DECISOES_ARQUITETURA.md sempre incluem:
   - A decisão tomada
   - Pelo menos 1 alternativa considerada e descartada
   - O motivo do descarte (não só "escolhemos X")

2. Entradas em SECURITY.md e DATA_PRIVACY.md nunca incluem valores reais
   de segredos, tokens ou dados pessoais — só nomes de variáveis e
   descrição do tipo de dado

3. CHANGELOG.md segue formato objetivo: o que mudou, não como foi
   implementado (implementação fica no código/commit, não no changelog)

4. TROUBLESHOOTING.md documenta a CAUSA RAIZ, não só o sintoma —
   "login não funcionava" é fraco; "o token expira antes do refresh
   automático disparar" é o padrão esperado

5. Nunca marcar um documento como atualizado só para satisfazer o
   checklist — se a mudança não justifica atualização de fato,
   marcar como "não aplicável" é aceitável; texto vazio ou genérico não é
```

---

## Como ativar este documento

Para que qualquer sessão de IA (Claude Code, Cursor, GitHub Copilot, etc.)
carregue estas regras automaticamente, adicionar no topo do documento de
contexto principal do projeto (o arquivo que a IA já lê no início de toda
sessão — `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, ou equivalente):

```markdown
## Governança de documentação (leitura obrigatória)

Antes de considerar qualquer tarefa concluída, consultar e seguir
`GOVERNANCA_DOCUMENTACAO.md`. Este projeto trata documentação
desatualizada como um bug — uma mudança de código sem a atualização
de `.md` correspondente não está completa.
```

Se o projeto ainda não tem um documento de contexto principal, criar um
agora é o primeiro passo — sem ele, nenhuma instrução de governança é
carregada automaticamente, e este documento vira só um arquivo que
ninguém lê.

---

## Reforço opcional — auditoria de divergência (não obrigatório, mas recomendado)

Como este mecanismo depende de a IA seguir a instrução (não é uma trava
técnica), é possível adicionar um reforço leve: um comando que compara
quais arquivos de código mudaram num commit contra quais `.md` mudaram
junto, e sinaliza se parece haver mudança de código sem documentação
correspondente.

**PowerShell:**
```powershell
$arquivosCodigo = git diff --cached --name-only |
  Where-Object { $_ -match "\.(js|ts|py|go|java|rb|php|gs|html)$" }
$arquivosMd = git diff --cached --name-only | Where-Object { $_ -match "\.md$" }

if ($arquivosCodigo.Count -gt 0 -and $arquivosMd.Count -eq 0) {
  Write-Host "ATENCAO: codigo alterado sem nenhum .md atualizado neste commit." -ForegroundColor Yellow
  $arquivosCodigo | ForEach-Object { Write-Host "  $_" }
  Write-Host "Consulte GOVERNANCA_DOCUMENTACAO.md antes de commitar." -ForegroundColor Yellow
}
```

**Bash/Linux/Mac:**
```bash
arquivos_codigo=$(git diff --cached --name-only | grep -E '\.(js|ts|py|go|java|rb|php|gs|html)$')
arquivos_md=$(git diff --cached --name-only | grep -E '\.md$')

if [ -n "$arquivos_codigo" ] && [ -z "$arquivos_md" ]; then
  echo "ATENCAO: codigo alterado sem nenhum .md atualizado neste commit."
  echo "$arquivos_codigo"
  echo "Consulte GOVERNANCA_DOCUMENTACAO.md antes de commitar."
fi
```

Isso não bloqueia o commit (para não travar o fluxo de trabalho) —
só avisa. Pode ser promovido a um pre-commit hook real do Git se quiser
que seja mais rígido conforme o projeto amadurece.

---

## Revisão deste documento

Este documento em si segue a mesma regra que impõe aos outros: se o
projeto ganhar uma nova categoria de mudança que não se encaixa em
nenhuma linha da tabela de gatilhos, adicionar uma linha nova aqui
antes de seguir em frente — governança de documentação também evolui
com o projeto.

---

## Notas de uso deste template

- Substituir `[Nome do Projeto]` no título antes de usar
- A estrutura mínima de documentos pode ser enxugada em projetos muito
  pequenos ou pessoais — mas `README.md`, `.env.example` e
  `DECISOES_ARQUITETURA.md` valem a pena mesmo em protótipos
- Se o projeto não lida com dados pessoais, a seção de Privacidade/LGPD
  pode ser removida da tabela de gatilhos
- Se o projeto não usa IA/agentes, a linha correspondente na tabela de
  Funcionalidade/Produto pode ser removida
