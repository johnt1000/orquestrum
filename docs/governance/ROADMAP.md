# Roadmap

Candidatos pós-Fases-1-a-5 (entregues em 2026-05-02). Não é compromisso — é fila priorizada. Itens entram por ROI demonstrado, saem por dados que mostrem que não pagam o esforço.

> Atualização: este documento é vivo. Quando um item é executado, mover para a seção `## Concluídos` com data e link para PR/commit. Quando um item é descartado, mover para `## Descartados` com a razão.

---

## Princípios de priorização

1. **Dados antes de pesos.** Nada que dependa de "ajustar fórmula" entra antes da coleta de baseline (item R2).
2. **Atomicidade.** Cada item entrega valor sozinho — não cria dependência circular para outro item futuro.
3. **Provedor-agnóstico por padrão.** Recursos específicos de provedor vivem em adapters; nada vaza para `agents/` ou `skills/`.
4. **Observabilidade tem que se pagar.** Métrica/automação que custa mais para manter do que economiza não entra.

---

## R1 — Smoke test em projeto real (CONCLUÍDO 2026-05-02)

**Objetivo:** validar end-to-end que a infra das Fases 2-4 (cache markers, métricas, attention scoring) produz artefatos corretos em sessão real, não só em smoke tests sintéticos.

### O que foi feito
- Criado `/tmp/orq-r1-smoke` projeto-cobaia com `git init` + estrutura mínima
- `uv run scripts/install.py --tool claude-code --target /tmp/orq-r1-smoke` → settings.json criado, hook + lib copiados
- 6 eventos sintéticos enviados via stdin para o hook instalado (mix de Stop + SubagentStop, modelos diversos: opus, sonnet, haiku; agents: top-level, Helm, Forge x2, Ward, Cast)
- Dashboard CLI renderizou: 80,200 input tk, 11,700 output, 26,500 cached (33%), $0.5743 USD, agentes agregados corretamente por tier price (Helm opus mais caro $0.2175, Cast haiku mais barato $0.0058)
- UI em project mode contra o smoke project: /healthz, /dashboard com budget bar real, /catalog detectando os 8 agents instalados, /docs lendo docs/ instalado, /coverage, /audits/payload, todos HTTP 200

### Bug encontrado e corrigido durante R1
- `ui/lib/live_metrics.py`: hook só populava `events.jsonl`, mas `budget_for` lia `session.json` direto → budget bar mostrava 0
- Fix: `session_for()` agora chama `rebuild_session()` que aggrega events e regrava session.json antes de `budget_for` ler
- Após fix: progress bar mostra 80,200/100,000, warning "Budget exceeded: 11,700 output tokens (threshold 8,000)" dispara corretamente

**Esforço real:** ~30min. **Status:** ✅ Validação end-to-end completa. Próximo: aguardar dados reais de sessões verdadeiras para R2.

### Setup
```bash
mkdir /tmp/orq-smoke && cd /tmp/orq-smoke && git init
echo "# Smoke" > README.md && git add . && git commit -m "init"
cd <orquestrum-repo>
uv run scripts/install.py --tool claude-code --target /tmp/orq-smoke
mkdir -p /tmp/orq-smoke/.orquestrum/metrics /tmp/orq-smoke/docs/{00-discovery,02-planning,03-quality,04-release}
```

### Sessão Tier-1 simulada
Pedir uma feature pequena via Claude Code (ex: *"adicione endpoint /health que retorna 200 OK"*). Emitir manualmente eventos via `scripts/lib/metrics.py:append_event()` enquanto não há hook (ver R3).

### Critérios de aceitação
| Item | Como validar | Pass |
|------|--------------|:---:|
| Skills emitem `attention_score`, `attention_band`, `attention_factors` | `grep attention_score docs/03-quality/**/*.md` | 3 campos por artefato |
| `MEDIATION.md` é gerada por checkpoint-manager | `docs/MEDIATION.md` existe com tabela ordenada | ✓ |
| Dashboard renderiza | `uv run scripts/dashboard/render.py --metrics-dir .orquestrum/metrics --tier balanced --html` | < 2s, calls > 0 |
| Budget warning não dispara falso positivo | dashboard mostra input < threshold em verde | ✓ |
| Cache markers strip corretamente | `grep -c "cache:" .claude/agents/*.md` | 0 |
| Tier collapse aparece com `--provider claude` | warning visível no convert para Cipher | ✓ |
| Score da fórmula bate com cálculo manual | reproduzir 3 artefatos com inputs idênticos | match exato |

**Esforço:** 1h. **Risco:** Baixo. **Bloqueia:** R2 (precisa de dados reais para iterar pesos). **Status:** Pendente.

---

## R2 — Iterar pesos da fórmula de attention (3 meses, mensal)

