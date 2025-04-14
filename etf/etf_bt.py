import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
from io import StringIO


def crawl(code):
    url = 'https://finance.naver.com/item/sise_day.nhn?code=' + code + '&page=1'
    html = requests.get(url, headers={'User-agent': 'Mozilla/5.0'}).text

    # BeautifulSoup 생성자 첫번째 인수로 HTML/XML 페이지를 넘겨주고, 두번째 인수로 페이지를 파싱할 방식을 넘겨준다.
    bs = BeautifulSoup(html, 'lxml')

    # find 함수를 통해 'pgRR'인 'td'태그를 찾으면, 결과값은 'bs4.element.Tag'타입으로 pgrr 변수에 반환한다.
    # pgRR = Page Right Right 맨 마지막 페이지를 의미한다.
    pgrr = bs.find('td', class_='pgRR')


    # pdRR 클래스 속성값으로 <td>하위의 <a> href 속성값을 구한다.
    # pfgg.a['href']를 출력하면 href의 속성값인 item/sise.naver?code=029780&page=1 문자열을 얻을 수 있다.
    s = str(pgrr.a['href']).split('=')

    last_page = s[-1]  

    # 빈 데이터프레임 생성
    df = pd.DataFrame()
    sise_url = 'https://finance.naver.com/item/sise_day.nhn?code=' + code  

    for page in range(1, int(last_page)+1):
        url = '{}&page={}'.format(sise_url, page)  
        html = requests.get(url, headers={'User-agent': 'Mozilla/5.0'}).text
        df = pd.concat([df, pd.read_html(StringIO(html), header=0)[0]])  # Wrap html in StringIO
    
    df['date'] = pd.to_datetime(df['날짜'])
    df.set_index('date', inplace=True)
    df.drop('날짜', axis=1, inplace=True)
    
    df.sort_index(inplace=True)
    
    # 일간데이터 -> 월간데이터
    # monthly_df = df.resample('M').agg({
    #     '시가': 'first',
    #     '고가': 'max',
    #     '저가': 'min',
    #     '종가': 'last',
    #     '거래량': 'sum'
    # })
    
    # monthly_df = monthly_df.dropna()
    # df = monthly_df

    df = df.dropna()
    
    # 차트 출력을 위해 데이터프레임 가공하기
    # df = df.iloc[0:1000]  
    # df = df.sort_values(by='날짜')  

    # 날짜, 종가 컬럼으로 차트 그리기
    # plt.title(code)
    # plt.xticks(rotation=45)  
    # plt.plot(df['날짜'], df['종가'], 'co-') 
    # plt.grid(color='gray', linestyle='--')
    # plt.show()

    return df


