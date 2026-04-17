"""Data models for stock analysis."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class MarketSnapshot:
    """Current market data snapshot."""

    price: float | None = None
    market_cap: str | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    eps: float | None = None
    book_value: float | None = None
    face_value: float | None = None
    one_year_return: float | None = None
    forward_pe: float | None = None
    ev_ebitda: float | None = None
    price_to_sales: float | None = None
    target_price: float | None = None


@dataclass
class FinancialPeriod:
    """Financial data for a single period."""

    period: str = ""
    sales: float | None = None
    operating_profit: float | None = None
    opm: float | None = None
    net_profit: float | None = None
    other_income: float | None = None
    interest: float | None = None
    depreciation: float | None = None
    tax: float | None = None


@dataclass
class BalanceSheetData:
    """Balance sheet data point."""

    period: str = ""
    total_equity: float | None = None
    total_borrowings: float | None = None
    total_liabilities: float | None = None
    total_assets: float | None = None
    reserves: float | None = None
    fixed_assets: float | None = None


@dataclass
class CashFlowData:
    """Cash flow data point."""

    period: str = ""
    operating_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None
    net_cash_flow: float | None = None


@dataclass
class ShareholdingData:
    """Shareholding pattern data."""

    period: str = ""
    promoter_holding: float | None = None
    fii_holding: float | None = None
    dii_holding: float | None = None
    public_holding: float | None = None


@dataclass
class PeerData:
    """Peer company comparison data."""

    name: str = ""
    pe_ratio: float | None = None
    market_cap: str | None = None
    roce: float | None = None
    roe: float | None = None
    price: float | None = None


@dataclass
class ReturnMetrics:
    """Return and efficiency metrics."""

    roe: float | None = None
    roce: float | None = None
    roe_3yr: float | None = None
    roe_5yr: float | None = None
    sales_growth_3yr: float | None = None
    sales_growth_5yr: float | None = None
    profit_growth_3yr: float | None = None
    profit_growth_5yr: float | None = None


@dataclass
class PortfolioData:
    """User portfolio holding data from Zerodha."""

    quantity: float = 0.0
    average_price: float = 0.0
    present_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class StockData:
    """Complete aggregated stock data from all sources."""

    ticker: str = ""
    company_name: str = ""
    data_date: date = field(default_factory=date.today)

    # Yahoo Finance data
    yahoo_snapshot: MarketSnapshot = field(default_factory=MarketSnapshot)
    yahoo_description: str = ""
    yahoo_sector: str = ""
    yahoo_industry: str = ""

    # Screener data
    screener_snapshot: MarketSnapshot = field(default_factory=MarketSnapshot)
    screener_description: str = ""
    screener_pros: list[str] = field(default_factory=list)
    screener_cons: list[str] = field(default_factory=list)

    # Financial data
    annual_financials: list[FinancialPeriod] = field(default_factory=list)
    quarterly_financials: list[FinancialPeriod] = field(default_factory=list)
    balance_sheet: list[BalanceSheetData] = field(default_factory=list)
    cash_flows: list[CashFlowData] = field(default_factory=list)

    # Shareholding & peers
    shareholding: list[ShareholdingData] = field(default_factory=list)
    peers: list[PeerData] = field(default_factory=list)

    # Return metrics
    return_metrics: ReturnMetrics = field(default_factory=ReturnMetrics)
    
    # Portfolio holding
    portfolio_holding: PortfolioData | None = None

    # Raw HTML/text for AI analysis (if structured parsing fails)
    raw_screener_text: str = ""
    raw_yahoo_text: str = ""

    # Data quality info
    screener_available: bool = False
    yahoo_available: bool = False
    fetch_errors: list[str] = field(default_factory=list)

    def to_analysis_text(self) -> str:
        """Convert all collected data into a structured text block for AI analysis."""
        sections = []

        sections.append(f"# Stock Data for {self.company_name} ({self.ticker})")
        sections.append(f"Data retrieved on: {self.data_date.isoformat()}")
        sections.append("")

        if self.portfolio_holding:
            ph = self.portfolio_holding
            sections.append("## YOUR CURRENT PORTFOLIO HOLDING")
            sections.append("The user analyzing this stock currently holds the following position in their portfolio:")
            sections.append(f"- Quantity: {ph.quantity}")
            sections.append(f"- Average Buy Price: ₹{ph.average_price}")
            sections.append(f"- Present Value: ₹{ph.present_value}")
            sections.append(f"- Unrealized P&L: ₹{ph.unrealized_pnl}")
            sections.append(f"- Unrealized P&L %: {ph.unrealized_pnl_pct}%")
            sections.append("\n**CRITICAL INSTRUCTION FOR AI:** Because the user currently owns this stock, your 'Portfolio action guidance' must prioritize what they should do with their current holding. Should they average down? Hold? Book profits? Exit? Factor their entry price and P&L into your advice.")
            sections.append("")

        # Yahoo Finance section
        sections.append("## Yahoo Finance Data")
        if self.yahoo_available:
            y = self.yahoo_snapshot
            sections.append(f"- Company Description: {self.yahoo_description}")
            sections.append(f"- Sector: {self.yahoo_sector}")
            sections.append(f"- Industry: {self.yahoo_industry}")
            sections.append(f"- Price: {y.price}")
            sections.append(f"- Market Cap: {y.market_cap}")
            sections.append(f"- P/E Ratio (Trailing): {y.pe_ratio}")
            sections.append(f"- P/B Ratio: {y.pb_ratio}")
            sections.append(f"- Forward P/E: {y.forward_pe}")
            sections.append(f"- EV/EBITDA: {y.ev_ebitda}")
            sections.append(f"- Price to Sales: {y.price_to_sales}")
            sections.append(f"- Dividend Yield: {y.dividend_yield}")
            sections.append(f"- Beta: {y.beta}")
            sections.append(f"- EPS: {y.eps}")
            sections.append(f"- Book Value: {y.book_value}")
            sections.append(f"- 52-Week High: {y.week_52_high}")
            sections.append(f"- 52-Week Low: {y.week_52_low}")
            sections.append(f"- 1-Year Return: {y.one_year_return}")
            sections.append(f"- Target Price: {y.target_price}")
        else:
            sections.append("Yahoo Finance data was not available.")
        sections.append("")

        # Screener section
        sections.append("## Screener.in Data")
        if self.screener_available:
            s = self.screener_snapshot
            sections.append(f"- Company Description: {self.screener_description}")
            sections.append(f"- Price: {s.price}")
            sections.append(f"- Market Cap: {s.market_cap}")
            sections.append(f"- P/E Ratio: {s.pe_ratio}")
            sections.append(f"- P/B Ratio: {s.pb_ratio}")
            sections.append(f"- Dividend Yield: {s.dividend_yield}")
            sections.append(f"- Book Value: {s.book_value}")
            sections.append(f"- Face Value: {s.face_value}")
            sections.append(f"- EPS: {s.eps}")

            if self.screener_pros:
                sections.append("\n### Pros (from Screener)")
                for pro in self.screener_pros:
                    sections.append(f"  - {pro}")

            if self.screener_cons:
                sections.append("\n### Cons (from Screener)")
                for con in self.screener_cons:
                    sections.append(f"  - {con}")
        else:
            sections.append("Screener.in data was not available.")
        sections.append("")

        # Return metrics
        sections.append("## Return & Efficiency Metrics")
        rm = self.return_metrics
        sections.append(f"- ROE: {rm.roe}")
        sections.append(f"- ROCE: {rm.roce}")
        sections.append(f"- ROE 3-Year: {rm.roe_3yr}")
        sections.append(f"- ROE 5-Year: {rm.roe_5yr}")
        sections.append(f"- Sales Growth 3-Year: {rm.sales_growth_3yr}")
        sections.append(f"- Sales Growth 5-Year: {rm.sales_growth_5yr}")
        sections.append(f"- Profit Growth 3-Year: {rm.profit_growth_3yr}")
        sections.append(f"- Profit Growth 5-Year: {rm.profit_growth_5yr}")
        sections.append("")

        # Annual financials
        if self.annual_financials:
            sections.append("## Annual Financial Data")
            sections.append(
                "| Period | Sales (Cr) | Operating Profit (Cr) | OPM (%) | Net Profit (Cr) |"
            )
            sections.append("| --- | --- | --- | --- | --- |")
            for f in self.annual_financials:
                sections.append(
                    f"| {f.period} | {f.sales} | {f.operating_profit} | {f.opm} | {f.net_profit} |"
                )
            sections.append("")

        # Quarterly financials
        if self.quarterly_financials:
            sections.append("## Quarterly Financial Data")
            sections.append(
                "| Period | Sales (Cr) | Operating Profit (Cr) | OPM (%) | Net Profit (Cr) |"
            )
            sections.append("| --- | --- | --- | --- | --- |")
            for f in self.quarterly_financials:
                sections.append(
                    f"| {f.period} | {f.sales} | {f.operating_profit} | {f.opm} | {f.net_profit} |"
                )
            sections.append("")

        # Balance sheet
        if self.balance_sheet:
            sections.append("## Balance Sheet Data")
            sections.append(
                "| Period | Equity (Cr) | Borrowings (Cr) | Total Liabilities (Cr) | Total Assets (Cr) |"
            )
            sections.append("| --- | --- | --- | --- | --- |")
            for b in self.balance_sheet:
                sections.append(
                    f"| {b.period} | {b.total_equity} | {b.total_borrowings} | {b.total_liabilities} | {b.total_assets} |"
                )
            sections.append("")

        # Cash flows
        if self.cash_flows:
            sections.append("## Cash Flow Data")
            sections.append(
                "| Period | Operating CF (Cr) | Investing CF (Cr) | Financing CF (Cr) | Net CF (Cr) |"
            )
            sections.append("| --- | --- | --- | --- | --- |")
            for c in self.cash_flows:
                sections.append(
                    f"| {c.period} | {c.operating_cash_flow} | {c.investing_cash_flow} | {c.financing_cash_flow} | {c.net_cash_flow} |"
                )
            sections.append("")

        # Shareholding
        if self.shareholding:
            sections.append("## Shareholding Pattern")
            sections.append(
                "| Period | Promoter (%) | FII (%) | DII (%) | Public (%) |"
            )
            sections.append("| --- | --- | --- | --- | --- |")
            for s in self.shareholding:
                sections.append(
                    f"| {s.period} | {s.promoter_holding} | {s.fii_holding} | {s.dii_holding} | {s.public_holding} |"
                )
            sections.append("")

        # Peers
        if self.peers:
            sections.append("## Peer Comparison")
            sections.append("| Company | P/E | ROCE (%) | Market Cap |")
            sections.append("| --- | --- | --- | --- |")
            for p in self.peers:
                sections.append(
                    f"| {p.name} | {p.pe_ratio} | {p.roce} | {p.market_cap} |"
                )
            sections.append("")

        # Raw text fallback
        if self.raw_screener_text:
            sections.append("## Raw Screener.in Page Text (for additional context)")
            sections.append(self.raw_screener_text[:15000])
            sections.append("")

        if self.raw_yahoo_text:
            sections.append("## Raw Yahoo Finance Page Text (for additional context)")
            sections.append(self.raw_yahoo_text[:10000])
            sections.append("")

        # Fetch errors
        if self.fetch_errors:
            sections.append("## Data Fetch Warnings")
            for err in self.fetch_errors:
                sections.append(f"- ⚠️ {err}")

        return "\n".join(sections)