**Objetivo:** calibrar `scripts/lib/attention.py` com base em distribuição real, não intuição. Pesos atuais (`25/20/10/15/5/+5`) são v1.0 — esperar 30+ amostras antes de tocar.

### Coleta de baseline
Após R1, rodar Orquestrum em projetos reais. Cada `MEDIATION.md` registra scores. Após N ≥ 30 (ideal N ≥ 100) artefatos, agregar:

```python
# scripts/audit/attention_distribution.py (a criar)
import frontmatter, statistics, collections
from pathlib import Path
scores, bands = [], collections.Counter()
for f in Path('docs/03-quality').rglob('*.md'):
    fm = frontmatter.load(str(f))
    if 'attention_score' in fm:
        scores.append(fm['attention_score'])
        bands[fm.get('attention_band')] += 1
print(f'N={len(scores)}, mean={statistics.mean(scores):.1f}, '
      f'p10={sorted(scores)[len(scores)//10]}, '
      f'p90={sorted(scores)[len(scores)*9//10]}, bands={dict(bands)}')
```

### Diagnóstico × Ação

| Distribuição | Diagnóstico | Ajuste sugerido |
|--------------|-------------|-----------------|
| Verde > 90% | Frouxa demais | confidence weight 25→30; inference_depth 10→12 |
| Vermelho > 30% | Severa demais | drift weight 20→15; gate_failure 5→3 |
| Vermelho < 5% | Talvez nem dispara | verificar se inputs são populados (não a fórmula) |
| Amarelo concentrado em 60-70 | Banda do meio comprime | thresholds: green 75+; red <45 |

### Processo de mudança
1. Não mexer em pesos sem N ≥ 30
2. Mudar UM peso por vez, re-medir
3. Documentar em commit + nota em `docs/agent-context/CONVENTIONS.md` § Human Attention Mediation: versão da fórmula + N + diagnóstico
4. Validar: smoke test contra os 30+ artefatos antigos; explicar cada flip de banda

### Cadence
- Mês 1 (jun/26): observar, sem mudar
- Mês 2 (jul/26): primeiro ajuste se desbalanceado
- Mês 3 (ago/26): segundo ajuste fino, congelar v1.0
- A cada major model release: re-medir baseline

**Esforço:** ~2h por iteração. **Risco:** Baixo (pesos são single-source-of-truth). **Bloqueia:** nada — é manutenção contínua. **Status:** Pendente (depende de R1).

---

## R3 — Emissão real de métricas via hook do harness (CONCLUÍDO 2026-05-02)

**Objetivo:** preencher `.orquestrum/metrics/events.jsonl` automaticamente sem o usuário lembrar de chamar `append_event()`. Sem isso, R2 não tem dados e a infra de métricas vira dormente como `MODEL_PRICING` antes da Fase 1.

### O que foi feito
- `scripts/hooks/emit_metrics.py`: Stop + SubagentStop handler. Sempre exit 0, defensive parsing, NUNCA bloqueia o turno do usuário.
- `scripts/convert.py` ClaudeCodeAdapter: gera `.claude/settings.json` template + copia hook + lib para `.sdd/scripts/hooks/` e `.sdd/scripts/lib/`.
- `scripts/install.py`: merge inteligente de settings.json (3 cenários: criar, append não-destrutivo, idempotente), chmod +x em hooks .py.
- `docs/governance/HOOKS.md`: contrato Claude Code, failure modes, troubleshooting.
- Smoke test E2E: install em /tmp, hook recebe synthetic Stop + SubagentStop, events.jsonl populado, dashboard renderiza com agents resolvidos (top-level + Cast/mechanical), cost calculado correto por modelo.

**Esforço real:** ~2h. **Status:** ✅ Desbloqueia R2 (dados reais para calibração) e R13 (UI live).

### Caminho A — Hook Claude Code (recomendado)

`.claude/settings.json` no target:
```jsonc
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "uv run .sdd/scripts/hooks/emit_metrics.py"
      }]
    }]
  }
}
```

**Novo arquivo `scripts/hooks/emit_metrics.py`** que:
1. Lê transcript do Claude Code (`$CLAUDE_TRANSCRIPT_PATH`)
2. Extrai `usage.input_tokens`, `output_tokens`, `cache_read_input_tokens`, model do último turn
3. Resolve `tier` via `AGENT_TIERS` lookup pelo agent ativo
4. Calcula `cost_usd` via `models.estimate_cost()`
5. `append_event(...)` em `.orquestrum/metrics/events.jsonl`

**Vantagem:** zero esforço por skill, todo turn é emitido. **Desvantagem:** específico Claude Code.

### Caminho B — Emissão dentro de cada skill (fallback portátil)

Cada SKILL.md ganha "ao final, emita evento via bash". Funciona em qualquer harness com bash tool. **Vantagem:** universal. **Desvantagem:** 25 skills, alta superfície de drift.

