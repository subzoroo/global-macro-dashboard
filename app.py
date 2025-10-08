import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ==============================
# 📊 APP CONFIG
# ==============================
st.set_page_config(page_title="Ultimate Global Macro Dashboard", layout="wide")
st.title("🌍 Ultimate Global Macro Dashboard (Real-time)")

# ==============================
# 🔑 API KEY CONFIG
# ==============================
FRED_KEY = st.secrets.get("FRED_API_KEY", None)

# ==============================
# ⚙️ HELPER FUNCTIONS
# ==============================
@st.cache_data(ttl=3600)
def fred_series_latest(series_id, api_key):
    """
    Fetch latest observation from FRED safely.
    Returns (float_value_or_None, date_string_or_None)
    """
    if not api_key:
        return None, None
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&limit=1&sort_order=desc"
    try:
        r = requests.get(url, timeout=15)
        j = r.json()
        obs = j.get("observations", [])
        if not obs:
            return None, None
        val = obs[0].get("value")
        date = obs[0].get("date")
        try:
            v = float(val)
            return v, date
        except Exception:
            return None, date
    except Exception:
        return None, None


@st.cache_data(ttl=7200)
def get_yield_curve_data():
    """
    Fetch 2-year and 10-year Treasury yields (for yield curve spread)
    """
    gs2 = fred_series_latest("GS2", FRED_KEY)
    gs10 = fred_series_latest("GS10", FRED_KEY)
    if gs2[0] and gs10[0]:
        spread = gs10[0] - gs2[0]
    else:
        spread = None
    return gs2, gs10, spread


@st.cache_data(ttl=7200)
def get_asset_price(ticker):
    """
    Fetch recent close price of any asset (from Yahoo Finance)
    """
    data = yf.download(ticker, period="5d", interval="1d", progress=False)
    if not data.empty:
        return data["Close"].iloc[-1]
    return None


# ==============================
# 🧩 LEVEL 1 — CORE MACRO
# ==============================
st.header("LEVEL 1 — Core Macro (Economic Drivers)")
col1, col2, col3, col4 = st.columns(4)

with col1:
    fed_val, fed_date = fred_series_latest("FEDFUNDS", FRED_KEY)
    if fed_val is not None:
        st.metric(label="Fed Funds Rate", value=f"{fed_val:.2f}%", delta=f"as of {fed_date}")
    elif not FRED_KEY:
        st.warning("FRED API key belum diset di Streamlit secrets.")
    else:
        st.info("Fed Funds data belum tersedia.")

with col2:
    cpi_val, cpi_date = fred_series_latest("CPILFESL", FRED_KEY)
    if cpi_val is not None:
        st.metric(label="Core CPI (YoY)", value=f"{cpi_val:.2f}%", delta=f"as of {cpi_date}")
    else:
        st.info("CPI data belum tersedia atau tidak valid.")

with col3:
    payroll_val, payroll_date = fred_series_latest("PAYEMS", FRED_KEY)
    if payroll_val is not None:
        st.metric(label="Nonfarm Payrolls", value=f"{int(payroll_val):,}", delta=f"as of {payroll_date}")
    else:
        st.info("Payrolls data belum tersedia.")

with col4:
    gdp_val, gdp_date = fred_series_latest("GDP", FRED_KEY)
    if gdp_val is not None:
        st.metric(label="Real GDP (Quarterly)", value=f"{gdp_val:.2f}", delta=f"as of {gdp_date}")
    else:
        st.info("GDP data belum tersedia.")

# ==============================
# 🧭 LEVEL 2 — INTERMARKET RELATION
# ==============================
st.header("LEVEL 2 — Cross Market / Intermarket Flows")

gs2, gs10, spread = get_yield_curve_data()
col1, col2, col3 = st.columns(3)

with col1:
    if gs2[0] is not None:
        st.metric(label="2Y Treasury Yield", value=f"{gs2[0]:.2f}%", delta=f"as of {gs2[1]}")
with col2:
    if gs10[0] is not None:
        st.metric(label="10Y Treasury Yield", value=f"{gs10[0]:.2f}%", delta=f"as of {gs10[1]}")
with col3:
    if spread is not None:
        st.metric(label="Yield Curve Spread (10Y-2Y)", value=f"{spread:.2f}%", delta="Recession risk ↑ if negative")

# ==============================
# 💰 RISK SENTIMENT
# ==============================
st.header("MARKET SENTIMENT — Risk On / Risk Off")

col1, col2, col3, col4 = st.columns(4)

try:
    spx = get_asset_price("^GSPC")
    gold = get_asset_price("GC=F")
    usd = get_asset_price("DX-Y.NYB")
    vix = get_asset_price("^VIX")

    if spx and gold and usd and vix:
        st.metric(label="S&P 500", value=f"{spx:,.0f}")
        st.metric(label="Gold (USD/oz)", value=f"{gold:,.0f}")
        st.metric(label="US Dollar Index (DXY)", value=f"{usd:.2f}")
        st.metric(label="VIX (Volatility Index)", value=f"{vix:.2f}")
    else:
        st.info("Tidak semua data aset berhasil diambil.")
except Exception:
    st.warning("Gagal mengambil data pasar. Coba reload atau periksa koneksi.")

# ==============================
# 📈 OPTIONAL: FEAR & GREED INDEX
# ==============================
st.header("Fear & Greed Sentiment (CNN Index)")
try:
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    res = requests.get(url, timeout=10)
    data = res.json()
    latest_score = data["fear_and_greed"]["score"]
    rating = data["fear_and_greed"]["rating"]
    st.metric(label="Fear & Greed Index", value=f"{latest_score}", delta=rating)
except Exception:
    st.info("Tidak dapat memuat Fear & Greed Index dari CNN.")


st.markdown("---")
st.caption("Data source: FRED, Yahoo Finance, CNN | Built with ❤️ by Global Macro AI Dashboard")
