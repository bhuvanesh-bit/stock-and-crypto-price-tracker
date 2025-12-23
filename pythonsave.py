import os
import requests
import sqlite3
import pandas as pd
import yfinance as yf
import streamlit as st
import smtplib
from email.mime.text import MIMEText

DB = "tracker.db"
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ---------------------------------------------------------
# DB
# ---------------------------------------------------------
def safe_connect(db_path=DB):
    return sqlite3.connect(db_path)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def _ensure_close(df, col="Close"):
    if col not in df.columns:
        for c in df.columns:
            if str(c).lower() == "close":
                return df[c]
        raise ValueError("Close column not found")
    return df[col]

# ---------------------------------------------------------
# STOCK DATA
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def get_stock_data(symbol, period="1mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df["Close"] = _ensure_close(df)
        return df
    except:
        return pd.DataFrame()

# ---------------------------------------------------------
# CRYPTO DATA
# ---------------------------------------------------------
def get_crypto_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        return requests.get(url).json()[coin_id]["usd"]
    except:
        return None

@st.cache_data(ttl=60)
def get_crypto_history(coin_id, days=30):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
        prices = requests.get(url).json()["prices"]
        df = pd.DataFrame(prices, columns=["timestamp", "Close"])
        df["Date"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except:
        return pd.DataFrame()

# ---------------------------------------------------------
# INDICATORS
# ---------------------------------------------------------
def add_indicators(df):
    if df.empty:
        return df
    close = df["Close"]
    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + rs))
    std = close.rolling(20).std()
    df["UB"] = df["MA20"] + 2 * std
    df["LB"] = df["MA20"] - 2 * std
    return df

# ---------------------------------------------------------
# DATABASE TABLES
# ---------------------------------------------------------
def create_tables():
    with safe_connect() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS portfolio(
            id INTEGER PRIMARY KEY,
            asset TEXT,
            quantity REAL,
            buy_price REAL
        )""")
        con.commit()

def get_portfolio():
    with safe_connect() as con:
        return pd.read_sql("SELECT * FROM portfolio", con)

def add_to_portfolio(asset, qty, price):
    with safe_connect() as con:
        con.execute(
            "INSERT INTO portfolio(asset, quantity, buy_price) VALUES (?,?,?)",
            (asset.upper(), qty, price)
        )
        con.commit()

# ---------------------------------------------------------
# ALERTS
# ---------------------------------------------------------
def send_email_alert(to, subject, message):
    if not EMAIL_USER or not EMAIL_PASS:
        return False
    try:
        msg = MIMEText(message)
        msg["From"] = EMAIL_USER
        msg["To"] = to
        msg["Subject"] = subject
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_USER, EMAIL_PASS)
            s.send_message(msg)
        return True
    except:
        return False

def send_telegram_alert(bot_token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message})
        return True
    except:
        return False

# ---------------------------------------------------------
# AUTH
# ---------------------------------------------------------
def signup_page():
    st.title("📝 Create Account")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Create"):
        st.session_state["APP_USER"] = u
        st.session_state["APP_PASS"] = p
        st.session_state["show_signup"] = False
        st.success("Account created")
        st.rerun()

def login_page():
    if st.session_state.get("show_signup"):
        signup_page()
        return
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == st.session_state.get("APP_USER","admin") and p == st.session_state.get("APP_PASS","admin"):
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    if st.button("Create Account"):
        st.session_state["show_signup"] = True
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------
def dashboard():
    st.set_page_config("Tracker", "📈")
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    st.title("📊 Crypto & Stock Tracker")
    create_tables()

    # -------- Market Data --------
    choice = st.selectbox("Type", ["Stock", "Crypto"])
    symbol = st.text_input("Symbol", "AAPL" if choice=="Stock" else "BTC")

    if st.button("Fetch Data"):
        df = get_stock_data(symbol) if choice=="Stock" else get_crypto_history(symbol.lower())
        df = add_indicators(df)
        if not df.empty:
            st.line_chart(df.set_index("Date")["Close"])
            st.dataframe(df.tail(10))

    # -------- Alerts --------
    st.write("---")
    st.subheader("⏰ Price Alerts")
    a = st.text_input("Alert Asset")
    t = st.number_input("Threshold", value=0.0)
    email = st.checkbox("Email")
    tg = st.checkbox("Telegram")

    if st.button("Check Alert"):
        price = get_crypto_price(a.lower()) if not a.isalpha() else (
            get_stock_data(a)["Close"].iloc[-1]
        )
        if price >= t:
            msg = f"{a} crossed {t}. Current: {price}"
            if email:
                send_email_alert(EMAIL_USER, f"{a} Alert", msg)
            if tg:
                send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)
            st.success("Alert triggered")
        else:
            st.info("No alert")

    # -------- Portfolio --------
    st.write("---")
    st.subheader("📦 Portfolio")

    with st.form("portfolio"):
        pa = st.text_input("Asset")
        pq = st.number_input("Quantity", min_value=0.0)
        pp = st.number_input("Buy Price", min_value=0.0)
        if st.form_submit_button("Add"):
            add_to_portfolio(pa, pq, pp)
            st.success("Added")
            st.rerun()

    st.dataframe(get_portfolio())

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("show_signup", False)
    if not st.session_state["logged_in"]:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()
