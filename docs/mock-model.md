# Deterministic Mock Model

## Purpose

`ScriptedModelClient` implements the existing asynchronous `ModelClient`
contract without contacting a real model provider.

It allows tests to control the model's output precisely and repeatably,
without credentials, network access, provider costs, or random output.

## Writing a script

Use `model_script()` to create a sequence of `ModelResponse` values and
exceptions. Use `text_response()` for a standard text response and
`tool_request_response()` for a response that requests tools.

Example:

    client = ScriptedModelClient(
        model_script(
            text_response("First response"),
            RuntimeError("simulated model failure"),
            text_response("Final response"),
        )
    )

Each call to `complete()` consumes exactly one script step.

- A `ModelResponse` step is returned.
- An `Exception` step is raised.
- If the script is exhausted, `MockModelScriptExhaustedError` is raised.
- Requests are recorded in `client.requests`, in received order.
- `client.remaining_steps` reports the number of unused steps.

The client never repeats the final response silently. This makes a missing
script step visible in the test instead of hiding an unexpected extra call.

## Tool requests

`tool_request_response()` creates a normal `ModelResponse` with the
`TOOL_REQUEST` stop reason and one or more existing `ToolRequest` values.

It describes what the model is requesting. It does not execute tools,
validate tool permissions, or claim an action succeeded.

## Error scenarios

An exception placed in the script is raised by `complete()`. This allows
tests to verify how their own code responds to model failures.

The mock does not decide whether an error should be retried, converted into
a user-facing message, or recorded as a durable event. Those responsibilities
belong to other components and later prompts.

## Scope

This module uses the existing `waxprep.model_client` contract and Python
standard-library types only. It introduces no provider dependency,
network behavior, tool execution, agent loop, tutoring behavior, or
application-specific workflow.
