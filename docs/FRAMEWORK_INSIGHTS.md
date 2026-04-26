# Orquestrum Framework — Insights Operacionais

**Baseado em:** Verificação de acessos em projeto real (Chat Connect Pro)  
**Data:** 26 de abril de 2026  
**Objetivo:** Validar padrões de organização de agents e skills para aplicação em novos projetos

---

## 1. Matriz de Acesso de Orchestrators

### Padrão Validado

O framework define uma matriz de acesso **rigorosamente compartimentalizada**:

```
┌──────────────┬──────────────┬──────────────┬────────────────┐
│ Orchestrator │ Leitura      │ Escrita      │ Status         │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ Lore (0–1)   │ Indústria    │ 00-discovery │ ✅ Isolado     │
│              │ Specs ant.   │ Spec/ADR     │                │
│              │              │ Glossário    │                │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ Forge (2–3)  │ 00-discovery │ 01-design    │ ✅ Isolado     │
│              │ (RO)         │ 02-planning  │                │
│              │ Padrões      │ Arch/Epics   │                │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ Ward (4)     │ Tudo ant.    │ 03-quality   │ ✅ Isolado     │
│              │ (RO)         │ Review/QA    │                │
│              │              │ Learning     │                │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ Cast (5+)    │ Tudo ant.    │ 04-release   │ ✅ Isolado     │
│              │ (RO)         │ Changelog    │                │
│              │              │ Runbook      │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

**Observação crítica:** A falta de write permissions em fases anteriores **previne contaminação de artefatos** e garante que cada orchestrator trabalhe apenas no escopo atribuído.

### Implementação Recomendada

Para novos projetos:

1. **Validar fencing antes de qualquer operação** — confirmar que cada orchestrator pode ler e escrever apenas em seus diretórios
2. **Usar permissões de filesystem** (se necessário) para reforçar o fencing em nível de OS
3. **Documentar matriz de acesso em `docs/FRAMEWORK.md`** para referência durante execução

---

## 2. Estrutura Canônica de Diretórios

### Layout Necessário para Orquestrum Funcionar

```
docs/
├── 00-discovery/          ← Lore (read+write) | Outros (read-only)
│   ├── glossary/
│   │   └── GLOSSARY.md          (OBRIGATÓRIO: ≥5 termos para Gate 0→1)
│   ├── spec/
│   │   ├── spec-v0-extracted.md (Trace output)
│   │   └── spec-v1-*.md         (Lore output — Fase 1)
│   ├── adr/
│   │   ├── ADR-001.md
│   │   └── ADR-NNN.md           (Lore output)
│   └── patterns/                (Diretório essencial)
│
├── 01-design/             ← Forge (write) | Lore (read-only)
│   └── architecture/
│       ├── ARCHITECTURE-v0-as-is.md  (Trace output)
│       └── ARCHITECTURE-v1.md        (Forge output — Fase 2, obrigatório para Gate 2→3)
│
├── 02-planning/           ← Forge (write) | Forge/Ward (task logs)
│   ├── epics/
│   │   ├── E001.md
│   │   └── E00N.md
│   ├── tasks/
│   │   ├── T001.md
│   │   ├── T00N.md
│   │   └── logs/            (OBRIGATÓRIO: logs de tasks completadas)
│   │       └── T001-log.md
│   └── logs/               (Alternativa: centralizar aqui)
│
├── 03-quality/            ← Ward (write) | All (read-only)
│   ├── review/
│   │   ├── REVIEW-v1.md    (Obrigatório para Gate 4→5)
│   │   └── SECURITY-AUDIT-*.md
│   ├── qa/
│   │   ├── QA-v1.md        (Status: Passed — obrigatório para Gate 4→5)
│   │   └── QA-Epic-*.md
│   └── learning/           (Diretório essencial)
│       └── L-*.md
│
└── 04-release/            ← Cast (write) | All (read-only)
    ├── CHANGELOG.md        (Obrigatório: changelog de versões)
    ├── RELEASE-vX.Y.Z.md   (Obrigatório para Gate 5→Release)
    └── RUNBOOK.md          (Obrigatório: procedimentos operacionais)
