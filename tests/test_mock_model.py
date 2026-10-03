from __future__ import annotations

import unittest

from waxprep.mock_model import (
    MockModelScriptExhaustedError,
    ScriptedModelClient,
    model_script,
    text_response,
    tool_request_response,
)
from waxprep.model_client import (
    ModelMessage,
    ModelMessageRole,
    ModelRequest,
    ModelResponse,
    StopReason,
    TextContentBlock,
    ToolRequest,
)


def make_request(text: str = "Hello") -> ModelRequest:
    """Build a small valid model request for mock-client tests."""

    return ModelRequest(
        messages=(
            ModelMessage(
                role=ModelMessageRole.USER,
                content=(TextContentBlock(text),),
            ),
        ),
    )


class ScriptedModelClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_scripted_text_response(self) -> None:
        expected = text_response("Hello back")
        client = ScriptedModelClient(model_script(expected))

        actual = await client.complete(make_request())

        self.assertEqual(actual, expected)
        self.assertEqual(client.remaining_steps, 0)

    async def test_returns_responses_in_script_order(self) -> None:
        first = text_response("First")
        second = text_response("Second")
        client = ScriptedModelClient(model_script(first, second))

        actual_first = await client.complete(make_request("One"))
        actual_second = await client.complete(make_request("Two"))

        self.assertEqual(actual_first, first)
        self.assertEqual(actual_second, second)
        self.assertEqual(client.remaining_steps, 0)

    async def test_records_requests_in_order(self) -> None:
        client = ScriptedModelClient(
            model_script(text_response("First"), text_response("Second"))
        )
        first_request = make_request("One")
        second_request = make_request("Two")

        await client.complete(first_request)
        await client.complete(second_request)

        self.assertEqual(client.requests, (first_request, second_request))

    async def test_requests_property_is_an_immutable_snapshot(self) -> None:
        client = ScriptedModelClient(model_script(text_response("Done")))

        before = client.requests
        await client.complete(make_request())

        self.assertEqual(before, ())
        self.assertEqual(len(client.requests), 1)

    async def test_returns_tool_request_response(self) -> None:
        tool_request = ToolRequest(
            id="call-1",
            name="example_tool",
            arguments={"value": 7},
        )
        expected = tool_request_response(tool_request)
        client = ScriptedModelClient(model_script(expected))

        actual = await client.complete(make_request())

        self.assertEqual(actual.stop_reason, StopReason.TOOL_REQUEST)
        self.assertEqual(actual.tool_requests, (tool_request,))
        self.assertEqual(actual, expected)

    async def test_raises_scripted_exception(self) -> None:
        client = ScriptedModelClient(model_script(ValueError("scripted failure")))

        with self.assertRaisesRegex(ValueError, "scripted failure"):
            await client.complete(make_request())

        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.remaining_steps, 0)

    async def test_can_script_error_then_success(self) -> None:
        expected = text_response("Recovered")
        client = ScriptedModelClient(
            model_script(RuntimeError("temporary failure"), expected)
        )

        with self.assertRaisesRegex(RuntimeError, "temporary failure"):
            await client.complete(make_request("First attempt"))

        actual = await client.complete(make_request("Second attempt"))

        self.assertEqual(actual, expected)
        self.assertEqual(len(client.requests), 2)

    async def test_exhausted_script_raises_clear_error(self) -> None:
        client = ScriptedModelClient(model_script(text_response("Only response")))

        await client.complete(make_request())

        with self.assertRaises(MockModelScriptExhaustedError):
            await client.complete(make_request())

        self.assertEqual(len(client.requests), 2)

    async def test_empty_script_is_allowed_but_exhausted_on_first_call(self) -> None:
        client = ScriptedModelClient(model_script())

        self.assertEqual(client.remaining_steps, 0)

        with self.assertRaises(MockModelScriptExhaustedError):
            await client.complete(make_request())

    async def test_script_helper_returns_immutable_tuple(self) -> None:
        response = text_response("Hello")

        script = model_script(response)

        self.assertIsInstance(script, tuple)
        self.assertEqual(script, (response,))

    async def test_script_helper_rejects_invalid_step(self) -> None:
        with self.assertRaisesRegex(TypeError, "Script step 0"):
            model_script("not a response")  # type: ignore[arg-type]

    async def test_tool_response_helper_requires_a_tool_request(self) -> None:
        with self.assertRaisesRegex(ValueError, "At least one"):
            tool_request_response()

    async def test_mock_obeys_model_client_contract(self) -> None:
        client: object = ScriptedModelClient(model_script(text_response("Hello")))
        self.assertTrue(callable(getattr(client, "complete", None)))


class MockModelHelperTests(unittest.TestCase):
    def test_text_helper_preserves_empty_text_if_contract_allows_it(self) -> None:
        response = text_response("")

        self.assertEqual(response.content, (TextContentBlock(""),))
        self.assertEqual(response.stop_reason, StopReason.END_TURN)

    def test_tool_helper_can_include_content(self) -> None:
        request = ToolRequest(
            id="call-2",
            name="example_tool",
            arguments={},
        )

        response = tool_request_response(
            request,
            content=(TextContentBlock("Requesting an action"),),
        )

        self.assertEqual(response.content, (TextContentBlock("Requesting an action"),))
        self.assertEqual(response.tool_requests, (request,))

    def test_script_step_types_match_contract(self) -> None:
        response = ModelResponse(
            content=(TextContentBlock("Done"),),
            stop_reason=StopReason.END_TURN,
        )

        client = ScriptedModelClient(model_script(response))

        self.assertEqual(client.remaining_steps, 1)


if __name__ == "__main__":
    unittest.main()
