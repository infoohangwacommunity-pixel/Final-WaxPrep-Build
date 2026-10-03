from __future__ import annotations

import inspect
import unittest

from waxprep.model_client import (
    ImageContentBlock,
    ModelClient,
    ModelContractError,
    ModelMessage,
    ModelMessageRole,
    ModelRequest,
    ModelResponse,
    ModelSettings,
    ModelUsage,
    StopReason,
    TextContentBlock,
    ToolDefinition,
    ToolRequest,
)


class ModelContentBlockTests(unittest.TestCase):
    def test_text_content_block_accepts_text(self) -> None:
        block = TextContentBlock("Hello")
        self.assertEqual(block.text, "Hello")

    def test_text_content_block_rejects_non_string(self) -> None:
        with self.assertRaises(ModelContractError):
            TextContentBlock(123)  # type: ignore[arg-type]

    def test_image_content_block_accepts_uri_and_media_type(self) -> None:
        block = ImageContentBlock(
            uri="https://example.invalid/image.png",
            media_type="image/png",
        )
        self.assertEqual(block.uri, "https://example.invalid/image.png")
        self.assertEqual(block.media_type, "image/png")

    def test_image_content_block_rejects_empty_uri(self) -> None:
        with self.assertRaises(ModelContractError):
            ImageContentBlock(uri=" ")

    def test_image_content_block_rejects_empty_media_type(self) -> None:
        with self.assertRaises(ModelContractError):
            ImageContentBlock(uri="image-reference", media_type=" ")


