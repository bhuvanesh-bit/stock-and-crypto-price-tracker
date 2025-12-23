# # # tracker_app.py
# # import os
# # import requests
# # import sqlite3
# # from datetime import datetime
# # import pandas as pd
# # import yfinance as yf
# # import streamlit as st
# # import smtplib
# # from email.mime.text import MIMEText
# # from typing import Callable, Dict, Optional

# # # ---------------------------
# # # Config (use env vars or Streamlit secrets)
# # # ---------------------------
# # DB = os.getenv("TRACKER_DB", "tracker.db")
# # EMAIL_USER = os.getenv("EMAIL_USER")       # example: youremail@gmail.com
# # EMAIL_PASS = os.getenv("EMAIL_PASS")       # app password or SMTP password
# # TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# # TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# # # ---------------------------
# # # Helpers / Utils
# # # ---------------------------
# # def safe_connect(db_path=DB):
# #     return sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

# # def coin_symbol_to_coingecko_id(symbol: str) -> str:
# #     """
# #     Best-effort mapping: accepts symbols like 'BTC', 'ETH' or ids like 'bitcoin'.
# #     For more symbols add to the map or call CoinGecko coin/list (not done here to avoid extra requests).
# #     """
# #     mapping = {
# #         "BTC": "bitcoin",
# #         "ETH": "ethereum",
# #         "LTC": "litecoin",
# #         "DOGE": "dogecoin",
# #         "ADA": "cardano",
# #         "BNB": "binancecoin",
# #         "SOL": "solana",
# #         # extend as needed
# #     }
# #     symbol = symbol.strip().lower()
# #     # if user supplied coingecko id already (e.g. "bitcoin"), return it:
# #     if symbol in mapping.values():
# #         return symbol
# #     # convert upper symbol like 'btc' -> 'BTC' key
# #     return mapping.get(symbol.upper(), symbol)  # fallback to the raw string

# # # ---------------------------
# # # MODULE 1: DATA FETCHER (Yahoo Finance + CoinGecko)
# # # ---------------------------
# # @st.cache_data(ttl=60)  # cache for 60 seconds in Streamlit
# # def get_stock_data(symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
# #     try:
# #         df = yf.download(symbol, period=period, interval=interval, progress=False)
# #         if df.empty:
# #             return pd.DataFrame()
# #         df = df.reset_index()
# #         # Ensure column names we expect
# #         if "Close" not in df.columns:
# #             raise ValueError("Missing 'Close' column from yfinance data.")
# #         return df
# #     except Exception as e:
# #         st.error(f"Failed to fetch stock data for {symbol}: {e}")
# #         return pd.DataFrame()

# # def get_crypto_price(coin_id: str = "bitcoin", currency: str = "usd") -> Optional[float]:
# #     try:
# #         url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}"
# #         r = requests.get(url, timeout=10)
# #         r.raise_for_status()
# #         data = r.json()
# #         return data.get(coin_id, {}).get(currency)
# #     except Exception as e:
# #         st.error(f"Failed to fetch crypto price for {coin_id}: {e}")
# #         return None

# # @st.cache_data(ttl=60)
# # def get_crypto_history(coin_id: str = "bitcoin", days: int = 30) -> pd.DataFrame:
# #     try:
# #         url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
# #         r = requests.get(url, timeout=10)
# #         r.raise_for_status()
# #         data = r.json()
# #         prices = data.get("prices", [])
# #         df = pd.DataFrame(prices, columns=["timestamp", "price"])
# #         df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
# #         # normalize to same format as yfinance: timestamp -> Date, price -> Close
# #         df = df.rename(columns={"timestamp": "Date", "price": "Close"})
# #         return df
# #     except Exception as e:
# #         st.error(f"Failed to fetch crypto history for {coin_id}: {e}")
# #         return pd.DataFrame()

# # # ---------------------------
# # # MODULE 2: INDICATORS (MA, RSI, Bollinger Bands)
# # # ---------------------------
# # def add_moving_averages(df: pd.DataFrame, short: int = 20, long: int = 50) -> pd.DataFrame:
# #     df = df.copy()
# #     df["MA20"] = df["Close"].rolling(window=short, min_periods=1).mean()
# #     df["MA50"] = df["Close"].rolling(window=long, min_periods=1).mean()
# #     return df

