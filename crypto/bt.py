import pyupbit
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

k = 1
window = 5
fee = 0.1/100

df = pyupbit.get_ohlcv("KRW-XRP", interval='day', count=9999999999)


def strat(df, k):
    df['range'] = df['high'] - df['close']  # 전일고가 - 전일종가: 전일 양봉이면 민감해지고 전일 음봉이면 둔감해짐
    df['target'] = df['range'].shift(1) * k + df['open']  # k = 1일 경우 df['target'] = df['high'].shift(1) 왜냐면 df['open'] = df['close'].shift(1)
    df['ma'] = df['close'].rolling(window=window).mean()
    df['ema'] = df['close'].ewm(span=window, adjust=False).mean()  # 이게 더 나음
    df['bull'] = df['high'].shift(1) >= df['ema'].shift(1)  # 전일 고가 >= 전일 5일 이평

    df['ror'] = np.where((df['high'].shift(1) > df['target'].shift(1)) & df['bull'].shift(1), 
                        df['open'] / df['target'].shift(1) * (1 - fee),
                        1)
    
    df['ror'] = (df['ror'] - 1) * 0.9 + 1  # 매 거래에 전체 자산의 90%만 투자

    # total
    df['total'] = df['ror'].cumprod()
    
    return df['total']


def mat(series):
    total = series.iloc[-1]

    # cagr
    n = len(df) / 365
    cagr = round(total ** (1 / n) * 100 - 100, 2)

    # mdd
    arr = np.array(series)
    dd_list = - (np.maximum.accumulate(arr) - arr) / np.maximum.accumulate(arr)
    peak_lower = np.argmax(np.maximum.accumulate(arr) - arr)
    peak_upper = np.argmax(arr[:peak_lower])
    mdd = round((arr[peak_lower] - arr[peak_upper]) / arr[peak_upper] * 100, 2)


    print(f'{round(n, 2)} 년간')
    print(f'- total : {round(total, 2)} 배')
    print(f'- cagr  : {cagr} %')
    print(f'- mdd   : {mdd} %')
    print('')


strat = strat(df, k)
print('strat')
mat(strat)

bm = df['close'] / df['close'].iloc[0]
print('benchmark')
mat(bm)

# Plot the balance history and MDD
plt.figure(figsize=(12, 8))

# Plot the balance history
#plt.subplot(2, 1, 1)
#plt.plot(df.index, balance_history, label="Portfolio Balance", color='b')
plt.semilogy(df.index, strat, label="Portfolio Balance", color='b')
plt.semilogy(df.index, bm, label='XRP (benchmark)', color='r')

plt.xlabel("Date")
plt.ylabel("Balance")
plt.title("Portfolio Balance Over Time")
plt.legend()
plt.grid()

# # Plot the Maximum Drawdown
# plt.subplot(2, 1, 2)
# plt.plot(df.index, dd_list, label="Drawdown", color='r')
# plt.xlabel("Date")
# plt.ylabel("Drawdown")
# plt.title("Maximum Drawdown Over Time")
# plt.legend()
# plt.grid()

plt.tight_layout()
plt.show()