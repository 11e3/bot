import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time

MIN_KRW_BALANCE = 5000
TICKER = 'KRW-XRP'
K = 1
EMA_WINDOW = 5

def get_upbit():
    config = pd.read_csv('config/config.csv')
    return pyupbit.Upbit(config.iloc[0, 1], config.iloc[1, 1])

def get_target_and_bull(ticker, k, window):
    df = pyupbit.get_ohlcv(ticker, count=10)
    if df is None or df.empty:
        print("[ERROR] OHLCV data fetch failed.")
        return None, None

    df['range'] = df['high'] - df['close']
    df['target'] = df['range'].shift(1) * k + df['open']
    df['ema'] = df['close'].ewm(span=window).mean()
    df['bull'] = df['high'].shift(1) >= df['ema'].shift(1)

    return df['target'].iloc[-1], df['bull'].iloc[-1]

def get_balance_float(upbit, ticker):
    try:
        return float(upbit.get_balance(ticker) or 0)
    except Exception as e:
        print(f"[ERROR] Balance fetch failed: {e}")
        return 0.0

def buy(upbit, krw, ticker):
    try:
        amount = krw * 0.9
        result = upbit.buy_market_order(ticker, amount)
        print(f"[BUY] {ticker} | {amount:.0f} KRW")
    except Exception as e:
        print(f"[ERROR] Buy failed: {e}")

def sell(upbit, volume, ticker):
    try:
        result = upbit.sell_market_order(ticker, volume)
        print(f"[SELL] {ticker} | Volume: {volume}")
    except Exception as e:
        print(f"[ERROR] Sell failed: {e}")

def is_reset_time(now):
    return now.time().hour == 0 and now.time().minute == 0

def main():
    upbit = get_upbit()
    target, bull = get_target_and_bull(TICKER, K, EMA_WINDOW)
    if target is None or bull is None:
        return

    loss_cut = False
    reset_done = False

    while True:
        try:
            now = datetime.now()
            price = pyupbit.get_current_price(TICKER)
            if price is None:
                time.sleep(1)
                continue

            xrp = get_balance_float(upbit, TICKER)

            # Daily reset
            if is_reset_time(now) and not reset_done:
                print("[RESET] Daily reset")
                if xrp > 0:
                    sell(upbit, xrp, TICKER)
                target, bull = get_target_and_bull(TICKER, K, EMA_WINDOW)
                loss_cut = False
                reset_done = True

            if now.time().minute > 0:
                reset_done = False

            # Buy condition
            if xrp < 0.0001 and not loss_cut and price >= target and bull:
                krw = get_balance_float(upbit, 'KRW')
                if krw > MIN_KRW_BALANCE:
                    buy(upbit, krw, TICKER)

            # Loss cut
            if xrp > 0 and price <= target * 0.95 and not loss_cut:
                print(f"[LOSS CUT] {price:.2f} <= {target * 0.95:.2f}")
                sell(upbit, xrp, TICKER)
                loss_cut = True

            time.sleep(1)

        except Exception as e:
            print(f"[ERROR] Main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"[CRITICAL] Restarting main(): {e}")
            time.sleep(10)
