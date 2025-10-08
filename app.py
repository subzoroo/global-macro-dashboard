import streamlit as st
import pandas_datareader.data as web
import pandas as pd
import datetime as dt
import plotly.express as px
import os

# === Konfigurasi Dasar ===
st.set_page_config(page_title="Ultimate Global Macro Dashboard", layout="wide")

st.title("🌐 Ultimate Global Macro Dashboard — Level 1: Core Macro")

# === Ambil API Key dari secrets ===
FRED_API_KEY = st.secrets.get("FRED_API_KEY", None)
if not FRED_API_KEY:
    st.warning("⚠️ Masukkan FRED_API_KEY di Streamlit secrets untuk menampilkan data ekonomi.")
    st.stop()

# === Tentukan rentang waktu ===
start = dt.datetime(2015, 1, 1)
end = dt.datetime.now()

# === Ambil data dari FRED ===
def get_fred_data(series_id, name):
    try:
        data = web.DataReader(series_id, "fred", start, end, api_key=FRED_API_KEY)
        data = data.dropna()
        data.columns = [name]
        return data
    except Exception as e:
        st.error(f"Gagal ambil data {name}: {e}")
        return pd.DataFrame()

# === Dataset utama ===
fedfunds = get_fred_data("FEDFUNDS", "Fed Funds Rate")
core_cpi = get_fred_data("CPILFESL", "Core CPI")
payems = get_fred_data("PAYEMS", "Nonfarm Payrolls")
gdp = get_fred_data("GDP", "US GDP")

# === Gabungkan semua data ===
data_dict = {"Fed Funds": fedfunds, "Core CPI": core_cpi, "Payrolls": payems, "GDP": gdp}
combined_data = pd.concat(data_dict.values(), axis=1)

if combined_data.empty:
    st.warning("Tidak ada data yang berhasil dimuat.")
else:
    # === Buat 4 kolom metrik ===
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fed Funds Rate", f"{fedfunds.iloc[-1,0]:.2f}%")
    col2.metric("Core CPI (YoY)", f"{core_cpi.iloc[-1,0]:.2f}")
    col3.metric("Nonfarm Payrolls (k)", f"{payems.iloc[-1,0]/1000:.1f}M")
    col4.metric("GDP (Trillion USD)", f"{gdp.iloc[-1,0]/1000:.1f}")

    st.markdown("---")
    st.subheader("📈 Visualisasi Data Ekonomi Utama")

    # === Grafik interaktif dengan Plotly ===
    fig = px.line(combined_data, x=combined_data.index, y=combined_data.columns,
                  title="Core Macro Overview", markers=True)
    st.plotly_chart(fig, use_container_width=True)
