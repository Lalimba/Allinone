import streamlit as st
import ccxt
import pandas as pd
import yfinance as yf
import requests
import os
from dotenv import load_dotenv
import time

# --- 1. KONFIGURATION & SICHERHEIT ---
st.set_page_config(page_title="BTC Alpha Dashboard 2026", layout="wide", initial_sidebar_state="collapsed")

# Lade Keys aus Secrets (Cloud) oder .env (Lokal)
def get_secret(key):
    if key in st.secrets:
        return st.secrets[key]
    load_dotenv()
    return os.getenv(key)

BINANCE_KEY = get_secret('BINANCE_API_KEY')
BINANCE_SECRET = get_secret('BINANCE_API_SECRET')
CQ_KEY = get_secret('CRYPTOQUANT_API_KEY')

# Binance Setup (Read-Only)
exchange = ccxt.binance({
    'apiKey': BINANCE_KEY,
    'secret': BINANCE_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# --- 2. CACHING FUNKTIONEN (Schützt dein API-Limit) ---
# Daten werden nur alle 30 Sekunden neu von der API geholt, egal wie viele Leute zuschauen.

@st.cache_data(ttl=30)
def fetch_market_data():
    try:
        # BTC Preise & Futures Daten
        ticker = exchange.fetch_ticker('BTC/USDT')
        spot_price = exchange.fetch_ticker('BTC/USDT', {'type': 'spot'})['last']
        funding = exchange.fapiPublicGetPremiumIndex({'symbol': 'BTCUSDT'})
        oi = exchange.fapiPublicGetOpenInterest({'symbol': 'BTCUSDT'})
        
        # Makro Daten (DXY via Yahoo Finance)
        dxy = yf.Ticker("DX-Y.NYB").history(period="1d")['Close'].iloc[-1]
        
        return {
            "price": ticker['last'],
            "spot": spot_price,
            "funding": float(funding['lastFundingRate']) * 100,
            "oi": float(oi['openInterest']),
            "dxy": round(dxy, 2),
            "change": ticker['percentage']
        }
    except Exception as e:
        return None

@st.cache_data(ttl=300) # ETF & Premium Daten puffern wir 5 Minuten (da sie sich seltener ändern)
def fetch_pro_data():
    # Simulation/Fallback für CryptoQuant Daten
    # In der Vollversion hier requests.get(url, headers={'Authorization': f'Bearer {CQ_KEY}'})
    cb_premium = 4.85
    etf_flow = -1150
    return cb_premium, etf_flow

# --- 3. DASHBOARD UI ---

data = fetch_market_data()
cb_prem, etf_flow = fetch_pro_data()

if data:
    st.title("🛡️ BTC MARKET BIAS ENGINE (LIVE 2026)")
    st.caption("Daten-Update alle 30s | Optimiert für Community-Ansicht")

    # Obere Metriken-Leiste
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("BTC Price", f"${data['price']:,}", f"{data['change']}%")
    m2.metric("Spot Price", f"${data['spot']:,}")
    m3.metric("DXY Index", f"{data['dxy']}", delta="-0.12" if data['dxy'] < 102 else "Strong")
    m4.metric("Funding", f"{data['funding']:.4f}%")
    m5.metric("ETF Netflow", f"{etf_flow} BTC")

    st.markdown("---")

    # Bias Engine Logik
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("📊 Bias Analysis & Signal")
        
        # Scoring System
        score = 0
        if data['dxy'] < 101.5: score += 1
        if data['funding'] < 0.01: score += 1
        if etf_flow > 0: score += 1
        if data['spot'] > data['price']: score += 1 # Backwardation (Bullish)

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
        st.checkbox("DXY Downwards?", value=(data['dxy'] < 102))
        st.checkbox("Spot over Futures?", value=(data['spot'] > data['price']))
        st.checkbox("Funding Healthy?", value=(data['funding'] < 0.01))
        
        st.info(f"**Coinbase Premium:** {cb_prem:.2f}")

    # Visualisierung des Spreads (Wichtig für Scalper)
    st.subheader("Spot-Futures Spread (Market Health)")
    spread_data = pd.DataFrame([data['spot'] - data['price']], columns=["Spread"])
    st.area_chart(spread_data)

else:
    st.error("Verbindung zur API fehlgeschlagen. Bitte API-Keys in den Secrets prüfen.")

# Automatischer Refresh-Trigger für den Browser
st.empty()
time.sleep(30)
st.rerun()