def main(code1, code2):
    df1 = crawl(code1)
    df2 = crawl(code2)

    # print(df1.index[0]) # 2015.12.17
    # print(df2.index[0])  # 2016.08.10

    start_date = '2016.08.10'
    start_date = pd.to_datetime(start_date, format='%Y.%m.%d')
    
    df1 = df1[df1.index >= start_date]
    
    # plt.plot(df1.index, df1['종가'])
    # plt.plot(df2.index, df2['종가'])
    # plt.show()
        
    # # Calculate Monthly Returns
    # df1 = df1['종가'].pct_change()
    # df2 = df2['종가'].pct_change()

    # # Combine returns into a single dataframe
    # returns_df = pd.concat([df1, df2], axis=1)
    # returns_df.columns = ['Asset1', 'Asset2']

    # Define Rebalancing Strategy
    def rebalance_portfolio(df1, df2):
        # 모멘텀 스코어 // 월간
        # mom1 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 1)).astype(int)  
        # mom2 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 2)).astype(int)    
        # mom3 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 3)).astype(int) 
        # mom4 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 4)).astype(int)   
        # mom5 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 5)).astype(int)  
        # mom6 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 6)).astype(int)   
        # mom7 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 7)).astype(int)  
        # mom8 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 8)).astype(int)  
        # mom9 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 9)).astype(int) 
        # mom10 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 10)).astype(int)  
        # mom11 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 11)).astype(int)   
        # mom12 = (returns['Asset1'].shift(1) > returns['Asset1'].shift(1 + 12)).astype(int)  

        # ratio = (mom1 + mom2 + mom3 + mom4 + mom5 + mom6 + mom7 + mom8 + mom9 + mom10 + mom11 + mom12) / 12

        # portfolio_returns = np.where(
        #                             (ratio > 0.5) & (returns['Asset1'].shift(1) > fee),
        #                             (ratio * returns['Asset1']) + ((1 - ratio) * 0) - fee,
        #                             0
        #                             )
        ma1 = df1['종가'].rolling(window=5).mean().shift(2)
        ma2 = df2['종가'].rolling(window=5).mean().shift(2)
        
        k = 0.5
        risk_ratio = 1
        
        portfolio_returns = np.where(
            ((df1['고가'].shift(2) - df1['저가'].shift(2)) * k + df1['시가'].shift(1) <= df1['고가'].shift(1)) \
                & (df1['종가'].shift(2) > ma1),
            (df1['시가'] / ((df1['고가'].shift(2) - df1['종가'].shift(2)) * k + df1['시가'].shift(1)) - 1) * risk_ratio - fee,
            np.where(
                ((df2['고가'].shift(2) - df2['저가'].shift(2)) * k + df2['시가'].shift(1) <= df2['고가'].shift(1)) \
                & (df2['종가'].shift(2) > ma2),
                (df2['시가'] / ((df2['고가'].shift(2) - df2['종가'].shift(2)) * k + df2['시가'].shift(1)) - 1) * risk_ratio - fee,
                0
            )
            # 0
        )
        return portfolio_returns

    # Simulate the Backtest
    portfolio_returns = pd.Series(rebalance_portfolio(df1, df2))

    # Calculate Cumulative Returns
    cumulative_returns = (1 + portfolio_returns).cumprod()
    print('cumulative return:', cumulative_returns.iloc[-1])
    print('cagr:', (cumulative_returns.iloc[-1]) ** (1/8) - 1)  # 대략 8년 지남
    
    def calculate_drawdown(series):
        """
        Calculate drawdown given a time series of asset prices.
        """
        # Calculate cumulative returns
        cum_returns = pd.Series((1 + series).cumprod())

        # Calculate the previous peaks
        previous_peaks = cum_returns.expanding(min_periods=1).max()

        # Calculate drawdown
        drawdown = (cum_returns - previous_peaks) / previous_peaks

        return drawdown

    # Assuming 'portfolio_returns' is the series of portfolio returns
    drawdown_series = calculate_drawdown(portfolio_returns)

    # Calculate Maximum Drawdown
    max_drawdown = drawdown_series.min()

    print("mdd:", max_drawdown)
    
    # Plot the Cumulative Returns
    plt.plot(df1.index, df1['종가']/df1['종가'].iloc[0])
    plt.plot(df1.index, cumulative_returns)
    plt.yscale('log')
    plt.show()
    
    plt.figure(figsize=(12, 8))

    plt.semilogy(df1.index, cumulative_returns, label="Portfolio Balance", color='b')
    plt.semilogy(df1.index, df1['종가']/df1['종가'].iloc[0], label='kodex_kosdaq_150_leverage (benchmark)', color='r')

    plt.xlabel("Date")
    plt.ylabel("Balance")
    plt.title("Portfolio Balance Over Time")
    plt.legend()
    plt.grid()

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    kodex_kosdaq_150_leverage = '233740'
    kodex_kosdaq_150_inverse = '251340'
    kodex_leverage = '122630'
    kodex_200_futures_inverse_2X = '252670'
    kodex_kosdaq_150 = '229200'
    tiger_america_sandp500 = '360750'
    
    fee = 0.03 / 100
    main(kodex_kosdaq_150_leverage, kodex_kosdaq_150_inverse)
    
    