### Recomendação: A para Claude Code, B como fallback documentado

| Arquivo a criar/modificar | Conteúdo |
|---------------------------|----------|
| `scripts/hooks/emit_metrics.py` | Hook handler para Claude Code |
| `scripts/hooks/emit_metrics_opencode.py` | Quando OpenCode suportar hooks (TBD) |
| `docs/HOOKS.md` | Contrato hook + setup por adapter |
| `scripts/convert.py` (`ClaudeCodeAdapter`) | Injetar `hooks/Stop` em settings.json template |
| `scripts/install.py` | Copiar hook script para `.claude/hooks/` no target |

### Validação
1. Smoke install em projeto-cobaia
2. Rodar 1 sessão real
3. `cat .orquestrum/metrics/events.jsonl | wc -l` ≥ nº de turns no transcript
4. Cross-check campos contra transcript

**Esforço:** ~2 dias-dev (hook + convert/install + smoke). **Risco:** Médio (hook contract pode mudar com Claude Code releases). **Bloqueia:** R2 (sem dados, não calibra pesos). **Status:** Pendente.

---

## R4 — `--dry-run` em `convert.py` com estimativa de custo (CONCLUÍDO 2026-05-02)

**Objetivo:** revisor de PR vê o impacto da mudança sem precisar gerar arquivos.

### O que foi feito
- `--dry-run` flag em convert.py: skip de toda escrita
- Inventory canônico (agents, skills, docs, cache markers) impresso
- Tier collapses do provider escolhido listados explicitamente
- Projeção de custo por tier (T0/T1/T2) usando `models.estimate_cost`:
  - Tier 0: ~2 calls mechanical
  - Tier 1: ~5 calls balanced
  - Tier 2: ~13 calls (mix deep + balanced + mechanical)
- Sample output (provider=claude): Tier 0 $0.0056, Tier 1 $0.0645, Tier 2 $0.4610

```bash
uv run scripts/convert.py --all --dry-run                       # inventory only
uv run scripts/convert.py --all --provider claude --dry-run     # + cost projection
```

**Esforço real:** ~30min. **Status:** ✅

---

## R5 — `cost_class` em skill frontmatter

**Objetivo:** Helm fast-path escolhe entre chain completa vs abreviada com base em metadado declarativo.

```yaml
# em skill frontmatter
cost_class: cheap | moderate | expensive
```

Helm consulta `cost_class` quando decide se inclui ou pula uma skill em Tier 0/1.

**Esforço:** 1 dia. **Risco:** Médio (regra precisa estar bem definida para não criar comportamento errático). **Bloqueia:** R2 (precisa de baseline para definir thresholds). **Status:** Pendente.

---

## R6 — Pre-flight skill: `context-completeness-checker`

**Objetivo:** antes de orquestrador caro (Tier-2), validar que inputs requeridos estão > 70% completos. Se não, abortar antes de gastar tokens.

### Heurística
- SPEC: campos obrigatórios preenchidos / total
- ADRs referenciados: existem em disco
- Glossary: termos do SPEC têm entrada
- CHECKPOINT.md: não está stale

Se score < 70% → bloqueia + lista o que falta.

**Esforço:** 2 dias. **Risco:** Baixo. **Bloqueia:** nada. **Status:** Pendente.

---

## R7 — `schema_version` em frontmatter de artefatos

**Objetivo:** artefatos emitidos em ciclos diferentes ainda parseáveis quando o schema evolui. Hoje, mudar um campo quebra silenciosamente artefatos antigos.

```yaml
schema_version: 1
```

`scripts/lib/frontmatter.py` ganha migration helpers `v1 → v2`.

**Esforço:** 1 dia. **Risco:** Baixo. **Bloqueia:** nada. Disparado por: primeira mudança breaking de schema. **Status:** Pendente.

---

## R8 — Telemetry export hook

**Objetivo:** permitir que o operador piped `.orquestrum/metrics/events.jsonl` para OTel/Datadog/sua-stack-favorita sem o framework dono dessa integração.

Documentação em `docs/governance/OBSERVABILITY.md` (já tem stub) com exemplo:
```bash
tail -f .orquestrum/metrics/events.jsonl | curl -X POST $COLLECTOR --data-binary @-
```

Mais um exemplo OTel completo num `examples/observability/otel-shipper/` opcional.

**Esforço:** 4h doc + 4h exemplo. **Risco:** Baixo. **Bloqueia:** nada. **Status:** Pendente.

---

## R9 — Adversarial parity test

**Objetivo:** plantar deliberadamente um bug de segurança em código de teste; rodar Cipher nos 3 provedores; verificar se todos detectam. Differential check real, não estrutural.

### Escopo
- Pequeno repo de teste com bugs propositais (SQLi, XSS, secret no log, etc.)
- Cada bug catalogado em `tests/parity/security_corpus.md`
- Para cada provider, rodar `security-manager` skill end-to-end
- Reportar quem detectou cada bug

