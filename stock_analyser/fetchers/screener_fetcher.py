"""Screener.in data fetcher using web scraping."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from stock_analyser.config import Config
from stock_analyser.models import (
    BalanceSheetData,
    CashFlowData,
    FinancialPeriod,
    MarketSnapshot,
    PeerData,
    ReturnMetrics,
    ShareholdingData,
    StockData,
)

logger = logging.getLogger(__name__)


class ScreenerFetcher:
    """Fetches stock data from Screener.in via web scraping."""

    def __init__(self, config: Config):
        self.config = config
        self.headers = {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch(self, ticker: str, stock_data: StockData) -> StockData:
        """
        Fetch data from Screener.in and populate the stock_data object.

        Args:
            ticker: Screener.in company ticker (e.g., 'TMPV').
            stock_data: StockData object to populate.

        Returns:
            Updated StockData object.
        """
        # Strip exchange suffix for Screener (e.g., TMPV.NS -> TMPV)
        screener_ticker = ticker.split(".")[0]
        url = f"{self.config.screener_base_url}/company/{screener_ticker}/"

        logger.info(f"Fetching Screener.in data from {url}...")

        try:
            response = httpx.get(
                url,
                headers=self.headers,
                timeout=self.config.request_timeout,
                follow_redirects=True,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            stock_data.screener_available = True

            # Store raw text for AI
            stock_data.raw_screener_text = soup.get_text(separator="\n", strip=True)

            # Parse structured data
            self._parse_company_info(soup, stock_data)
            self._parse_top_ratios(soup, stock_data)
            self._parse_pros_cons(soup, stock_data)
            self._parse_annual_financials(soup, stock_data)
            self._parse_quarterly_financials(soup, stock_data)
            self._parse_balance_sheet(soup, stock_data)
            self._parse_cash_flows(soup, stock_data)
            self._parse_shareholding(soup, stock_data)
            self._parse_peers(soup, stock_data)
            self._parse_return_metrics(soup, stock_data)

            logger.info("Screener.in data fetched and parsed successfully.")

        except httpx.HTTPStatusError as e:
            error_msg = f"Screener.in HTTP error: {e.response.status_code} for {url}"
            logger.error(error_msg)
            stock_data.fetch_errors.append(error_msg)
        except Exception as e:
            error_msg = f"Screener.in fetch error: {e}"
            logger.error(error_msg)
            stock_data.fetch_errors.append(error_msg)

        return stock_data

    def _parse_number(self, text: str | None) -> float | None:
        """Parse a number from text, handling commas and percentage signs."""
        if not text:
            return None
        text = text.strip().replace(",", "").replace("%", "").replace("₹", "")
        text = text.strip()
        if not text or text == "--" or text == "—":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _parse_company_info(self, soup: BeautifulSoup, stock_data: StockData) -> None:
        """Parse company name and description."""
        name_tag = soup.find("h1")
        if name_tag:
            stock_data.company_name = stock_data.company_name or name_tag.get_text(
                strip=True
            )

        desc_tag = soup.find("div", class_="company-profile")
        if not desc_tag:
            desc_tag = soup.find("div", class_="about")
        if desc_tag:
            p_tag = desc_tag.find("p")
            if p_tag:
                stock_data.screener_description = p_tag.get_text(strip=True)

    def _parse_top_ratios(self, soup: BeautifulSoup, stock_data: StockData) -> None:
        """Parse the top-level ratio boxes (Market Cap, P/E, Book Value, etc.)."""
        top_ratios = soup.find("div", id="top-ratios")
        if not top_ratios:
            top_ratios = soup.find("ul", id="top-ratios")
        if not top_ratios:
            return

        ratio_items = top_ratios.find_all("li")
        snapshot = MarketSnapshot()

        for item in ratio_items:
            name_tag = item.find("span", class_="name")
            value_tag = item.find("span", class_="value") or item.find(
                "span", class_="number"
            )
            if not name_tag or not value_tag:
                continue

            name = name_tag.get_text(strip=True).lower()
            value_text = value_tag.get_text(strip=True)

            if "market cap" in name:
                snapshot.market_cap = value_text
            elif "current price" in name or "stock p/e" in name:
                if "p/e" in name:
                    snapshot.pe_ratio = self._parse_number(value_text)
                else:
                    snapshot.price = self._parse_number(value_text)
            elif "book value" in name:
                snapshot.book_value = self._parse_number(value_text)
            elif "dividend" in name:
                snapshot.dividend_yield = self._parse_number(value_text)
            elif "face value" in name:
                snapshot.face_value = self._parse_number(value_text)
            elif "p/e" in name:
                snapshot.pe_ratio = self._parse_number(value_text)

        # Try to get price from a different location if not found
        if not snapshot.price:
            price_tag = soup.find("span", id="stock-price-value")
            if not price_tag:
                price_tag = soup.find("div", class_="current-price")
            if price_tag:
                snapshot.price = self._parse_number(price_tag.get_text(strip=True))

        stock_data.screener_snapshot = snapshot

    def _parse_pros_cons(self, soup: BeautifulSoup, stock_data: StockData) -> None:
        """Parse pros and cons sections."""
        pros_section = soup.find("div", class_="pros")
        if pros_section:
            for li in pros_section.find_all("li"):
                text = li.get_text(strip=True)
                if text:
                    stock_data.screener_pros.append(text)

        cons_section = soup.find("class_", "cons")
        if not cons_section:
            cons_section = soup.find("div", class_="cons")
        if cons_section:
            for li in cons_section.find_all("li"):
                text = li.get_text(strip=True)
                if text:
                    stock_data.screener_cons.append(text)

    def _parse_table_data(
        self, soup: BeautifulSoup, section_id: str
    ) -> tuple[list[str], list[list[str]]]:
        """Parse a data table from a Screener section. Returns (headers, rows)."""
        section = soup.find("section", id=section_id)
        if not section:
            return [], []

        table = section.find("table")
        if not table:
            return [], []

        # Parse headers
        headers = []
        thead = table.find("thead")
        if thead:
            for th in thead.find_all("th"):
                headers.append(th.get_text(strip=True))

        # Parse rows
        rows = []
        tbody = table.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                row = [td.get_text(strip=True) for td in tr.find_all("td")]
                if row:
                    rows.append(row)

        return headers, rows

    def _parse_annual_financials(
        self, soup: BeautifulSoup, stock_data: StockData
    ) -> None:
        """Parse annual profit & loss data."""
        headers, rows = self._parse_table_data(soup, "profit-loss")
        if not headers:
            return

        periods = headers[1:]  # First header is the row label

        # Map row labels to fields
        row_map: dict[str, list[str]] = {}
        for row in rows:
            if row:
                label = row[0].lower().strip()
                row_map[label] = row[1:]

        for i, period in enumerate(periods):
            fp = FinancialPeriod(period=period)
            for label, values in row_map.items():
                if i < len(values):
                    val = self._parse_number(values[i])
                    if "sales" in label or "revenue" in label:
                        fp.sales = val
                    elif "operating profit" in label:
                        fp.operating_profit = val
                    elif "opm" in label:
                        fp.opm = val
                    elif "net profit" in label:
                        fp.net_profit = val
                    elif "other income" in label:
                        fp.other_income = val
                    elif "interest" in label:
                        fp.interest = val
                    elif "depreciation" in label:
                        fp.depreciation = val
                    elif "tax" in label:
                        fp.tax = val

            stock_data.annual_financials.append(fp)

    def _parse_quarterly_financials(
        self, soup: BeautifulSoup, stock_data: StockData
    ) -> None:
        """Parse quarterly results data."""
        headers, rows = self._parse_table_data(soup, "quarters")
        if not headers:
            return

        periods = headers[1:]
        row_map: dict[str, list[str]] = {}
        for row in rows:
            if row:
                label = row[0].lower().strip()
                row_map[label] = row[1:]

        for i, period in enumerate(periods):
            fp = FinancialPeriod(period=period)
            for label, values in row_map.items():
                if i < len(values):
                    val = self._parse_number(values[i])
                    if "sales" in label or "revenue" in label:
                        fp.sales = val
                    elif "operating profit" in label:
                        fp.operating_profit = val
                    elif "opm" in label:
                        fp.opm = val
                    elif "net profit" in label:
                        fp.net_profit = val

            stock_data.quarterly_financials.append(fp)

    def _parse_balance_sheet(
        self, soup: BeautifulSoup, stock_data: StockData
    ) -> None:
        """Parse balance sheet data."""
        headers, rows = self._parse_table_data(soup, "balance-sheet")
        if not headers:
            return

        periods = headers[1:]
        row_map: dict[str, list[str]] = {}
        for row in rows:
            if row:
                label = row[0].lower().strip()
                row_map[label] = row[1:]

        for i, period in enumerate(periods):
            bs = BalanceSheetData(period=period)
            for label, values in row_map.items():
                if i < len(values):
                    val = self._parse_number(values[i])
                    if "equity" in label and "share" not in label:
                        bs.total_equity = val
                    elif "borrowing" in label:
                        bs.total_borrowings = val
                    elif "total liabilities" in label:
                        bs.total_liabilities = val
                    elif "total assets" in label:
                        bs.total_assets = val
                    elif "reserves" in label:
                        bs.reserves = val
                    elif "fixed assets" in label:
                        bs.fixed_assets = val

            stock_data.balance_sheet.append(bs)

    def _parse_cash_flows(self, soup: BeautifulSoup, stock_data: StockData) -> None:
        """Parse cash flow data."""
        headers, rows = self._parse_table_data(soup, "cash-flow")
        if not headers:
            return

        periods = headers[1:]
        row_map: dict[str, list[str]] = {}
        for row in rows:
            if row:
                label = row[0].lower().strip()
                row_map[label] = row[1:]

        for i, period in enumerate(periods):
            cf = CashFlowData(period=period)
            for label, values in row_map.items():
                if i < len(values):
                    val = self._parse_number(values[i])
                    if "operating" in label and "cash" in label:
                        cf.operating_cash_flow = val
                    elif "investing" in label:
                        cf.investing_cash_flow = val
                    elif "financing" in label:
                        cf.financing_cash_flow = val
                    elif "net cash" in label:
                        cf.net_cash_flow = val

            stock_data.cash_flows.append(cf)

    def _parse_shareholding(
        self, soup: BeautifulSoup, stock_data: StockData
    ) -> None:
        """Parse shareholding pattern data."""
        headers, rows = self._parse_table_data(soup, "shareholding")
        if not headers:
            return

        periods = headers[1:]
        row_map: dict[str, list[str]] = {}
        for row in rows:
            if row:
                label = row[0].lower().strip()
                row_map[label] = row[1:]

        for i, period in enumerate(periods):
            sh = ShareholdingData(period=period)
            for label, values in row_map.items():
                if i < len(values):
                    val = self._parse_number(values[i])
                    if "promoter" in label:
                        sh.promoter_holding = val
                    elif "fii" in label or "foreign" in label:
                        sh.fii_holding = val
                    elif "dii" in label or "mutual" in label or "domestic" in label:
                        sh.dii_holding = val
                    elif "public" in label:
                        sh.public_holding = val

            stock_data.shareholding.append(sh)

    def _parse_peers(self, soup: BeautifulSoup, stock_data: StockData) -> None:
        """Parse peer comparison table."""
        peer_section = soup.find("section", id="peers")
        if not peer_section:
            return

        table = peer_section.find("table")
        if not table:
            return

        thead = table.find("thead")
        if not thead:
            return

        # Get column headers to find relevant columns
        headers = [th.get_text(strip=True).lower() for th in thead.find_all("th")]

        tbody = table.find("tbody")
        if not tbody:
            return

        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if not cells:
                continue

            peer = PeerData()
            for i, cell in enumerate(cells):
                if i >= len(headers):
                    break
                header = headers[i]
                text = cell.get_text(strip=True)

                if i == 0 or "name" in header or "company" in header:
                    # First column or name column
                    link = cell.find("a")
                    peer.name = link.get_text(strip=True) if link else text
                elif "p/e" in header:
                    peer.pe_ratio = self._parse_number(text)
                elif "market cap" in header or "mar cap" in header:
                    peer.market_cap = text
                elif "roce" in header:
                    peer.roce = self._parse_number(text)
                elif "roe" in header:
                    peer.roe = self._parse_number(text)
                elif "price" in header or "cmp" in header:
                    peer.price = self._parse_number(text)

            if peer.name:
                stock_data.peers.append(peer)

    def _parse_return_metrics(
        self, soup: BeautifulSoup, stock_data: StockData
    ) -> None:
        """Parse ROE, ROCE, and growth metrics from the page."""
        text = stock_data.raw_screener_text

        rm = ReturnMetrics()

        # Try to find key metrics using regex on the full page text
        patterns = {
            "roe": r"ROE\s*[:=]?\s*([\d.]+)\s*%",
            "roce": r"ROCE\s*[:=]?\s*([\d.]+)\s*%",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                setattr(rm, key, float(match.group(1)))

        # Look for compounded growth metrics
        growth_patterns = {
            "sales_growth_3yr": r"Compounded Sales Growth.*?3 Years?\s*[:=]?\s*([\d.]+)\s*%",
            "sales_growth_5yr": r"Compounded Sales Growth.*?5 Years?\s*[:=]?\s*([\d.]+)\s*%",
            "profit_growth_3yr": r"Compounded Profit Growth.*?3 Years?\s*[:=]?\s*([\d.]+)\s*%",
            "profit_growth_5yr": r"Compounded Profit Growth.*?5 Years?\s*[:=]?\s*([\d.]+)\s*%",
            "roe_3yr": r"Return on Equity.*?3 Years?\s*[:=]?\s*([\d.]+)\s*%",
            "roe_5yr": r"Return on Equity.*?5 Years?\s*[:=]?\s*([\d.]+)\s*%",
        }

        for key, pattern in growth_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                setattr(rm, key, float(match.group(1)))

        stock_data.return_metrics = rm
