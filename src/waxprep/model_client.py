from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from waxprep.tool_schema import ToolSchemaError, validate_json_schema


class ModelContractError(ValueError):
    """Raised when normalized model contract data is invalid."""


class ModelMessageRole(StrEnum):
    """Vendor-neutral roles for messages sent to or returned by a model."""

    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class StopReason(StrEnum):
    """Vendor-neutral semantic reasons a model response stopped."""

    END_TURN = "end_turn"
    TOOL_REQUEST = "tool_request"
    MAX_TOKENS = "max_tokens"
    CONTENT_FILTER = "content_filter"
    UNKNOWN = "unknown"


def _require_non_empty_string(value: object, field_name: str) -> str:
    """Require a string containing at least one non-whitespace character."""

    if not isinstance(value, str) or not value.strip():
        raise ModelContractError(f"{field_name} must be a non-empty string.")
    return value


def _freeze_mapping(value: object, field_name: str) -> Mapping[str, object]:
    """Copy and protect a mapping's top level."""

    if not isinstance(value, Mapping):
        raise ModelContractError(f"{field_name} must be a mapping.")

    copied = dict(value)

    if any(not isinstance(key, str) for key in copied):
        raise ModelContractError(f"{field_name} keys must be strings.")

    return MappingProxyType(copied)


def _freeze_schema_value(value: object) -> object:
    """Recursively copy and freeze a tool schema's JSON-like values."""

    if isinstance(value, Mapping):
        copied: dict[str, object] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise ModelContractError("Tool input schema keys must be strings.")
            copied[key] = _freeze_schema_value(item)

        return MappingProxyType(copied)

    if isinstance(value, (list, tuple)):
        return tuple(_freeze_schema_value(item) for item in value)

    return value