class ModelMessageTests(unittest.TestCase):
    def test_message_accepts_text_and_image_blocks(self) -> None:
        message = ModelMessage(
            role=ModelMessageRole.USER,
            content=(
                TextContentBlock("Describe this image."),
                ImageContentBlock("https://example.invalid/image.png"),
            ),
        )

        self.assertEqual(message.role, ModelMessageRole.USER)
        self.assertEqual(len(message.content), 2)

    def test_message_rejects_non_normalized_role(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelMessage(
                role="user",  # type: ignore[arg-type]
                content=(TextContentBlock("Hello"),),
            )

    def test_message_rejects_list_instead_of_content_tuple(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelMessage(
                role=ModelMessageRole.USER,
                content=[TextContentBlock("Hello")],  # type: ignore[arg-type]
            )

    def test_tool_result_requires_tool_call_id(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelMessage(
                role=ModelMessageRole.TOOL,
                content=(TextContentBlock("Completed"),),
            )

    def test_non_tool_message_rejects_tool_call_id(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelMessage(
                role=ModelMessageRole.USER,
                content=(TextContentBlock("Hello"),),
                tool_call_id="call-1",
            )

    def test_only_assistant_message_can_contain_tool_requests(self) -> None:
        tool_request = ToolRequest(
            id="call-1",
            name="read_file",
            arguments={"path": "README.md"},
        )

        with self.assertRaises(ModelContractError):
            ModelMessage(
                role=ModelMessageRole.USER,
                content=(TextContentBlock("Read a file"),),
                tool_requests=(tool_request,),
            )

    def test_assistant_message_can_represent_prior_tool_request(self) -> None:
        tool_request = ToolRequest(
            id="call-1",
            name="read_file",
            arguments={"path": "README.md"},
        )

        message = ModelMessage(
            role=ModelMessageRole.ASSISTANT,
            content=(),
            tool_requests=(tool_request,),
        )

        self.assertEqual(message.tool_requests, (tool_request,))


class ToolContractTests(unittest.TestCase):
    def test_tool_definition_copies_and_protects_schema_mapping(self) -> None:
        schema = {"type": "object"}
        tool = ToolDefinition(
            name="read_file",
            description="Read a permitted file.",
            input_schema=schema,
        )

        schema["type"] = "string"

        self.assertEqual(tool.input_schema["type"], "object")

        with self.assertRaises(TypeError):
            tool.input_schema["type"] = "string"  # type: ignore[index]

    def test_tool_definition_rejects_empty_name(self) -> None:
        with self.assertRaises(ModelContractError):
            ToolDefinition(
                name=" ",
                description="Read a file.",
                input_schema={"type": "object"},
            )

    def test_tool_request_copies_and_protects_arguments(self) -> None:
        arguments = {"path": "README.md"}
        request = ToolRequest(
            id="call-1",
            name="read_file",
            arguments=arguments,
        )

        arguments["path"] = "changed.md"

        self.assertEqual(request.arguments["path"], "README.md")

        with self.assertRaises(TypeError):
            request.arguments["path"] = "changed.md"  # type: ignore[index]

    def test_tool_request_rejects_non_mapping_arguments(self) -> None:
        with self.assertRaises(ModelContractError):
            ToolRequest(
                id="call-1",
                name="read_file",
                arguments=[],  # type: ignore[arg-type]
            )


class ModelSettingsTests(unittest.TestCase):
    def test_default_settings_are_valid(self) -> None:
        settings = ModelSettings()

        self.assertIsNone(settings.temperature)
        self.assertIsNone(settings.top_p)
        self.assertIsNone(settings.max_output_tokens)
        self.assertEqual(settings.stop_sequences, ())

    def test_valid_settings_are_preserved(self) -> None:
        settings = ModelSettings(
            temperature=0.5,
            top_p=0.9,
            max_output_tokens=500,
            stop_sequences=("<END>",),
        )

        self.assertEqual(settings.temperature, 0.5)
        self.assertEqual(settings.top_p, 0.9)
        self.assertEqual(settings.max_output_tokens, 500)
        self.assertEqual(settings.stop_sequences, ("<END>",))

    def test_negative_temperature_is_rejected(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelSettings(temperature=-0.1)

    def test_non_finite_temperature_is_rejected(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelSettings(temperature=float("nan"))

    def test_invalid_top_p_is_rejected(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelSettings(top_p=0)

        with self.assertRaises(ModelContractError):
            ModelSettings(top_p=1.1)

    def test_invalid_max_output_tokens_is_rejected(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelSettings(max_output_tokens=0)

        with self.assertRaises(ModelContractError):
            ModelSettings(max_output_tokens=True)  # type: ignore[arg-type]

    def test_stop_sequences_must_be_non_empty_strings(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelSettings(stop_sequences=("",))

        with self.assertRaises(ModelContractError):
            ModelSettings(stop_sequences=["END"])  # type: ignore[arg-type]


class ModelRequestTests(unittest.TestCase):
    def _message(self) -> ModelMessage:
        return ModelMessage(
            role=ModelMessageRole.USER,
            content=(TextContentBlock("Hello"),),
        )

    def test_request_accepts_normalized_messages_and_tools(self) -> None:
        request = ModelRequest(
            messages=(self._message(),),
            tools=(
                ToolDefinition(
                    name="read_file",
                    description="Read a file.",
                    input_schema={"type": "object"},
                ),
            ),
            settings=ModelSettings(max_output_tokens=100),
        )

        self.assertEqual(len(request.messages), 1)
        self.assertEqual(len(request.tools), 1)
        self.assertEqual(request.settings.max_output_tokens, 100)

    def test_request_rejects_empty_messages(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelRequest(messages=())

    def test_request_rejects_duplicate_tool_names(self) -> None:
        tool = ToolDefinition(
            name="read_file",
            description="Read a file.",
            input_schema={"type": "object"},
        )

        with self.assertRaises(ModelContractError):
            ModelRequest(
                messages=(self._message(),),
                tools=(tool, tool),
            )

    def test_request_rejects_invalid_settings_type(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelRequest(
                messages=(self._message(),),
                settings={},  # type: ignore[arg-type]
            )


class ModelUsageTests(unittest.TestCase):
    def test_usage_can_be_unavailable(self) -> None:
        usage = ModelUsage()

        self.assertIsNone(usage.input_tokens)
        self.assertIsNone(usage.output_tokens)
        self.assertIsNone(usage.total_tokens)

    def test_usage_accepts_non_negative_counts(self) -> None:
        usage = ModelUsage(
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
        )

        self.assertEqual(usage.input_tokens, 10)
        self.assertEqual(usage.output_tokens, 20)
        self.assertEqual(usage.total_tokens, 30)

    def test_usage_rejects_negative_counts(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelUsage(input_tokens=-1)

    def test_usage_rejects_bool_as_token_count(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelUsage(input_tokens=True)  # type: ignore[arg-type]


class ModelResponseTests(unittest.TestCase):
    def test_response_accepts_text_and_usage(self) -> None:
        response = ModelResponse(
            content=(TextContentBlock("Hello back"),),
            stop_reason=StopReason.END_TURN,
            usage=ModelUsage(input_tokens=5, output_tokens=3, total_tokens=8),
        )

        self.assertEqual(response.content[0].text, "Hello back")
        self.assertEqual(response.stop_reason, StopReason.END_TURN)
        self.assertEqual(response.usage.total_tokens, 8)

    def test_response_accepts_tool_request_stop_reason(self) -> None:
        tool_request = ToolRequest(
            id="call-1",
            name="read_file",
            arguments={"path": "README.md"},
        )

        response = ModelResponse(
            content=(),
            stop_reason=StopReason.TOOL_REQUEST,
            tool_requests=(tool_request,),
        )

        self.assertEqual(response.tool_requests, (tool_request,))

    def test_tool_request_stop_reason_requires_tool_request(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelResponse(
                content=(),
                stop_reason=StopReason.TOOL_REQUEST,
            )

    def test_tool_requests_require_tool_request_stop_reason(self) -> None:
        tool_request = ToolRequest(
            id="call-1",
            name="read_file",
            arguments={},
        )

        with self.assertRaises(ModelContractError):
            ModelResponse(
                content=(),
                stop_reason=StopReason.END_TURN,
                tool_requests=(tool_request,),
            )

    def test_response_rejects_non_normalized_stop_reason(self) -> None:
        with self.assertRaises(ModelContractError):
            ModelResponse(
                content=(),
                stop_reason="finished",  # type: ignore[arg-type]
            )


class ModelClientInterfaceTests(unittest.TestCase):
    def test_model_client_is_a_protocol(self) -> None:
        self.assertTrue(getattr(ModelClient, "_is_protocol", False))

    def test_complete_is_declared_as_async(self) -> None:
        self.assertTrue(inspect.iscoroutinefunction(ModelClient.complete))


if __name__ == "__main__":
    unittest.main()