# # def compute_RSI(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
# #     # Classic RSI using simple rolling means. For less-laggy RSI use exponential moving averages (ewm).
# #     df = df.copy()
# #     delta = df["Close"].diff()
# #     gain = delta.clip(lower=0)
# #     loss = -delta.clip(upper=0)
# #     avg_gain = gain.rolling(period, min_periods=period).mean()
# #     avg_loss = loss.rolling(period, min_periods=period).mean()
# #     rs = avg_gain / (avg_loss.replace(0, pd.NA))
# #     df["RSI"] = 100 - (100 / (1 + rs))
# #     return df

# # def add_bollinger_bands(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
# #     df = df.copy()
# #     df["MB"] = df["Close"].rolling(period, min_periods=1).mean()
# #     df["UB"] = df["MB"] + 2 * df["Close"].rolling(period, min_periods=1).std()
# #     df["LB"] = df["MB"] - 2 * df["Close"].rolling(period, min_periods=1).std()
# #     return df

# # def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
# #     if df.empty:
# #         return df
# #     df = df.sort_values(by="Date" if "Date" in df.columns else "index").reset_index(drop=True)
# #     # Ensure a Date column for uniformity
# #     if "Date" not in df.columns and "DateTime" in df.columns:
# #         df = df.rename(columns={"DateTime": "Date"})
# #     # If DataFrame from yfinance has 'Date' as datetime index, ensure it's present:
# #     if "Date" not in df.columns and "index" in df.columns:
# #         df = df.rename(columns={"index": "Date"})
# #     df = add_moving_averages(df)
# #     df = compute_RSI(df)
# #     df = add_bollinger_bands(df)
# #     return df

# # # ---------------------------
# # # MODULE 3: DATABASE MODULE (SQLite)
# # # ---------------------------
# # def create_tables(db_path=DB):
# #     with safe_connect(db_path) as con:
# #         cur = con.cursor()
# #         cur.execute("""
# #             CREATE TABLE IF NOT EXISTS prices (
# #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
# #                 asset TEXT,
# #                 price REAL,
# #                 timestamp TEXT
# #             );
# #         """)
# #         cur.execute("""
# #             CREATE TABLE IF NOT EXISTS portfolio (
# #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
# #                 asset TEXT,
# #                 quantity REAL,
# #                 buy_price REAL
# #             );
# #         """)
# #         cur.execute("""
# #             CREATE TABLE IF NOT EXISTS alerts (
# #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
# #                 asset TEXT,
# #                 threshold REAL,
# #                 method TEXT
# #             );
# #         """)
# #         con.commit()

# # def insert_price(asset: str, price: float, db_path=DB):
# #     ts = datetime.utcnow().isoformat()
# #     with safe_connect(db_path) as con:
# #         cur = con.cursor()
# #         cur.execute(
# #             "INSERT INTO prices(asset, price, timestamp) VALUES (?, ?, ?)",
# #             (asset, price, ts),
# #         )
# #         con.commit()

# # def get_portfolio(db_path=DB) -> pd.DataFrame:
# #     with safe_connect(db_path) as con:
# #         df = pd.read_sql_query("SELECT * FROM portfolio", con)
# #     return df

# # # ---------------------------
# # # MODULE 4: ALERT SYSTEM MODULE (Email + Telegram)
# # # ---------------------------
# # def send_email_alert(to: str, subject: str, message: str) -> bool:
# #     if not EMAIL_USER or not EMAIL_PASS:
# #         st.warning("Email credentials not configured (EMAIL_USER / EMAIL_PASS). Skipping email.")
# #         return False
# #     try:
# #         msg = MIMEText(message)
# #         msg["Subject"] = subject
# #         msg["From"] = EMAIL_USER
# #         msg["To"] = to
# #         with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
# #             server.login(EMAIL_USER, EMAIL_PASS)
# #             server.sendmail(EMAIL_USER, [to], msg.as_string())
# #         return True
# #     except Exception as e:
# #         st.error(f"Failed to send email alert: {e}")
# #         return False

# # def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
# #     try:
# #         if not bot_token or not chat_id:
# #             st.warning("Telegram credentials not configured. Skipping telegram.")
# #             return False
# #         url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
# #         data = {"chat_id": chat_id, "text": message}
# #         r = requests.post(url, data=data, timeout=10)
# #         r.raise_for_status()
# #         return True
# #     except Exception as e:
# #         st.error(f"Failed to send telegram alert: {e}")
# #         return False

