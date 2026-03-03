import asyncio
import os

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from dotenv import load_dotenv

from app.prompts import SYSTEM_PROMPT
from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

_SPINNER_FRAMES = ["|", "/", "-", "\\"]
_SPINNER_WIDTH = 40  # chars to clear when erasing the spinner line


async def _spin() -> None:
    i = 0
    while True:
        print(f"\r{_SPINNER_FRAMES[i % 4]} thinking...", end="", flush=True)
        i += 1
        await asyncio.sleep(0.12)


def _clear_line() -> None:
    print("\r" + " " * _SPINNER_WIDTH + "\r", end="", flush=True)


def _format_input(tool_input: dict) -> str:
    for key in ("query", "url", "command", "prompt"):
        if key in tool_input:
            value = str(tool_input[key])
            return value[:70] + "..." if len(value) > 70 else value
    for value in tool_input.values():
        if isinstance(value, str):
            return value[:70] + "..." if len(value) > 70 else value
    return ""


class StockMarketChat:
    def __init__(self) -> None:
        fmp_key = os.environ["FMP_API_KEY"]
        self._options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            permission_mode="bypassPermissions",
            allowed_tools=["WebSearch", "WebFetch", "mcp__fmp__*"],
            mcp_servers={
                "fmp": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "mcp_servers.fmp"],
                    "env": {"FMP_API_KEY": fmp_key},
                }
            },
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
        spinner = asyncio.create_task(_spin())
        try:
            async for msg in self._client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, ToolUseBlock):
                            _clear_line()
                            desc = _format_input(block.input)
                            if desc:
                                logger.info("[tool] %s — %s", block.name, desc)
                            else:
                                logger.info("[tool] %s", block.name)
                        elif isinstance(block, TextBlock):
                            parts.append(block.text)
                elif isinstance(msg, ResultMessage) and msg.total_cost_usd is not None:
                    logger.debug("cost: $%.4f", msg.total_cost_usd)
        finally:
            spinner.cancel()
            try:
                await spinner
            except asyncio.CancelledError:
                pass
            _clear_line()
        return "".join(parts)
