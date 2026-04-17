"""Fetcher for parsing local Zerodha portfolio excel files."""

import logging
from pathlib import Path

import pandas as pd

from stock_analyser.models import PortfolioData, StockData

logger = logging.getLogger(__name__)


class PortfolioFetcher:
    """Reads a Zerodha holdings excel file to find the user's holding for a ticker."""

    def __init__(self, excel_path: str | Path):
        self.excel_path = Path(excel_path)
        self._holdings: dict[str, PortfolioData] = {}
        self._parsed = False

    def _parse_excel(self) -> None:
        """Parse the Zerodha excel file into a dictionary of holdings."""
        if self._parsed:
            return

        if not self.excel_path.exists():
            logger.warning(f"Portfolio file not found: {self.excel_path}")
            self._parsed = True
            return

        try:
            # Zerodha's export has the main tabular data starting around row 22 (0-indexed).
            # We use header=22 to set that row as the column headers.
            df = pd.read_excel(self.excel_path, header=22)

            # Drop rows where 'Symbol' is NaN or 'Symbol' is literally 'Total'
            df = df.dropna(subset=["Symbol"])
            df = df[df["Symbol"] != "Total"]

            for _, row in df.iterrows():
                symbol = str(row["Symbol"]).strip().upper()

                # Build holding data
                quantity = float(row.get("Quantity Available", 0.0))
                average_price = float(row.get("Average Price", 0.0))
                unrealized_pnl = float(row.get("Unrealized P&L", 0.0))
                unrealized_pnl_pct = float(row.get("Unrealized P&L Pct.", 0.0))
                
                # Present value calculation
                # Previous closing price * quantity is approximately the present value
                # (or just use average_price * quantity + unrealized_pnl)
                invested = average_price * quantity
                present_value = invested + unrealized_pnl

                self._holdings[symbol] = PortfolioData(
                    quantity=quantity,
                    average_price=average_price,
                    present_value=present_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                )

            logger.info(f"Parsed {len(self._holdings)} holdings from {self.excel_path}")
        except Exception as e:
            logger.error(f"Error parsing portfolio excel: {e}")
        finally:
            self._parsed = True


    def fetch(self, ticker: str, stock_data: StockData) -> StockData:
        """Find the ticker in the parsed portfolio and attach it to StockData."""
        self._parse_excel()

        # The ticker we pass here should be the bare symbol, e.g., 'TMPV' instead of 'TMPV.NS'
        bare_ticker = ticker.split(".")[0].upper()

        holding = self._holdings.get(bare_ticker)
        if holding:
            stock_data.portfolio_holding = holding
            logger.info(f"Found portfolio holding for {bare_ticker}: {holding.quantity} shares @ {holding.average_price}")
        else:
            logger.info(f"No portfolio holding found for {bare_ticker}")

        return stock_data
