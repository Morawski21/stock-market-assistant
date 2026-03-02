from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from app.prompts import SYSTEM_PROMPT
from utils.logger import get_logger

logger = get_logger(__name__)


class StockMarketChat:
    def __init__(self) -> None:
        self._options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            permission_mode="bypassPermissions",
            allowed_tools=["WebSearch", "WebFetch"],
        )
        self._client = ClaudeSDKClient(options=self._options)

    async def __aenter__(self) -> "StockMarketChat":
        await self._client.connect()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.disconnect()

    async def send(self, message: str) -> str:
        await self._client.query(message)
        parts: list[str] = []
        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
            elif isinstance(msg, ResultMessage) and msg.total_cost_usd is not None:
                logger.debug("cost: $%.4f", msg.total_cost_usd)
        return "".join(parts)
