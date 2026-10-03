"""A deterministic, scripted ModelClient for tests."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from waxprep.model_client import (
    ContentBlock,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    StopReason,
    TextContentBlock,
    ToolRequest,
)

type ModelScriptStep = ModelResponse | Exception


class MockModelScriptError(RuntimeError):
    """Raised when a scripted mock-model interaction cannot continue."""


class MockModelScriptExhaustedError(MockModelScriptError):
    """Raised when the mock model receives a request with no steps remaining."""


def model_script(*steps: ModelScriptStep) -> tuple[ModelScriptStep, ...]:
    """Create a validated immutable script of responses and scripted exceptions."""

    for index, step in enumerate(steps):
        if not isinstance(step, (ModelResponse, Exception)):
            raise TypeError(
                f"Script step {index} must be a ModelResponse or Exception."
            )

    return tuple(steps)


def text_response(
    text: str,
    *,
    usage: ModelUsage | None = None,
) -> ModelResponse:
    """Create a normal assistant text response for a test script."""

    return ModelResponse(
        content=(TextContentBlock(text),),
        stop_reason=StopReason.END_TURN,
        usage=usage if usage is not None else ModelUsage(),
    )


def tool_request_response(
    *tool_requests: ToolRequest,
    content: tuple[ContentBlock, ...] = (),
) -> ModelResponse:
    """Create a model response that requests one or more tools.

    The response describes requested actions only. It does not execute them.
    """

    if not tool_requests:
        raise ValueError("At least one tool request is required.")

    return ModelResponse(
        content=content,
        stop_reason=StopReason.TOOL_REQUEST,
        tool_requests=tuple(tool_requests),
    )


class ScriptedModelClient:
    """A predictable ModelClient that consumes one script step per request.

    A step may be a ModelResponse, which is returned, or an Exception,
    which is raised. Script steps are consumed in order.

    Requests are recorded in the order received, including requests that
    encounter a scripted exception or an exhausted script. No network access,
    provider SDK, randomness, or real model is involved.
    """

    def __init__(self, steps: Iterable[ModelScriptStep]) -> None:
        validated_steps = model_script(*tuple(steps))
        self._steps: deque[ModelScriptStep] = deque(validated_steps)
        self._requests: list[ModelRequest] = []

    @property
    def requests(self) -> tuple[ModelRequest, ...]:
        """Return an immutable snapshot of requests received so far."""

        return tuple(self._requests)

    @property
    def remaining_steps(self) -> int:
        """Return the number of responses or exceptions left in the script."""

        return len(self._steps)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Return or raise the next scripted step for one model request."""

        self._requests.append(request)

        if not self._steps:
            raise MockModelScriptExhaustedError(
                "The scripted mock model has no response steps remaining."
            )

        step = self._steps.popleft()

        if isinstance(step, Exception):
            raise step

        return step


__all__ = [
    "MockModelScriptError",
    "MockModelScriptExhaustedError",
    "ModelScriptStep",
    "ScriptedModelClient",
    "model_script",
    "text_response",
    "tool_request_response",
]
