import os
import requests
import sqlite3
from datetime import datetime
import pandas as pd
import yfinance as yf
import streamlit as st
import smtplib
from email.mime.text import MIMEText

DB = "tracker.db"
EMAIL_USER = os.getenv("EMAIL_USER")  # optional
EMAIL_PASS = os.getenv("EMAIL_PASS")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ---------------------------------------------------------
# DB CONNECTION
# ---------------------------------------------------------
def safe_connect(db_path=DB):
    return sqlite3.connect(db_path)

# ---------------------------------------------------------
# FIX CLOSE COLUMN
# ---------------------------------------------------------
def _ensure_close(df, col="Close"):
    if col not in df.columns:
        for c in df.columns:
            if str(c).lower() == "close":
                series = df[c]
                return series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
        raise ValueError("Close column not found")
    series = df[col]
    if isinstance(series, pd.DataFrame):
        numeric_cols = [c for c in series.columns if pd.api.types.is_numeric_dtype(series[c])]
        return series[numeric_cols[0]] if numeric_cols else series.iloc[:, 0]
    return series

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
        r = requests.get(url)
        return r.json()[coin_id]["usd"]
    except:
        return None

@st.cache_data(ttl=60)
def get_crypto_history(coin_id, days=30):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
        prices = requests.get(url).json()["prices"]
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["Date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.rename(columns={"price": "Close"})
        return df
    except:
        return pd.DataFrame()

# ---------------------------------------------------------
# INDICATORS
# ---------------------------------------------------------
def add_moving_averages(df):
    df = df.copy()
    close = _ensure_close(df)
    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    return df

def compute_RSI(df, period=14):
    df = df.copy()
    close = _ensure_close(df)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def add_bollinger(df):
    df = df.copy()
    close = _ensure_close(df)
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    df["MB"] = mid
    df["UB"] = mid + (2 * std)
    df["LB"] = mid - (2 * std)
    return df

def add_all_indicators(df):
    if df.empty:
        return df

    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="ignore")
        df = df.sort_values("Date")

    df = add_moving_averages(df)
    df = compute_RSI(df)
    df = add_bollinger(df)
    return df

# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------
def create_tables():
    with safe_connect(DB) as con:
        con.execute("CREATE TABLE IF NOT EXISTS prices(id INTEGER PRIMARY KEY, asset TEXT, price REAL, timestamp TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS portfolio(id INTEGER PRIMARY KEY, asset TEXT, quantity REAL, buy_price REAL)")
        con.execute("CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, asset TEXT, threshold REAL, method TEXT)")
        con.commit()

def get_portfolio():
    try:
        with safe_connect(DB) as con:
            return pd.read_sql("SELECT * FROM portfolio", con)
    except:
        return pd.DataFrame()

def add_to_portfolio(asset, quantity, buy_price):
    try:
        with safe_connect(DB) as con:
            con.execute(
                "INSERT INTO portfolio (asset, quantity, buy_price) VALUES (?, ?, ?)",
                (asset.upper(), quantity, buy_price)
            )
            con.commit()
        return True
    except Exception as e:
        st.error(f"DB Error: {e}")
        return False


# ---------------------------------------------------------
# AUTH: SIGNUP + LOGIN
# ---------------------------------------------------------
def signup_page():
    st.title("📝 Create Account")

    u = st.text_input("New Username")
    p = st.text_input("New Password", type="password")
    cp = st.text_input("Confirm Password", type="password")

    if st.button("Create Account"):
        if not u or not p:
            st.error("Username & password required")
        elif p != cp:
            st.error("Passwords must match")
        else:
            st.session_state["APP_USER"] = u
            st.session_state["APP_PASS"] = p
            st.session_state["show_signup"] = False
            st.success("Account created!")
            st.rerun()

def login_page():
    if st.session_state.get("show_signup"):
        signup_page()
        return

    st.title("🔐 Login")

    USER = st.session_state.get("APP_USER", "admin")
    PASS = st.session_state.get("APP_PASS", "admin")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == USER and p == PASS:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Incorrect username or password")

    if st.button("Create Account"):
        st.session_state["show_signup"] = True
        st.rerun()

    st.stop()

