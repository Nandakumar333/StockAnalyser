"""Yahoo Finance data fetcher using yfinance library."""

import logging

import yfinance as yf

from stock_analyser.models import MarketSnapshot, StockData

logger = logging.getLogger(__name__)


class YahooFinanceFetcher:
    """Fetches stock data from Yahoo Finance using yfinance."""

    def fetch(self, ticker: str, stock_data: StockData) -> StockData:
        """
        Fetch data from Yahoo Finance and populate the stock_data object.

        Args:
            ticker: Yahoo Finance ticker symbol (e.g., 'TMPV.NS' for NSE stocks).
            stock_data: StockData object to populate.

        Returns:
            Updated StockData object.
        """
        logger.info(f"Fetching Yahoo Finance data for {ticker}...")

        try:
            info = self._fetch_ticker_info(ticker)
            if not info:
                stock_data.fetch_errors.append(
                    f"Yahoo Finance: No data returned for {ticker}"
                )
                return stock_data

            stock_data.yahoo_available = True
            stock_data.company_name = info.get("longName", "") or info.get(
                "shortName", ticker
            )
            stock_data.yahoo_description = info.get("longBusinessSummary", "")
            stock_data.yahoo_sector = info.get("sector", "")
            stock_data.yahoo_industry = info.get("industry", "")

            stock_data.yahoo_snapshot = self._build_snapshot(info)

            # Build raw text summary for AI
            stock_data.raw_yahoo_text = self._build_raw_text(info)

            logger.info(
                f"Yahoo Finance data fetched successfully for {stock_data.company_name}"
            )

        except Exception as e:
            error_msg = f"Yahoo Finance fetch error: {e}"
            logger.error(error_msg)
            stock_data.fetch_errors.append(error_msg)

        return stock_data

    def _fetch_ticker_info(self, ticker: str) -> dict:
        """Fetch ticker info from yfinance."""
        t = yf.Ticker(ticker)
        return t.info or {}

    def _build_snapshot(self, info: dict) -> MarketSnapshot:
        """Build MarketSnapshot from yfinance info dict."""
        market_cap_raw = info.get("marketCap")
        if market_cap_raw:
            if market_cap_raw >= 1e12:
                market_cap_str = f"Rs {market_cap_raw / 1e12:.3f}T"
            elif market_cap_raw >= 1e9:
                market_cap_str = f"Rs {market_cap_raw / 1e9:.2f}B"
            elif market_cap_raw >= 1e7:
                market_cap_str = f"Rs {market_cap_raw / 1e7:.0f} Cr"
            else:
                market_cap_str = f"Rs {market_cap_raw:,.0f}"
        else:
            market_cap_str = None

        return MarketSnapshot(
            price=info.get("currentPrice") or info.get("regularMarketPrice"),
            market_cap=market_cap_str,
            pe_ratio=info.get("trailingPE"),
            pb_ratio=info.get("priceToBook"),
            forward_pe=info.get("forwardPE"),
            ev_ebitda=info.get("enterpriseToEbitda"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            dividend_yield=(
                round(info.get("dividendYield", 0) * 100, 2)
                if info.get("dividendYield")
                else None
            ),
            beta=info.get("beta"),
            eps=info.get("trailingEps"),
            book_value=info.get("bookValue"),
            week_52_high=info.get("fiftyTwoWeekHigh"),
            week_52_low=info.get("fiftyTwoWeekLow"),
            one_year_return=None,  # Not directly in yfinance info
            target_price=info.get("targetMeanPrice"),
        )

    def _build_raw_text(self, info: dict) -> str:
        """Build a raw text summary from all available yfinance fields."""
        lines = ["Yahoo Finance Key Data:"]
        important_keys = [
            "longName",
            "sector",
            "industry",
            "currentPrice",
            "marketCap",
            "trailingPE",
            "forwardPE",
            "priceToBook",
            "priceToSalesTrailing12Months",
            "enterpriseToEbitda",
            "enterpriseToRevenue",
            "profitMargins",
            "operatingMargins",
            "grossMargins",
            "returnOnEquity",
            "returnOnAssets",
            "revenueGrowth",
            "earningsGrowth",
            "totalRevenue",
            "totalDebt",
            "totalCash",
            "debtToEquity",
            "freeCashflow",
            "operatingCashflow",
            "dividendYield",
            "dividendRate",
            "payoutRatio",
            "beta",
            "trailingEps",
            "forwardEps",
            "bookValue",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "targetMeanPrice",
            "targetHighPrice",
            "targetLowPrice",
            "recommendationKey",
            "numberOfAnalystOpinions",
            "sharesOutstanding",
            "floatShares",
            "heldPercentInsiders",
            "heldPercentInstitutions",
        ]
        for key in important_keys:
            val = info.get(key)
            if val is not None:
                lines.append(f"  {key}: {val}")

        return "\n".join(lines)
