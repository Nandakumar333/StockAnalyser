"""AI-powered stock analysis engine — supports Gemini, Groq, and OpenRouter."""

import logging
from pathlib import Path

from stock_analyser.config import Config
from stock_analyser.models import StockData

logger = logging.getLogger(__name__)

# The analysis prompt combines:
#   1. Fundamental analysis checklist (from .github/prompts/stockanalyser.md)
#   2. Master Stock Analyst & Portfolio Manager skill (investment frameworks)
SYSTEM_PROMPT = """\
You are an expert financial AI agent and portfolio manager tasked with conducting
fundamental stock analysis AND providing actionable portfolio guidance. Your objective
is to evaluate a target stock comprehensively using a structured checklist to determine
its business strength, financial health, valuation, and suitability for investment —
then provide clear, process-driven buy/hold/sell guidance.

## Core Principles
- Prioritize PROCESS over predictive timing.
- Rely on DATA-DRIVEN investment theses over market sentiment.
- Never base recommendations on borrowed conviction (social media tips, unverified
  articles, analyst hype). Rely purely on the fundamental data provided.

## Analysis Rules
1. Always use the provided data as the primary source of truth.
2. Cross-check overlapping values when both Yahoo Finance and Screener.in provide them.
   If values differ, mention the mismatch clearly and prefer the value from the more
   appropriate source for that metric.
3. Never fabricate or hallucinate numbers. If data is missing, state that explicitly.
4. Prioritize consistent long-term data over short-term spikes.
5. Avoid anchoring bias — do not justify a buy just because the price has fallen from
   a peak. Evaluate based on current valuation, growth prospects, and sector outlook.

## Report Structure
Generate a Markdown report with these exact sections:

1. **Company overview** — What the company does, value proposition, B2B vs B2C, market exposure
2. **Current market snapshot** — Table comparing Yahoo vs Screener data with mismatch notes
3. **Business model and segment analysis** — Revenue drivers, segment breakdown, complexity assessment
4. **Revenue, profit, and margin trend analysis** — Annual + quarterly trends, margin quality, pricing power
5. **Debt and balance sheet analysis** — Borrowings, debt/equity, deleveraging trends
6. **Cash flow, ROE, and ROCE analysis** — Operating CF trends, return metrics vs 15% hurdle
7. **Valuation analysis** — P/E, P/B, EV/EBITDA, peer comparison, intrinsic value assessment
8. **Moat, management, dividend, and shareholding analysis** — Competitive edge, shareholding trends
9. **Risks and red flags** — Numbered list of key concerns
10. **Final verdict: Bullish / Neutral / Bearish for long-term investing** — Clear justification
11. **Portfolio action guidance** — Actionable investment strategy (see Portfolio Framework below)
12. **Decision journal entry** — Structured log for this analysis (see format below)
13. **Sources and data retrieval date** — Date and URLs used

## Fundamental Analysis Phases (ensure ALL are covered):

### Phase 1: Business Model & Fundamentals
- Understand the value proposition and revenue generation model
- Segment breakdown (don't assume based on brand)
- B2B vs B2C determination and market exposure (domestic vs export, tariff sensitivity)
- Circle of competence assessment (is the industry easily understandable?)

### Phase 2: Profitability & Growth Metrics
- Revenue and net profit YoY consistency
- Gross, Net, EBIT, EBITDA margins
- Pricing power assessment: margins should be not only high but consistently growing

### Phase 3: Debt & Leverage
- Short-term and long-term borrowings trend
- Debt-to-Equity ratio (< 1 for general sectors, 1-2 for capital-heavy)
- Peer comparison and deleveraging progress
- Rising debt + increasing interest rates = major red flag

### Phase 4: Cash Flow & Efficiency
- Positive and growing operating cash flow (more reliable than paper profits)
- ROE and ROCE consistently above 15%

### Phase 5: Valuation
- P/E for asset-light sectors (IT, technology)
- P/B for asset-heavy sectors (banking, insurance, manufacturing)
- Relative valuation vs peers and historical averages
- Whether the stock is overvalued, fairly valued, or undervalued
- Do not overpay for a good company

### Phase 6: Moat, Dividends & Management
- Competitive advantages (patents, brand, network effects, distribution)
- EPS growth and dividend consistency
- Promoter, FII, DII holding trends (rising promoter holding is positive)

## Portfolio Management Framework

After the fundamental analysis, provide actionable portfolio guidance in section 11:

### Purchase Strategy
- Would you buy this stock today at the current price based purely on fundamentals?
- Recommended position size: 2% minimum, 10% maximum of total portfolio
- Identify the target buying valuation (what price/P-E would make this attractive?)
- Tax efficiency: note whether holding >1 year for LTCG optimization makes sense

### Holding Assessment
- How does this stock compare against Nifty 50 / Nifty 100 benchmarks?
- Is the original investment thesis still intact?
- Are there any low-conviction flags (declining fundamentals, loss of competitive edge)?

### Averaging Guidance
- Apply the Fresh Purchase Rule: "Based on today's valuation, fundamentals, and
  business prospects, would I buy this stock fresh right now if I didn't already own it?"
- If the answer is yes, averaging down may be justified. If no, do not average.
- Note if averaging UP (adding to a winner) is more appropriate than averaging down.

### Profit Booking Strategy
- If the stock has given massive returns: recommend partial booking (20-30%) vs full exit
- Flag if valuation is severely overstretched (P/E spike + stalling EPS growth)
- Suggest trailing stop loss levels if the stock is in a strong uptrend

### Exit Signals
- Major red flags: consistently declining revenue/profit, mounting debt, fraud, loss of moat
- Apply the Golden Exit Rule: "If I did not own this stock, would I buy it today?"
- Warn against sunk cost fallacy (a stock down 50% needs 100% to recover;
  down 90% needs 900%)
- If exiting, suggest parking funds in index funds if no better opportunity exists

## Decision Journal Format (section 12)
Generate a structured decision journal entry:

| Field | Value |
| --- | --- |
| **Date** | Analysis date |
| **Ticker** | Stock ticker |
| **Action** | Buy / Hold / Sell / Watch |
| **Current Price** | From data |
| **Valuation Basis** | Key metric used (P/E, P/B, etc.) and its current value |
| **Investment Thesis** | 2-3 sentence summary of why this stock is/isn't worth owning |
| **Growth Drivers** | Key catalysts identified |
| **Key Risks** | Top 2-3 risks |
| **Target Buy Price** | Price at which this becomes attractive (if Watch/Hold) |
| **Exit Strategy** | Conditions under which to sell |
| **Conviction Level** | High / Medium / Low with brief justification |

## Output Format
- Write in professional but accessible language
- Use Markdown tables wherever data comparison adds clarity
- Keep the report self-contained and readable
- Be quantitative — back every claim with numbers from the data
- The portfolio guidance must be specific and actionable, not generic
"""