# ---------------------------------------------------------
# COINGECKO ID MAP
# ---------------------------------------------------------
def coin_symbol_to_id(symbol):
    mapping = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "LTC": "litecoin",
        "DOGE": "dogecoin",
        "SOL": "solana",
        "BNB": "binancecoin",
        "ADA": "cardano",
    }
    symbol = symbol.strip().upper()
    return mapping.get(symbol, symbol.lower())

# ---------------------------------------------------------
# ALERT MODULE
# ---------------------------------------------------------
def send_email_alert(to, subject, message):
    if not EMAIL_USER or not EMAIL_PASS:
        return False
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_USER, EMAIL_PASS)
            s.sendmail(EMAIL_USER, to, msg.as_string())
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

def check_alert(asset, current_price, threshold, methods):
    """methods = {'email': send_email_alert, 'telegram': send_telegram_alert}"""
    if current_price >= threshold:
        msg = f"🚨 {asset} crossed {threshold}! Current: {current_price}"

        results = {}
        for name, func in methods.items():
            if name == "email":
                results["email"] = func(EMAIL_USER, f"{asset} Alert", msg)
            elif name == "telegram":
                results["telegram"] = func(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)

        return results

    return False

# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------
def dashboard():
    st.set_page_config(page_title="Tracker", page_icon="📈")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    st.title("📊 Crypto & Stock Tracker")

    create_tables()

    choice = st.selectbox("Choose Type", ["Stock", "Crypto"])
    symbol = st.text_input("Symbol", "BTC" if choice == "Crypto" else "AAPL")

    if st.button("Fetch Data"):
        if choice == "Stock":
            df = get_stock_data(symbol)
        else:
            df = get_crypto_history(coin_symbol_to_id(symbol))

        df = add_all_indicators(df)

        if not df.empty:
            st.line_chart(df.set_index("Date")["Close"])
            st.dataframe(df.tail(10))

    # -------------------------
    # ALERT UI
    # -------------------------
    st.write("---")
    st.subheader("⏰ Price Alerts")

    a = st.text_input("Alert Asset")
    t = st.number_input("Threshold Price", value=0.0)
    use_email = st.checkbox("fun.knowledge7@gmail.com")
    use_tg = st.checkbox("Telegram Alert")

    if st.button("Check Alert Now"):
        current = None

        if a.isalpha() and len(a) <= 5:
            df = get_stock_data(a)
            current = float(df["Close"].iloc[-1]) if not df.empty else None
            name = a.upper()
        else:
            cid = coin_symbol_to_id(a)
            current = get_crypto_price(cid)
            name = cid

        if current is None:
            st.error("Price fetch failed")
        else:
            methods = {}
            if use_email:
                methods["email"] = send_email_alert
            if use_tg:
                methods["telegram"] = send_telegram_alert

            res = check_alert(name, current, t, methods)

            if res:
                st.success(f"Alert Triggered → {res}")
            else:
                st.info(f"No Alert. Price {current} < {t}")

    # -------------------------
    # PORTFOLIO
    # -------------------------
                                
    st.write("---")
    st.subheader("📦 Portfolio")

    with st.form("portfolio_form"):
        p_asset = st.text_input("Asset (BTC / AAPL)")
        p_qty = st.number_input("Quantity", min_value=0.0, step=0.01)
        p_price = st.number_input("Buy Price", min_value=0.0, step=0.01)
        add_btn = st.form_submit_button("Add to Portfolio")

    if add_btn:
        if p_asset and p_qty > 0 and p_price > 0:
            success = add_to_portfolio(p_asset, p_qty, p_price)
            if success:
                st.success("Asset added to portfolio")
                st.rerun()
            else:
                st.warning("Please fill all fields correctly")

    st.dataframe(get_portfolio())

    

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "show_signup" not in st.session_state:
        st.session_state["show_signup"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()



