import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock

from app.chat import StockMarketChat, _format_input


def test_chat_can_be_instantiated():
    chat = StockMarketChat()
    assert isinstance(chat, StockMarketChat)


def test_chat_options_bypass_permissions():
    chat = StockMarketChat()
    assert chat._options.permission_mode == "bypassPermissions"


def test_chat_options_allow_web_tools():
    chat = StockMarketChat()
    assert "WebSearch" in chat._options.allowed_tools
    assert "WebFetch" in chat._options.allowed_tools


def test_chat_is_async_context_manager():
    chat = StockMarketChat()
    assert inspect.iscoroutinefunction(chat.__aenter__)
    assert inspect.iscoroutinefunction(chat.__aexit__)


def test_chat_send_is_coroutine():
    chat = StockMarketChat()
    assert inspect.iscoroutinefunction(chat.send)


def test_format_input_extracts_query():
    assert _format_input({"query": "Micron stock"}) == "Micron stock"


def test_format_input_extracts_url():
    assert _format_input({"url": "https://example.com"}) == "https://example.com"


def test_format_input_truncates_long_values():
    long = "x" * 100
    result = _format_input({"query": long})
    assert result.endswith("...")
    assert len(result) <= 73  # 70 chars + "..."


def test_format_input_returns_empty_for_empty_dict():
    assert _format_input({}) == ""


async def _make_async_gen(*items):
    for item in items:
        yield item


async def _noop_spin():
    await asyncio.sleep(0)


def _make_assistant_message(*blocks):
    msg = MagicMock(spec=AssistantMessage)
    msg.content = list(blocks)
    return msg


def _make_text_block(text: str):
    block = MagicMock(spec=TextBlock)
    block.text = text
    return block


def _make_tool_use_block(name: str, tool_input: dict | None = None):
    block = MagicMock(spec=ToolUseBlock)
    block.name = name
    block.input = tool_input or {}
    return block


@pytest.mark.asyncio
async def test_send_returns_text_from_response():
    chat = StockMarketChat()
    text_block = _make_text_block("hello world")
    msg = _make_assistant_message(text_block)

    chat._client.query = AsyncMock()
    chat._client.receive_response = MagicMock(return_value=_make_async_gen(msg))

    with patch("app.chat._spin", new=_noop_spin):
        result = await chat.send("hi")

    assert result == "hello world"


@pytest.mark.asyncio
async def test_send_logs_tool_name_without_description_when_input_empty():
    chat = StockMarketChat()
    tool_block = _make_tool_use_block("WebSearch", {})
    text_block = _make_text_block("found something")
    msg = _make_assistant_message(tool_block, text_block)

    chat._client.query = AsyncMock()
    chat._client.receive_response = MagicMock(return_value=_make_async_gen(msg))

    with (
        patch("app.chat._spin", new=_noop_spin),
        patch("app.chat.logger") as mock_logger,
    ):
        result = await chat.send("search for X")

    assert result == "found something"
    mock_logger.info.assert_called_once_with("[tool] %s", "WebSearch")


@pytest.mark.asyncio
async def test_send_logs_tool_name_with_description_when_input_present():
    chat = StockMarketChat()
    tool_block = _make_tool_use_block("WebSearch", {"query": "Micron stock price"})
    msg = _make_assistant_message(tool_block, _make_text_block("result"))

    chat._client.query = AsyncMock()
    chat._client.receive_response = MagicMock(return_value=_make_async_gen(msg))

    with (
        patch("app.chat._spin", new=_noop_spin),
        patch("app.chat.logger") as mock_logger,
    ):
        await chat.send("search for X")

    mock_logger.info.assert_called_once_with(
        "[tool] %s — %s", "WebSearch", "Micron stock price"
    )


@pytest.mark.asyncio
async def test_send_concatenates_multiple_text_blocks():
    chat = StockMarketChat()
    msg = _make_assistant_message(_make_text_block("part1"), _make_text_block("part2"))

    chat._client.query = AsyncMock()
    chat._client.receive_response = MagicMock(return_value=_make_async_gen(msg))

    with patch("app.chat._spin", new=_noop_spin):
        result = await chat.send("hi")

    assert result == "part1part2"
