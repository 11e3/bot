import pyupbit
import pandas as pd
from datetime import datetime
import time
import requests

MIN_KRW_BALANCE = 5000
TICKER = 'KRW-XRP'
K = 1
EMA_WINDOW = 5
WEBHOOK_URL = 'https://discord.com/api/webhooks/1364749640842346537/-17AKG2TnRNmCtSzLCS2SIzV-GE924Jj7yKc8JkhpK4zVuPslByxReNCn1sOFcHwI-uH'

def send_discord_message(message: str):
    try:
        requests.post(WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print(f"[ERROR] Failed to send Discord message: {e}")

def load_upbit_api():
    config = pd.read_csv('config/config.csv')
    return pyupbit.Upbit(config.iloc[0, 1], config.iloc[1, 1])

def calculate_target_and_bull(ticker, k, window):
    df = pyupbit.get_ohlcv(ticker, count=10)
    if df is None or df.empty:
        send_discord_message("[ERROR] Failed to fetch OHLCV data.")
        return None, None

    df['range'] = df['high'] - df['close']
    df['target'] = df['range'].shift(1) * k + df['open']
    df['ema'] = df['close'].ewm(span=window).mean()
    df['bull'] = df['high'].shift(1) >= df['ema'].shift(1)

    return df['target'].iloc[-1], df['bull'].iloc[-1]

def get_balance(upbit, ticker):
    try:
        return float(upbit.get_balance(ticker) or 0)
    except Exception as e:
        send_discord_message(f"[ERROR] Failed to fetch balance: {e}")
        return 0.0

def execute_buy(upbit, krw, ticker):
    try:
        amount = krw * 0.9
        upbit.buy_market_order(ticker, amount)
        send_discord_message(f"[BUY] {ticker} | {amount:.0f} KRW")
    except Exception as e:
        send_discord_message(f"[ERROR] Buy failed: {e}")

def execute_sell(upbit, volume, ticker):
    try:
        upbit.sell_market_order(ticker, volume)
        send_discord_message(f"[SELL] {ticker} | Volume: {volume}")
    except Exception as e:
        send_discord_message(f"[ERROR] Sell failed: {e}")

def is_midnight(now):
    return now.hour == 0 and now.minute == 0

def main():
    upbit = load_upbit_api()
    target, bull = calculate_target_and_bull(TICKER, K, EMA_WINDOW)
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

            xrp_balance = get_balance(upbit, TICKER)

            # Daily reset
            if is_midnight(now) and not reset_done:
                send_discord_message("[RESET] Daily reset")
                if xrp_balance > 0:
                    execute_sell(upbit, xrp_balance, TICKER)
                target, bull = calculate_target_and_bull(TICKER, K, EMA_WINDOW)
                loss_cut = False
                reset_done = True

            if now.minute > 0:
                reset_done = False

            # Buy condition
            if xrp_balance < 0.0001 and not loss_cut and price >= target and bull:
                krw_balance = get_balance(upbit, 'KRW')
                if krw_balance > MIN_KRW_BALANCE:
                    execute_buy(upbit, krw_balance, TICKER)

            # Loss cut condition
            if xrp_balance > 0 and price <= target * 0.95 and not loss_cut:
                send_discord_message(f"[LOSS CUT] {price:.2f} <= {target * 0.95:.2f}")
                execute_sell(upbit, xrp_balance, TICKER)
                loss_cut = True

            time.sleep(1)

        except Exception as e:
            send_discord_message(f"[ERROR] Main loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            send_discord_message(f"[CRITICAL] Restarting main(): {e}")
            time.sleep(10)