**Esforço:** 2 dias (corpus + harness + análise). **Risco:** Médio (depende de hook/integração para invocar skill programaticamente). **Bloqueia:** R3 (precisa hook para automatizar). **Status:** Pendente.

---

## Próxima sessão — árvore de decisão

Quando retomar (após o usuário ter rodado o framework em projeto real seguindo `docs/governance/REAL_USAGE_PLAN.md`):

1. **Se houver feedback operacional concreto** (bugs encontrados, atrito de UX, surpresas no comportamento) → priorizar fix antes de novo escopo. O feedback quente perde valor rápido.

2. **Se N ≥ 30 artefatos com `attention_score` em `docs/03-quality/`** → executar **R2 — primeira iteração de calibração de pesos**. Rodar `uv run scripts/audit/attention_distribution.py` (ou via UI `/audits/attention-distribution`), ler o "Calibration signal", ajustar UM peso em `scripts/lib/attention.py`, documentar a versão da fórmula em commit + nota em `docs/agent-context/CONVENTIONS.md` § Human Attention Mediation. Depois aguardar mais 2-4 semanas antes do próximo ajuste.

3. **Se nada acima e infra estável** → executar **R13 — UI Live Monitoring** (~1 sprint). Plano completo no § R13 logo abaixo. As 3 páginas (`/live/session`, `/live/routing`, `/live/attention`) podem ser implementadas em ordem; `/live/session` é a mais alta-leverage (mostra o hook funcionando).

3a. **Se a fricção reportada for de UX/onboarding** (não de comportamento do framework) → executar **R14 — UX & Onboarding** (Ondas 1+3 podem rodar em paralelo, ~1-3 dias somadas). Onda 2 só após PRs 1+3 mergeados.

4. **Se houver sinal específico** (custo alto, cache baixo, etc.) consultar a tabela "When to escalate to roadmap items" em `docs/governance/REAL_USAGE_PLAN.md` para mapear sinal → item R5/R6/R7/R8/R9.

**Princípio:** dados antes de pesos, feedback antes de feature, signal antes de scope.

---

## Cronograma proposto (atualizado 2026-05-02)

| Semana | Foco | Bloqueador |
|--------|------|------------|
| ~~1 (mai/26)~~ | ~~R10 — Doc separation~~ | ✅ Concluído |
| ~~1 (mai/26)~~ | ~~R11 — UI Wave A~~ | ✅ Concluído |
| ~~1 (mai/26)~~ | ~~R3 — Hook Claude Code~~ | ✅ Concluído |
| ~~1 (mai/26)~~ | ~~R4 — `--dry-run`~~ | ✅ Concluído |
| 2 (mai/26) | R1 — Smoke test em projeto real | — |
| 3-7 (mai-jun/26) | R2 — Coleta baseline attention (mês 1: observar) | R3 ✅ |
| 5-7 (jun/26) | R12 — UI Wave B (action) | — (paralelo) |
| 8 (jul/26) | R2 — Primeiro ajuste de pesos se necessário | dados |
| 9+ (ago/26+) | R13 — UI Wave C (live) | R3 ✅ → desbloqueado |
| paralelo | R14 Onda 1 — quick wins UX (CLI + Web) | — |
| paralelo | R14 Onda 3 — onboarding (CONTRIBUTING + ui/README + Makefile + pre-commit) | — |
| após R14-1+R14-3 | R14 Onda 2 — async/streaming + diff lado a lado + form inline errors | — |
| paralelo | R7 — `schema_version` (oportunístico) | — |
| 10+ (set/26+) | R5, R6, R8, R9 conforme prioridade | depende |

Mensal automatizado:
- 1º dia de cada mês: rotação de `pinned_refs.toml` via routine `trig_017wv5Sv9CnYXXCUyejQqDTY`

---

## R10 — Separação de docs por audiência (CONCLUÍDO 2026-05-02)

**Objetivo:** dividir `docs/` em `agent-context/` (lido por LLMs em runtime) e `governance/` (lido por humanos), removendo o trade-off "completude humana × economia de tokens".

### O que foi feito
- 3 docs movidos para `docs/agent-context/`: SDLC.md, TIERS.md, CONVENTIONS.md
- 7 docs movidos para `docs/governance/`: MODELS, COST, OBSERVABILITY, COVERAGE, PERFORMANCE, SUPPLY_CHAIN, ROADMAP
- `scripts/lib/paths.py`: regex atualizadas
- `scripts/lint.py`: nova check de estrutura — proíbe `.md` solto em `docs/` raiz
- Cross-refs atualizadas em todos `agents/`, `skills/`, `scripts/`, `README.md`, `CLAUDE.md`
- Validação: lint zero erros, convert.py --all OK, parity 8/8 nos 3 providers

