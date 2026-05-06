# StockAnalyser Memory

## Project Overview
StockAnalyser is an AI-powered fundamental stock analysis tool for Indian equities. It uses data from Yahoo Finance and Screener.in and generates comprehensive fundamental analysis reports using various AI providers (Gemini, Groq, OpenRouter).

## Directory Structure
- `.env` and `.env.example`: Configuration files for API keys and provider selection.
- `.github/prompts/stockanalyser.md`: Master prompt detailing the 6-stage stock screening and filtering system, and portfolio management rules. It's used as a basis for the AI analysis.
- `stock_analyser/`: Main package directory.
  - `cli.py`: Command-line interface with commands `analyse`, `setup`, and `list`. Uses Rich for formatting.
  - `models.py`: Data models (`StockData`, `MarketSnapshot`, `PortfolioData`, etc.) that aggregate information from fetchers and format it as text for the AI.
  - `config.py`: Configuration management for AI providers, URLs, and API keys.
  - `analyser.py`: AI-powered analysis engine integrating the fundamental analysis checklist and portfolio manager skill. Calls the selected AI provider to generate Markdown reports.
  - `fetchers/`: Modules to fetch data from different sources.
    - `portfolio_fetcher.py`: Parses Zerodha holdings Excel file.
    - `screener_fetcher.py`: Fetches and parses data from Screener.in.
    - `yahoo_fetcher.py`: Fetches data using `yfinance`.
- `reports/`: Directory where the AI-generated Markdown analysis reports are saved.

## Key Concepts
- **Providers:** Supports Gemini, Groq, OpenRouter.
- **Data Gathering:** Merges user portfolio holding data, Yahoo Finance market data, and Screener.in fundamental/financial data.
- **AI Analysis:** The prompt `SYSTEM_PROMPT` inside `analyser.py` incorporates principles from the `.github/prompts/stockanalyser.md` file to generate a structured fundamental and portfolio analysis report.

## Pending Tasks / Future Requirements
1. Enhance the tool to pick Indian stocks based on an analyser based on sector and implement their metrics.
2. Filter and pick top 10 to 50 stocks using NSE, NYSE, Screener, yfinance, etc., and analyze individual stocks.
3. Build a modern UI with options for:
   - Refreshing stock picker.
   - Individual stock analysis.
   - Stock picker whole analysis.
