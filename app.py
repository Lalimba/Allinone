import streamlit as st
import ccxt
import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv

st.set_page_config(
    page_title="BTC Alpha Dashboard 2026",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Lokale .env nur für Entwicklung
load_dotenv()

def get_secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return os.getenv(key, default)

BINANCE_KEY = get_secret("BINANCE_API_KEY")
BINANCE_SECRET = get_secret("BINANCE_API_SECRET")

# Für öffentliche Daten sind Keys nicht nötig
exchange_config = {
    "enableRateLimit": True,
    "options": {"defaultType": "future"}
}

if BINANCE_KEY and BINANCE_SECRET:
    exchange_config["apiKey"] = BINANCE_KEY
    exchange_config["secret"] = BINANCE_SECRET

exchange = ccxt.binance(exchange_config)

@st.cache_data(ttl=30)
def fetch_market_data():
    try:
        # Futures-Ticker
        futures_ticker = exchange.fetch_ticker("BTC/USDT")
        futures_price = futures_ticker["last"]

        # Spot-Ticker
        spot_exchange = ccxt.binance({"enableRateLimit": True})
        spot_ticker = spot_exchange.fetch_ticker("BTC/USDT")
        spot_price = spot_ticker["last"]

        # Futures Public Endpoints
        funding = exchange.fapiPublicGetPremiumIndex({"symbol": "BTCUSDT"})
        oi = exchange.fapiPublicGetOpenInterest({"symbol": "BTCUSDT"})

        # DXY via Yahoo Finance
        dxy_hist = yf.Ticker("DX-Y.NYB").history(period="5d")
        dxy = float(dxy_hist["Close"].dropna().iloc[-1])

        return {
            "price": futures_price,
            "spot": spot_price,
            "funding": float(funding["lastFundingRate"]) * 100,
            "oi": float(oi["openInterest"]),
            "dxy": round(dxy, 2),
            "change": futures_ticker.get("percentage", 0.0)
        }
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=300)
def fetch_pro_data():
    # Kein CryptoQuant -> Platzhalter/Fallback
    cb_premium = None
    etf_flow = None
    return cb_premium, etf_flow

st.title("🛡️ BTC MARKET BIAS ENGINE")
st.caption("Auto-Update alle 30s")

@st.fragment(run_every="30s")
def live_dashboard():
    data = fetch_market_data()
    cb_prem, etf_flow = fetch_pro_data()

    if not data or "error" in data:
        st.error(f"Verbindung zur API fehlgeschlagen: {data.get('error', 'Unbekannter Fehler') if data else 'Keine Daten'}")
        return

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("BTC Futures", f"${data['price']:,.2f}", f"{data['change']:.2f}%")
    m2.metric("BTC Spot", f"${data['spot']:,.2f}")
    m3.metric("DXY Index", f"{data['dxy']}")
    m4.metric("Funding", f"{data['funding']:.4f}%")
    m5.metric("Open Interest", f"{data['oi']:,.0f}")

    st.markdown("---")

    col_left, col_right = st.columns([2, 1])

    score = 0
    if data["dxy"] < 101.5:
        score += 1
    if data["funding"] < 0.01:
        score += 1
    if data["spot"] > data["price"]:
        score += 1

    # ETF-Flow nur werten, wenn vorhanden
    if etf_flow is not None and etf_flow > 0:
        score += 1

    with col_left:
        st.subheader("📊 Bias Analysis & Signal")
        if score >= 3:
            st.success("### BIAS: CONSTRUCTIVE (Risk-On) 🟢")
            st.write("**Empfehlung:** BUY THE DIP / LONG ACCUMULATION")
        elif score <= 1:
            st.error("### BIAS: DEFENSIVE (Risk-Off) 🔴")
            st.write("**Empfehlung:** CAUTION / SHORT / INCREASE CASH")
        else:
            st.warning("### BIAS: NEUTRAL 🟡")
            st.write("**Empfehlung:** RANGE TRADING / SCALPING ONLY")

    with col_right:
        st.subheader("✅ Trade Checklist")
        st.checkbox("DXY Downwards?", value=(data["dxy"] < 102), disabled=True)
        st.checkbox("Spot over Futures?", value=(data["spot"] > data["price"]), disabled=True)
        st.checkbox("Funding Healthy?", value=(data["funding"] < 0.01), disabled=True)

        if cb_prem is None:
            st.info("Coinbase Premium: nicht verfügbar")
        else:
            st.info(f"Coinbase Premium: {cb_prem:.2f}")

    st.subheader("Spot-Futures Spread (Market Health)")
    spread = data["spot"] - data["price"]
    spread_df = pd.DataFrame({"Spread": [spread]})
    st.area_chart(spread_df)

live_dashboard()
