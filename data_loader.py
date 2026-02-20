import pandas as pd
import requests
from datetime import datetime
import time

def get_fng_data():
    """
    Fetches the Fear and Greed Index data from alternative.me API in JSON format.
    """
    url = "https://api.alternative.me/fng/?limit=0"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data['data'])
        
        # Convert timestamp to date
        df['date'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='s').dt.date
        df = df.rename(columns={'value': 'fng_value', 'value_classification': 'fng_classification'})
        
        return df[['date', 'fng_value', 'fng_classification']]
    except Exception as e:
        print(f"Error fetching FNG data: {e}")
        return None

def get_btc_data_from_binance(start_year=2018):
    """
    Fetches historical BTC price data from Binance using pagination.
    """
    symbol = "BTCUSDT"
    interval = "1d"
    url = "https://api.binance.com/api/v3/klines"
    
    # Start time in ms
    start_time = int(datetime(start_year, 1, 1).timestamp() * 1000)
    all_klines = []
    
    try:
        while True:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'limit': 1000
            }
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            klines = response.json()
            
            if not klines:
                break
            
            all_klines.extend(klines)
            
            # Update start_time for next batch: last_timestamp + 1ms
            # The timestamp is the first element of each kline
            last_timestamp = klines[-1][0]
            start_time = last_timestamp + 86400000 # plus 1 day in ms
            
            # Stop if we reached today
            if start_time > int(time.time() * 1000):
                break
                
            # Rate limiting safety
            time.sleep(0.1)
            
        # [0] Open time, [4] Close price
        df = pd.DataFrame(all_klines)
        df = df[[0, 4]].rename(columns={0: 'timestamp', 4: 'price'})
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df['price'] = pd.to_numeric(df['price'])
        
        # Ensure daily (Binance might return multiple if not aligned)
        df = df.groupby('date').last().reset_index()
        
        return df[['date', 'price']]
    except Exception as e:
        print(f"Error fetching BTC data from Binance: {e}")
        return None

def get_merged_data():
    """
    Fetches both and merges them on date.
    """
    fng_df = get_fng_data()
    btc_df = get_btc_data_from_binance()
    
    if fng_df is None or btc_df is None:
        return None
    
    # Merge on date
    merged_df = pd.merge(fng_df, btc_df, on='date', how='inner')
    merged_df = merged_df.sort_values('date')
    
    return merged_df

if __name__ == "__main__":
    df = get_merged_data()
    if df is not None:
        print(f"Merged data preview (first 5 days):\n{df.head()}")
        print(f"Merged data preview (last 5 days):\n{df.tail()}")
        print(f"Total rows: {len(df)}")
    else:
        print("Failed to fetch/merge data.")
