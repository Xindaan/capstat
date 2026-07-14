# CLAUDE.md — capstat

Follow `AGENTS.md` — it is the single source for project conventions.
Additional notes for Claude Code sessions:

- **Language override** (vs. the German default in `~/src/CLAUDE.md`,
  decided 2026-07-13): all repo content is English. Chat with the
  maintainer may remain German.
- **Orchestrator mode:** the main model plans, reviews, and synthesizes;
  delegate volume/boilerplate work to cheap subagents (Haiku default,
  Sonnet only where real multi-step reasoning is needed). Never
  delegate: reference-value transcription and statistical formula
  review — verify those twice against the source yourself.
- **Effort routing:** default `high`. `/effort xhigh` only for long
  agentic implementation blocks (M1 and later). Single `ultrathink`
  turns for the two riskiest spots: Gage R&R variance components
  (incl. negative-variance handling) and non-normal capability design.
- Project memory: `~/.claude/projects/-Users-Andre-src-capstat/memory/`.
