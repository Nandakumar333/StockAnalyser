"""CLI interface for the AI-powered stock analyser."""

import logging
import os
import sys
from datetime import date

# Force UTF-8 on Windows to avoid cp1252 encoding errors with Rich
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text
from rich import box

from stock_analyser.config import Config
from stock_analyser.models import StockData

console = Console(force_terminal=True)

BANNER = """
[bold cyan]
  +-----------------------------------------------------------+
  |       AI Stock Analyser -- Fundamental Analysis            |
  |                                                            |
  |     Powered by Google Gemini + Yahoo Finance + Screener    |
  +-----------------------------------------------------------+
[/bold cyan]
"""


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy third-party loggers
    for name in ("httpx", "httpcore", "urllib3", "yfinance", "peewee"):
        logging.getLogger(name).setLevel(logging.WARNING)


@click.group()
@click.version_option(version="1.0.0", prog_name="stock-analyser")
def cli():
    """AI-powered fundamental stock analyser for Indian equities."""
    pass


@cli.command()
@click.argument("ticker")
@click.option(
    "--exchange",
    "-e",
    default="NS",
    show_default=True,
    help="Exchange suffix for Yahoo Finance (NS=NSE, BO=BSE).",
)
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Output directory for the report. Defaults to 'reports/'.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
@click.option(
    "--env-file", default=None, help="Path to .env file. Defaults to '.env'."
)
@click.option(
    "--portfolio",
    "-p",
    default=None,
    help="Path to Zerodha holdings excel file to include your portfolio status.",
)
def analyse(
    ticker: str,
    exchange: str,
    output_dir: str | None,
    verbose: bool,
    env_file: str | None,
    portfolio: str | None,
):
    """Analyse a stock and generate a fundamental analysis report.

    TICKER is the stock symbol (e.g., TMPV, INFY, TCS, RELIANCE).

    Examples:

        stock-analyser analyse TMPV

        stock-analyser analyse INFY --exchange BO

        stock-analyser analyse TCS -o ./my-reports
        
        stock-analyser analyse TCS -p ./holdings.xlsx
    """
    setup_logging(verbose)
    console.print(BANNER)

    # Load config
    config = Config.load(env_file)
    errors = config.validate()
    if errors:
        for err in errors:
            console.print(f"  [bold red]✗[/bold red] {err}")
        console.print(
            "\n  [dim]Create a .env file from .env.example and add your API key.[/dim]"
        )
        sys.exit(1)

    if output_dir:
        from pathlib import Path

        config.reports_dir = Path(output_dir)

    # Build Yahoo ticker
    yahoo_ticker = f"{ticker.upper()}.{exchange}" if "." not in ticker else ticker
    screener_ticker = ticker.split(".")[0].upper()

    console.print(
        f"  [bold]Target:[/bold]    {screener_ticker}  "
        f"[dim](Yahoo: {yahoo_ticker})[/dim]"
    )
    console.print(
        f"  [bold]AI Provider:[/bold] {config.ai_provider}  "
        f"[dim](Model: {config.active_model})[/dim]\n"
    )

    # Progress tracking
    progress = Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )

    with progress:
        # Total steps defaults to 4. Add 1 if a portfolio is provided.
        total_steps = 5 if portfolio else 4
        main_task = progress.add_task("Overall Progress", total=total_steps)

        # Step 1: Initialise stock data
        progress.update(main_task, description="[cyan]Initialising...")
        stock_data = StockData(
            ticker=yahoo_ticker,
            company_name=screener_ticker,
            data_date=date.today(),
        )
        progress.advance(main_task)

        # Step 1.5: Identify Portfolio Holding if provided
        if portfolio:
            progress.update(main_task, description="[cyan]Checking portfolio...")
            try:
                from stock_analyser.fetchers.portfolio_fetcher import PortfolioFetcher
                
                portfolio_fetcher = PortfolioFetcher(portfolio)
                stock_data = portfolio_fetcher.fetch(screener_ticker, stock_data)
                
                if stock_data.portfolio_holding:
                    qty = stock_data.portfolio_holding.quantity
                    avg_price = stock_data.portfolio_holding.average_price
                    pnl = stock_data.portfolio_holding.unrealized_pnl_pct
                    color = "green" if pnl >= 0 else "red"
                    console.print(f"  [cyan][MEMORY][/cyan] You hold {qty} shares @ ₹{avg_price} (P&L: [{color}]{pnl}%[/{color}])")
                else:
                    console.print("  [cyan][MEMORY][/cyan] You do not currently hold this stock.")
            except Exception as e:
                console.print(f"  [red][FAIL][/red] Portfolio error: {e}")
            progress.advance(main_task)

        # Step 2: Fetch Yahoo Finance data
        progress.update(main_task, description="[yellow]Fetching Yahoo Finance data...")
        try:
            from stock_analyser.fetchers.yahoo_fetcher import YahooFinanceFetcher

            yahoo = YahooFinanceFetcher()
            stock_data = yahoo.fetch(yahoo_ticker, stock_data)
            if stock_data.yahoo_available:
                console.print(
                    "  [green][OK][/green] Yahoo Finance data fetched"
                )
            else:
                console.print(
                    "  [yellow][!!][/yellow] Yahoo Finance -- no data returned"
                )
        except Exception as e:
            console.print(f"  [red][FAIL][/red] Yahoo Finance error: {e}")
        progress.advance(main_task)

        # Step 3: Fetch Screener.in data
        progress.update(main_task, description="[yellow]Fetching Screener.in data...")
        try:
            from stock_analyser.fetchers.screener_fetcher import ScreenerFetcher

            screener = ScreenerFetcher(config)
            stock_data = screener.fetch(screener_ticker, stock_data)
            if stock_data.screener_available:
                console.print("  [green][OK][/green] Screener.in data fetched")
            else:
                console.print(
                    "  [yellow][!!][/yellow] Screener.in -- no data returned"
                )
        except Exception as e:
            console.print(f"  [red][FAIL][/red] Screener.in error: {e}")
        progress.advance(main_task)

        # Step 4: AI Analysis
        progress.update(
            main_task,
            description="[magenta]Generating AI analysis (this may take a minute)...",
        )
        try:
            from stock_analyser.analyser import AIAnalyser

            analyser = AIAnalyser(config)
            report = analyser.analyse(stock_data)
            filepath = analyser.save_report(report, stock_data)
            progress.advance(main_task)
        except Exception as e:
            console.print(f"\n  [bold red][FAIL] AI Analysis failed:[/bold red] {e}")
            if verbose:
                console.print_exception()
            sys.exit(1)

    # Show fetch warnings
    if stock_data.fetch_errors:
        console.print()
        for err in stock_data.fetch_errors:
            console.print(f"  [yellow][!!] {err}[/yellow]")

    # Success panel
    console.print()
    console.print(
        Panel(
            Text.from_markup(
                f"[bold green][OK] Analysis complete![/bold green]\n\n"
                f"  [bold]Company:[/bold]  {stock_data.company_name}\n"
                f"  [bold]Ticker:[/bold]   {stock_data.ticker}\n"
                f"  [bold]Date:[/bold]     {stock_data.data_date.isoformat()}\n"
                f"  [bold]Report:[/bold]   {filepath}"
            ),
            title="[bold] Report Generated ",
            border_style="green",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )


@cli.command()
def setup():
    """Interactive setup -- create .env file with your API key."""
    from pathlib import Path

    console.print(BANNER)

    env_path = Path(".env")
    if env_path.exists():
        overwrite = click.confirm(
            "  .env file already exists. Overwrite?", default=False
        )
        if not overwrite:
            console.print("  [dim]Keeping existing .env file.[/dim]")
            return

    console.print("  [bold]Choose your AI provider:[/bold]\n")
    console.print("    [cyan]1[/cyan]  Groq       [green](FREE)[/green] -- Llama 3.3 70B, very fast")
    console.print("    [cyan]2[/cyan]  Gemini     -- Google Gemini 2.0 Flash")
    console.print("    [cyan]3[/cyan]  OpenRouter [green](free models)[/green] -- Multi-model gateway")
    console.print()

    provider_choice = click.prompt(
        "  Select provider (1/2/3)", type=click.Choice(["1", "2", "3"]), default="1"
    )

    provider_map = {"1": "groq", "2": "gemini", "3": "openrouter"}
    provider = provider_map[provider_choice]

    key_urls = {
        "groq": "https://console.groq.com/keys",
        "gemini": "https://aistudio.google.com/apikey",
        "openrouter": "https://openrouter.ai/keys",
    }
    key_env_names = {
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }

    console.print(
        f"\n  [bold]Get your {provider.title()} API key at:[/bold] {key_urls[provider]}\n"
    )

    api_key = click.prompt(f"  Enter your {provider.title()} API key", hide_input=True)

    default_models = {
        "groq": "grok-4-0709",
        "gemini": "gemini-2.5-flash",
        "openrouter": "google/gemma-4-31b-it:free",
    }

    if provider == "openrouter":
        console.print("\n  [bold]Popular Free OpenRouter Models:[/bold]")
        console.print("    - google/gemma-4-31b-it:free")
        console.print("    - meta-llama/llama-3.3-70b-instruct:free")
        console.print("    - deepseek/deepseek-r1-distill-llama-70b:free")
        console.print("    (See more at https://openrouter.ai/models?max_price=0)\n")
        
    model = click.prompt(
        f"  Model to use", default=default_models[provider], show_default=True
    )

    env_content = (
        f"# AI Stock Analyser Configuration\n"
        f"# Provider: {provider}\n\n"
        f"{key_env_names[provider]}={api_key}\n"
        f"AI_MODEL={model}\n"
    )

    env_path.write_text(env_content, encoding="utf-8")
    console.print(f"\n  [green][OK][/green] .env file created at {env_path.resolve()}")
    console.print(f"  [dim]Provider: {provider} | You can now run: stock-analyser analyse <TICKER>[/dim]")


@cli.command(name="list")
def list_reports():
    """List all generated analysis reports."""
    from pathlib import Path

    config = Config.load()
    reports_dir = config.reports_dir

    if not reports_dir.exists():
        console.print("  [yellow]No reports directory found.[/yellow]")
        return

    reports = sorted(reports_dir.glob("*-analysis-*.md"), reverse=True)
    if not reports:
        console.print("  [yellow]No analysis reports found.[/yellow]")
        return

    console.print(f"\n  [bold]Analysis Reports[/bold] ({len(reports)} found)\n")

    from rich.table import Table

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Ticker", style="bold")
    table.add_column("Date")
    table.add_column("File", style="dim")
    table.add_column("Size")

    for i, report in enumerate(reports, 1):
        name = report.stem
        parts = name.split("-analysis-")
        ticker = parts[0] if parts else name
        analysis_date = parts[1] if len(parts) > 1 else "unknown"
        size = f"{report.stat().st_size / 1024:.1f} KB"
        table.add_row(str(i), ticker, analysis_date, report.name, size)

    console.print(table)


if __name__ == "__main__":
    cli()