# # def check_alert(asset: str, current_price: float, threshold: float, alert_methods: Dict[str, Callable[[str, str, str], bool]]):
# #     """
# #     alert_methods: dict of method_name -> function (for email, telegram, etc.)
# #     Each function should accept parameters (to_or_id, subject_or_none, message) or be wrapped appropriately.
# #     """
# #     if current_price is None:
# #         return False
# #     if current_price >= threshold:
# #         message = f"🚨 {asset} crossed {threshold:.4f}! Current: {current_price:.4f} (UTC {datetime.utcnow().isoformat()})"
# #         # attempt each provided alert method
# #         results = {}
# #         for key, func in alert_methods.items():
# #             try:
# #                 if key == "email":
# #                     results[key] = func(os.getenv("ALERT_EMAIL_TO", EMAIL_USER), f"{asset} Alert", message)
# #                 elif key == "telegram":
# #                     results[key] = func(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
# #                 else:
# #                     # generic call: pass message only
# #                     results[key] = func(message)
# #             except Exception as e:
# #                 results[key] = False
# #                 st.error(f"Alert method {key} failed: {e}")
# #         return results
# #     return False

# # # ---------------------------
# # # MODULE 5: PORTFOLIO TRACKER MODULE
# # # ---------------------------
# # def calculate_portfolio_value(df: pd.DataFrame, live_prices: Dict[str, float]) -> pd.DataFrame:
# #     df = df.copy()
# #     df["Current Price"] = df["asset"].apply(lambda x: live_prices.get(x, 0.0))
# #     df["Value"] = df["Current Price"] * df["quantity"]
# #     df["P/L"] = (df["Current Price"] - df["buy_price"]) * df["quantity"]
# #     return df

# # # ---------------------------
# # # MODULE 6: STREAMLIT DASHBOARD MODULE
# # # ---------------------------
# # def dashboard():
# #     st.set_page_config(page_title="Crypto & Stock Tracker", page_icon="📈")
# #     st.title("📈 Real-Time Crypto & Stock Tracker")

# #     create_tables()  # ensure DB exists

# #     choice = st.selectbox("Choose asset type", ["Stock", "Crypto"])
# #     symbol = st.text_input("Enter symbol or id (e.g. AAPL or BTC or bitcoin)", value="BTC" if choice == "Crypto" else "AAPL")

# #     col1, col2 = st.columns([2, 1])
# #     with col1:
# #         period = st.selectbox("Period", ["7d", "14d", "1mo", "3mo", "6mo", "1y"])
# #     with col2:
# #         interval = st.selectbox("Interval", ["1d", "1h", "30m"])

# #     if st.button("Fetch Data"):
# #         if not symbol:
# #             st.warning("Please enter a symbol.")
# #             return

# #         if choice == "Stock":
# #             df = get_stock_data(symbol, period=period, interval=interval)
# #             if df.empty:
# #                 st.info("No stock data returned.")
# #                 return
# #             # ensure Date column exists
# #             if "Date" not in df.columns:
# #                 df = df.rename(columns={"index": "Date"}) if "index" in df.columns else df
# #             df["Date"] = pd.to_datetime(df["Date"])
# #             df = add_all_indicators(df)
# #             st.subheader(f"{symbol.upper()} - Closing Price")
# #             st.line_chart(df.set_index("Date")["Close"])
# #             st.subheader("Recent Data & Indicators")
# #             st.dataframe(df.tail(10), use_container_width=True)
# #             latest_price = df["Close"].iloc[-1]
# #             insert_price(symbol.upper(), float(latest_price))
# #             st.metric(label=f"{symbol.upper()} Latest", value=f"{latest_price:.4f}")

# #         else:  # Crypto
# #             coin_id = coin_symbol_to_coingecko_id(symbol)
# #             price = get_crypto_price(coin_id)
# #             if price is None:
# #                 st.info("No crypto price available.")
# #                 return
# #             insert_price(coin_id, float(price))
# #             st.metric(label=f"{coin_id.upper()} Price (USD)", value=f"${price:.4f}")
# #             df = get_crypto_history(coin_id, days=30)
# #             if not df.empty:
# #                 df = add_all_indicators(df)
# #                 st.subheader("Price History (30d)")
# #                 st.line_chart(df.set_index("Date")["Close"])
# #                 st.subheader("Recent Data & Indicators")
# #                 st.dataframe(df.tail(10), use_container_width=True)

