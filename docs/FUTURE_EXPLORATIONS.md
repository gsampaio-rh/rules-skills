# Future Explorations

Ideas and themes outside the current scope. Each exploration defines an objective and exit criteria.

---

## Sprint A — Task Visualization

**Objetivo:** Criar uma forma de visualizar tarefas, progresso e dependências entre itens de trabalho gerenciados por agentes de IA.

**Critérios de saída:**
- [ ] Protótipo funcional de visualização (CLI, TUI, ou web dashboard)
- [ ] Suporte a pelo menos dois formatos de entrada (TODO lists em markdown, task files estruturados)
- [ ] Visualização de status (pending, in_progress, completed, blocked) com filtragem

**Notas de exploração:**
- Avaliar se uma TUI (textual, rich) é suficiente ou se precisa de uma interface web
- Investigar integração com task management nativo do Cursor e Claude Code
- Considerar formatos existentes: GitHub Projects, Linear, plain markdown checklists
- Explorar geração automática de diagramas de dependência (mermaid, graphviz)
- Definir schema de metadados por task: owner, prioridade, estimativa, dependências, labels, data de criação/conclusão
- Avaliar quebra de tarefas em arquivos individuais (`tasks/TASK-001.md`) vs tudo centralizado no PLAN.md — trade-off entre granularidade e overhead de navegação
- Investigar convenções de naming e numeração para task files (sequencial, slug-based, hash)
- Considerar um índice leve (`tasks/INDEX.md` ou `tasks.yaml`) que lista todas as tasks com status, enquanto o detalhe vive em arquivos separados

---

## Sprint B — Multi-Agent / Multi-Person Task Sharing

**Objetivo:** Definir como múltiplos agentes (Cursor, Claude Code, etc.) e múltiplas pessoas podem compartilhar, delegar e sincronizar tarefas num mesmo projeto.

**Critérios de saída:**
- [ ] Formato de task file que suporta ownership (agente ou pessoa) e handoff
- [ ] Protocolo de sincronização que evita conflitos (file-based, lock-free)
- [ ] Demonstração com pelo menos 2 agentes trabalhando no mesmo projeto

**Notas de exploração:**
- Investigar como cada tool persiste estado de tarefas (Cursor TodoWrite, Claude task files)
- Avaliar se um formato compartilhado (YAML, JSONL, markdown) pode ser lido/escrito por ambos
- Considerar padrões de ownership: quem "pega" uma task? Como sinalizar que terminou?
- Explorar integração com git branches — uma branch por agente? Task assignment via commit metadata?
- Investigar protocolos existentes: MCP task resources, A2A (Agent-to-Agent), shared context files

---

## Sprint C — Long-Running Project Management

**Objetivo:** Definir workflows e estruturas para projetos de longo prazo onde o contexto se perde entre sessões, sprints duram semanas, e múltiplas pessoas/agentes entram e saem.

**Critérios de saída:**
- [ ] Estrutura de documentação que preserva contexto entre sessões (decisions, rationale, current state)
- [ ] Mecanismo de "onboarding" automático — agente novo consegue entender o estado do projeto rapidamente
- [ ] Estratégia de archival: como mover contexto antigo sem perder rastreabilidade

**Notas de exploração:**
- O document hierarchy atual (PRD, PLAN, CHANGELOG, ADRs) já endereça parte disso — avaliar gaps
- Investigar "project memory" files que sumarizam o estado atual para onboarding rápido de agentes
- Considerar session handoff: ao final de uma sessão, o agente gera um resumo estruturado do que fez e do que ficou pendente
- Explorar integração com CHANGELOG.md como fonte de verdade histórica
- Avaliar limites de contexto: quando o projeto fica grande demais, como o agente prioriza o que ler?
- Investigar padrões de "progressive disclosure" — agente carrega contexto em camadas (resumo → detalhe)
