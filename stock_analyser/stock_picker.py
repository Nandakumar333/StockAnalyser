"""Stock Picker and Screener module."""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any

import urllib.request
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# Default lists of stocks to screen
DEFAULT_NSE_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "SBIN.NS", "INFY.NS", "LICI.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS",
    "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS", "TATAMOTORS.NS", "NTPC.NS",
    "AXISBANK.NS", "DMART.NS", "ADANIPORTS.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS",
    "COALINDIA.NS", "BAJAJFINSV.NS", "POWERGRID.NS", "WIPRO.NS", "M&M.NS",
    "LTIM.NS", "HAL.NS", "DLF.NS", "TATASTEEL.NS", "JIOFIN.NS", "SBILIFE.NS",
    "GRASIM.NS", "HDFCLIFE.NS", "BEL.NS", "TRENT.NS", "INDUSINDBK.NS",
    "HINDALCO.NS", "TECHM.NS", "BRITANNIA.NS", "GODREJCP.NS", "EICHERMOT.NS",
    "DIVISLAB.NS", "DRREDDY.NS", "APOLLOHOSP.NS"
]

DEFAULT_NYSE_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "TSM", "UNH"
]

def get_live_tickers(market: str = "NSE", index_name: str = "Nifty 50") -> List[str]:
    """Fetch live ticker lists from NSE or Wikipedia for S&P 500."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    if market == "NSE":
        urls = {
            "Nifty 50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
            "Nifty 100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
            "Nifty 500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        }
        url = urls.get(index_name)
        if not url: return DEFAULT_NSE_TICKERS
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                df = pd.read_csv(response)
                # Ticker column is usually 'Symbol'
                col = 'Symbol' if 'Symbol' in df.columns else df.columns[2]
                return [f"{str(sym).strip()}.NS" for sym in df[col].tolist()]
        except Exception as e:
            logger.warning(f"Failed to fetch {index_name} list: {e}")
            return DEFAULT_NSE_TICKERS
            
    else:
        # NYSE / NASDAQ -> S&P 500 or Nasdaq 100
        if index_name == "S&P 500":
            try:
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    tables = pd.read_html(response)
                    df = tables[0]
                    return [str(sym).replace('.', '-') for sym in df['Symbol'].tolist()]
            except Exception as e:
                logger.warning(f"Failed to fetch S&P 500 list: {e}")
                
        return DEFAULT_NYSE_TICKERS

def fetch_single_stock_metrics(ticker: str, market: str = "NSE") -> Dict[str, Any]:
    """Fetch metrics for a single stock using yfinance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        # Calculate ROE from financials if not in info
        roe = info.get("returnOnEquity", None)
        if roe is not None:
            roe = roe * 100
            
        pe = info.get("trailingPE", None) or info.get("forwardPE", None)
        
        raw_mc = info.get("marketCap", 0)
        if market == "NSE":
            market_cap = raw_mc / 10000000  # Convert to Crores approx for India
        else:
            market_cap = raw_mc / 1000000000  # Convert to Billions for US
        
        return {
            "Ticker": ticker,
            "Name": info.get("shortName", ticker),
            "Sector": info.get("sector", "Unknown"),
            "Industry": info.get("industry", "Unknown"),
            "Market Cap": round(market_cap, 2) if market_cap else None,
            "Price": info.get("currentPrice", info.get("previousClose", None)),
            "P/E": round(pe, 2) if pe else None,
            "ROE (%)": round(roe, 2) if roe else None,
            "Debt To Equity": info.get("debtToEquity", None),
            "Dividend Yield (%)": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else 0,
            "52W High": info.get("fiftyTwoWeekHigh", None),
            "52W Low": info.get("fiftyTwoWeekLow", None)
        }
    except Exception as e:
        logger.warning(f"Failed to fetch {ticker}: {e}")
        return {
            "Ticker": ticker,
            "Name": ticker,
            "Sector": "Unknown",
            "Market Cap": None,
            "P/E": None,
            "ROE (%)": None
        }

class StockPicker:
    """Picks and filters stocks based on various metrics and sectors."""
    
    def __init__(self, tickers: List[str] = None, market: str = "NSE"):
        self.tickers = tickers or DEFAULT_NSE_TICKERS
        self.market = market
        
    def fetch_all_metrics(self) -> pd.DataFrame:
        """Fetch metrics for all tickers concurrently."""
        results = []
        # Increased max_workers to 30 for faster fetching of 500 stocks
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(fetch_single_stock_metrics, t, self.market) for t in self.tickers]
            for future in futures:
                results.append(future.result())
                
        df = pd.DataFrame(results)
        return df

    def screen(self, df: pd.DataFrame, 
               sector: str = "All", 
               min_market_cap: float = 1000, 
               max_pe: float = 100, 
               min_roe: float = 12,
               max_debt_equity: float = 1.5) -> pd.DataFrame:
        """Filter the dataframe based on provided criteria (Defaults based on Part 1 rules)."""
        filtered_df = df.copy()
        
        if sector != "All":
            filtered_df = filtered_df[filtered_df["Sector"] == sector]
            
        if min_market_cap > 0:
            filtered_df = filtered_df[filtered_df["Market Cap"] >= min_market_cap]
            
        if max_pe < 100:
            filtered_df = filtered_df[(filtered_df["P/E"] <= max_pe) & (filtered_df["P/E"].notna())]
            
        if min_roe > 0:
            filtered_df = filtered_df[(filtered_df["ROE (%)"] >= min_roe) & (filtered_df["ROE (%)"].notna())]
            
        if max_debt_equity < 100:
            # Drop those where Debt To Equity is significantly higher (allow NaNs to pass if missing)
            filtered_df = filtered_df[(filtered_df["Debt To Equity"].isna()) | (filtered_df["Debt To Equity"] <= max_debt_equity * 100)]
            
        # Sort by Market Cap descending by default
        filtered_df = filtered_df.sort_values(by="Market Cap", ascending=False)
        
        return filtered_df
