"""Streamlit UI for the AI Stock Analyser & Picker."""

import os
import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

from stock_analyser.config import Config
from stock_analyser.stock_picker import StockPicker, DEFAULT_NSE_TICKERS, DEFAULT_NYSE_TICKERS, get_live_tickers
from stock_analyser.models import StockData
from stock_analyser.analyser import AIAnalyser

# Page config for modern design
st.set_page_config(
    page_title="AI Stock Analyser Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Modern Design ---
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stButton>button {
        background-color: #2e66ff;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #1a4cd2;
        transform: translateY(-2px);
    }
    h1, h2, h3 {
        color: #4da6ff;
    }
    .metric-card {
        background-color: #1e2532;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State ---
if "stock_df" not in st.session_state:
    st.session_state.stock_df = None
if "config" not in st.session_state:
    st.session_state.config = Config.load()
if "analysis_reports" not in st.session_state:
    st.session_state.analysis_reports = {}

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def fetch_picker_data(market="NSE", index_name="Nifty 50"):
    tickers = get_live_tickers(market, index_name)
    picker = StockPicker(tickers, market)
    return picker.fetch_all_metrics()

def run_analysis(ticker: str, exchange: str = "NS", portfolio: str = None) -> str:
    """Run full analysis pipeline for a single stock."""
    from stock_analyser.cli import setup_logging
    setup_logging(False)
    
    config = st.session_state.config
    
    yahoo_ticker = f"{ticker.upper()}.{exchange}" if "." not in ticker and exchange else ticker
    screener_ticker = ticker.split(".")[0].upper()
    
    from datetime import date
    stock_data = StockData(
        ticker=yahoo_ticker,
        company_name=screener_ticker,
        data_date=date.today(),
    )
    
    if portfolio and os.path.exists(portfolio):
        from stock_analyser.fetchers.portfolio_fetcher import PortfolioFetcher
        fetcher = PortfolioFetcher(portfolio)
        stock_data = fetcher.fetch(screener_ticker, stock_data)

    from stock_analyser.fetchers.yahoo_fetcher import YahooFinanceFetcher
    try:
        y_fetcher = YahooFinanceFetcher()
        stock_data = y_fetcher.fetch(yahoo_ticker, stock_data)
    except Exception as e:
        st.warning(f"Yahoo fetch error: {e}")

    from stock_analyser.fetchers.screener_fetcher import ScreenerFetcher
    try:
        s_fetcher = ScreenerFetcher(config)
        stock_data = s_fetcher.fetch(screener_ticker, stock_data)
    except Exception as e:
        st.warning(f"Screener fetch error: {e}")

    analyser = AIAnalyser(config)
    report = analyser.analyse(stock_data)
    analyser.save_report(report, stock_data)
    return report

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("⚙️ Configuration")
    ai_provider = st.selectbox("AI Provider", ["gemini", "groq", "openrouter"], index=["gemini", "groq", "openrouter"].index(st.session_state.config.ai_provider))
    if ai_provider != st.session_state.config.ai_provider:
        st.session_state.config.ai_provider = ai_provider
        
    portfolio_file = st.text_input("Portfolio Excel Path (optional)", value="")
    
    st.markdown("---")
    st.markdown("### AI Stock Analyser")
    st.caption("Powered by Google Gemini & Llama")

# --- Main App ---
st.title("📈 AI Stock Analyser & Picker")

tab1, tab2, tab3, tab4 = st.tabs(["🎯 Stock Picker", "🔍 Individual Analysis", "📑 Batch Analysis Reports", "⚙️ Settings"])

with tab1:
    st.header("Stock Picker & Screener")
    st.markdown("Filter top Indian & Global stocks based on Sector and Fundamental Metrics.")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        market = st.selectbox("Market", ["NSE", "NYSE"])
    with col2:
        index_options = ["Nifty 50", "Nifty 100", "Nifty 500"] if market == "NSE" else ["S&P 500", "Default Tech"]
        index_name = st.selectbox("Index", index_options)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data"):
            st.session_state.stock_df = fetch_picker_data(market, index_name)
            st.session_state.last_market = market
            st.session_state.last_index = index_name
            st.rerun()
            
    # Auto-fetch if first load or if market/index changed
    if (st.session_state.stock_df is None or 
        st.session_state.get('last_market') != market or 
        st.session_state.get('last_index') != index_name):
        with st.spinner(f"Fetching {index_name} stock data from Yahoo Finance... (Please wait)"):
            st.session_state.stock_df = fetch_picker_data(market, index_name)
            st.session_state.last_market = market
            st.session_state.last_index = index_name

    if st.session_state.stock_df is not None:
        df = st.session_state.stock_df
        
        # Filters
        st.subheader("Filters")
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
        
        sectors = ["All"] + sorted([s for s in df["Sector"].unique() if s and s != "Unknown"])
        with f_col1:
            sel_sector = st.selectbox("Sector", sectors)
        with f_col2:
            min_roe = st.number_input("Min ROE (%)", value=12.0)
        with f_col3:
            max_pe = st.number_input("Max P/E", value=100.0)
        with f_col4:
            if market == "NSE":
                min_mc = st.number_input("Min Market Cap (Cr)", value=1000.0)
            else:
                min_mc = st.number_input("Min Market Cap (Billion $)", value=2.0)
        with f_col5:
            max_de = st.number_input("Max Debt/Eq", value=1.5)
            
        # Apply filters
        picker = StockPicker()
        filtered_df = picker.screen(df, sector=sel_sector, min_market_cap=min_mc, max_pe=max_pe, min_roe=min_roe, max_debt_equity=max_de)
        
        st.write(f"**Found {len(filtered_df)} stocks matching criteria**")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # Visualizations
        if len(filtered_df) > 0:
            st.subheader("Sector Breakdown & Valuation")
            v_col1, v_col2 = st.columns(2)
            with v_col1:
                fig1 = px.pie(filtered_df, names='Sector', title='Sector Distribution', hole=0.4, template='plotly_dark')
                st.plotly_chart(fig1, use_container_width=True)
            with v_col2:
                plot_df = filtered_df.dropna(subset=['P/E', 'ROE (%)', 'Market Cap'])
                if not plot_df.empty:
                    fig2 = px.scatter(plot_df, x='P/E', y='ROE (%)', color='Sector', 
                                      hover_name='Name', size='Market Cap',
                                      title='P/E vs ROE', template='plotly_dark')
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Not enough data to plot P/E vs ROE scatter plot.")
                
            # Batch Analysis Action
            st.subheader("Batch Analysis")
            top_n = st.slider("Select Top N stocks to analyze", 1, min(50, len(filtered_df)), min(10, len(filtered_df)))
            if st.button("🚀 Run Whole Analysis on Top Selected"):
                selected_tickers = filtered_df.head(top_n)["Ticker"].tolist()
                st.write(f"Starting batch analysis for: {', '.join(selected_tickers)}")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, t in enumerate(selected_tickers):
                    status_text.text(f"Analyzing {t} ({i+1}/{top_n})...")
                    try:
                        ex = "NS" if market == "NSE" else ""
                        if t.endswith(".NS"):
                            clean_t = t.replace(".NS", "")
                            ex = "NS"
                        else:
                            clean_t = t
                            
                        report = run_analysis(clean_t, exchange=ex, portfolio=portfolio_file)
                        st.session_state.analysis_reports[clean_t] = report
                    except Exception as e:
                        st.error(f"Failed to analyze {t}: {e}")
                    
                    progress_bar.progress((i + 1) / top_n)
                
                status_text.text("Batch Analysis Complete! Check 'Batch Analysis Reports' tab.")
                st.success("All selected stocks analyzed.")

with tab2:
    st.header("Individual Stock Analysis")
    st.markdown("Run the 6-stage AI fundamental analysis on any specific stock.")
    
    i_col1, i_col2, i_col3 = st.columns([2, 1, 1])
    with i_col1:
        single_ticker = st.text_input("Enter Ticker (e.g., RELIANCE, TCS, AAPL)")
    with i_col2:
        single_exchange = st.selectbox("Exchange Suffix", ["NS", "BO", "None (US)"])
    with i_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🧠 Analyze Stock")
        
    if analyze_btn and single_ticker:
        ex = "" if "None" in single_exchange else single_exchange
        with st.spinner(f"Running deep fundamental analysis on {single_ticker}..."):
            try:
                report = run_analysis(single_ticker, exchange=ex, portfolio=portfolio_file)
                st.session_state.analysis_reports[single_ticker] = report
                st.success("Analysis Generated Successfully!")
                st.markdown(report)
            except Exception as e:
                st.error(f"Analysis failed: {e}")

with tab3:
    st.header("Saved Analysis Reports")
    st.markdown("Reports generated in this session.")
    
    if not st.session_state.analysis_reports:
        st.info("No reports generated yet. Use the Picker or Individual Analysis tabs.")
    else:
        report_options = list(st.session_state.analysis_reports.keys())
        selected_report = st.selectbox("Select Report to View", report_options)
        
        if selected_report:
            st.download_button(
                label="📥 Download Markdown",
                data=st.session_state.analysis_reports[selected_report],
                file_name=f"{selected_report}_analysis.md",
                mime="text/markdown"
            )
            st.markdown("---")
            st.markdown(st.session_state.analysis_reports[selected_report])

with tab4:
    st.header("⚙️ Settings & Configuration")
    st.markdown("Configure your AI Providers and API Keys for stock analysis here. Note: Keys are saved in memory for this session.")
    
    st.subheader("AI Provider Selection")
    new_provider = st.selectbox("Active AI Provider", ["gemini", "groq", "openrouter"], 
                                index=["gemini", "groq", "openrouter"].index(st.session_state.config.ai_provider),
                                key="settings_provider")
    if new_provider != st.session_state.config.ai_provider:
        st.session_state.config.ai_provider = new_provider
        st.rerun()
        
    st.subheader("API Keys")
    gemini_key = st.text_input("Gemini API Key", value=st.session_state.config.gemini_api_key, type="password")
    groq_key = st.text_input("Groq API Key", value=st.session_state.config.groq_api_key, type="password")
    openrouter_key = st.text_input("OpenRouter API Key", value=st.session_state.config.openrouter_api_key, type="password")
    
    if st.button("💾 Save Keys"):
        st.session_state.config.gemini_api_key = gemini_key
        st.session_state.config.groq_api_key = groq_key
        st.session_state.config.openrouter_api_key = openrouter_key
        
        # Save to .env file for persistence
        try:
            from pathlib import Path
            env_path = Path(".env")
            content = []
            if env_path.exists():
                with open(env_path, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    if not line.startswith(("GEMINI_API_KEY=", "GROQ_API_KEY=", "OPENROUTER_API_KEY=", "AI_PROVIDER=")):
                        content.append(line)
            
            content.append(f"AI_PROVIDER={st.session_state.config.ai_provider}\n")
            if gemini_key: content.append(f"GEMINI_API_KEY={gemini_key}\n")
            if groq_key: content.append(f"GROQ_API_KEY={groq_key}\n")
            if openrouter_key: content.append(f"OPENROUTER_API_KEY={openrouter_key}\n")
            
            with open(env_path, "w") as f:
                f.writelines(content)
            st.success("API Keys saved successfully to session and .env file!")
        except Exception as e:
            st.success("API Keys saved to session! (Failed to write to .env file)")