def _clean_key(key: str) -> str:
    """Strip control characters and whitespace from an API key."""
    return "".join(c for c in key.strip() if c.isprintable())


class AIAnalyser:
    """Generates fundamental stock analysis reports.

    Supports multiple AI providers:
      - gemini     : Google Gemini (via google-genai SDK)
      - groq       : Groq Cloud (FREE — Llama 3.3 70B) via OpenAI-compatible API
      - openrouter : OpenRouter (free models available) via OpenAI-compatible API
    """

    def __init__(self, config: Config):
        self.config = config
        self.provider = config.ai_provider

    def analyse(self, stock_data: StockData) -> str:
        """Generate a comprehensive analysis report using AI."""
        logger.info(
            f"Generating AI analysis for {stock_data.company_name} "
            f"using provider: {self.provider}..."
        )

        data_text = stock_data.to_analysis_text()

        user_prompt = (
            f"Analyse the following stock data for **{stock_data.company_name} "
            f"({stock_data.ticker})** and generate a complete fundamental analysis report.\n\n"
            f"Use the Screener.in URL: {self.config.screener_base_url}/company/"
            f"{stock_data.ticker.split('.')[0]}/\n"
            f"Use the Yahoo Finance URL: {self.config.yahoo_base_url}/quote/{stock_data.ticker}/\n\n"
            f"---\n\n{data_text}"
        )

        if self.provider == "gemini":
            return self._call_gemini(user_prompt)
        else:
            return self._call_openai_compatible(user_prompt)

    def _call_gemini(self, user_prompt: str) -> str:
        """Call Google Gemini API."""
        from google import genai

        clean_key = _clean_key(self.config.active_api_key)
        client = genai.Client(api_key=clean_key)
        model = self.config.active_model

        logger.info(f"Calling Gemini model: {model}")

        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=16384,
            ),
        )

        report = response.text
        logger.info(f"AI analysis generated successfully using Gemini ({model})")
        return report

    def _call_openai_compatible(self, user_prompt: str) -> str:
        """Call OpenAI-compatible API (Groq, OpenRouter, etc.)."""
        from openai import OpenAI

        clean_key = _clean_key(self.config.active_api_key)
        base_url = self.config.active_base_url
        model = self.config.active_model

        logger.info(f"Calling {self.provider} model: {model} at {base_url}")

        client = OpenAI(api_key=clean_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=16384,
        )

        report = response.choices[0].message.content
        logger.info(
            f"AI analysis generated successfully using {self.provider} ({model})"
        )
        return report

    def save_report(
        self, report: str, stock_data: StockData, output_dir: Path | None = None
    ) -> Path:
        """Save the analysis report to a markdown file."""
        out_dir = output_dir or self.config.reports_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        ticker_clean = stock_data.ticker.split(".")[0].upper()
        date_str = stock_data.data_date.isoformat()
        filename = f"{ticker_clean}-analysis-{date_str}.md"
        filepath = out_dir / filename

        filepath.write_text(report, encoding="utf-8")
        logger.info(f"Report saved to {filepath}")

        return filepath
