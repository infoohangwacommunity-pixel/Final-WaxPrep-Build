# WaxPrep Decision Log

This document records the major project decisions made during the foundation phase
(Prompts 1–14).

WaxPrep is being built first as a general-purpose computer agent. Application-specific
behavior, including tutoring, is intentionally postponed until the architecture is
ready for it.

---

## 1. Project Identity

**Decision:** The project is named WaxPrep.

**Reason:** The repository and architecture were intentionally established under the
WaxPrep name before implementation of the agent system begins.

---

## 2. Project Purpose

**Decision:** WaxPrep is a general-purpose computer agent foundation.

**Reason:** The foundation must be useful independently of any single application or
domain.

The eventual Waza educational tutor will be built on top of this foundation, but
tutoring behavior does not belong in the foundation itself.

---

## 3. Core Agent Philosophy

**Decision:** The AI model is the primary intelligence of the system.

The core relationship is:

    model decides
        ↓
    action request
        ↓
    real world / runtime
        ↓
    actual result
        ↓
    observation
        ↓
    model decides again

**Reason:** The model should interpret situations, choose actions, and reason about
results. Infrastructure should provide the environment in which those decisions can
be carried out.

The infrastructure must not secretly become a second intelligence layer.

---

## 4. Runtime as the Real World

**Decision:** The runtime is the physical execution layer of the agent.

The runtime may eventually provide general capabilities such as:

- filesystem access
- terminal execution
- processes
- network access
- clock/time
- workspace access

**Reason:** The agent needs a real environment in which actions can happen.

The runtime reports what actually happened. It does not decide what an action means.

---

## 5. Action and Observation

**Decision:** A requested action is not treated as proof that the action succeeded.

**Reason:** The model can request an action, but only the runtime can establish what
actually happened.

Therefore:

- requested is not the same as executed
- executed is not the same as successful
- permission is not the same as execution
- the runtime observation is the source of truth about execution

---

## 6. General Infrastructure Only

**Decision:** Foundation infrastructure must remain general-purpose.

The foundation must not contain workflows specifically designed for:

- websites
- PDFs
- audio
- reminders
- tutoring
- individual applications
- hardcoded user intents

**Reason:** Those decisions belong to the model or to later domain/application
layers, not to the general agent infrastructure.

---

## 7. No Hidden Intent Router

**Decision:** WaxPrep will not use a hidden application-specific intent-routing
layer.

**Reason:** An intent router would move part of the intelligence from the model into
infrastructure and could cause the infrastructure to decide what the user means.

The model remains responsible for interpreting the user's request.

---

## 8. No Mandatory Embedding or Vector Architecture

**Decision:** WaxPrep does not require embeddings, vector databases, or keyword
matching as a foundation requirement.

**Reason:** These are implementation techniques, not architectural requirements.

If a later capability genuinely requires one of them, that decision must be made
explicitly at that stage.

---

## 9. Sessions and Events

**Decision:** Durable sessions and event records represent what physically happened
during agent operation.

**Reason:** The system needs a reliable record of reality rather than relying only
on the model's current context.

A session may contain multiple turns, and a turn may contain multiple
model/action/observation cycles.

---

## 10. Durable History vs Active Context

**Decision:** Durable history and the model's active context are separate concepts.

**Reason:** The system may preserve a large amount of history without sending all of
that history to the model on every request.

Future context-management work will decide what information is relevant to a specific
model call.

---

## 11. Workspace

**Decision:** A workspace is an area in which the agent can operate.

**Reason:** The agent needs a defined place where real-world operations can occur.

Workspace design remains general-purpose and is not tied to a tutoring workflow.

---

## 12. Permissions and Sandboxing

**Decision:** Permissions and sandboxing are runtime/world boundaries.

**Reason:** They exist to control what the agent is physically allowed to do.

They are not an application-level role system such as:

- administrator
- teacher
- student

Those concepts belong to a future application/domain layer if they are ever needed.

---

## 13. Skills and Subagents

**Decision:** Skills and subagents are optional extensions around the core agent loop.

**Reason:** They can provide reusable guidance or isolated agent contexts without
changing the fundamental model → action → runtime → observation cycle.

They must not become hidden application routers.

---

## 14. Language and Runtime

**Decision:** WaxPrep uses Python 3.14.

**Reason:** Python 3.14 was selected as the project runtime during the foundation phase.

The supported Python range is:

    >=3.14,<3.15

---

## 15. Package and Environment Management

**Decision:** WaxPrep uses `uv` for Python environment and package management.

**Reason:** The project requires a deterministic and simple development workflow.

---

## 16. Code Quality

**Decision:** WaxPrep uses:

- Ruff for formatting and linting
- mypy in strict mode for type checking
- Python unittest for tests

**Reason:** These provide deterministic automated checks while keeping the foundation
small.

The standard project verification command is:

    make check

---

## 17. Continuous Integration

**Decision:** GitHub Actions runs the project's quality checks.

**Reason:** Changes should be automatically verified rather than relying only on a
developer's local environment.

Automated changes must still pass the project's quality gate.

---

## 18. Dependency Automation

**Decision:** Dependabot is used for dependency update management, with automated
merging governed by the repository's quality checks.

**Reason:** Dependency maintenance should remain controlled by automated verification
rather than bypassing project checks.

---

## 19. Licensing

**Decision:** WaxPrep uses the Apache License 2.0.

**Reason:** This is the repository's selected project license.

The repository also records third-party licensing policy separately.

---

## 20. Third-Party Code and Research

**Decision:** WaxPrep studies publicly documented architectures from:

- OpenHands
- OpenAI Codex
- OpenCode
- Aider
- SWE-agent
- Claude Code

**Reason:** These projects provide useful publicly documented patterns for reliable
computer-agent systems.

WaxPrep borrows architectural ideas, not entire codebases.

Third-party source code may only be reused when permitted by the repository's licensing
policy, and required attribution must be recorded.

---

## 21. Research Lessons

The shared architectural pattern identified during research is:

    model decision
        ↓
    action
        ↓
    real environment
        ↓
    observation
        ↓
    next model decision

Important lessons include:

- execution results must come from the real environment
- durable history should not automatically equal active model context
- sessions can contain multiple turns
- turns can contain multiple execution cycles
- permissions should remain separate from action implementation
- long-running agents need continuity
- context must be managed rather than blindly sending everything to the model

---

## 22. Architecture Boundary

**Decision:** The smallest important architectural boundary is between intelligence
and the real world.

The model decides.

The agent loop connects the decision to execution.

The runtime executes.

The runtime produces observations.

The model receives those observations and continues reasoning.

**Reason:** This boundary prevents infrastructure from silently becoming application
intelligence.

---

## 23. Tutoring Is Deferred

**Decision:** Tutoring and educational application behavior are intentionally postponed.

**Reason:** The general-purpose agent foundation must be reliable before domain-specific
behavior is introduced.

Tutoring is therefore a future application/domain phase, not part of the Phase 0
foundation.

---

## 24. Build Scope Discipline

**Decision:** Each implementation prompt should implement only the capability assigned
to that prompt.

**Reason:** Building future stages early makes the architecture harder to verify and
makes it difficult to identify which decision introduced a problem.

Future capabilities should be added only when their stage is explicitly reached.

---

## Phase 0 Status

Prompts 1–14 established the project foundation, research record, philosophy, and
architecture blueprint.

Prompt 15 is the Phase 0 review gate.

No identifier scheme, agent loop implementation, runtime implementation, tutoring
logic, or other later-stage capability belongs in this review.

The repository should proceed to the next prompt only after the Phase 0 checks pass
and the resulting repository state is tagged or otherwise recorded.
