# WaxPrep Philosophy

## The Core Idea

WaxPrep is a general-purpose computer agent.

The central idea is simple:

**The model is the brain. The agent loop is the nervous system. The real runtime and computer environment are the body and hands. Session and event records are the memory of what physically happened.**

WaxPrep should let intelligence decide what needs to happen, while the real world provides the means to carry out that decision and report what actually happened.

## The Four Core Parts

### 1. The Model Is the Brain

The model provides the intelligence that interprets the situation, reasons about what to do, chooses the next action, and decides what matters.

WaxPrep's infrastructure should not try to replace that intelligence with a collection of application-specific rules.

The model should be able to decide based on the information and results available to it.

### 2. The Agent Loop Is the Nervous System

The agent loop connects the model to the real world.

It carries decisions from the model toward execution, then carries real results back to the model.

The loop is what allows the agent to continue from what actually happened instead of assuming that an attempted action succeeded.

### 3. The Runtime Is the Body and Hands

The runtime is the real environment in which the agent acts.

It provides the computer-world capabilities the model needs, such as working with files, processes, the operating system, networks, and other permitted runtime capabilities.

The runtime does not decide what those capabilities mean for a particular application. It provides the general ability to act and reports the real result.

### 4. Session and Event Records Are Memory of What Physically Happened

Session and event records preserve what happened during the agent's interaction with the real world.

They are not a substitute for intelligence.

They provide a durable record of actions, observations, outcomes, and session state so the agent can understand what has physically happened and continue from that reality.

## The Core Cycle

WaxPrep follows one basic cycle:

**The model decides → an action executes in the real world → the real result is observed → that result becomes input to the model → the model decides again.**

The important rule is that the result must come from the real execution.

An action being requested is not the same thing as an action succeeding.

The agent should observe what actually happened and continue from that observation.

## The Generality Rule

WaxPrep is general infrastructure, not a collection of special-purpose application workflows.

The core system must not contain logic that is specifically designed around:

- websites
- PDFs
- audio
- reminders
- or other individual application types

Instead, the infrastructure should provide general capabilities that an intelligent agent can use.

The model decides what a file, website, audio recording, reminder, or other piece of information means and what should be done with it when the relevant capability exists.

This keeps the core agent general and prevents application-specific behavior from being hidden inside infrastructure.

## Layering

WaxPrep is developed in layers.

The intended order is:

1. **Intelligence** — the model that reasons and decides.
2. **Agent loop** — the cycle that connects decisions, actions, and observations.
3. **Session and state** — the information needed to continue an agent session and remember what physically happened.
4. **World/runtime** — the real computer environment in which actions execute.
5. **Permissions and sandbox** — the boundaries that control what the agent is allowed to do.
6. **Identity and domain behavior, much later** — application-specific identity and behavior are added only after the general agent foundation exists and there is an explicit reason to add them.

Each layer should have a clear responsibility.

A lower layer should provide general capabilities rather than secretly taking over decisions that belong to the intelligence layer.

## Tutoring Comes Last

Tutoring is a domain behavior, not the foundation of the general-purpose agent.

WaxPrep must not build tutoring-specific behavior into the foundation merely because the eventual product may be used as a tutor.

Tutoring should be introduced much later, and only when a future prompt explicitly instructs the project to add it.

Until then, the system should remain a general-purpose computer agent.

## A Rule for Future Decisions

When a future design decision is unclear, this document provides a basic question:

**Does this make the agent more capable of letting intelligence decide and then act through a real world, or does it move application-specific decisions into infrastructure?**

The first direction belongs in the general foundation when the current stage calls for it.

The second direction should wait for an explicit domain stage.

This philosophy is the foundation against which later architecture and implementation decisions should be checked.