# #     # Portfolio viewer
# #     st.write("---")
# #     st.subheader("Portfolio")
# #     try:
# #         portfolio_df = get_portfolio()
# #         if portfolio_df.empty:
# #             st.info("Portfolio is empty. Use DB to insert holdings (insert via other UI or direct SQL).")
# #         else:
# #             # Build live prices key-value map for assets present in portfolio
# #             unique_assets = portfolio_df["asset"].unique().tolist()
# #             live_prices = {}
# #             for a in unique_assets:
# #                 # try stock first, else coin
# #                 s = get_stock_data(a, period="7d", interval="1d")
# #                 if not s.empty:
# #                     live_prices[a] = float(s["Close"].iloc[-1])
# #                 else:
# #                     # try coinGecko id conversion
# #                     cid = coin_symbol_to_coingecko_id(a)
# #                     cp = get_crypto_price(cid)
# #                     live_prices[a] = float(cp) if cp is not None else 0.0
# #             val_df = calculate_portfolio_value(portfolio_df, live_prices)
# #             st.dataframe(val_df, use_container_width=True)
# #             st.metric("Total Portfolio Value (USD)", value=f"${val_df['Value'].sum():.2f}")
# #     except Exception as e:
# #         st.error(f"Failed to load portfolio: {e}")

# #     # Alerts UI
# #     st.write("---")
# #     st.subheader("Quick Alert Checker")
# #     alert_asset = st.text_input("Asset for quick check (AAPL or BTC)", value="")
# #     alert_threshold = st.number_input("Alert threshold (price)", value=0.0, format="%.4f")
# #     email_alert = st.checkbox("Send email on trigger (uses EMAIL_USER/EMAIL_PASS)", value=False)
# #     telegram_alert = st.checkbox("Send Telegram on trigger (uses TELEGRAM env vars)", value=False)

# #     if st.button("Check Alert Now"):
# #         if not alert_asset or alert_threshold <= 0:
# #             st.warning("Provide asset and threshold > 0.")
# #         else:
# #             # figure out price
# #             if alert_asset.isalpha() and len(alert_asset) <= 5:  # heuristic: stock ticker or crypto symbol
# #                 # try stock then crypto
# #                 s = get_stock_data(alert_asset, period="7d", interval="1d")
# #                 if not s.empty:
# #                     current = float(s["Close"].iloc[-1])
# #                     display_name = alert_asset.upper()
# #                 else:
# #                     cid = coin_symbol_to_coingecko_id(alert_asset)
# #                     current = get_crypto_price(cid)
# #                     display_name = cid
# #             else:
# #                 # treat as coin id
# #                 cid = coin_symbol_to_coingecko_id(alert_asset)
# #                 current = get_crypto_price(cid)
# #                 display_name = cid

# #             if current is None:
# #                 st.error("Could not determine current price.")
# #             else:
# #                 methods = {}
# #                 if email_alert:
# #                     methods["email"] = send_email_alert
# #                 if telegram_alert:
# #                     methods["telegram"] = send_telegram_alert
# #                 res = check_alert(display_name, float(current), float(alert_threshold), methods)
# #                 if res:
# #                     st.success(f"Alert triggered for {display_name}: current={current:.4f}. Methods: {res}")
# #                 else:
# #                     st.info(f"No alert: {display_name} current price {current:.4f} is below {alert_threshold:.4f}")

# # def main():
# #     dashboard()

# # if __name__ == "__main__":
# #     main()







# # tracker_app_fixed.py
# import os
# import requests
# import sqlite3
# from datetime import datetime
# import pandas as pd
# import yfinance as yf
# import streamlit as st
# import smtplib
# from email.mime.text import MIMEText
# from typing import Callable, Dict, Optional

# # ---------------------------
# # Config (use env vars or Streamlit secrets)
# # ---------------------------
# DB = os.getenv("TRACKER_DB", "tracker.db")
# EMAIL_USER = os.getenv("EMAIL_USER")       # example: youremail@gmail.com
# EMAIL_PASS = os.getenv("EMAIL_PASS")       # app password or SMTP password
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# # ---------------------------
# # Helpers / Utils
# # ---------------------------

# def safe_connect(db_path=DB):
#     # allow sqlite to return rows as normal tuples (pandas read_sql will handle conversion)
#     return sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)


# def _ensure_close_series(df: pd.DataFrame, close_col: str = "Close") -> pd.Series:
#     """Return a 1-D pandas Series for the closing price even if df[Close] is a DataFrame or MultiIndex.

#     Raises ValueError if it cannot find a sensible Close column.
#     """
#     if close_col not in df.columns:
#         # try to find a Close-like column in MultiIndex or prefixed columns
#         # if columns are MultiIndex like ("Close", "") or ("AAPL", "Close")
#         cols = df.columns
#         # flatten multiindex to strings and search
#         if isinstance(cols, pd.MultiIndex):
#             # look for any column where the second level is 'Close' or first level is 'Close'
#             for c in cols:
#                 if isinstance(c, tuple):
#                     if str(c[-1]).lower() == "close":
#                         return df[c].iloc[:, 0] if isinstance(df[c], pd.DataFrame) else df[c]
#                     if str(c[0]).lower() == "close":
#                         return df[c].iloc[:, 0] if isinstance(df[c], pd.DataFrame) else df[c]
#         # fallback: try case-insensitive match
#         for c in df.columns:
#             if str(c).lower() == "close":
#                 return df[c]
#         # last resort: if there's only one numeric column, use it
#         numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
#         if len(numeric_cols) == 1:
#             return df[numeric_cols[0]]
#         raise ValueError("Could not find a single 'Close' column in dataframe.")

