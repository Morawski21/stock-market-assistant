"""FMP MCP server — exposes Financial Modeling Prep data as focused report tools."""

import json
import os
from datetime import datetime

from fmp_data import FMPDataClient
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fmp")


def _client() -> FMPDataClient:
    return FMPDataClient(api_key=os.environ["FMP_API_KEY"])


@mcp.tool()
def search_company(query: str) -> str:
    """Find a company's ticker symbol by name or keyword. Returns top matches."""
    with _client() as c:
        results = c.market.search_company(query=query, limit=5)
    return json.dumps(
        [
            {
                "symbol": r.symbol,
                "name": r.name,
                "exchange": r.exchange_short_name,
                "sector": r.sector,
            }
            for r in results
        ]
    )


@mcp.tool()
def company_overview(symbol: str) -> str:
    """
    Get a complete company snapshot: profile, live quote, and key TTM metrics.
    Returns sector, description, price, market cap, valuation ratios, and returns.
    """
    with _client() as c:
        profile = c.company.get_profile(symbol.upper())
        quote = c.company.get_quote(symbol.upper())
        metrics_list = c.company.get_key_metrics_ttm(symbol.upper())

    metrics = metrics_list[0] if metrics_list else None

    data: dict = {
        "symbol": profile.symbol,
        "name": profile.company_name,
        "sector": profile.sector,
        "industry": profile.industry,
        "exchange": profile.exchange_short_name,
        "ceo": profile.ceo,
        "employees": profile.full_time_employees,
        "description": profile.description,
        "quote": {
            "price": quote.price,
            "change": quote.change,
            "change_pct": quote.change_percentage,
            "open": quote.open_price,
            "day_low": quote.day_low,
            "day_high": quote.day_high,
            "year_low": quote.year_low,
            "year_high": quote.year_high,
            "volume": quote.volume,
            "market_cap": quote.market_cap,
            "avg_50d": quote.price_avg_50,
            "avg_200d": quote.price_avg_200,
        },
    }

    if metrics:

        def _pct(v: float | None) -> float | None:
            return round(v * 100, 2) if v is not None else None

        def _round(v: float | None) -> float | None:
            return round(v, 2) if v is not None else None

        earnings_yield = metrics.earnings_yield_ttm
        data["key_metrics_ttm"] = {
            "pe_ratio": _round(1 / earnings_yield) if earnings_yield else None,
            "ev_ebitda": _round(metrics.ev_to_ebitda_ttm),
            "ev_fcf": _round(metrics.ev_to_free_cash_flow_ttm),
            "fcf_yield_pct": _pct(metrics.free_cash_flow_yield_ttm),
            "roe_pct": _pct(metrics.return_on_equity_ttm),
            "roic_pct": _pct(metrics.return_on_invested_capital_ttm),
            "roa_pct": _pct(metrics.return_on_assets_ttm),
        }

    return json.dumps(data)


@mcp.tool()
def financial_statements(symbol: str, period: str = "annual", limit: int = 3) -> str:
    """
    Get income statement, balance sheet, and cash flow for a company.
    period: 'annual' or 'quarter'. limit: number of periods (default 3).
    """
    with _client() as c:
        income = c.fundamental.get_income_statement(
            symbol.upper(), period=period, limit=limit
        )
        balance = c.fundamental.get_balance_sheet(
            symbol.upper(), period=period, limit=limit
        )
        cashflow = c.fundamental.get_cash_flow(
            symbol.upper(), period=period, limit=limit
        )

    def _date(s: object) -> str:
        return str(getattr(s, "date", ""))[:10]

    return json.dumps(
        {
            "income_statement": [
                {
                    "date": _date(s),
                    "period": s.period,
                    "revenue": s.revenue,
                    "gross_profit": s.gross_profit,
                    "operating_income": s.operating_income,
                    "net_income": s.net_income,
                    "ebitda": s.ebitda,
                    "eps": s.eps,
                    "eps_diluted": s.eps_diluted,
                }
                for s in income
            ],
            "balance_sheet": [
                {
                    "date": _date(s),
                    "total_assets": s.total_assets,
                    "total_liabilities": s.total_liabilities,
                    "total_equity": s.total_equity,
                    "cash": s.cash_and_cash_equivalents,
                    "total_debt": s.total_debt,
                    "net_debt": s.net_debt,
                }
                for s in balance
            ],
            "cash_flow": [
                {
                    "date": _date(s),
                    "operating_cash_flow": s.operating_cash_flow,
                    "capex": s.capital_expenditure,
                    "free_cash_flow": s.free_cash_flow,
                    "dividends_paid": s.common_dividends_paid,
                    "stock_repurchased": s.common_stock_repurchased,
                }
                for s in cashflow
            ],
        }
    )


@mcp.tool()
def analyst_view(symbol: str) -> str:
    """
    Get analyst price targets and forward EPS/revenue estimates.
    Returns consensus target, estimate range, and forward projections.
    """
    with _client() as c:
        consensus = c.company.get_price_target_consensus(symbol.upper())
        estimates = c.company.get_analyst_estimates(symbol.upper())

    return json.dumps(
        {
            "price_target": {
                "consensus": consensus.target_consensus,
                "median": consensus.target_median,
                "high": consensus.target_high,
                "low": consensus.target_low,
            },
            "forward_estimates": [
                {
                    "date": str(e.date)[:10],
                    "revenue_avg": e.estimated_revenue_avg,
                    "ebitda_avg": e.estimated_ebitda_avg,
                    "net_income_avg": e.estimated_net_income_avg,
                    "eps_avg": e.estimated_eps_avg,
                    "eps_low": e.estimated_eps_low,
                    "eps_high": e.estimated_eps_high,
                    "num_analysts": e.number_analysts_estimated_eps,
                }
                for e in estimates[:3]
            ],
        }
    )


@mcp.tool()
def historical_prices(symbol: str, from_date: str, to_date: str) -> str:
    """
    Get daily OHLCV price history for a symbol.
    from_date and to_date must be in YYYY-MM-DD format.
    Useful for calculating returns, spotting trends, and studying volatility.
    """
    start = datetime.strptime(from_date, "%Y-%m-%d").date()
    end = datetime.strptime(to_date, "%Y-%m-%d").date()

    with _client() as c:
        data = c.company.get_historical_prices(
            symbol.upper(), from_date=start, to_date=end
        )

    return json.dumps(
        [
            {
                "date": str(e.date)[:10],
                "open": e.open,
                "high": e.high,
                "low": e.low,
                "close": e.close,
                "volume": e.volume,
                "change_pct": e.change_percent,
            }
            for e in data.historical
        ]
    )


if __name__ == "__main__":
    mcp.run()
