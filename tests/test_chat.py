import inspect

from app.chat import StockMarketChat


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
