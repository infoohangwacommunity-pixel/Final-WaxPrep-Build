"""Static type-checking fixture for structural ModelClient compatibility."""

from waxprep.model_client import (
    ModelClient,
    ModelRequest,
    ModelResponse,
    StopReason,
)


class CompatibleModelClient:
    """Example implementation used only to prove the protocol's type contract."""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content=(),
            stop_reason=StopReason.END_TURN,
        )


# mypy must accept this assignment without explicit inheritance from ModelClient.
COMPATIBLE_CLIENT: ModelClient = CompatibleModelClient()
