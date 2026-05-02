# Real-World Usage Plan

> Operational guide for running Orquestrum on a real project to validate the end-to-end pipeline and collect baseline data for ROADMAP R2 (attention-weight calibration).

**Why this exists.** Until the framework is exercised on real work, all the metrics, attention scoring, and budget machinery is plumbing that has only been smoke-tested with synthetic inputs. The real signal — whether the formulas are tuned right, whether the hook captures meaningful events, whether the dashboard tells useful stories — only comes from honest sessions.

This doc is the standing operating procedure for that exercise.

---

## Pre-flight (~5 min)

Before starting any real session, verify the project is set up:

```bash
# 1. Confirm install is current
cd <orquestrum-repo>
uv run scripts/lint.py                          # must pass
uv run scripts/tests/parity/run.py              # must pass
uv run scripts/convert.py --all                 # regenerate integrations

# 2. Install into the target project (idempotent — safe to re-run)
uv run scripts/install.py --tool claude-code --target /path/to/your/project

# 3. Verify hook is active in the target
ls /path/to/your/project/.sdd/scripts/hooks/emit_metrics.py
cat /path/to/your/project/.claude/settings.json | python3 -m json.tool
# Expect: hooks.Stop and hooks.SubagentStop both present, command `uv run .sdd/scripts/hooks/emit_metrics.py`

# 4. Open the UI in project mode (separate terminal)
cd <orquestrum-repo>
uv run scripts/ui/serve.py --mode project --root /path/to/your/project
# → http://127.0.0.1:7700/dashboard
```

Leave the UI running in a browser tab. You will refresh `/dashboard` between sessions.

---

## During work — what NOT to do

- **Don't manually edit** `.orquestrum/metrics/events.jsonl`. The hook owns it.
- **Don't suppress the hook** during "quick" sessions — the data we lose is exactly the data we need.
- **Don't run the framework on a project with confidential prompts and then share the metrics file.** Token counts are safe to share; if you ever re-enable transcript parsing in the future, that's not.
- **Don't tune `attention.py` weights yet.** Wait for R2's threshold (N ≥ 30 artifacts).

---

## Signals to watch (refresh `/dashboard` after each session)

### Cost signals (immediate)

| Look at | Action if... |
|---------|--------------|
| Total cost | grows faster than your monthly budget tolerance → split sessions or shift to mechanical/balanced tier |
| Cached-token ratio | < 20% on a returning session → cache markers may not be effective; review CONVENTIONS.md cache discipline |
| Top skill / agent | one skill dominates > 50% → it may be reading too much context; check `inject_references: full` use |

### Quality signals (need accumulation)

| Look at | When | Action if... |
|---------|------|--------------|
| `/audits/attention-distribution` | After ~30 artifacts emitted | Run weekly. Calibration signal at the bottom: green > 90% → too lax; red > 30% → too severe; red < 5% → inputs may not be populated |
| `MEDIATION.md` (per session) | After every checkpoint | Lowest-scored artifacts demand attention. If consistently red bands without true defects, weights need tuning |
| Budget warnings on `/dashboard` | Per session | Warning is informational. Consider splitting if recurring on the same skill |

### Operational signals (rare, important)

| If you see... | Likely cause | Action |
|---------------|--------------|--------|
| Empty `events.jsonl` after a real session | Hook didn't fire | Check `cat /tmp/orq-ui-r1.log` (UI runs subprocess; errors land in stderr); confirm `.claude/settings.json` has hooks; manually run `uv run .sdd/scripts/hooks/emit_metrics.py` with a fake JSON |
| `cost_usd: 0` on every event | Model not in MODEL_PRICING | Update `scripts/lib/models.py` MODEL_PRICING table |
| Tier collapse warning unexpected | Provider mapping changed | Check `TIER_COLLAPSES` in `scripts/lib/models.py`; cross-check `docs/governance/MODELS.md` |
| Hook stops working after Claude Code update | Hook contract drifted | Re-check claude-code-guide; update `scripts/hooks/emit_metrics.py` with new fields |

---

## Minimum viable observation window

To unlock the next phase of work:

| Goal | Threshold | Time estimate |
|------|-----------|--------------|
| **R2 baseline** (attention calibration) | 30+ artifacts with `attention_score` in `docs/03-quality/` | ~2 weeks of regular use |
| **R13 dashboard meaningful** (live routing) | 100+ events across multiple sessions | ~1 week |
| **Identify a real bug** | 1 unexpected behavior | possibly first session |

**You don't need to wait for all three.** Each unlocks independent work.

---

## Reporting back

After each session worth ≥ 5 LLM calls, capture in a free-form note:

1. **What you did** (1 sentence: "added validation to user form" / "rolled back v1.4.2")
2. **Tier classified by Helm vs your gut**: did Helm get it right?
3. **Surprises**: anything that broke, was missing, or felt wrong?
4. **Cost** (paste from `/dashboard` totals)
5. **Did `MEDIATION.md` flag anything?** Was the flag valid?

After ~5 sessions, revisit this list. Patterns will emerge that direct the next round of fixes.

---

## When to escalate to roadmap items

| Observation | ROADMAP item to revisit |
|-------------|--------------------------|
| Skill takes too much context (`inject_references: full` always loaded) | R5 (`cost_class` on skills) + R6 (compress_refs.py) |
| Dashboard refresh is annoying (manual reload) | R13 (live routing dashboard with auto-refresh) |
| Attention scoring feels off after 30 artifacts | R2 (tune weights with documented diagnosis) |
| Cipher misses something on `claude` (sharp collapse) | Document in COVERAGE.md; consider adding adversarial parity test (R9) |
| Hook stops being reliable | Investigate; may need fallback in-skill emission per skill (B-path of R3) |

---

## Hand-off note for future-self

The system is designed to **be useful imperfect**. Don't wait for "the right moment" to test it. The first session is more valuable than reading another doc. The dashboard will look weird at first; that's fine — the alternative (no signal at all) is worse.

If something breaks: read the stderr (UI logs to terminal stdout where you launched serve.py; hooks log to whatever Claude Code shows in debug mode). Most failures are due to the hook contract or path resolution. Both have known fixes documented in `HOOKS.md` and `UI_GUIDE.md`.

If everything works: the next decision-point is around R2 (after 30 artifacts). The data will tell you whether the weights need tuning. Until then, don't tune.