```

**Ponto crítico:** A presença de **diretórios vazios** (como `docs/00-discovery/patterns/`) é essencial. Eles indicam ao Helm onde os artefatos **devem ser** criados em execuções futuras.

---

## 3. Validação de Skills e Localização

### Mapeamento Skills → Orchestrators

**Lore (Fases 0–1):**
- ✅ `glossary-manager` — Criar/atualizar glossário
- ✅ `spec-manager` — Criar/versionar SPECs
- ✅ `adr-manager` — Documentar decisões arquiteturais

**Forge (Fases 2–3):**
- ✅ `architecture-manager` — Diagrama e design
- ✅ `epic-manager` — Organizar trabalho em épicos
- ✅ `task-manager` — Detalhar tasks + logs

**Ward (Fase 4):**
- ✅ `review-manager` — Code review estruturado
- ✅ `qa-manager` — Validação funcional
- ✅ `learning-manager` — Capturar aprendizados

**Cast (Fase 5 + Maintenance):**
- ✅ `changelog-manager` — Versioning + release notes
- ✅ `runbook-manager` — Procedimentos operacionais

**Trace (Fase -1 — apenas projetos existentes):**
- ✅ `codebase-mapper` — Mapear estrutura existente
- ✅ `reverse-spec` — Extrair specs implícitos

### Recomendação

Todos os skills **devem estar** em `~/.config/opencode/skills/` (ou `__OPENCODE_ROOT__/skills/` em instalação local). Helm lê referências diretas aos SKILL.md em tempo de execução.

---

## 4. Fencing e Isolamento de Contexto

### Implementação Validada

A verificação mostrou que **fencing é efetivo quando:**

1. **Cada orchestrator tem `permission.task: "*": deny` por padrão**
   - Helm: `permission.task` = lista explícita de 5 subagents (nem mais, nem menos)
   - Subagents: `permission.task: "*": allow` (podem chamar agência-agents livremente)

2. **Leitura é **sempre** read-only em fases anteriores**
   - Forge não consegue reescrever SPEC de Lore
   - Ward não consegue reescrever Tasks de Forge
   - Cast não consegue reescrever Reviews de Ward

3. **Artefatos críticos têm seção `## References`**
   - Cada artefato aponta para seus predecessores
   - Cria rastreabilidade automática da cadeia de dependências

### Validação de Fencing Antes de Executar

```markdown
## Verificação de Fencing — Checklist

- [ ] `docs/00-discovery/` — apenas Lore pode escrever
- [ ] `docs/01-design/` + `docs/02-planning/` — apenas Forge pode escrever
- [ ] `docs/03-quality/` — apenas Ward pode escrever
- [ ] `docs/04-release/` — apenas Cast pode escrever
- [ ] Todos exceto Lore podem ler `docs/00-discovery/` (read-only)
- [ ] Forge e posteriores podem ler `docs/01-design/` + `docs/02-planning/` (read-only)
- [ ] Ward e Cast podem ler `docs/03-quality/` (read-only)
```

---

## 5. Handoff Checklists — Padrão Crítico

### Estrutura Necessária

Todo artefato produzido por um orchestrator **deve ter**:

```markdown
## Handoff Checklist

Antes de avançar para a próxima fase, confirme:

- [ ] Este artefato tem versão e data
- [ ] Seção `## References` aponta para predecessores
- [ ] Status está marcado (Draft | Active | Accepted | Completed | Passed)
- [ ] Não há TODOs abertos ou itens pendentes críticos
- [ ] Documento foi revisado por [responsável]

**Responsável pela entrega:** [nome/role]  
**Data de aprovação:** YYYY-MM-DD  
**Próxima fase:** [Orchestrator] — [Fase N→N+1]
```

### Por Que É Crítico

A validação mostrou que **handoff checklists são o ponto de validação antes de cada gate**. Sem eles:
- Artefatos incompletos avançam para fases posteriores
- Cascata de erros aumenta exponencialmente
- Helm não consegue validar readiness

**Recomendação:** Incluir geração automática de handoff checklist nos templates de cada skill.

---

## 6. Validação de Traceability

### Cadeia de Dependências Esperada

```
GLOSSARY.md
    ↓ (Referenciado por)
SPEC-v1.md
    ↓
ADR-001 até ADR-NNN
    ↓
ARCHITECTURE-v1.md
    ↓
Epics (E001, E002, E003)
    ↓
Tasks (T001–T00N)
    ↓
REVIEW-v1.md
    ↓
QA-v1.md
    ↓
RELEASE-vX.Y.Z
    ↓
RUNBOOK.md
```

### Como Validar

Em cada artefato, adicionar:

```markdown
## References

**Predecessores:**
- SPEC-v1: Requisitos funcionais
- ADR-003: Decisão sobre padrão X