#     close = df[close_col]
#     # if close is a DataFrame (e.g., multiple tickers), pick the first numeric column
#     if isinstance(close, pd.DataFrame):
#         # try to pick first numeric column
#         numeric = [c for c in close.columns if pd.api.types.is_numeric_dtype(close[c])]
#         if numeric:
#             return close[numeric[0]]
#         # as fallback, take first column
#         return close.iloc[:, 0]
#     return close

# # ---------------------------
# # MODULE 1: DATA FETCHER (Yahoo Finance + CoinGecko)
# # ---------------------------
# @st.cache_data(ttl=60)  # cache for 60 seconds in Streamlit
# def get_stock_data(symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
#     try:
#         # yfinance accepts many period formats; we pass-through
#         df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)

#         if df is None or df.empty:
#             return pd.DataFrame()

#         # yfinance often returns a DataFrame indexed by Date
#         df = df.copy()

#         # If the result has a MultiIndex on columns (e.g., multiple tickers), try to normalize
#         # Reset index to make Date a column
#         if not isinstance(df.index, pd.DatetimeIndex):
#             try:
#                 df.index = pd.to_datetime(df.index)
#             except Exception:
#                 pass
#         df = df.reset_index()

#         # Ensure we have a single Close series available under 'Close'
#         try:
#             close_series = _ensure_close_series(df)
#             # If the 'Close' column already exists but was multi-col, overwrite with single series
#             df["Close"] = close_series
#         except ValueError:
#             # If we couldn't find a Close, just return the dataframe as-is (caller will handle empty)
#             pass

#         # Ensure column names we expect
#         if "Close" not in df.columns:
#             raise ValueError("Missing 'Close' column from yfinance data after normalization.")

#         return df
#     except Exception as e:
#         st.error(f"Failed to fetch stock data for {symbol}: {e}")
#         return pd.DataFrame()


# def get_crypto_price(coin_id: str = "bitcoin", currency: str = "usd") -> Optional[float]:
#     try:
#         url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}"
#         r = requests.get(url, timeout=10)
#         r.raise_for_status()
#         data = r.json()
#         return data.get(coin_id, {}).get(currency)
#     except Exception as e:
#         st.error(f"Failed to fetch crypto price for {coin_id}: {e}")
#         return None

# @st.cache_data(ttl=60)
# def get_crypto_history(coin_id: str = "bitcoin", days: int = 30) -> pd.DataFrame:
#     try:
#         url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
#         r = requests.get(url, timeout=10)
#         r.raise_for_status()
#         data = r.json()
#         prices = data.get("prices", [])
#         df = pd.DataFrame(prices, columns=["timestamp", "price"]) if prices else pd.DataFrame()
#         if df.empty:
#             return df
#         df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
#         # normalize to same format as yfinance: timestamp -> Date, price -> Close
#         df = df.rename(columns={"timestamp": "Date", "price": "Close"})
#         return df
#     except Exception as e:
#         st.error(f"Failed to fetch crypto history for {coin_id}: {e}")
#         return pd.DataFrame()

# # ---------------------------
# # MODULE 2: INDICATORS (MA, RSI, Bollinger Bands)
# # ---------------------------

# def add_moving_averages(df: pd.DataFrame, short: int = 20, long: int = 50) -> pd.DataFrame:
#     df = df.copy()
#     close = _ensure_close_series(df)
#     df["MA20"] = close.rolling(window=short, min_periods=1).mean().values
#     df["MA50"] = close.rolling(window=long, min_periods=1).mean().values
#     return df


# def compute_RSI(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
#     # Classic RSI using simple rolling means. For less-laggy RSI use exponential moving averages (ewm).
#     df = df.copy()
#     close = _ensure_close_series(df)
#     delta = close.diff()
#     gain = delta.clip(lower=0)
#     loss = -delta.clip(upper=0)
#     # use rolling means
#     avg_gain = gain.rolling(period, min_periods=period).mean()
#     avg_loss = loss.rolling(period, min_periods=period).mean()
#     rs = avg_gain / (avg_loss.replace(0, pd.NA))
#     rsi = 100 - (100 / (1 + rs))
#     df["RSI"] = rsi.values
#     return df


