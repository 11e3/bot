import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time


def buy(krw, ticker):
    result = upbit.buy_market_order(ticker=ticker, price=krw * 0.9)  # 전체 자산의 90% 투자

def sell(xrp, ticker):
    result = upbit.sell_market_order(ticker=ticker, volume=xrp)

def update(ticker, k, window):
    df = pyupbit.get_ohlcv(ticker=ticker, count=10)  # 10정도 줘야 ma 계산하고 shift로 밀고 할 때 편함
    if df is None or df.empty:
        return None, None

    df['range'] = df['high'] - df['close']
    df['target'] = df['range'].shift(1) * k + df['open']
    df['ema'] = df['close'].ewm(span=window, adjust=False).mean()
    df['bull'] = df['high'].shift(1) >= df['ema'].shift(1)
    
    target = df['target'].iloc[-1]
    bull = df['bull'].iloc[-1]
    
    return target, bull

def main():
    k = 1
    window = 5
    ticker = 'KRW-XRP'

    f = pd.read_csv('config/config.csv')
    access_key = f.iloc[0, 1]
    secret_key = f.iloc[1, 1]
    global upbit
    upbit = pyupbit.Upbit(access_key, secret_key)

    target, bull = update(ticker, k, window)
    if target is None or bull is None:
        print("Error: Unable to fetch initial target and bull values.")
        return

    loss_cut = False
    reset_done = False
    
    while True:
        try:
            now = datetime.now()
            reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

            price = pyupbit.get_current_price(ticker)
            if price is None:
                print("Error: Unable to fetch current price.")
                with open("error_log.txt", "a") as f:
                    f.write(f"{datetime.now()} - Unable to fetch current price.\n")
                time.sleep(1)
                continue

            xrp = upbit.get_balance(ticker)  # typeerror 뜨면 ip 등록 안 된 거
            if xrp is None:
                print("Error: Unable to fetch XRP balance.")
                with open("error_log.txt", "a") as f:
                    f.write(f"{datetime.now()} - Unable to fetch XRP balance.\n")
                time.sleep(1)
                continue
            
            # 매일 UTC기준 0시마다 초기화
            if reset_time <= now < reset_time + timedelta(seconds=10) and not reset_done:
                loss_cut = False
                if xrp > 0:
                    sell(xrp, ticker)
                target, bull = update(ticker, k, window)
                reset_done = True
            
            if now >= reset_time + timedelta(minutes=1):
                reset_done = False

            # 매수 조건
            if reset_done == False and xrp == 0 and not loss_cut:
                if price >= target and bull:
                    krw = upbit.get_balance('KRW')
                    if krw is not None and krw > 5000:
                        buy(krw, ticker)
                    else:
                        print("Error: krw is None or krw <= 5000.")
                        with open("error_log.txt", "a") as f:
                            f.write(f"{datetime.now()} - krw is None or krw <= 5000.\n")

            # 손절 조건 (5%)
            if reset_done == False and xrp > 0 and price <= target * 0.95:
                loss_cut = True
                sell(xrp, ticker)

            time.sleep(1)
            
        except Exception as e:
            print(f"Error: {str(e)}")
            with open("error_log.txt", "a") as f:
                f.write(f"{datetime.now()} - {str(e)}\n")
            time.sleep(10)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            with open("error_log.txt", "a") as f:
                f.write(f"[RESTART] {datetime.now()} - {str(e)}\n")
            time.sleep(10)
