import requests
import json
from datetime import datetime, timedelta
import time
import pandas as pd


f = pd.read_csv('config/config.csv')
app_key    = f.iloc[3, 1]
app_secret = f.iloc[4, 1]
acc_num    = f.iloc[5, 1]
acc_num_2  = f.iloc[6, 1]

kodex_kosdaq_150_leverage_code = '233740'
kodex_kosdaq_150_inverse_code = '251340'

url_base = 'https://openapi.koreainvestment.com:9443'


########################## access token ##########################
def get_access_token():
    headers = {"content-type":"application/json"}
    body = {"grant_type":"client_credentials",
            "appkey":app_key, 
            "appsecret":app_secret}

    path = "oauth2/tokenP"
    url = f"{url_base}/{path}"
    res = requests.post(url, headers=headers, data=json.dumps(body))

    access_token = res.json()["access_token"]

    return access_token

access_token = get_access_token()
access_token_issue_time = datetime.now()


########################## hash key ##########################
def hashkey(datas):
    PATH = "uapi/hashkey"
    URL = f"{url_base}/{PATH}"
    headers = {
      'content-Type' : 'application/json',
      'appKey' : app_key,
      'appSecret' : app_secret,
    }
    res = requests.post(URL, headers=headers, data=json.dumps(datas))
    hashkey = res.json()["HASH"]

    return hashkey


########################## get account ##########################
def get_account_code_qty():
    path = 'uapi/domestic-stock/v1/trading/inquire-balance'
    url = f"{url_base}/{path}"
    
    headers = {
        "authorization":f"Bearer {access_token}",
        "appKey":app_key,
        "appSecret":app_secret,
        "tr_id":"TTTC8434R"
    }

    params = {
        "CANO": acc_num,
        "ACNT_PRDT_CD": acc_num_2,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "01",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
        }
    
    try:
        res = requests.get(url, headers=headers, params=params).json()['output1'][0]
        code = res['pdno']
        qty = res['hldg_qty']
    except:
        code = ''
        qty = 0
    
    return code, qty


def get_qty(code):
    path = 'uapi/domestic-stock/v1/trading/inquire-psbl-order'
    url = f"{url_base}/{path}"
    
    headers = {
        "authorization":f"Bearer {access_token}",
        "appKey":app_key,
        "appSecret":app_secret,
        "tr_id":"TTTC8908R"
    }
    
    params = {
        "CANO": acc_num,
        "ACNT_PRDT_CD": acc_num_2,
        "PDNO": code,
        "ORD_UNPR":'',
        "ORD_DVSN":'01',
        "CMA_EVLU_AMT_ICLD_YN": 'N',
        "OVRS_ICLD_YN":'N'
        }
    
    res = int(requests.get(url, headers=headers, params=params).json()['output']['nrcvb_buy_qty'])
    
    return res
    

########################## get data ##########################
def get_data(code, start, end):
    path = "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    url = f"{url_base}/{path}"
    
    headers = {
        "Content-Type":"application/json", 
        "authorization":f"Bearer {access_token}",
        "appKey":app_key,
        "appSecret":app_secret,
        "tr_id":"FHKST03010100"
        }
    
    params = {
        "fid_cond_mrkt_div_code":"J",
        "fid_input_iscd":code,
        'FID_INPUT_DATE_1':start,
        'FID_INPUT_DATE_2':end,
        "fid_org_adj_prc":"0",
        "fid_period_div_code":"D"
        }
    
    res = requests.get(url, headers=headers, params=params).json()['output2']
    date = []
    open = []
    high = []
    low = []
    close = []
    for i in range(10):
        date.append(res[i]['stck_bsop_date'])
        open.append(int(res[i]['stck_oprc']))
        high.append(int(res[i]['stck_hgpr']))
        low.append(int(res[i]['stck_lwpr']))
        close.append(int(res[i]['stck_clpr']))
    ohlc = {
        'date':date,
        'open':open, 
        'high':high, 
        'low':low, 
        'close':close
        }
    df = pd.DataFrame(ohlc).iloc[::-1]
    df.reset_index(drop=True, inplace=True)

    return df

def get_current_price(code):
    path = "uapi/domestic-stock/v1/quotations/inquire-price"
    url = f"{url_base}/{path}"
    
    headers = {
        "Content-Type":"application/json", 
        "authorization": f"Bearer {access_token}",
        "appKey":app_key,
        "appSecret":app_secret,
        "tr_id":"FHKST01010100"
        }
    
    params = {
        "fid_cond_mrkt_div_code":"J",
        "fid_input_iscd":code
        }
    
    res = requests.get(url, headers=headers, params=params)
    res = int(res.json()['output']['stck_prpr'])

    return res


