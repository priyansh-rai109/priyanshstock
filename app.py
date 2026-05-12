import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="StockSense",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CACHING ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker_symbol, period):
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period=period)
    info = ticker.info
    return hist, info

@st.cache_data(ttl=3600)
def get_current_price(symbol):
    t = yf.Ticker(symbol)
    hist = t.history(period="1d")
    if not hist.empty:
        return hist['Close'].iloc[-1]
    return None

import hashlib, base64, requests as _req

def _make_svg_logo(ticker):
    """Always-available fallback: gradient SVG with ticker initials."""
    palette = [
        ("#00d4aa","#004d3d"),("#3399ff","#002d66"),("#ff6b35","#6b1a00"),
        ("#a855f7","#3b0066"),("#f59e0b","#6b3d00"),("#ef4444","#6b0000"),
        ("#10b981","#004d30"),("#06b6d4","#003d4d"),("#8b5cf6","#2d0066"),
        ("#ec4899","#6b0033"),
    ]
    idx = int(hashlib.md5(ticker.encode()).hexdigest(), 16) % len(palette)
    fg, bg = palette[idx]
    initials = ticker[:2]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
        f'<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" style="stop-color:{fg}"/>'
        f'<stop offset="100%" style="stop-color:{bg}"/></linearGradient></defs>'
        f'<rect width="64" height="64" rx="14" fill="url(#g)"/>'
        f'<text x="32" y="38" font-family="Arial,sans-serif" font-size="22" '
        f'font-weight="700" fill="white" text-anchor="middle" dominant-baseline="middle">{initials}</text>'
        f'</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

