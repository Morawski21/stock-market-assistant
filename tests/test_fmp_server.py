"""Tests for the FMP MCP server tools."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from mcp_servers.fmp import (
    analyst_view,
    company_overview,
    financial_statements,
    historical_prices,
    search_company,
)


def _mock_client(spec: dict) -> MagicMock:
    """Build a MagicMock FMPDataClient with the given attribute tree."""
    client = MagicMock()
    for dotted_path, value in spec.items():
        parts = dotted_path.split(".")
        obj = client
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
    client.__enter__ = lambda s: s
    client.__exit__ = MagicMock(return_value=False)
    return client


@pytest.fixture()
def mock_profile():
    p = MagicMock()
    p.symbol = "AAPL"
    p.company_name = "Apple Inc."
    p.sector = "Technology"
    p.industry = "Consumer Electronics"
    p.exchange_short_name = "NASDAQ"
    p.ceo = "Tim Cook"
    p.full_time_employees = 150000
    p.description = "Apple designs consumer electronics."
    return p


@pytest.fixture()
def mock_quote():
    q = MagicMock()
    q.price = 200.0
    q.change = 1.0
    q.change_percentage = 0.5
    q.open_price = 199.0
    q.day_low = 198.0
    q.day_high = 202.0
    q.year_low = 150.0
    q.year_high = 230.0
    q.volume = 50_000_000
    q.market_cap = 3_000_000_000_000
    q.price_avg_50 = 195.0
    q.price_avg_200 = 185.0
    return q


@pytest.fixture()
def mock_metrics():
    m = MagicMock()
    m.earnings_yield_ttm = 0.04  # P/E = 25
    m.ev_to_ebitda_ttm = 20.0
    m.ev_to_free_cash_flow_ttm = 30.0
    m.free_cash_flow_yield_ttm = 0.03
    m.return_on_equity_ttm = 1.5
    m.return_on_invested_capital_ttm = 0.5
    m.return_on_assets_ttm = 0.3
    return m


def test_search_company_returns_symbols():
    result = MagicMock()
    result.symbol = "AAPL"
    result.name = "Apple Inc."
    result.exchange_short_name = "NASDAQ"
    result.sector = "Technology"

    client = _mock_client({"market.search_company": MagicMock(return_value=[result])})

    with patch("mcp_servers.fmp._client", return_value=client):
        output = json.loads(search_company("Apple"))

    assert len(output) == 1
    assert output[0]["symbol"] == "AAPL"
    assert output[0]["name"] == "Apple Inc."


def test_company_overview_includes_price_and_pe(mock_profile, mock_quote, mock_metrics):
    client = _mock_client(
        {
            "company.get_profile": MagicMock(return_value=mock_profile),
            "company.get_quote": MagicMock(return_value=mock_quote),
            "company.get_key_metrics_ttm": MagicMock(return_value=[mock_metrics]),
        }
    )

    with patch("mcp_servers.fmp._client", return_value=client):
        output = json.loads(company_overview("AAPL"))

    assert output["name"] == "Apple Inc."
    assert output["quote"]["price"] == 200.0
    assert output["key_metrics_ttm"]["pe_ratio"] == 25.0
    assert output["key_metrics_ttm"]["roe_pct"] == 150.0


def test_company_overview_handles_missing_metrics(mock_profile, mock_quote):
    client = _mock_client(
        {
            "company.get_profile": MagicMock(return_value=mock_profile),
            "company.get_quote": MagicMock(return_value=mock_quote),
            "company.get_key_metrics_ttm": MagicMock(return_value=[]),
        }
    )

    with patch("mcp_servers.fmp._client", return_value=client):
        output = json.loads(company_overview("AAPL"))

    assert "key_metrics_ttm" not in output
    assert output["quote"]["price"] == 200.0


def test_financial_statements_returns_all_three_sections():
    def _make_income():
        s = MagicMock()
        s.date = date(2024, 9, 30)
        s.period = "FY"
        s.revenue = 391_000_000_000
        s.gross_profit = 170_000_000_000
        s.operating_income = 120_000_000_000
        s.net_income = 100_000_000_000
        s.ebitda = 130_000_000_000
        s.eps = 6.5
        s.eps_diluted = 6.4
        return s

    def _make_balance():
        s = MagicMock()
        s.date = date(2024, 9, 30)
        s.total_assets = 350_000_000_000
        s.total_liabilities = 300_000_000_000
        s.total_equity = 50_000_000_000
        s.cash_and_cash_equivalents = 30_000_000_000
        s.total_debt = 100_000_000_000
        s.net_debt = 70_000_000_000
        return s

    def _make_cashflow():
        s = MagicMock()
        s.date = date(2024, 9, 30)
        s.operating_cash_flow = 110_000_000_000
        s.capital_expenditure = -10_000_000_000
        s.free_cash_flow = 100_000_000_000
        s.common_dividends_paid = -15_000_000_000
        s.common_stock_repurchased = -80_000_000_000
        return s

    client = _mock_client(
        {
            "fundamental.get_income_statement": MagicMock(
                return_value=[_make_income()]
            ),
            "fundamental.get_balance_sheet": MagicMock(return_value=[_make_balance()]),
            "fundamental.get_cash_flow": MagicMock(return_value=[_make_cashflow()]),
        }
    )

    with patch("mcp_servers.fmp._client", return_value=client):
        output = json.loads(financial_statements("AAPL"))

    assert len(output["income_statement"]) == 1
    assert output["income_statement"][0]["revenue"] == 391_000_000_000
    assert len(output["balance_sheet"]) == 1
    assert output["balance_sheet"][0]["net_debt"] == 70_000_000_000
    assert len(output["cash_flow"]) == 1
    assert output["cash_flow"][0]["free_cash_flow"] == 100_000_000_000


def test_analyst_view_returns_target_and_estimates():
    consensus = MagicMock()
    consensus.target_consensus = 250.0
    consensus.target_median = 260.0
    consensus.target_high = 300.0
    consensus.target_low = 200.0

    estimate = MagicMock()
    estimate.date = date(2025, 9, 30)
    estimate.estimated_revenue_avg = 420_000_000_000
    estimate.estimated_ebitda_avg = 140_000_000_000
    estimate.estimated_net_income_avg = 110_000_000_000
    estimate.estimated_eps_avg = 7.2
    estimate.estimated_eps_low = 6.8
    estimate.estimated_eps_high = 7.6
    estimate.number_analysts_estimated_eps = 30

    client = _mock_client(
        {
            "company.get_price_target_consensus": MagicMock(return_value=consensus),
            "company.get_analyst_estimates": MagicMock(return_value=[estimate]),
        }
    )

    with patch("mcp_servers.fmp._client", return_value=client):
        output = json.loads(analyst_view("AAPL"))

    assert output["price_target"]["consensus"] == 250.0
    assert len(output["forward_estimates"]) == 1
    assert output["forward_estimates"][0]["eps_avg"] == 7.2


def test_historical_prices_parses_dates_and_returns_ohlcv():
    entry = MagicMock()
    entry.date = date(2025, 1, 3)
    entry.open = 185.0
    entry.high = 190.0
    entry.low = 184.0
    entry.close = 188.0
    entry.volume = 60_000_000
    entry.change_percent = 1.6

    hist = MagicMock()
    hist.historical = [entry]

    client = _mock_client(
        {
            "company.get_historical_prices": MagicMock(return_value=hist),
        }
    )

    with patch("mcp_servers.fmp._client", return_value=client):
        output = json.loads(historical_prices("AAPL", "2025-01-01", "2025-01-10"))

    assert len(output) == 1
    assert output[0]["close"] == 188.0
    assert output[0]["date"] == "2025-01-03"