########################## calculate ##########################
def target(df):
    return df['open'].iloc[-1] + 0.5 * (df['high'].iloc[-2] - df['low'].iloc[-2])

def ma(df):
    return df['close'].rolling(window=5).mean().shift(1).iloc[-1]


########################## buy/sell ##########################
def order(buy_or_sell, code, qty):
    path = "uapi/domestic-stock/v1/trading/order-cash"
    url = f"{url_base}/{path}"
    
    data = {
        "CANO": acc_num,
        "ACNT_PRDT_CD": acc_num_2,
        "PDNO": code,
        "ORD_DVSN": "01",  # 시장가 주문
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0",  
    }
    
    if buy_or_sell == 'buy':
        tr_id = "TTTC0802U"  # buy
    else:
        tr_id = "TTTC0801U"  # sell
    
    headers = {
        "Content-Type":"application/json", 
        "authorization":f"Bearer {access_token}",
        "appKey":app_key,
        "appSecret":app_secret,
        "tr_id":tr_id,
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    
    res = requests.post(url, headers=headers, data=json.dumps(data))
    print(res.json())


########################## loop ##########################
update = 0

now = datetime.now()
many_days_ago = now - timedelta(days=30)
start = many_days_ago.strftime('%Y%m%d')
end = now.strftime('%Y%m%d')

kodex_kosdaq_150_leverage = get_data(kodex_kosdaq_150_leverage_code, start, end)
kodex_kosdaq_150_inverse = get_data(kodex_kosdaq_150_inverse_code, start, end)
leverage_target = target(kodex_kosdaq_150_leverage)
inverse_target = target(kodex_kosdaq_150_inverse)
print(leverage_target, inverse_target)
leverage_ma = ma(kodex_kosdaq_150_leverage)
inverse_ma = ma(kodex_kosdaq_150_inverse)
leverage_price = 0
inverse_price = 0

while True:
    now = datetime.now()
    try:
        leverage_price = get_current_price(kodex_kosdaq_150_leverage_code)
        inverse_price = get_current_price(kodex_kosdaq_150_inverse_code)
    except Exception as e:
        print(e)
    
    if (now.hour == 0) and (now.minute == 0) and (update == 0):  # UTC
        time_difference = now - access_token_issue_time
        if time_difference.days * 24 + time_difference.seconds > 1:
            access_token = get_access_token()

        code, qty = get_account_code_qty()
        if code == kodex_kosdaq_150_leverage_code:
            order('sell', code, qty)
            
        elif code == kodex_kosdaq_150_inverse_code:
            order('sell', code, qty)

        many_days_ago = now - timedelta(days=30)
        start = many_days_ago.strftime('%Y%m%d')
        end = now.strftime('%Y%m%d')
            
        try:
            time.sleep(60)
            kodex_kosdaq_150_leverage = get_data(kodex_kosdaq_150_leverage_code, start, end)
            kodex_kosdaq_150_inverse = get_data(kodex_kosdaq_150_inverse_code, start, end)
            
            leverage_price = get_current_price(kodex_kosdaq_150_leverage_code)
            inverse_price = get_current_price(kodex_kosdaq_150_inverse_code)
            
        except Exception as e:
            time.sleep(60)
            kodex_kosdaq_150_leverage = get_data(kodex_kosdaq_150_leverage_code, start, end)
            kodex_kosdaq_150_inverse = get_data(kodex_kosdaq_150_inverse_code, start, end)
            
            leverage_price = get_current_price(kodex_kosdaq_150_leverage_code)
            inverse_price = get_current_price(kodex_kosdaq_150_inverse_code)
        
        leverage_target = target(kodex_kosdaq_150_leverage)
        inverse_target = target(kodex_kosdaq_150_inverse)
        print(leverage_target, inverse_target)
        
        leverage_ma = ma(kodex_kosdaq_150_leverage)
        inverse_ma = ma(kodex_kosdaq_150_inverse)
        
        update = 1
            
    if update == 1:
        if (leverage_price >= leverage_target) and (kodex_kosdaq_150_leverage['close'].iloc[-2] > leverage_ma):
            qty = get_qty(kodex_kosdaq_150_leverage_code)
            order('buy', kodex_kosdaq_150_leverage_code, qty)
            update = 0
            
        if (inverse_price >= inverse_target) and (kodex_kosdaq_150_inverse['close'].iloc[-2] > inverse_ma):
            qty = get_qty(kodex_kosdaq_150_inverse_code)
            order('buy', kodex_kosdaq_150_inverse_code, qty)
            update = 0
    
    if (now.hour == 6) and (now.minute == 30):  # UTC
        update = 0
        
    time.sleep(2)