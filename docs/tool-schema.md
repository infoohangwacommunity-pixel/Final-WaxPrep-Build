# Tool Schema and Argument Validation

WaxPrep defines model-facing tools through the existing ToolDefinition
contract. Each definition contains a name, description, and input schema.

## Supported schema dialect

Tool input schemas use JSON Schema Draft 2020-12.

A tool input schema must be a JSON object schema with top-level
"type": "object". Its properties, required fields, nested values, and
other constraints are defined by JSON Schema.

## Defining a tool

```python
from waxprep.model_client import ToolDefinition

tool = ToolDefinition(
    name="read_file",
    description="Read a permitted file.",
    input_schema={
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "path": {"type": "string", "minLength": 1},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
)
```

The definition validates its schema when it is constructed. Invalid schemas
raise ModelContractError.

The schema is copied and frozen so later mutation of the original dictionary
cannot change the tool's declared input contract.

## Validating arguments

```python
from waxprep.tool_schema import (
    ToolArgumentsError,
    validate_tool_arguments,
)

try:
    validate_tool_arguments(tool, {"path": "README.md"})
except ToolArgumentsError as exc:
    print(f"Invalid tool arguments: {exc}")
```

Successful validation returns None. Invalid arguments raise
ToolArgumentsError, including a useful description of the validation
failure.

## Important boundaries

Schema validation establishes only that the supplied arguments match the
declared input schema.

It does not:
- execute the tool;
- authorize the requested operation;
- establish that an operation is safe;
- establish that the requested operation succeeded;
- convert the schema into a provider-specific API format.

A future execution layer must separately handle tool registration,
authorization, execution boundaries, real results, and failures.

Provider-specific schema conversion belongs in the relevant provider
adapter, not in this vendor-neutral schema module.