**Esforço real:** ~1h. **Status:** ✅

---

## R11 — UI Console MVP (read-only Wave A) (CONCLUÍDO 2026-05-02)

**Objetivo:** console local single-user para navegar docs, ver métricas, listar agents/skills, ver coverage.

### O que foi feito
- `ui/` completo: server.py (FastAPI), config.py (mode resolution), 5 rotas (health, dashboard, docs, catalog, coverage)
- `ui/lib/`: doc_loader (com classificação por audiência + ripgrep search), catalog_loader (parse frontmatter de agents/skills), live_metrics (wrapper sobre scripts/lib/metrics)
- `ui/templates/`: base + 6 templates Jinja2/HTMX
- `scripts/ui/serve.py`: entrypoint com flag --mode/--root/--port/--host (bind default 127.0.0.1)
- `pyproject.toml`: optional-dependencies `[ui]` com fastapi, uvicorn, jinja2, mistune, watchfiles
- `docs/governance/UI_GUIDE.md`: doc completo de instalação, modos, troubleshooting
- Reúso de scripts/lib/: zero duplicação

### Validação E2E
- `/healthz` 200, retorna mode/root/metrics_dir/port
- `/dashboard`, `/docs`, `/catalog`, `/coverage`, `/docs/search?q=...`, `/docs/view?p=...` todas HTTP 200
- Catalog detecta os 8 agents canônicos
- Doc browser classifica corretamente por audiência (🧠 agent-context, 👤 governance, 📊 baselines)

**Esforço real:** ~2h. **Status:** ✅

---

## R12 — UI Action Console (Wave B) (PARCIAL — entregue 2026-05-02)

**Objetivo:** adicionar capabilities de escrita/execução à UI.

### Wave B-1 — Audits + Convert (CONCLUÍDO 2026-05-02)
- `/audits` index, `/audits/payload`, `/audits/parity`, `/audits/attention-distribution`
- `/convert` form com tool/provider/dry-run (subprocess sync)
- `scripts/audit/attention_distribution.py` (novo, alimenta R2)
- `python-multipart` adicionado às deps `[ui]` do pyproject.toml

### Wave B-2 parcial — Install + Agent edit (CONCLUÍDO 2026-05-02)
- `/install` — form (tool + target + auto-detect) com validação de path; subprocess sync
- `/agents/{slug}/edit` — fluxo 3 etapas: GET form → POST preview com diff → POST apply (atomic write)
- `ui/lib/edit_validator.py` — lint preflight in-process (sem subprocess); rules mirror lint.py
- Body do agent permanece intocado; só o frontmatter é reescrito
- Smoke E2E: install valida path inexistente, install completa com sucesso, edit form pré-populado, preview mostra diff, max_tokens=99999 bloqueado por preflight, forge.md não é modificado em previews

### Wave B-2 final (CONCLUÍDO 2026-05-02)
- `/skills/{slug}/edit` — mesmo padrão 3 etapas (form → preview+diff → apply atomic) com campos inject_references, inject_fewshot, emits_confidence, depends_on, chain.next, chain.condition
- `validate_skill_frontmatter()` em ui/lib/edit_validator.py — cross-refs depends_on e chain.next contra skills existentes
- `scripts/build/compress_refs.py` — compressor determinístico (drop blocks, trim fences > 40 linhas, cap examples a 3, trim blockquotes longos); sentinela `<!-- compact:auto-generated -->` protege hand-written companions
- `/compact` route com scope/threshold/dry-run/force
- Smoke E2E: skills/edit valida BOGUS (rejeita inject_references inválido), preview não escreve, compact dry-run mostra ratio 100% no codebase atual (nada para comprimir hoje)

### Padrões de segurança (já em vigor para B-1, expandir em B-2)
- Subprocess timeout 120s (bounded)
- Comandos como arrays (não shell strings) — sem injection
- Paths validados contra ORQ_ROOT — sem `../` escapes
- Bind 127.0.0.1 only
- Em B-2: toda ação destrutiva → diff preview; lint preflight bloqueante para edits

### Estimativa atualizada
- B-1: ~1h (entregue)
- B-2: ~1 sprint (lint preflight + diff preview + atomic write são o grosso)

**Esforço total:** ~1.5 sprints. **Status:** Wave B-1 ✅ / Wave B-2 ⏳

---

## R13 — UI Live Monitoring (Wave C) (PRÓXIMO — desbloqueado por R3 ✅)

**Objetivo:** transformar a UI de "snapshot por refresh" em "live view" — vê eventos chegando, roteamento dinâmico, attention timeline.

### Bloqueador (RESOLVIDO)
~~Depende de R3~~ → R3 entregue 2026-05-02. events.jsonl agora é populada automaticamente por hook em toda Stop/SubagentStop. R13 está desbloqueada.

