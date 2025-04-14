import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time


# 매수
def buy(krw, ticker):
    result = upbit.buy_market_order(ticker=ticker, price=krw * 0.9)  # 전체 자산의 90% 투자

# 매도
def sell(xrp, ticker):
    result = upbit.sell_market_order(ticker=ticker, volume=xrp)

# target, bull 업데이트
def update(ticker, k, window):
    df = pyupbit.get_ohlcv(ticker=ticker, count=10)  # 10 이상은 줘야 ma 계산하고 shift로 밀고 할 수 있음

    df['range'] = df['high'] - df['close']
    df['target'] = df['range'].shift(1) * k + df['open']
    df['ema'] = df['close'].ewm(span=window, adjust=False).mean()
    df['bull'] = df['high'].shift(1) >= df['ema'].shift(1)
    
    target = df['target'].iloc[-1]
    bull = df['bull'].iloc[-1]
    
    return target, bull

# 메인 코드
if __name__ == "__main__":
    k = 1
    window = 5
    ticker = 'KRW-XRP'

    # config 파일 로드
    f = pd.read_csv('config/config.csv')
    access_key = f.iloc[0, 1]
    secret_key = f.iloc[1, 1]
    upbit = pyupbit.Upbit(access_key, secret_key)

    # 초기 target 및 bull 계산
    target, bull = update(ticker, k, window)

    # 손절 상태 초기화
    loss_cut = False
    
    while True:
        # 가격 조회
        try:
            price = pyupbit.get_current_price(ticker)
        except:
            time.sleep(1)
            continue
        
        # 현재 시간 및 보유 XRP 조회
        now = datetime.now()
        xrp = upbit.get_balance(ticker)  # typeerror 뜨면 ip 등록 안된거
        
        # 0시부터 10초 이내에 초기화
        reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now < reset_time + timedelta(seconds=10):
            loss_cut = False
            if xrp > 0:
                sell(xrp, ticker)

            # target 및 bull 갱신
            target, bull = update(ticker, k, window)

        # 손절이 안된 경우 모니터링
        elif xrp == 0 and not loss_cut:
            if price >= target and bull:
                krw = upbit.get_balance('KRW')
                buy(krw, ticker)

        # 손절 조건 체크 (5% 손실 시)
        elif xrp > 0 and price <= target * 0.95:
            loss_cut = True
            sell(xrp, ticker)

        time.sleep(1)
