from __future__ import annotations

import unittest

from waxprep.model_client import ModelContractError, ToolDefinition
from waxprep.tool_schema import (
    ToolArgumentsError,
    ToolSchemaError,
    validate_json_schema,
    validate_tool_arguments,
)


def make_tool() -> ToolDefinition:
    """Create a representative tool definition for schema tests."""

    return ToolDefinition(
        name="read_file",
        description="Read a permitted file.",
        input_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "minLength": 1,
                    "enum": ["README.md", "CONTRIBUTING.md"],
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "include_hidden": {"type": "boolean"},
                    },
                    "required": ["include_hidden"],
                    "additionalProperties": False,
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    )


class ToolSchemaDefinitionTests(unittest.TestCase):
    def test_valid_object_schema_is_accepted(self) -> None:
        tool = make_tool()
        self.assertEqual(tool.name, "read_file")
        self.assertEqual(tool.input_schema["type"], "object")

    def test_invalid_schema_is_rejected_during_tool_definition(self) -> None:
        with self.assertRaises(ModelContractError):
            ToolDefinition(
                name="bad_tool",
                description="A tool with an invalid schema.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "not-a-json-schema-type"},
                    },
                },
            )

    def test_non_object_top_level_schema_is_rejected(self) -> None:
        with self.assertRaises(ModelContractError):
            ToolDefinition(
                name="bad_tool",
                description="A tool with the wrong top-level schema type.",
                input_schema={"type": "string"},
            )

    def test_schema_must_be_a_mapping(self) -> None:
        with self.assertRaises(ModelContractError):
            ToolDefinition(
                name="bad_tool",
                description="A tool with a non-mapping schema.",
                input_schema=[],  # type: ignore[arg-type]
            )

    def test_schema_is_deeply_copied(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
            "additionalProperties": False,
        }

        tool = ToolDefinition(
            name="read_file",
            description="Read a permitted file.",
            input_schema=schema,
        )

        schema["properties"]["path"]["type"] = "integer"
        validate_tool_arguments(tool, {"path": "README.md"})

    def test_nested_schema_mappings_are_immutable(self) -> None:
        tool = make_tool()

        with self.assertRaises(TypeError):
            tool.input_schema["properties"]["path"]["type"] = "integer"  # type: ignore[index]

    def test_nested_schema_arrays_are_immutable(self) -> None:
        tool = make_tool()

        with self.assertRaises(AttributeError):
            tool.input_schema["properties"]["path"]["enum"].append(  # type: ignore[index,union-attr]
                "NEW.md"
            )

    def test_validate_json_schema_rejects_invalid_schema(self) -> None:
        with self.assertRaises(ToolSchemaError):
            validate_json_schema(
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "unknown-type"},
                    },
                }
            )


class ToolArgumentValidationTests(unittest.TestCase):
    def test_valid_arguments_are_accepted(self) -> None:
        validate_tool_arguments(
            make_tool(),
            {
                "path": "README.md",
                "limit": 100,
                "options": {"include_hidden": False},
            },
        )

    def test_required_field_must_be_present(self) -> None:
        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(make_tool(), {"limit": 10})

    def test_wrong_argument_type_is_rejected(self) -> None:
        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(make_tool(), {"path": 123})

    def test_empty_path_is_rejected(self) -> None:
        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(make_tool(), {"path": ""})

    def test_enum_constraints_are_enforced(self) -> None:
        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(make_tool(), {"path": "secret.txt"})

    def test_additional_fields_are_rejected(self) -> None:
        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(
                make_tool(),
                {"path": "README.md", "unexpected": True},
            )

    def test_integer_bounds_are_enforced(self) -> None:
        tool = make_tool()

        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(
                tool,
                {"path": "README.md", "limit": 0},
            )

        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(
                tool,
                {"path": "README.md", "limit": 1001},
            )

    def test_boolean_is_not_accepted_as_an_integer(self) -> None:
        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(
                make_tool(),
                {"path": "README.md", "limit": True},
            )

    def test_nested_object_constraints_are_enforced(self) -> None:
        tool = make_tool()

        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(
                tool,
                {"path": "README.md", "options": {}},
            )

        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(
                tool,
                {
                    "path": "README.md",
                    "options": {
                        "include_hidden": False,
                        "unexpected": True,
                    },
                },
            )

    def test_non_mapping_arguments_are_rejected(self) -> None:
        with self.assertRaises(ToolArgumentsError):
            validate_tool_arguments(
                make_tool(),
                [],  # type: ignore[arg-type]
            )

    def test_error_identifies_the_tool(self) -> None:
        with self.assertRaisesRegex(ToolArgumentsError, "read_file"):
            validate_tool_arguments(make_tool(), {"path": 123})


if __name__ == "__main__":
    unittest.main()