# def add_bollinger_bands(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
#     df = df.copy()
#     close = _ensure_close_series(df)
#     mb = close.rolling(period, min_periods=1).mean()
#     std = close.rolling(period, min_periods=1).std()
#     df["MB"] = mb.values
#     df["UB"] = (mb + 2 * std).values
#     df["LB"] = (mb - 2 * std).values
#     return df


# def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
#     if df is None or df.empty:
#         return pd.DataFrame()

#     df = df.copy()

#     # Normalize / ensure Date column exists
#     if "Date" not in df.columns and "DateTime" in df.columns:
#         df = df.rename(columns={"DateTime": "Date"})
#     if "Date" not in df.columns and "index" in df.columns:
#         df = df.rename(columns={"index": "Date"})

#     # If Date is still not present but index is datetime, take it
#     if "Date" not in df.columns:
#         try:
#             if isinstance(df.index, pd.DatetimeIndex):
#                 df = df.reset_index().rename(columns={"index": "Date"})
#         except Exception:
#             pass

#     # Ensure Close is a single Series and will not cause assignment issues later
#     try:
#         close = _ensure_close_series(df)
#         df["Close"] = close.values
#     except ValueError:
#         raise ValueError("DataFrame does not contain a usable 'Close' column for indicators.")

#     # Ensure Date dtype
#     if "Date" in df.columns:
#         df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
#         # sort by date if possible
#         if df["Date"].notna().all():
#             df = df.sort_values("Date").reset_index(drop=True)

#     # add indicators
#     df = add_moving_averages(df)
#     df = compute_RSI(df)
#     df = add_bollinger_bands(df)
#     return df

# # ---------------------------
# # MODULE 3: DATABASE MODULE (SQLite)
# # ---------------------------