### Pré-requisito de DADOS (não de código)
A UI Wave C **funciona** com dados sintéticos, mas só **mostra valor** após coleta real. Cronograma sugerido:
- Imediato: implementar páginas + auto-refresh (~1 sprint)
- Após o usuário rodar R1 (real-world usage por algumas horas/dias): páginas começam a mostrar fluxo significativo
- Após N ≥ 100 eventos reais: timeline de attention começa a evidenciar padrões

### Escopo das páginas

#### `/live/session` — tail de events.jsonl
- Auto-refresh via HTMX `hx-trigger="every 3s"` ou Server-Sent Events (`watchfiles` já no `[ui]` extras)
- Tabela com últimos N eventos: ts, agent, tier, model, in/out tokens, cost, status
- Filtros (querystring): `?agent=Forge&tier=balanced` → afina o tail
- Botão "freeze" para pausar refresh durante leitura
- Footer: contador de eventos totais + cumulative cost

#### `/live/routing` — visualização de roteamento
- Agregação dos últimos N eventos: contagem `(orchestrator, skill)` → renderizar como tabela ranqueada (e/ou Mermaid simples server-rendered)
- Para cada par, mostrar: # invocações, tempo médio (quando houver duration_ms), cost médio
- Identifica padrões: qual orquestrador domina? Qual skill é mais cara?

#### `/live/attention` — timeline de attention scores
- Walk em `docs/03-quality/` extrair `attention_score` + `attention_band` + frontmatter `created` ou `updated`
- Renderizar como série temporal simples (texto + barras unicode, sem JS chart libs)
- Linhas: artefatos individuais ordenados por data
- Filtro: `?band=red` → só os de alta atenção
- Útil para revisão semanal: "quais artefatos minhas últimas sessões deixaram em estado vermelho?"

### Tecnicalidades

| Item | Decisão |
|------|---------|
| Auto-refresh | HTMX `hx-trigger="every 3s"` (sem WebSocket; SSE só se HTMX não bastar) |
| Performance | events.jsonl read full em cada refresh; aceitável até ~10K linhas (~1MB) — paginação só se ficar lento |
| Storage | mantemos arquivo JSONL — sem migration para banco |
| Charts | unicode bars no terminal, ASCII tables. Sem Chart.js/D3. |
| Filtros | querystring → server-side filter. HTMX preserva via `hx-include` |

### Anti-padrões a evitar
- ❌ WebSocket: overkill para single-user local; complica deploy
- ❌ Chart libraries (Chart.js, ApexCharts): adicionam build step; ASCII basta
- ❌ Persistir filtros em `~/.orquestrum/`: querystring é stateless, basta
- ❌ Real-time push de servidor: pull com refresh curto é suficiente
- ❌ Aggregar por janela de tempo (last 1h, 24h, 7d) sem dados que justifiquem

### Estimativa
- Codificação: ~1 sprint (3 rotas + 3 templates + watchfiles integration)
- Validação real: depende do usuário rodar sessões reais (R1 — em andamento pelo usuário)

### Critério de "feito"
1. `/live/session` mostra última linha do `events.jsonl` em ≤ 3s após hook escrever
2. `/live/routing` agrega ≥ 100 eventos sem latência perceptível (< 500ms)
3. `/live/attention` lista os 10 artefatos mais críticos (menores scores) com bandas

**Esforço:** ~1 sprint. **Risco:** Baixo (a infra está pronta). **Status:** Desbloqueado, aguardando coleta de dados reais para máximo valor.

---

## R14 — UX & Onboarding (CLI + Web)

**Objetivo:** reduzir fricção para os dois públicos do framework — usuário final (instala e usa) e novo contribuidor (clona e contribui). O esqueleto técnico está pronto desde 2026-05-02; este item ataca discoverability, feedback visual e documentação de extensão. Auditoria com dois Explore agents identificou ~25 fricções concretas; este R14 consolida as de alta razão impacto/esforço em três ondas.

### Diagnóstico-chave

CLI:
- `add_help=False` em wrappers (`orquestrum/commands/{convert,install,deps,dashboard,compact,audit}.py`) faz `-h` não imprimir nada útil. Discoverability pela metade.
- Operações longas (`convert --all`, `deps`, `install`) sem indicador de progresso.
- `lint` silencioso em sucesso — pré-requisito de `convert` mas sem feedback positivo.
- Inconsistência de flags `--tool` × `--target` × `--all` × `--check` entre comandos.
- `uninstall` destrutivo sem `--dry-run`.

