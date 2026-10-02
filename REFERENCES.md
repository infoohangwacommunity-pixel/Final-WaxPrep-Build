# Reference Study Plan

This document is a **study map**, not an implementation plan.

WaxPrep will study selected external agent systems for **patterns and ideas** only.
We take patterns, not whole codebases.

- Do **not** clone these repositories into this project.
- Do **not** copy proprietary implementation code into WaxPrep.
- Do **not** merge architectures from multiple projects into one design.
- Any future code reuse must follow `LICENSES.md` and be recorded in `THIRD_PARTY`.

This map exists so later prompts can research specific topics without reinventing the list.

---

## 1. OpenHands Software Agent SDK

- **Repository:** https://github.com/OpenHands/software-agent-sdk
- **Docs:** https://docs.openhands.dev/sdk
- **License (verified):** MIT
- **Study focus:** agent, conversation, workspace, events
- **Why it matters for WaxPrep:** How a real system structures the pieces that connect intelligence, ongoing interaction, a place to work, and records of what happened—aligned with model → action → observation → model.
- **Not studying:** wholesale adoption of OpenHands as WaxPrep’s architecture.

---

## 2. OpenAI Codex

- **Repository:** https://github.com/openai/codex
- **License (verified):** Apache-2.0
- **Study focus:** session, turn, environment, executor
- **Why it matters for WaxPrep:** How an agent session progresses from task → turn → environment interaction → actual execution and result.
- **Not studying:** copying Codex’s product surface or implementation as-is.

---

## 3. OpenCode

- **Repository:** https://github.com/anomalyco/opencode  
  *(also referenced publicly as an open-source coding agent; confirm the canonical repo URL at study time)*
- **License (expected / re-verify at study time):** MIT
- **Study focus:** processing loop, permissions, compaction, skills
- **Why it matters for WaxPrep:** Continuous think → act → observe loops; what the agent is allowed to do; how history is compacted when context grows; reusable capabilities without hardcoding application workflows.
- **Not studying:** importing OpenCode’s full stack into WaxPrep.

---

## 4. Aider

- **Repository:** https://github.com/Aider-AI/aider
- **License (verified):** Apache-2.0
- **Study focus:** repo map and context efficiency
- **Why it matters for WaxPrep:** How an agent can understand a large codebase without sending the entire repository to the model every time.
- **Not studying:** building Aider’s product features or becoming a pair-programming CLI clone.

---

## 5. SWE-agent

- **Repository:** https://github.com/SWE-agent/SWE-agent
- **License (verified):** MIT
- **Study focus:** agent, environment, and trajectory separation
- **Why it matters for WaxPrep:** Clear separation between the decision-maker, the place where actions run, and the recorded sequence of decisions and outcomes.
- **Not studying:** SWE-bench harness details as WaxPrep’s core product.

---

## 6. Claude Code

- **Repository / product:** https://github.com/anthropics/claude-code  
  *(public product and documentation; implementation terms are proprietary)*
- **License (verified boundary):** Proprietary — Anthropic commercial terms / all rights reserved. **Implementation must not be copied.**
- **Study focus:** public UX, memory, skills, and observable behaviour
- **Why it matters for WaxPrep:** What users experience from the outside: interaction feel, memory presentation, reusable skills, and behaviour patterns visible in public materials.
- **Not studying / not allowed:** copying Claude Code’s source, internal protocols, or proprietary implementation into WaxPrep.

---

## General rules for later research prompts

1. Study **only** the focus areas listed above unless a later prompt expands the scope.
2. Prefer public documentation and architecture descriptions over bulk code import.
3. If a pattern is useful, re-express it in WaxPrep’s own terms under `PHILOSOPHY.md`—do not paste foreign modules.
4. Re-verify licenses at the time of any concrete study or reuse; this file records status as of **2026-10-02**.
5. Prompt 11 and beyond may research individual entries; this file does not implement any of them.