@st.cache_data(ttl=86400)
def get_best_logo(ticker, website):
    """
    Fetch a real company logo.
    Priority: Clearbit → apple-touch-icon → favicon.ico → Google → SVG fallback.
    Returns a base64 data URI — no broken images ever.
    """
    # Known domains for popular tickers (fallback if yfinance has no website)
    KNOWN_DOMAINS = {
        "AAPL": "apple.com",       "MSFT": "microsoft.com",  "GOOGL": "google.com",
        "GOOG": "google.com",      "AMZN": "amazon.com",     "TSLA": "tesla.com",
        "META": "meta.com",        "NVDA": "nvidia.com",     "NFLX": "netflix.com",
        "AMD":  "amd.com",         "INTC": "intel.com",      "ORCL": "oracle.com",
        "CRM":  "salesforce.com",  "ADBE": "adobe.com",      "PYPL": "paypal.com",
        "UBER": "uber.com",        "LYFT": "lyft.com",       "SNAP": "snap.com",
        "TWTR": "twitter.com",     "SPOT": "spotify.com",    "SHOP": "shopify.com",
        "SQ":   "squareup.com",    "COIN": "coinbase.com",   "ABNB": "airbnb.com",
        "BRK-B":"berkshirehathaway.com", "JPM": "jpmorganchase.com",
        "BAC":  "bankofamerica.com","GS":  "goldmansachs.com","V":   "visa.com",
        "MA":   "mastercard.com",  "DIS":  "disney.com",     "WMT": "walmart.com",
        "KO":   "coca-cola.com",   "PEP":  "pepsico.com",    "MCD": "mcdonalds.com",
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    # Resolve domain: prefer known map, then parse from yfinance website
    domain = KNOWN_DOMAINS.get(ticker.upper(), "")
    if not domain and website:
        domain = website.replace("https://", "").replace("http://", "").split("/")[0]
        domain = domain.lstrip("www.")

    if not domain:
        return _make_svg_logo(ticker)

    sources = [
        f"https://logo.clearbit.com/{domain}",
        f"https://{domain}/apple-touch-icon.png",
        f"https://www.{domain}/apple-touch-icon.png",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=128",
    ]

    for url in sources:
        try:
            r = _req.get(url, headers=headers, timeout=5, allow_redirects=True)
            ct = r.headers.get("Content-Type", "")
            if r.status_code == 200 and "image" in ct and len(r.content) > 200:
                mime = ct.split(";")[0].strip()
                b64  = base64.b64encode(r.content).decode()
                return f"data:{mime};base64,{b64}"
        except Exception:
            continue

    return _make_svg_logo(ticker)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
        
        :root {
            --accent: #00d4aa;
            --accent-dim: rgba(0,212,170,0.15);
            --bg-card: rgba(255,255,255,0.03);
            --border: rgba(255,255,255,0.07);
        }

        html, body, [class*="css"] {
            font-family: 'IBM Plex Sans', sans-serif;
        }

        /* ── Animated accent gradient header ── */
        .stock-header {
            display: flex; align-items: center; gap: 20px;
            background: linear-gradient(135deg, rgba(0,212,170,0.08) 0%, rgba(0,189,255,0.05) 100%);
            border: 1px solid rgba(0,212,170,0.2);
            border-radius: 16px; padding: 20px 28px; margin-bottom: 20px;
            position: relative; overflow: hidden;
        }
        .stock-header::before {
            content: '';
            position: absolute; top: 0; left: -60%;
            width: 40%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0,212,170,0.07), transparent);
            animation: shimmer 3s infinite;
        }
        @keyframes shimmer { 0%{left:-60%} 100%{left:130%} }

        .company-logo {
            width: 64px; height: 64px; border-radius: 12px;
            object-fit: contain; background: white; padding: 6px;
            box-shadow: 0 4px 20px rgba(0,212,170,0.25);
            flex-shrink: 0;
        }
        .company-logo-placeholder {
            width: 64px; height: 64px; border-radius: 12px;
            background: linear-gradient(135deg, #00d4aa22, #00bdff22);
            border: 1px solid var(--accent); display: flex;
            align-items: center; justify-content: center;
            font-size: 28px; flex-shrink: 0;
        }
        .company-name { line-height: 1.2; }
        .company-name h2 {
            margin: 0 !important; font-size: 1.6rem !important;
            background: linear-gradient(90deg, #00d4aa, #00bdff);
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
        }
        .company-meta { font-size: 0.82rem; color: rgba(255,255,255,0.5); margin-top: 4px; }
        .price-badge {
            margin-left: auto; text-align: right;
        }
        .price-badge .price {
            font-size: 2rem; font-weight: 700; color: white; line-height: 1;
        }
        .price-badge .change-pos { color: #26a69a; font-size: 0.95rem; font-weight: 600; }
        .price-badge .change-neg { color: #ef5350; font-size: 0.95rem; font-weight: 600; }

        /* ── Metric cards ── */
        .stMetric {
            background: var(--bg-card); padding: 18px; border-radius: 12px;
            border: 1px solid var(--border); border-left: 3px solid var(--accent);
            transition: all 0.25s ease;
        }
        .stMetric:hover {
            background: rgba(0,212,170,0.06);
            box-shadow: 0 0 20px rgba(0,212,170,0.1);
            transform: translateY(-2px);
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0a0f1a 0%, #0e1117 100%);
            border-right: 1px solid var(--border);
        }

        /* ── Headings ── */
        h1, h2, h3 { font-weight: 600 !important; }
        h3 { color: var(--accent) !important; }

        /* ── Buttons ── */
        .stButton>button {
            border-radius: 8px; border: 1px solid var(--accent);
            color: var(--accent); transition: all 0.2s;
            font-weight: 500;
        }
        .stButton>button:hover {
            background: var(--accent); color: #0e1117;
            box-shadow: 0 0 16px rgba(0,212,170,0.35);
        }

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab"] {
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            color: var(--accent) !important;
            border-bottom-color: var(--accent) !important;
        }

        /* ── Signal badge ── */
        .signal-badge {
            display: inline-block; padding: 4px 14px; border-radius: 20px;
            font-size: 12px; font-weight: 600; margin-left: 10px;
            letter-spacing: 0.5px;
        }

        /* ── Download button ── */
        [data-testid="stDownloadButton"] button {
            font-size: 0.82rem; padding: 6px 14px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INIT ---
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "portfolio" not in st.session_state:
    # Each entry: {ticker, shares, avg_price}
    st.session_state.portfolio = []

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429218.png", width=80)
    st.title("StockSense")

    ticker_symbol = st.text_input("Ticker Symbol", value="AAPL").upper()

    if st.button("➕ Add to Watchlist"):
        if ticker_symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(ticker_symbol)
            st.success(f"Added {ticker_symbol}")
        else:
            st.warning("Already in Watchlist")

    with st.expander("⭐ My Watchlist", expanded=True):
        if not st.session_state.watchlist:
            st.write("No tickers saved.")
        for wt in st.session_state.watchlist:
            try:
                w_price = get_current_price(wt)
                wc1, wc2 = st.columns([3, 1])
                wc1.write(f"**{wt}**: ${w_price:.2f}" if w_price else f"**{wt}**: N/A")
                if wc2.button("🗑️", key=f"remove_{wt}"):
                    st.session_state.watchlist.remove(wt)
                    st.rerun()
            except:
                st.write(f"**{wt}**: Error")

    st.markdown("---")
    period = st.selectbox("Time Period", options=["1d", "5d", "1mo", "3mo", "1y", "5y", "max"], index=2)

    st.markdown("### 📐 Indicators")
    show_bb     = st.checkbox("Bollinger Bands", value=True)
    show_ma20   = st.checkbox("MA 20", value=True)
    show_ma50   = st.checkbox("MA 50", value=False)

    st.markdown("---")
    st.markdown("### About StockSense")
    st.info("A premium real-time stock analysis dashboard.")

# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────
with st.spinner("Fetching market data..."):
    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        hist_data, info_data = get_stock_data(ticker_symbol, period)
        if hist_data.empty:
            st.error("No data found for this ticker.")
            st.stop()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

# ─────────────────────────────────────────────
# HEADER  — Logo + Name + Live Price
# ─────────────────────────────────────────────
company_name  = info_data.get('longName', ticker_symbol)
website       = info_data.get('website', '')
logo_data_url = get_best_logo(ticker_symbol, website)
sector        = info_data.get('sector', 'N/A')
industry      = info_data.get('industry', 'N/A')
exchange      = info_data.get('exchange', '')
currency      = info_data.get('currency', 'USD')

# KPI values needed for header
current_price = hist_data['Close'].iloc[-1]
open_price    = hist_data['Open'].iloc[-1]
day_high      = hist_data['High'].max()
day_low       = hist_data['Low'].min()
volume        = hist_data['Volume'].iloc[-1]
delta_price   = current_price - open_price
delta_color   = "normal" if current_price >= open_price else "inverse"
wk52_high     = info_data.get('fiftyTwoWeekHigh', None)
wk52_low      = info_data.get('fiftyTwoWeekLow', None)

change_class = "change-pos" if delta_price >= 0 else "change-neg"
change_arrow = "▲" if delta_price >= 0 else "▼"

logo_html = f'<img src="{logo_data_url}" class="company-logo" />'

st.markdown(f"""
<div class="stock-header">
    {logo_html}
    <div class="company-name">
        <h2>{company_name}</h2>
        <div class="company-meta">
            <b style="color:#00d4aa">{ticker_symbol}</b> &nbsp;·&nbsp;
            {exchange} &nbsp;·&nbsp; {sector} &nbsp;·&nbsp; {industry}
        </div>
    </div>
    <div class="price-badge">
        <div class="price">{currency} {current_price:,.2f}</div>
        <div class="{change_class}">{change_arrow} {abs(delta_price):,.2f} ({abs(delta_price/open_price*100):.2f}%) today</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Download button on its own row
csv = hist_data.to_csv().encode('utf-8')
st.download_button("📥 Download Historical Data (CSV)", data=csv,
                   file_name=f"{ticker_symbol}_history.csv", mime='text/csv')

# ─────────────────────────────────────────────
# KPI METRICS
# ─────────────────────────────────────────────
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Current Price",  f"${current_price:,.2f}", f"{delta_price:+,.2f}", delta_color=delta_color)
m2.metric("Day High",       f"${day_high:,.2f}")
m3.metric("Day Low",        f"${day_low:,.2f}")
m4.metric("Volume",         f"{volume:,.0f}")
m5.metric("52W High",       f"${wk52_high:,.2f}" if wk52_high else "N/A")
m6.metric("52W Low",        f"${wk52_low:,.2f}"  if wk52_low  else "N/A")

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Analysis", "💼 Portfolio", "📊 Financials", "📜 Description"])

# ══════════════════════════════════════════════
# TAB 1 — ANALYSIS
# ══════════════════════════════════════════════
with tab1:
    # ── Calculations ──────────────────────────
    hist_data['MA20'] = hist_data['Close'].rolling(20).mean()
    hist_data['MA50'] = hist_data['Close'].rolling(50).mean()

    # Bollinger Bands (20-day, 2σ)
    hist_data['BB_mid']   = hist_data['Close'].rolling(20).mean()
    hist_data['BB_std']   = hist_data['Close'].rolling(20).std()
    hist_data['BB_upper'] = hist_data['BB_mid'] + 2 * hist_data['BB_std']
    hist_data['BB_lower'] = hist_data['BB_mid'] - 2 * hist_data['BB_std']

    # RSI
    rsi_delta = hist_data['Close'].diff()
    gain = rsi_delta.clip(lower=0).rolling(14).mean()
    loss = (-rsi_delta.clip(upper=0)).rolling(14).mean()
    hist_data['RSI'] = 100 - (100 / (1 + gain / loss))

    # MACD
    ema12 = hist_data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = hist_data['Close'].ewm(span=26, adjust=False).mean()
    hist_data['MACD']      = ema12 - ema26
    hist_data['Signal']    = hist_data['MACD'].ewm(span=9, adjust=False).mean()
    hist_data['MACD_Hist'] = hist_data['MACD'] - hist_data['Signal']

    # RSI Signal label
    latest_rsi = hist_data['RSI'].iloc[-1]
    if latest_rsi >= 70:
        rsi_signal = ("🔴 Overbought", "#ef5350")
    elif latest_rsi <= 30:
        rsi_signal = ("🟢 Oversold / Buy Zone", "#26a69a")
    else:
        rsi_signal = ("⚪ Neutral", "#888888")

    # Volume Colors
    colors = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350'
              for _, row in hist_data.iterrows()]

    # ── Main Chart ────────────────────────────
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.7, 0.3],
        subplot_titles=(f"{ticker_symbol} — Price & Volume", "")
    )

    fig.add_trace(go.Candlestick(
        x=hist_data.index, open=hist_data['Open'], high=hist_data['High'],
        low=hist_data['Low'], close=hist_data['Close'], name="OHLC"
    ), row=1, col=1)

    if show_ma20:
        fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA20'],
            name='MA 20', line=dict(color='#3399ff', width=1.5)), row=1, col=1)
    if show_ma50:
        fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA50'],
            name='MA 50', line=dict(color='orange', width=1.5)), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BB_upper'],
            name='BB Upper', line=dict(color='rgba(0,212,170,0.6)', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BB_lower'],
            name='BB Lower', line=dict(color='rgba(0,212,170,0.6)', width=1, dash='dash'),
            fill='tonexty', fillcolor='rgba(0,212,170,0.05)'), row=1, col=1)

    fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'],
        name="Volume", marker_color=colors, showlegend=False), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", xaxis_rangeslider_visible=False, height=520,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

    # ── Technical Indicators ──────────────────
    st.markdown("### Technical Indicators")
    ti_tab1, ti_tab2, ti_tab3 = st.tabs(["RSI", "MACD", "Summary"])

    with ti_tab1:
        # RSI Signal Badge
        st.markdown(
            f"**Latest RSI: {latest_rsi:.1f}** &nbsp;"
            f"<span class='signal-badge' style='background:{rsi_signal[1]}33;"
            f"color:{rsi_signal[1]};border:1px solid {rsi_signal[1]}'>"
            f"{rsi_signal[0]}</span>",
            unsafe_allow_html=True
        )
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI'],
            name='RSI', line=dict(color='#8884d8'), fill='tozeroy',
            fillcolor='rgba(136,132,216,0.08)'))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ef5350",
                          annotation_text="Overbought (70)", annotation_position="right")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="#26a69a",
                          annotation_text="Oversold (30)", annotation_position="right")

        # Annotate buy/sell signals on RSI
        buy_signals  = hist_data[hist_data['RSI'] < 30]
        sell_signals = hist_data[hist_data['RSI'] > 70]
        if not buy_signals.empty:
            fig_rsi.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['RSI'],
                mode='markers', name='Buy Signal',
                marker=dict(symbol='triangle-up', size=10, color='#26a69a')))
        if not sell_signals.empty:
            fig_rsi.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['RSI'],
                mode='markers', name='Sell Signal',
                marker=dict(symbol='triangle-down', size=10, color='#ef5350')))

        fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.07, line_width=0)
        fig_rsi.update_layout(template="plotly_dark", height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_rsi, use_container_width=True)

    with ti_tab2:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MACD'],
            name='MACD', line=dict(color='cyan')))
        fig_macd.add_trace(go.Scatter(x=hist_data.index, y=hist_data['Signal'],
            name='Signal', line=dict(color='magenta')))
        macd_colors = ['#26a69a' if v >= 0 else '#ef5350' for v in hist_data['MACD_Hist']]
        fig_macd.add_trace(go.Bar(x=hist_data.index, y=hist_data['MACD_Hist'],
            name='Histogram', marker_color=macd_colors))
        fig_macd.update_layout(template="plotly_dark", height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_macd, use_container_width=True)

    with ti_tab3:
        st.dataframe(
            hist_data[['Open','High','Low','Close','Volume','RSI','MACD']].tail(10),
            use_container_width=True
        )

    # ── Stock Comparison ──────────────────────
    st.markdown("---")
    st.markdown("### Stock Comparison")
    compare_tickers = st.multiselect(
        "Select tickers to compare (Max 5)",
        options=["AAPL","MSFT","GOOGL","AMZN","TSLA","META","NVDA","BRK-B"],
        default=["AAPL","MSFT"]
    )
    if compare_tickers:
        with st.spinner("Comparing performance..."):
            try:
                comp_data = yf.download(compare_tickers, period=period, auto_adjust=True)['Close']
                if isinstance(comp_data, pd.Series):
                    comp_data = comp_data.to_frame(name=compare_tickers[0])
                normalized_df = comp_data / comp_data.iloc[0] * 100
                fig_comp = go.Figure()
                for t in compare_tickers:
                    col = t if t in normalized_df.columns else None
                    if col:
                        fig_comp.add_trace(go.Scatter(x=normalized_df.index,
                            y=normalized_df[col], name=t, mode='lines'))
                fig_comp.update_layout(
                    title="Normalized Performance (%)", template="plotly_dark", height=450,
                    margin=dict(l=0, r=0, t=40, b=0),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_title="Percent (%)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_comp, use_container_width=True)
            except Exception as e:
                st.error(f"Comparison Error: {e}")

# ══════════════════════════════════════════════
# TAB 2 — PORTFOLIO P&L TRACKER
# ══════════════════════════════════════════════
with tab2:
    st.markdown("### 💼 Portfolio P&L Tracker")
    st.caption("Track your holdings and see live unrealized gains/losses.")

    # Add position form
    with st.expander("➕ Add Position", expanded=not bool(st.session_state.portfolio)):
        pc1, pc2, pc3 = st.columns(3)
        p_ticker = pc1.text_input("Ticker", value="AAPL", key="port_ticker").upper()
        p_shares = pc2.number_input("Shares", min_value=0.01, value=10.0, step=1.0)
        p_avg    = pc3.number_input("Avg Buy Price ($)", min_value=0.01, value=150.0, step=0.5)
        if st.button("Add to Portfolio"):
            # Check if ticker already in portfolio, update if so
            exists = False
            for pos in st.session_state.portfolio:
                if pos['ticker'] == p_ticker:
                    pos['shares'] = p_shares
                    pos['avg_price'] = p_avg
                    exists = True
                    break
            if not exists:
                st.session_state.portfolio.append({
                    'ticker': p_ticker, 'shares': p_shares, 'avg_price': p_avg
                })
            st.success(f"{'Updated' if exists else 'Added'} {p_ticker}")
            st.rerun()

    if not st.session_state.portfolio:
        st.info("No positions yet. Add a position above to get started.")
    else:
        total_invested = 0.0
        total_current  = 0.0
        rows = []

        for pos in st.session_state.portfolio:
            live_price = get_current_price(pos['ticker'])
            if live_price is None:
                live_price = pos['avg_price']

            invested = pos['shares'] * pos['avg_price']
            current  = pos['shares'] * live_price
            pnl      = current - invested
            pnl_pct  = (pnl / invested) * 100 if invested else 0

            total_invested += invested
            total_current  += current
            rows.append({
                'Ticker':      pos['ticker'],
                'Shares':      pos['shares'],
                'Avg Price':   f"${pos['avg_price']:,.2f}",
                'Live Price':  f"${live_price:,.2f}",
                'Invested':    f"${invested:,.2f}",
                'Current':     f"${current:,.2f}",
                'P&L ($)':     f"{'+' if pnl>=0 else ''}{pnl:,.2f}",
                'P&L (%)':     f"{'+' if pnl_pct>=0 else ''}{pnl_pct:.2f}%",
                '':            '🟢' if pnl >= 0 else '🔴'
            })

        total_pnl     = total_current - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

        # Summary KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Invested",  f"${total_invested:,.2f}")
        k2.metric("Current Value",   f"${total_current:,.2f}")
        k3.metric("Total P&L",       f"${total_pnl:+,.2f}",
                  delta=f"{total_pnl_pct:+.2f}%",
                  delta_color="normal" if total_pnl >= 0 else "inverse")
        k4.metric("Positions",       str(len(st.session_state.portfolio)))

        st.markdown("---")
        # Detailed table
        port_df = pd.DataFrame(rows)
        st.dataframe(port_df, use_container_width=True, hide_index=True)

        # P&L bar chart per position
        st.markdown("#### P&L by Position")
        pnl_vals    = [pos['shares'] * (get_current_price(pos['ticker']) or pos['avg_price'])
                       - pos['shares'] * pos['avg_price']
                       for pos in st.session_state.portfolio]
        pnl_colors  = ['#26a69a' if v >= 0 else '#ef5350' for v in pnl_vals]
        tickers_list = [pos['ticker'] for pos in st.session_state.portfolio]

        fig_pnl = go.Figure(go.Bar(
            x=tickers_list, y=pnl_vals,
            marker_color=pnl_colors,
            text=[f"${v:+,.2f}" for v in pnl_vals],
            textposition='outside'
        ))
        fig_pnl.update_layout(
            template="plotly_dark", height=350,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            yaxis_title="Unrealized P&L ($)"
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

        # Clear portfolio button
        if st.button("🗑️ Clear All Positions"):
            st.session_state.portfolio = []
            st.rerun()

# ══════════════════════════════════════════════
# TAB 3 — FINANCIALS
# ══════════════════════════════════════════════
with tab3:
    st.markdown("### Key Financial Metrics")
    f1, f2, f3, f4 = st.columns(4)
    market_cap = info_data.get('marketCap')
    f1.metric("Market Cap",     f"${market_cap/1e9:.2f}B" if market_cap else "N/A")
    f2.metric("Trailing P/E",   str(round(info_data.get('trailingPE', 0), 2)) if info_data.get('trailingPE') else "N/A")
    div_yield = info_data.get('dividendYield')
    f3.metric("Dividend Yield", f"{div_yield*100:.2f}%" if div_yield else "N/A")
    f4.metric("Beta",           str(round(info_data.get('beta', 0), 2)) if info_data.get('beta') else "N/A")

    st.markdown("---")
    st.markdown("### Recent History")
    st.dataframe(hist_data.tail(10), use_container_width=True)

# ══════════════════════════════════════════════
# TAB 4 — DESCRIPTION & NEWS
# ══════════════════════════════════════════════
with tab4:
    st.markdown(f"### About {info_data.get('longName', ticker_symbol)}")
    st.write(info_data.get('longBusinessSummary', "No description available."))

    st.markdown("---")
    st.markdown("### 📰 Latest News")
    try:
        news_items = ticker_obj.news[:5]
        for item in news_items:
            with st.expander(f"📌 {item['title']}"):
                st.write(f"**Source:** {item['publisher']}")
                st.write(f"**Time:** {datetime.fromtimestamp(item['providerPublishTime']).strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"[Read full article]({item['link']})")
    except Exception:
        st.write("Could not fetch news items at this time.")