**Dependentes (conhecidos):**
- Epic E001: Utiliza requirement Y do SPEC
- Task T005: Implementa funcionalidade Z
```

**Ferramentas recomendadas:**
- Grep para verificar referências cruzadas
- Script que mapeia dependências entre arquivos
- Validação durante cada gate

---

## 7. Modelo de Custo — Atribuição por Orchestrator

### Validação de Modelos Observada

| Orchestrator | Modelo          | Custo | Justificativa |
|-------------|-----------------|-------|---------------|
| **Helm**    | `claude-opus-4-6` | Alto  | Erros em tier detection = cascata. Melhor modelo aqui economiza downstream |
| **Lore**    | `claude-sonnet-4-6` | Médio | Sub-skills críticas (spec-manager, adr-manager) usam opus internamente |
| **Forge**   | `claude-sonnet-4-6` | Médio | Tradução estruturada de SPEC em planos |
| **Ward**    | `claude-sonnet-4-6` | Médio | Validação contra critérios definidos |
| **Cast**    | `claude-haiku-4-5` | Baixo | Triagem estruturada; changelog/runbook são mecânicos |
| **Trace**   | `claude-sonnet-4-6` | Médio | Leitura + categorização estruturada |

### Estratégia Observada

**"Invista em pontos de decisão; economize em pontos de execução."**

- Helm = ponto de decisão crítico → investir em opus
- Lore = decisões arquiteturais → sonnet
- Cast = execução mecânica → haiku

**Economia esperada:** ~40-50% redução em custo total comparado a usar opus em todo lugar.

---

## 8. Verificação de Gates — Checklist por Fase

### Gate 0→1: Foundation (Tier 2 only)

```markdown
- [ ] docs/00-discovery/glossary/GLOSSARY.md existe
- [ ] GLOSSARY.md tem ≥5 termos definidos
- [ ] Lore confirmou leitura e consenso
```

### Gate 1→2: Discovery (Tier 2 only)

```markdown
- [ ] docs/00-discovery/spec/ tem ≥1 SPEC com status Active ou Draft
- [ ] docs/00-discovery/adr/ tem ≥1 ADR
- [ ] Ambos têm seção References validada
- [ ] Handoff Checklist de SPEC-v1 está 100% marcado
```

### Gate 2→3: Design (Tier 2 only)

```markdown
- [ ] docs/01-design/architecture/ARCHITECTURE-v1.md existe
- [ ] ARCHITECTURE-v1 contém diagrama Mermaid (não genérico)
- [ ] Diagrama é específico do projeto (não é template)
```

### Gate 3→4: Planning (Tier 1–2)

```markdown
- [ ] ≥1 Task com status Completed (docs/02-planning/tasks/)
- [ ] Task Completed tem seção Artifacts preenchida
- [ ] docs/02-planning/tasks/logs/ tem log correspondente (T00N-log.md)
```

### Gate 4→5: Quality (Tier 2 only)

```markdown
- [ ] docs/03-quality/review/REVIEW-v1.md existe
- [ ] REVIEW-v1 tem status Approved (não Ask ou Changes Requested)
- [ ] docs/03-quality/qa/QA-v1.md existe
- [ ] QA-v1 tem status Passed (não Failed)
- [ ] Nenhum finding Critical aberto
```

### Gate 5→Release (Tier 2 only)

```markdown
- [ ] docs/04-release/RELEASE-vX.Y.Z.md existe
- [ ] RELEASE-vX.Y.Z referencia QA Passed
- [ ] docs/04-release/RUNBOOK.md existe e está atualizado
- [ ] RUNBOOK contém procedures de deploy, rollback, health check
```

---

## 9. Recomendações para Novos Projetos

### Setup Inicial (Tier 2 Projects)

1. **Estrutura de diretórios:** Copiar template `docs/` com todos os subdirs vazios
2. **Validar fencing:** Confirmar permissões de filesystem antes de começar
3. **Preparar CLAUDE.md:** Adicionar contexto do projeto (tech stack, convenções, quick commands)
4. **Registrar modelos:** Confirmar atribuição de modelos LLM em `docs/MODELS.md`
5. **Executar Trace (se projeto existente):** Mapear codebase antes de começar fases 0–1

### Validações Críticas

1. **Antes de cada gate:**
   - Validar que Handoff Checklist de artefato anterior está 100%
   - Confirmar que References apontam corretamente
   - Validar status de artefatos (Draft → Active → Accepted, etc.)

2. **Antes de avançar orchestrator:**
   - Confirmar que Task tool permissions estão corretos
   - Verificar que fencing não foi violado
   - Confirmar acesso a skills necessários

3. **Antes de entregar (Phase 5 → Release):**
   - Executar verificação de traceability completa
   - Confirmar que todas as referências cruzadas existem
   - Validar que RUNBOOK cobre todos os cenários de operação

---

## 10. Conclusão

O framework Orquestrum, quando implementado corretamente:

✅ **Define responsabilidades claras** por phase  
✅ **Implementa fencing rigoroso** para evitar contaminação  
✅ **Fornece skills especializadas** para cada orchestrator  
✅ **Valida com gates** em pontos críticos  
✅ **Rastreia tudo** via References  
✅ **Otimiza custo** via modelo assignment inteligente  

**Padrão validado em projeto real:** Chat Connect Pro
- 5 subagents operacionais
- 13+ skills acessíveis
- 6 fases de pipeline cobrindo discovery até release
- Fencing implementado em 100% das fases

**Recomendação final:** Usar este documento como checklist para setup de novos projetos e referência durante execução do pipeline.

---

**Próximas iterações do framework devem:**
1. Automatizar validação de handoff checklists
2. Gerar relatórios de traceability automaticamente
3. Implementar warnings se fencing for violado
4. Integrar com git hooks para validar artefatos em commit
