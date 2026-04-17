# 📊 AI Stock Analyser

AI-powered fundamental stock analysis tool for Indian equities. Fetches live data from **Yahoo Finance** and **Screener.in**, then uses **Google Gemini** to generate comprehensive analysis reports with portfolio action guidance.

## Features

- 🔍 **Dual-source data fetching** — Yahoo Finance (via `yfinance`) + Screener.in (web scraping)
- 🤖 **AI-powered analysis** — Google Gemini generates structured fundamental reports
- 📋 **13-section reports** — Company overview → Valuation → Portfolio guidance → Decision journal
- 💼 **Portfolio management framework** — Buy/hold/sell strategy, position sizing, exit rules
- 🎯 **Decision journal** — Structured logging for every analysis decision
- ✨ **Rich CLI** — Progress bars, coloured output, beautiful terminal UX

## Quick Start

### 1. Install

```bash
# From the project directory
pip install -e .
```

### 2. Setup API Key

```bash
# Interactive setup
stock-analyser setup

# Or manually: copy .env.example to .env and add your Gemini API key
cp .env.example .env
# Edit .env with your key from https://aistudio.google.com/apikey
```

### 3. Analyse a Stock

```bash
# Analyse a stock (NSE by default)
stock-analyser analyse TMPV
stock-analyser analyse INFY
stock-analyser analyse TCS

# Analyse BSE-listed stock
stock-analyser analyse RELIANCE --exchange BO

# Custom output directory
stock-analyser analyse HDFCBANK -o ./my-reports

# Verbose mode
stock-analyser analyse WIPRO -v
```

### 4. List Reports

```bash
stock-analyser list
```

## Report Structure

Every generated report follows this structure:

1. **Company overview** — Business model, B2B/B2C, market exposure
2. **Current market snapshot** — Yahoo vs Screener data comparison
3. **Business model and segment analysis** — Revenue drivers, complexity
4. **Revenue, profit, and margin trend analysis** — Annual + quarterly trends
5. **Debt and balance sheet analysis** — Borrowings, debt/equity
6. **Cash flow, ROE, and ROCE analysis** — Return metrics vs 15% hurdle
7. **Valuation analysis** — P/E, P/B, EV/EBITDA, peer comparison
8. **Moat, management, dividend, and shareholding** — Competitive edge
9. **Risks and red flags** — Key concerns
10. **Final verdict** — Bullish / Neutral / Bearish with justification
11. **Portfolio action guidance** — Buy/hold/sell strategy with position sizing
12. **Decision journal entry** — Structured log for tracking decisions
13. **Sources and data retrieval date**

## AI Skills Integrated

This tool combines two AI analysis frameworks:

- **Fundamental Stock Analyst** — 6-phase checklist covering business model, profitability, debt, cash flow, valuation, and moat analysis
- **Master Stock Analyst & Portfolio Manager** — 7-pillar investment framework covering stock selection, purchase strategy, holding strategy, averaging rules, profit booking, exit strategy, and decision journaling

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `REPORTS_DIR` | `reports/` | Output directory for reports |

## Project Structure

```
StockAnalyser/
├── .github/prompts/
│   └── stockanalyser.md          # AI prompt for Copilot Chat usage
├── stock_analyser/
│   ├── __init__.py
│   ├── cli.py                    # Rich CLI interface
│   ├── config.py                 # Configuration management
│   ├── models.py                 # Data models
│   ├── analyser.py               # AI analysis engine (Gemini)
│   └── fetchers/
│       ├── yahoo_fetcher.py      # Yahoo Finance data fetcher
│       └── screener_fetcher.py   # Screener.in web scraper
├── reports/                      # Generated analysis reports
├── pyproject.toml
├── .env.example
└── README.md
```
