# app.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="Ultimate Global Macro Dashboard (Pro)")

# ------------------------
# Helper functions
# ------------------------
def fred_series_latest(series_id, api_key):
    if not api_key:
        return None
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&limit=1&sort_order=desc"
    try:
        r = requests.get(url, timeout=15)
        j = r.json()
        obs = j.get("observations", [])
        if obs:
            val = obs[0].get("value")
            date = obs[0].get("date")
            try:
                return float(val), date
            except:
                return val, date
    except Exception:
        return None

def fred_series_df(series_id, api_key, start_date=None):
    if not api_key:
        return None
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&sort_order=asc"
    if start_date:
        url += f"&observation_start={start_date}"
    r = requests.get(url, timeout=20)
    j = r.json()
    obs = j.get("observations", [])
    if not obs:
        return None
    df = pd.DataFrame(obs)
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.set_index('date')['value']
    return df

def yfin_download(ticker, period="6mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if not df.empty:
            df = df['Close'].rename(ticker)
            return df
        else:
            return pd.Series(dtype=float)
    except Exception:
        return pd.Series(dtype=float)

# ------------------------
# Secrets & config
# ------------------------
FRED_KEY = st.secrets.get("FRED_API_KEY") if "FRED_API_KEY" in st.secrets else None
# ALPHA_KEY reserved for optional expansion
ALPHA_KEY = st.secrets.get("ALPHA_VANTAGE_KEY") if "ALPHA_VANTAGE_KEY" in st.secrets else None

st.title("🌐 Ultimate Global Macro Dashboard — PRO")
st.markdown("**Top-Down: Level 1 (Core Macro) → Level 2 (Cross-Market) → Level 3 (Positioning & Liquidity)**")

# ------------------------
# Level 1 — Core Macro (Quick Metrics)
# ------------------------
st.subheader("Level 1 — Core Macro (Quick Metrics)")
col1, col2, col3, col4 = st.columns(4)

with col1:
    fed_latest = fred_series_latest("FEDFUNDS", FRED_KEY)
    if fed_latest:
        st.metric("Fed Funds (Effective)", f"{fed_latest[0]:.2f} %", label=f"as of {fed_latest[1]}")
    else:
        st.write("Fed Funds: (set FRED_API_KEY in Streamlit secrets)")

with col2:
    cpi_latest = fred_series_latest("CPILFESL", FRED_KEY)  # core CPI
    if cpi_latest:
        st.metric("Core CPI (YoY)", f"{cpi_latest[0]:.2f} %", label=f"as of {cpi_latest[1]}")
    else:
        st.write("Core CPI: (set FRED_API_KEY in Streamlit secrets)")

with col3:
    payrolls = fred_series_latest("PAYEMS", FRED_KEY)
    if payrolls:
        st.metric("Nonfarm Payrolls (PAYEMS)", f"{int(payrolls[0])}", label=f"as of {payrolls[1]}")
    else:
        st.write("PAYEMS: (set FRED_API_KEY in Streamlit secrets)")

with col4:
    gdp_latest = fred_series_latest("GDP", FRED_KEY)
    if gdp_latest:
        st.metric("US GDP (Real, Quarterly)", f"{gdp_latest[0]:.2f}", label=f"as of {gdp_latest[1]}")
    else:
        st.write("GDP: (set FRED_API_KEY in Streamlit secrets)")

st.markdown("---")

# ------------------------
# Level 2 — Cross-Market Panel
# ------------------------
st.subheader("Level 2 — Cross-Market / Intermarket")

left_col, right_col = st.columns([2,1])

with left_col:
    st.write("**Yields & Spreads**")
    us10 = fred_series_df("GS10", FRED_KEY, start_date=(datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d"))
    us2 = fred_series_df("GS2", FRED_KEY, start_date=(datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d"))
    if us10 is not None and us2 is not None:
        spread = (us10 - us2) * 100  # in bps roughly
        df_spread = pd.DataFrame({"10Y": us10, "2Y": us2, "10y-2y (bps)": spread}).dropna()
        fig = px.line(df_spread.reset_index(), x='index', y=['10Y','2Y'], labels={'index':'Date'}, title="US 10Y & 2Y Yields")
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.line(df_spread.reset_index(), x='index', y='10y-2y (bps)', title="10Y - 2Y Spread (approx bps)")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.write("US Yields: FRED API key required to fetch GS10 & GS2 series.")

    st.write("**FX & Commodities (recent)**")
    cols = st.columns(3)
    eurusd = yfin_download("EURUSD=X", period="3mo")
    usdjpy = yfin_download("JPY=X", period="3mo")  # JPY=X gives USD/JPY close series
    spx = yfin_download("^GSPC", period="3mo")
    gold = yfin_download("GC=F", period="3mo")
    oil = yfin_download("CL=F", period="3mo")

    if not eurusd.empty:
        fig_fx = px.line(eurusd.reset_index(), x='Date', y='EURUSD=X', title="EUR/USD (3m)")
        st.plotly_chart(fig_fx, use_container_width=True)
    if not usdjpy.empty:
        fig_jpy = px.line(usdjpy.reset_index(), x='Date', y='JPY=X', title="USD/JPY (3m)")
        st.plotly_chart(fig_jpy, use_container_width=True)

with right_col:
    st.write("**Equities & Volatility**")
    spx = yfin_download("^GSPC", period="6mo")
    vix = yfin_download("^VIX", period="6mo")
    if not spx.empty:
        st.line_chart(spx, height=200)
    if not vix.empty:
        st.line_chart(vix, height=200)
    latest_spx = spx.iloc[-1] if not spx.empty else None
    latest_vix = vix.iloc[-1] if not vix.empty else None
    if latest_spx is not None:
        st.metric("S&P 500 (Last)", f"{latest_spx:.0f}")
    if latest_vix is not None:
        st.metric("VIX (Last)", f"{latest_vix:.2f}")

st.markdown("---")

# ------------------------
# Level 3 — Positioning & Liquidity
# ------------------------
st.subheader("Level 3 — Positioning & Liquidity")

colA, colB, colC = st.columns(3)

with colA:
    st.write("Fed Balance Sheet & M2 (liquidity indicators)")
    bal = fred_series_df("WALCL", FRED_KEY, start_date=(datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d"))
    m2 = fred_series_df("M2SL", FRED_KEY, start_date=(datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d"))
    if bal is not None and m2 is not None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=bal.index, y=bal.values, name="Fed Balance Sheet (WALCL)"))
        fig.add_trace(go.Scatter(x=m2.index, y=m2.values, name="M2 Money Supply (M2SL)"))
        fig.update_layout(title="Fed Balance Sheet vs M2", legend=dict(x=0.02,y=0.98))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Need FRED API key to plot WALCL & M2 data.")

with colB:
    st.write("CFTC COT (Commitment of Traders) — weekly positions")
    st.info("Upload COT CSV downloaded from CFTC site (optional) to inspect positioning of major futures markets.")
    uploaded = st.file_uploader("Upload COT CSV (optional)", type=["csv"])
    if uploaded:
        try:
            cot = pd.read_csv(uploaded)
            st.write("COT preview:")
            st.dataframe(cot.head())
        except Exception:
            st.error("Failed to parse CSV. Ensure proper COT file format from cftc.gov.")

with colC:
    st.write("Sentiment & Greed/Fear")
    try:
        url = "https://edition.cnn.com/business/fear-and-greed"
        req = requests.get(url, timeout=10)
        if req.status_code == 200 and "Fear & Greed" in req.text:
            import re
            m = re.search(r'(\d{1,3})\s*\/\s*100', req.text)
            if m:
                score = int(m.group(1))
                st.metric("CNN Fear & Greed Index", f"{score} / 100")
            else:
                st.write("Greed & Fear page reachable; parsing may fail due to site changes.")
        else:
            st.write("CNN Fear & Greed not reachable or parsing blocked.")
    except Exception:
        st.write("Greed & Fear: unable to fetch (site blocked or offline)")

st.markdown("---")

# ------------------------
# Signals Panel: simple composite
# ------------------------
st.subheader("Signals & Composite Indicators")
st.write("Simple Risk Sentiment Composite (example): combining VIX (inverse), 10y-2y spread, and DXY trend.")

vix_series = yfin_download("^VIX", period="3mo")
vix_norm = 50
spread_norm = 50
dxy_norm = 50
try:
    if not vix_series.empty:
        vix_norm = np.interp(vix_series.iloc[-1], [vix_series.min(), vix_series.max()], [0,100])
    if us10 is not None and us2 is not None:
        latest_spread = (us10.iloc[-1] - us2.iloc[-1]) if (len(us10)>0 and len(us2)>0) else 0
        spread_norm = np.interp(latest_spread, [-200,200],[100,0])
    eurusd_series = yfin_download("EURUSD=X", period="3mo")
    if not eurusd_series.empty:
        latest_eurusd = eurusd_series.iloc[-1]
        dxy_norm = np.interp(latest_eurusd, [eurusd_series.min(), eurusd_series.max()], [100,0])
except Exception:
    pass

composite_score = (vix_norm * 0.4) + (spread_norm * 0.4) + (dxy_norm * 0.2)
composite_score = int(np.clip(composite_score, 0, 100))
st.metric("Risk Sentiment Composite (0=Extreme Risk-On, 100=Extreme Risk-Off)", f"{composite_score} / 100")

st.markdown("""
---
### Notes & Instructions
- This dashboard uses free public data sources: **FRED API** (macro & yields) and **Yahoo Finance (yfinance)** for tickers. Add your FRED API key into Streamlit secrets as `FRED_API_KEY` for full functionality.
- Some institutional indicators (MOVE index, cross-currency basis, realtime CDS) require paid vendors (ICE, Bloomberg). The free sources here cover core signals for most macro work.
- Streamlit Community Cloud runs apps on demand (ideal if you open the dashboard a few hours/day). For 24/7 uptime, deploy to Render/VPS.
- To extend: add AlphaVantage (set `ALPHA_VANTAGE_KEY`), TradingEconomics (paid), or Refinitiv/Bloomberg (institutional).
""")
