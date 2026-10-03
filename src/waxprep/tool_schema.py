from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Protocol

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


class ToolSchemaError(ValueError):
    """Raised when a tool's JSON Schema is invalid."""


class ToolArgumentsError(ValueError):
    """Raised when tool arguments do not satisfy the declared schema."""


class _ToolDefinitionLike(Protocol):
    """Minimum tool definition interface needed by the validator."""

    name: str
    input_schema: Mapping[str, object]


def _to_json_value(value: object) -> object:
    """Convert immutable mappings and tuples into ordinary JSON-like values."""

    if isinstance(value, Mapping):
        result: dict[str, object] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise ToolSchemaError("JSON object keys must be strings.")
            result[key] = _to_json_value(item)

        return result

    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]

    if isinstance(value, float) and not math.isfinite(value):
        raise ToolSchemaError("JSON numbers must be finite.")

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    raise ToolSchemaError(
        f"Value of type {type(value).__name__} is not JSON-compatible."
    )


def validate_json_schema(schema: Mapping[str, object]) -> None:
    """Validate a tool input schema using JSON Schema Draft 2020-12.

    Tool input schemas must describe a JSON object because tool arguments
    are represented by mappings in WaxPrep's normalized model contract.
    """

    try:
        normalized = _to_json_value(schema)
    except ToolSchemaError as exc:
        raise ToolSchemaError(f"Invalid tool input schema: {exc}") from exc

    if not isinstance(normalized, dict):
        raise ToolSchemaError("A tool input schema must be a JSON object.")

    if normalized.get("type") != "object":
        raise ToolSchemaError("A tool input schema must have top-level type 'object'.")

    try:
        Draft202012Validator.check_schema(normalized)
    except SchemaError as exc:
        raise ToolSchemaError(f"Invalid tool input schema: {exc.message}") from exc


def validate_tool_arguments(
    tool: _ToolDefinitionLike,
    arguments: Mapping[str, object],
) -> None:
    """Raise ToolArgumentsError unless arguments satisfy the tool schema.

    This function validates data only. It does not execute the tool,
    authorize the requested action, or establish that an action is safe.
    """

    if not isinstance(arguments, Mapping):
        raise ToolArgumentsError("Tool arguments must be a mapping.")

    validate_json_schema(tool.input_schema)

    try:
        normalized_arguments = _to_json_value(arguments)
    except ToolSchemaError as exc:
        raise ToolArgumentsError(
            f"Invalid arguments for tool '{tool.name}': {exc}"
        ) from exc

    if not isinstance(normalized_arguments, dict):
        raise ToolArgumentsError("Tool arguments must describe a JSON object.")

    normalized_schema = _to_json_value(tool.input_schema)

    if not isinstance(normalized_schema, dict):
        raise ToolSchemaError("A tool input schema must be a JSON object.")

    validator = Draft202012Validator(normalized_schema)
    errors = sorted(
        validator.iter_errors(normalized_arguments),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            error.message,
        ),
    )

    if errors:
        error = errors[0]
        path = "$"

        for part in error.absolute_path:
            if isinstance(part, int):
                path += f"[{part}]"
            else:
                path += f".{part}"

        raise ToolArgumentsError(
            f"Invalid arguments for tool '{tool.name}' at {path}: {error.message}"
        )


__all__ = [
    "ToolArgumentsError",
    "ToolSchemaError",
    "validate_json_schema",
    "validate_tool_arguments",
]