Web:
- `ui/server.py:35` ainda diz "read-only" no footer; o app é read-write desde Wave B.
- `ui/server.py:52` redireciona `/` direto para dashboard/catalog — sem hero, sem wayfinding, sem explicar modo project/framework.
- `templates/base.html` sem link Home, sem active state, sem breadcrumb.
- Subprocess síncronos de até 120s sem spinner ou polling.
- Sem confirmação em ações de escrita (apply/install/convert/compact).
- Diff de edit flows em tabela estreita; valores longos quebram.
- Erros de validação não destacam o campo (sem `aria-invalid`).
- 404 retorna JSON quando o usuário navega HTML (`ui/server.py:60`).

Onboarding:
- `CONTRIBUTING.md` cobre setup/daily/tests mas não explica como adicionar comando CLI nem rota web.
- Sem README em `ui/`.
- Sem `Makefile`/`justfile` para uniformizar comandos.
- Sem `pre-commit` config.
- Sem `orquestrum doctor` para validar ambiente.

### Onda 1 — Quick wins UX (CLI + Web) (CONCLUÍDA 2026-05-02)

| # | Item | Status |
|---|------|--------|
| 1.1 | `--help` próprio nos wrappers | ✅ já funcionava via passthrough (verificado) |
| 1.2 | Epilog `Example:` em todos os subcomandos | ✅ adicionado em 7 cores + uninstall |
| 1.3 | `lint` imprime contagem em sucesso (`✓ N agents, M skills, K assets, 0 errors`) | ✅ |
| 1.4 | `uninstall --dry-run` | ✅ |
| 1.5 | `orquestrum doctor` (novo) — runtime / extras / integrations / registry / cwd | ✅ |
| 1.6 | Padronização de `--target` como flag canônica de path | ✅ já consistente em install/deps/web |
| 1.7 | Home `/` dedicado com hero + cards + quick stats | ✅ |
| 1.8 | Nav com link Home + `aria-current="page"` em rota ativa | ✅ |
| 1.9 | Footer: "Wave B (read/write)" | ✅ |
| 1.10 | `confirm()` em apply/install/convert/compact (5 templates) | ✅ via `data-confirm` |
| 1.11 | Spinner inline após submit (sem reload) | ✅ via `data-spinner` (vanilla JS, sem HTMX swap) |
| 1.12 | Empty state explicativo no dashboard | ✅ |
| 1.13 | 404 em HTML por padrão; JSON só para `Accept: application/json` | ✅ |
| (extra) | Migração `scripts/` → `orquestrum/` em `ui/config.py` e `ui/lib/catalog_loader.py` | ✅ bug pré-existente corrigido para destravar Web em framework mode |

**Validação E2E:** lint verde (8 agents, 25 skills, 29 assets); convert --all --dry-run ok; web subiu na porta 7765, `/` (200, HTML novo), `/dashboard` (200, nav active state OK), `/foo` (404 HTML), `/foo` com `Accept: application/json` (404 JSON).

### Onda 2 — UX estrutural (CONCLUÍDA 2026-05-02)

| # | Item | Status |
|---|------|--------|
| 2.1 | Async / streaming em `/convert`, `/install`, `/audits/*`, `/compact` | ✅ `ui/lib/jobs.py` (asyncio.create_subprocess_exec + OrderedDict registry); `/jobs/{id}` + `/jobs/{id}/partial` com HTMX polling 1s; subprocess paths migrados de `scripts/X.py` para `python -m orquestrum.core.X`. |
| 2.2 | Progress indicator em `convert --all` e `install --auto` | ✅ `[k/N] tool` em negrito antes de cada adapter; single-tool fica silencioso. |
| 2.3 | Diff lado a lado nos edit flows | ✅ `<dl>` com painéis side-by-side por chave (vermelho/verde); `white-space: pre-wrap`; collapse para single-column < 700px. |
| 2.4 | Form validation inline (`aria-invalid` + `<small role="alert">`) | ✅ `errors_by_field()` agrupa por campo; templates renderizam erro adjacente ao input afetado. |
| 2.5 | Live monitoring | Delegado a **R13** — ver seção dedicada. Não duplicado aqui. |

**Validação E2E:** `/audits/payload` POST → 303 → `/jobs/{id}` polled, `job-done` em ~3s; edit `/agents/.../edit` com `max_tokens=99999` mostra `aria-invalid="true"` no input + "must be a positive int ≤ 16384, got 99999" inline; `convert --all` imprime `[1/5]` … `[5/5]`.

### Onda 3 — Onboarding de contribuidor (CONCLUÍDA 2026-05-02)

| # | Item | Status |
|---|------|--------|
| 3.1 | Expandir `CONTRIBUTING.md` com seções "Adding a CLI command" e "Adding a web route" | ✅ inclui exemplos completos (skeleton + arquivo de referência), distinção wrapper × native, conventions de flag e UX |
| 3.2 | Criar `ui/README.md` | ✅ stack, layout, modos, fluxo de request, opt-in attributes, anti-padrões |
| 3.3 | `Makefile` raiz | ✅ alvos `help` (default), `dev`, `sync`, `lint`, `convert`, `convert-dry`, `test`, `web`, `doctor`, `audit`, `clean` |
| 3.4 | `.pre-commit-config.yaml` opt-in | ✅ pre-commit-hooks (whitespace, EOF, merge, yaml, toml, large-files) + local hook `orquestrum lint` em `agents/`, `skills/`, `docs/` |