# def create_tables(db_path=DB):
#     with safe_connect(db_path) as con:
#         cur = con.cursor()
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS prices (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 asset TEXT,
#                 price REAL,
#                 timestamp TEXT
#             );
#         """)
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS portfolio (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 asset TEXT,
#                 quantity REAL,
#                 buy_price REAL
#             );
#         """)
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS alerts (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 asset TEXT,
#                 threshold REAL,
#                 method TEXT
#             );
#         """)
#         con.commit()


# def insert_price(asset: str, price: float, db_path=DB):
#     ts = datetime.utcnow().isoformat()
#     with safe_connect(db_path) as con:
#         cur = con.cursor()
#         cur.execute(
#             "INSERT INTO prices(asset, price, timestamp) VALUES (?, ?, ?)",
#             (asset, price, ts),
#         )
#         con.commit()


# def get_portfolio(db_path=DB) -> pd.DataFrame:
#     with safe_connect(db_path) as con:
#         try:
#             df = pd.read_sql_query("SELECT * FROM portfolio", con)
#         except Exception:
#             df = pd.DataFrame()
#     return df

# # ---------------------------
# # MODULE 4: ALERT SYSTEM MODULE (Email + Telegram)
# # ---------------------------

# def send_email_alert(to: str, subject: str, message: str) -> bool:
#     if not EMAIL_USER or not EMAIL_PASS:
#         st.warning("Email credentials not configured (EMAIL_USER / EMAIL_PASS). Skipping email.")
#         return False
#     try:
#         msg = MIMEText(message)
#         msg["Subject"] = subject
#         msg["From"] = EMAIL_USER
#         msg["To"] = to
#         with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
#             server.login(EMAIL_USER, EMAIL_PASS)
#             server.sendmail(EMAIL_USER, [to], msg.as_string())
#         return True
#     except Exception as e:
#         st.error(f"Failed to send email alert: {e}")
#         return False


# def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
#     try:
#         if not bot_token or not chat_id:
#             st.warning("Telegram credentials not configured. Skipping telegram.")
#             return False
#         url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
#         data = {"chat_id": chat_id, "text": message}
#         r = requests.post(url, data=data, timeout=10)
#         r.raise_for_status()
#         return True
#     except Exception as e:
#         st.error(f"Failed to send telegram alert: {e}")
#         return False


# def check_alert(asset: str, current_price: float, threshold: float, alert_methods: Dict[str, Callable[[str, str, str], bool]]):
#     """
#     alert_methods: dict of method_name -> function (for email, telegram, etc.)
#     Each function should accept parameters (to_or_id, subject_or_none, message) or be wrapped appropriately.
#     """
#     if current_price is None:
#         return False
#     if current_price >= threshold:
#         message = f"🚨 {asset} crossed {threshold:.4f}! Current: {current_price:.4f} (UTC {datetime.utcnow().isoformat()})"
#         # attempt each provided alert method
#         results = {}
#         for key, func in alert_methods.items():
#             try:
#                 if key == "email":
#                     results[key] = func(os.getenv("ALERT_EMAIL_TO", EMAIL_USER), f"{asset} Alert", message)
#                 elif key == "telegram":
#                     results[key] = func(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
#                 else:
#                     # generic call: pass message only
#                     results[key] = func(message)
#             except Exception as e:
#                 results[key] = False
#                 st.error(f"Alert method {key} failed: {e}")
#         return results
#     return False

# # ---------------------------
# # MODULE 5: PORTFOLIO TRACKER MODULE
# # ---------------------------

# def calculate_portfolio_value(df: pd.DataFrame, live_prices: Dict[str, float]) -> pd.DataFrame:
#     df = df.copy()
#     if df.empty:
#         return df
#     df["Current Price"] = df["asset"].apply(lambda x: live_prices.get(x, 0.0))
#     df["Value"] = df["Current Price"] * df["quantity"]
#     df["P/L"] = (df["Current Price"] - df["buy_price"]) * df["quantity"]
#     return df

# # ---------------------------
# # MODULE 6: STREAMLIT DASHBOARD MODULE
# # ---------------------------

# def dashboard():
#     st.set_page_config(page_title="Crypto & Stock Tracker", page_icon="📈")
#     st.title("📈 Real-Time Crypto & Stock Tracker")

#     create_tables()  # ensure DB exists

#     choice = st.selectbox("Choose asset type", ["Stock", "Crypto"])
#     default_symbol = "BTC" if choice == "Crypto" else "AAPL"
#     symbol = st.text_input("Enter symbol or id (e.g. AAPL or BTC or bitcoin)", value=default_symbol)

#     col1, col2 = st.columns([2, 1])
#     with col1:
#         period = st.selectbox("Period", ["7d", "14d", "1mo", "3mo", "6mo", "1y"], index=2)
#     with col2:
#         interval = st.selectbox("Interval", ["1d", "1h", "30m"], index=0)

#     if st.button("Fetch Data"):
#         if not symbol:
#             st.warning("Please enter a symbol.")
#             return

#         if choice == "Stock":
#             df = get_stock_data(symbol, period=period, interval=interval)
#             if df.empty:
#                 st.info("No stock data returned.")
#                 return
#             # ensure Date column exists
#             if "Date" not in df.columns:
#                 df = df.rename(columns={df.columns[0]: "Date"}) if len(df.columns) > 0 else df
#             df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
#             try:
#                 df = add_all_indicators(df)
#             except Exception as e:
#                 st.error(f"Failed to compute indicators: {e}")
#                 return

#             st.subheader(f"{symbol.upper()} - Closing Price")
#             try:
#                 st.line_chart(df.set_index("Date")["Close"])
#             except Exception:
#                 st.line_chart(df.set_index("Date").iloc[:, 0])

#             st.subheader("Recent Data & Indicators")
#             st.dataframe(df.tail(10), use_container_width=True)
#             latest_price = float(df["Close"].iloc[-1])
#             insert_price(symbol.upper(), float(latest_price))
#             st.metric(label=f"{symbol.upper()} Latest", value=f"{latest_price:.4f}")

#         else:  # Crypto
#             coin_id = coin_symbol_to_coingecko_id(symbol)
#             price = get_crypto_price(coin_id)
#             if price is None:
#                 st.info("No crypto price available.")
#                 return
#             insert_price(coin_id, float(price))
#             st.metric(label=f"{coin_id.upper()} Price (USD)", value=f"${price:.4f}")
#             df = get_crypto_history(coin_id, days=30)
#             if not df.empty:
#                 try:
#                     df = add_all_indicators(df)
#                 except Exception as e:
#                     st.error(f"Failed to compute indicators for crypto: {e}")
#                     return
#                 st.subheader("Price History (30d)")
#                 st.line_chart(df.set_index("Date")["Close"])
#                 st.subheader("Recent Data & Indicators")
#                 st.dataframe(df.tail(10), use_container_width=True)

#     # Portfolio viewer
#     st.write("---")
#     st.subheader("Portfolio")
#     try:
#         portfolio_df = get_portfolio()
#         if portfolio_df.empty:
#             st.info("Portfolio is empty. Use DB to insert holdings (insert via other UI or direct SQL).")
#         else:
#             # Build live prices key-value map for assets present in portfolio
#             unique_assets = portfolio_df["asset"].unique().tolist()
#             live_prices = {}
#             for a in unique_assets:
#                 # try stock first, else coin
#                 s = get_stock_data(a, period="7d", interval="1d")
#                 if not s.empty:
#                     try:
#                         live_prices[a] = float(s["Close"].iloc[-1])
#                     except Exception:
#                         # fallback to first numeric column
#                         numeric_cols = [c for c in s.columns if pd.api.types.is_numeric_dtype(s[c])]
#                         live_prices[a] = float(s[numeric_cols[-1]].iloc[-1]) if numeric_cols else 0.0
#                 else:
#                     # try coinGecko id conversion
#                     cid = coin_symbol_to_coingecko_id(a)
#                     cp = get_crypto_price(cid)
#                     live_prices[a] = float(cp) if cp is not None else 0.0
#             val_df = calculate_portfolio_value(portfolio_df, live_prices)
#             st.dataframe(val_df, use_container_width=True)
#             st.metric("Total Portfolio Value (USD)", value=f"${val_df['Value'].sum():.2f}")
#     except Exception as e:
#         st.error(f"Failed to load portfolio: {e}")

#     # Alerts UI
#     st.write("---")
#     st.subheader("Quick Alert Checker")
#     alert_asset = st.text_input("Asset for quick check (AAPL or BTC)", value="")
#     alert_threshold = st.number_input("Alert threshold (price)", value=0.0, format="%.4f")
#     email_alert = st.checkbox("Send email on trigger (uses EMAIL_USER/EMAIL_PASS)", value=False)
#     telegram_alert = st.checkbox("Send Telegram on trigger (uses TELEGRAM env vars)", value=False)

#     if st.button("Check Alert Now"):
#         if not alert_asset or alert_threshold <= 0:
#             st.warning("Provide asset and threshold > 0.")
#         else:
#             # figure out price
#             current = None
#             display_name = alert_asset
#             # heuristic: alphanumeric short -> maybe stock or symbol
#             if alert_asset.isalpha() and len(alert_asset) <= 5:
#                 s = get_stock_data(alert_asset, period="7d", interval="1d")
#                 if not s.empty:
#                     try:
#                         current = float(s["Close"].iloc[-1])
#                         display_name = alert_asset.upper()
#                     except Exception:
#                         # fallback
#                         numeric_cols = [c for c in s.columns if pd.api.types.is_numeric_dtype(s[c])]
#                         if numeric_cols:
#                             current = float(s[numeric_cols[-1]].iloc[-1])
#                             display_name = alert_asset.upper()
#                 else:
#                     cid = coin_symbol_to_coingecko_id(alert_asset)
#                     current = get_crypto_price(cid)
#                     display_name = cid
#             else:
#                 cid = coin_symbol_to_coingecko_id(alert_asset)
#                 current = get_crypto_price(cid)
#                 display_name = cid

#             if current is None:
#                 st.error("Could not determine current price.")
#             else:
#                 methods = {}
#                 if email_alert:
#                     methods["email"] = send_email_alert
#                 if telegram_alert:
#                     methods["telegram"] = send_telegram_alert
#                 res = check_alert(display_name, float(current), float(alert_threshold), methods)
#                 if res:
#                     st.success(f"Alert triggered for {display_name}: current={current:.4f}. Methods: {res}")
#                 else:
#                     st.info(f"No alert: {display_name} current price {current:.4f} is below {alert_threshold:.4f}")


# def coin_symbol_to_coingecko_id(symbol: str) -> str:
#     """
#     Best-effort mapping: accepts symbols like 'BTC', 'ETH' or ids like 'bitcoin'.
#     For more symbols add to the map or call CoinGecko coin/list (not done here to avoid extra requests).
#     """
#     mapping = {
#         "BTC": "bitcoin",
#         "ETH": "ethereum",
#         "LTC": "litecoin",
#         "DOGE": "dogecoin",
#         "ADA": "cardano",
#         "BNB": "binancecoin",
#         "SOL": "solana",
#         # extend as needed
#     }
#     s = symbol.strip()
#     if not s:
#         return s
#     # if user supplied coingecko id already (e.g. "bitcoin"), return it:
#     if s.lower() in mapping.values():
#         return s.lower()
#     # convert upper symbol like 'btc' -> 'BTC' key
#     return mapping.get(s.upper(), s.lower())  # fallback to the raw lower-case string


# def main():
#     dashboard()


# if __name__ == "__main__":
#     main()
























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