@dataclass(frozen=True, slots=True)
class TextContentBlock:
    """A vendor-neutral text content block."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise ModelContractError("Text content must be a string.")


@dataclass(frozen=True, slots=True)
class ImageContentBlock:
    """A vendor-neutral reference to image content."""

    uri: str
    media_type: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.uri, "Image URI")

        if self.media_type is not None:
            _require_non_empty_string(self.media_type, "Image media type")


type ContentBlock = TextContentBlock | ImageContentBlock


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """A tool the model is permitted to request through the caller."""

    name: str
    description: str
    input_schema: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_non_empty_string(self.name, "Tool name")

        if not isinstance(self.description, str):
            raise ModelContractError("Tool description must be a string.")

        schema = _freeze_mapping(
            self.input_schema,
            "Tool input schema",
        )
        frozen_schema = _freeze_schema_value(schema)

        if not isinstance(frozen_schema, Mapping):
            raise ModelContractError("Tool input schema must be a mapping.")

        object.__setattr__(self, "input_schema", frozen_schema)

        try:
            validate_json_schema(frozen_schema)
        except ToolSchemaError as exc:
            raise ModelContractError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """A normalized request for the caller to consider executing a tool."""

    id: str
    name: str
    arguments: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_non_empty_string(self.id, "Tool request ID")
        _require_non_empty_string(self.name, "Tool request name")

        object.__setattr__(
            self,
            "arguments",
            _freeze_mapping(self.arguments, "Tool arguments"),
        )


@dataclass(frozen=True, slots=True)
class ModelMessage:
    """A vendor-neutral message supplied as part of a model request."""

    role: ModelMessageRole
    content: tuple[ContentBlock, ...]
    name: str | None = None
    tool_call_id: str | None = None
    tool_requests: tuple[ToolRequest, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.role, ModelMessageRole):
            raise ModelContractError("Message role must be a ModelMessageRole.")

        if not isinstance(self.content, tuple):
            raise ModelContractError("Message content must be a tuple.")

        if not all(
            isinstance(block, (TextContentBlock, ImageContentBlock))
            for block in self.content
        ):
            raise ModelContractError(
                "Message content must contain supported content blocks."
            )

        if self.name is not None:
            _require_non_empty_string(self.name, "Message name")

        if not isinstance(self.tool_requests, tuple):
            raise ModelContractError("Message tool_requests must be a tuple.")

        if not all(isinstance(item, ToolRequest) for item in self.tool_requests):
            raise ModelContractError(
                "Message tool_requests must contain ToolRequest values."
            )

        if self.role is ModelMessageRole.TOOL:
            _require_non_empty_string(self.tool_call_id, "Tool call ID")
        elif self.tool_call_id is not None:
            raise ModelContractError(
                "tool_call_id is only valid for tool-result messages."
            )

        if self.tool_requests and self.role is not ModelMessageRole.ASSISTANT:
            raise ModelContractError(
                "Only assistant messages may contain tool requests."
            )


@dataclass(frozen=True, slots=True)
class ModelSettings:
    """Common settings whose meanings do not depend on a specific vendor."""

    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    stop_sequences: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.temperature is not None and (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or not math.isfinite(self.temperature)
            or self.temperature < 0
        ):
            raise ModelContractError(
                "temperature must be a finite non-negative number."
            )

        if self.top_p is not None and (
            isinstance(self.top_p, bool)
            or not isinstance(self.top_p, (int, float))
            or not math.isfinite(self.top_p)
            or not 0 < self.top_p <= 1
        ):
            raise ModelContractError("top_p must be greater than zero and at most one.")

        if self.max_output_tokens is not None and (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or self.max_output_tokens < 1
        ):
            raise ModelContractError("max_output_tokens must be a positive integer.")

        if not isinstance(self.stop_sequences, tuple):
            raise ModelContractError("stop_sequences must be a tuple.")

        for sequence in self.stop_sequences:
            _require_non_empty_string(sequence, "Stop sequence")


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """A normalized request independent of any model vendor."""

    messages: tuple[ModelMessage, ...]
    tools: tuple[ToolDefinition, ...] = ()
    settings: ModelSettings = field(default_factory=ModelSettings)

    def __post_init__(self) -> None:
        if not isinstance(self.messages, tuple) or not self.messages:
            raise ModelContractError(
                "Model request messages must be a non-empty tuple."
            )

        if not all(isinstance(message, ModelMessage) for message in self.messages):
            raise ModelContractError(
                "Model request messages must contain ModelMessage values."
            )

        if not isinstance(self.tools, tuple):
            raise ModelContractError("Model request tools must be a tuple.")

        if not all(isinstance(tool, ToolDefinition) for tool in self.tools):
            raise ModelContractError(
                "Model request tools must contain ToolDefinition values."
            )

        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ModelContractError("Model request tool names must be unique.")

        if not isinstance(self.settings, ModelSettings):
            raise ModelContractError("Model request settings must be ModelSettings.")


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """Token usage reported by a model, when available."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("total_tokens", self.total_tokens),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ModelContractError(
                    f"{field_name} must be a non-negative integer or None."
                )


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """A normalized response independent of any model vendor."""

    content: tuple[ContentBlock, ...]
    stop_reason: StopReason
    tool_requests: tuple[ToolRequest, ...] = ()
    usage: ModelUsage = field(default_factory=ModelUsage)

    def __post_init__(self) -> None:
        if not isinstance(self.content, tuple):
            raise ModelContractError("Response content must be a tuple.")

        if not all(
            isinstance(block, (TextContentBlock, ImageContentBlock))
            for block in self.content
        ):
            raise ModelContractError(
                "Response content must contain supported content blocks."
            )

        if not isinstance(self.tool_requests, tuple):
            raise ModelContractError("Response tool_requests must be a tuple.")

        if not all(isinstance(item, ToolRequest) for item in self.tool_requests):
            raise ModelContractError(
                "Response tool_requests must contain ToolRequest values."
            )

        if not isinstance(self.stop_reason, StopReason):
            raise ModelContractError("Response stop_reason must be a StopReason.")

        if not isinstance(self.usage, ModelUsage):
            raise ModelContractError("Response usage must be ModelUsage.")

        if self.tool_requests and self.stop_reason is not StopReason.TOOL_REQUEST:
            raise ModelContractError(
                "A response containing tool requests must use "
                "the tool_request stop reason."
            )

        if self.stop_reason is StopReason.TOOL_REQUEST and not self.tool_requests:
            raise ModelContractError(
                "The tool_request stop reason requires at least one tool request."
            )


class ModelClient(Protocol):
    """Asynchronous contract implemented by future model-provider clients."""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Complete one normalized model request."""


__all__ = [
    "ContentBlock",
    "ImageContentBlock",
    "ModelClient",
    "ModelContractError",
    "ModelMessage",
    "ModelMessageRole",
    "ModelRequest",
    "ModelResponse",
    "ModelSettings",
    "ModelUsage",
    "StopReason",
    "TextContentBlock",
    "ToolDefinition",
    "ToolRequest",
]