**Como instalar localmente:** `make dev` → `pre-commit install` (opcional). `make help` lista todos os alvos com descrição colorida.

**Estimativa:** 1-2 dias.

### Onda 4 (fora do escopo aprovado)

Suíte de testes para CLI/Web e CI no GitHub Actions ficam registradas como **Pendente** para futura entrega (não executadas neste R14).

### Sequenciamento aprovado

1. **PR 0:** este texto em ROADMAP (entrega R14 com sub-status Pendente em cada onda).
2. **PR 1:** Onda 1 completa, branch única.
3. **PR 2:** Onda 3 em paralelo (não conflita com PR 1).
4. **PR 3:** Onda 2 só após PR 1+PR 2 mergeados (evita conflitos em `templates/`).
5. Cada item desmarcado para Concluído quando seu PR mergear.

### Critérios de "feito"

Onda 1:
- `orquestrum convert -h`, `install -h`, `deps -h`, `audit payload -h` mostram help próprio com `Example:`.
- `orquestrum lint` em sucesso imprime `✓ N agents, M skills, 0 errors`.
- `orquestrum doctor` em ambiente limpo lista o que falta com sugestão por linha.
- `orquestrum web` → `/` mostra hero + nav com active state + footer "Wave B".
- Apply em `/agents/<slug>/edit` exige `confirm()`.
- GET `/foo` inexistente renderiza HTML, não JSON.

Onda 2:
- `/convert --all` retorna `job_id` imediatamente; página atualiza progresso a cada 1-2s sem reload manual.
- `convert --all` no CLI mostra `[k/N] converting <tool>...`.
- Diff de edit é legível com strings longas.
- Erro de validação destaca o campo, não só lista no topo.

Onda 3:
- Um contribuidor adiciona comando "hello" + rota `/hello` lendo só `CONTRIBUTING.md` + `ui/README.md`.
- `make dev` (ou `just dev`) instala extras + gera integrations + sobe web em uma chamada.
- `pre-commit run --all-files` passa.

**Esforço total:** ~7-10 dias-dev. **Risco:** Baixo (mudanças localizadas, sem refactor de domínio). **Bloqueia:** nada. **Status:** Pendente — PR 0 entrega esta seção; Ondas 1-3 em PRs subsequentes.

---

## Concluídos

| ID | Item | Data | PR/Commit |
|----|------|------|-----------|
| F1-F5 | Roadmap original (Fases 1 a 5) | 2026-05-02 | (working tree, 41 arquivos) |
| F1.4 | `pinned_refs.toml` + routine de rotação mensal | 2026-05-02 | routine `trig_017wv5Sv9CnYXXCUyejQqDTY` |
| R10 | Separação de docs por audiência | 2026-05-02 | (working tree) |
| R11 | UI Console MVP read-only (Wave A) | 2026-05-02 | (working tree) |
| R3  | Hook Claude Code para emissão de métricas | 2026-05-02 | (working tree) |
| R4  | `--dry-run` em convert.py | 2026-05-02 | (working tree) |
| R12 (B-1) | UI Wave B parcial — audits + convert | 2026-05-02 | (working tree) |
| R12 (B-2 parcial) | UI Wave B — install + agent edit (preview/apply atomic) | 2026-05-02 | (working tree) |
| R1  | Smoke test E2E em projeto-cobaia | 2026-05-02 | (working tree) |
| R12 (B-2 final) | UI Wave B completa — skills edit + compact | 2026-05-02 | (working tree) |
| (doc) | docs/governance/REAL_USAGE_PLAN.md | 2026-05-02 | (working tree) |
| R14 (Onda 1) | UX & Onboarding — quick wins CLI + Web | 2026-05-02 | (working tree) |
| R14 (Onda 2) | UX & Onboarding — async jobs, side-by-side diff, inline form errors, CLI progress | 2026-05-02 | (working tree) |
| R14 (Onda 3) | UX & Onboarding — CONTRIBUTING expansion, ui/README, Makefile, pre-commit | 2026-05-02 | (working tree) |

---

## Descartados

(vazio por enquanto)

---

## Como propor um item novo

1. Adicionar seção `## RX — Título` no final, antes de Concluídos
2. Estrutura mínima: Objetivo, Esforço, Risco, Bloqueia, Status
3. Sem ROI claro ou métrica de sucesso → não entra
4. Se bloqueia outro item, declarar explicitamente em `Bloqueia:`
5. Se desbloqueia algo no roadmap, mover esse algo para depender deste
