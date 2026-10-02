# SWE-agent Research Notes

## Purpose

This document records architectural observations from the current public SWE-agent repository.

WaxPrep is studying SWE-agent for patterns and ideas only. SWE-agent is a software-engineering agent and contains domain-specific behavior that should not be copied into WaxPrep's general foundation.

## Repository studied

- **Project:** SWE-agent
- **Repository:** https://github.com/SWE-agent/SWE-agent

The current project describes itself as an open-source Agent Computer Interface for running language models as software engineers.

Its current architecture separates the agent from the environment/runtime through `SWEEnv` and SWE-ReX.

## 1. Agent loop

The central agent loop is intentionally straightforward.

A run performs setup and then repeatedly executes agent steps until the step reports that the run is finished.

The basic cycle is:

1. Prepare the environment.
2. Prepare the model history.
3. Ask the model for the next response.
4. Parse the response into thought/action information.
5. Check whether the action is permitted.
6. Execute the action in the environment.
7. Capture the resulting observation.
8. Capture useful environment state.
9. Add the action and observation to model history.
10. Record the completed step in the trajectory.
11. Repeat.

The main implementation is in `DefaultAgent`.

### Important source location

- `sweagent/agent/agents.py` — `DefaultAgent.run()`, `step()`, `forward()`, `handle_action()`, `add_step_to_history()`, `add_step_to_trajectory()`

## 2. Model → action → environment → observation

In `forward()`, SWE-agent sends the current history to the model.

The model response is then parsed into:

- model output
- thought
- action
- optional tool-call information

The resulting action is passed to `handle_action()`.

`handle_action()` checks the action, sends the command to the environment, captures the output, captures environment state, and returns the resulting `StepOutput`.

This is a very direct implementation of:

**model decision → action → world execution → observation**

### Important source location

- `sweagent/agent/agents.py`

## 3. History

SWE-agent maintains a `history` list for the current agent attempt.

History contains the information used to construct future model requests.

After a step, the agent adds:

- the model response
- thought
- action
- tool-call information

and then adds the observation as the next history item.

Observation templates can also tell the model when output was empty or when the observation was truncated.

This is useful because the model does not merely receive the raw command result; the system can represent the result in a form appropriate for the next model request.

### Important source locations

- `sweagent/agent/agents.py`
- `sweagent/agent/history_processors.py`

## 4. Trajectory

SWE-agent separately records a trajectory.

A trajectory is a sequence of structured `TrajectoryStep` records.

Each step includes fields such as:

- action
- observation
- response
- thought
- execution time
- environment state
- query
- extra information

The trajectory is written to `.traj` JSON output.

This means SWE-agent separates:

- **history** used to continue reasoning
- **trajectory** used to record what happened during the run

That distinction is highly relevant to WaxPrep.

### Important source locations

- `sweagent/types.py`
- `sweagent/agent/agents.py`
- `docs/usage/trajectories.md`

## 5. State

Each trajectory step can contain environment state.

The state is obtained through the tool/environment layer after action execution.

The state can include information needed to understand the current environment, such as the working directory or other tool-defined state.

This is different from the trajectory itself.

- The trajectory records the sequence.
- The environment state describes the world at a particular point in that sequence.

## 6. Environment abstraction

SWE-agent uses `SWEEnv` as the environment interface used by the agent.

The current architecture deliberately keeps `SWEEnv` relatively thin.

The actual runtime/deployment work is handled by SWE-ReX.

SWE-ReX can provide sandboxed execution locally or on remote infrastructure such as Docker-based or cloud environments while allowing the agent code to remain largely unchanged.

This creates a strong separation:

- SWE-agent decides what to do.
- SWE-ReX provides somewhere to do it.

### Important source locations

- `sweagent/environment/swe_env.py`
- `docs/background/architecture.md`
- SWE-ReX repository

## 7. Actions and observations

SWE-agent has a structured `Command` model for defining executable commands.

A command can define:

- name
- description
- signature
- arguments
- argument types
- required arguments
- optional arguments
- enumerated values
- invocation formatting

Commands can also be converted into function-calling tool definitions.

However, the actual default execution path is still command-oriented: the model ultimately proposes a command that is passed to the environment.

The completed step is then represented in `StepOutput` and `TrajectoryStep`.

This differs from OpenHands:

- OpenHands has richer typed `Action` and `Observation` domain objects.
- SWE-agent has structured command definitions but represents the actual executed command and resulting output more directly as step data.

Neither approach should automatically be considered the correct WaxPrep implementation. The useful lesson is the explicit boundary between proposed action and observed result.

### Important source locations

- `sweagent/tools/commands.py`
- `sweagent/types.py`
- `sweagent/agent/agents.py`

## 8. Error handling

SWE-agent treats several failures as part of the agent loop.

For example, formatting errors, blocked actions, and shell syntax errors can cause the model to be queried again with corrective information.

Other failures, such as environment failures, cost limits, context limits, or repeated execution problems, can terminate the run through the project's failure handling.

This demonstrates an important general principle:

**An execution failure can become new information for the model rather than being silently ignored.**

However, the exact recovery policies in SWE-agent are specific to its software-engineering task and should not be copied into WaxPrep.

## 9. Complexity to avoid

The current SWE-agent contains many features that exist because it is solving software-engineering benchmark and repository tasks.

Examples include:

- problem statements
- repository-specific setup
- patch extraction
- edited-file summaries
- submission commands
- SWE-bench-oriented result handling
- autosubmission after certain failures
- retry-agent/reviewer logic
- benchmark-oriented batch execution
- specialized configuration

These are not fundamental requirements for a general computer agent.

WaxPrep should learn the general mechanism:

**model → action → environment → observation → next model input**

without importing software-engineering-specific decisions into the foundation.

## 10. Particularly valuable lesson from SWE-ReX

SWE-ReX was created partly to separate agent logic from execution infrastructure.

The agent can ask the environment to execute commands while the runtime layer handles whether that execution happens locally, inside a container, or through remote infrastructure.

This is closely aligned with WaxPrep's philosophy:

- AI is the brain.
- The runtime is the hands.
- The intelligence should not need to know how the hands are physically implemented.

### Important source location

- SWE-ReX repository and documentation

## 11. What WaxPrep should learn from SWE-agent

1. Keep the core loop small and explicit.
2. Separate model history from durable run records.
3. Record action, observation, and world state together for each physical step when useful.
4. Keep the agent independent from the infrastructure that executes commands.
5. Let execution errors become information for the next model decision where appropriate.
6. Make the environment boundary replaceable.
7. Keep application/benchmark-specific completion rules outside the general agent foundation.

## 12. What WaxPrep should not copy

WaxPrep should not copy:

- SWE-bench-specific behavior
- repository patch/submission logic
- benchmark batch infrastructure
- SWE-agent's problem-statement model
- benchmark-specific retry/reviewer architecture
- its complete command/tool configuration system
- coding-agent-specific prompts
- its entire environment configuration
- SWE-agent-specific output/evaluation behavior

The purpose is to study the general agent/environment/trajectory relationship.

## Research status

Verified against the current public SWE-agent repository and its current public architecture/documentation.

No SWE-agent source code is copied into WaxPrep.
