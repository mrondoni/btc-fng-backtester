import pandas as pd
import requests
from datetime import datetime
import time
import os
import json

def get_fng_data():
    """
    Loads FNG data from local JSON if available, otherwise fetches from API.
    """
    json_path = "fng_data.json"
    
    # Try local JSON first
    if os.path.exists(json_path):
        try:
            df = pd.read_json(json_path)
            df['date'] = pd.to_datetime(df['date']).dt.date
            return df[['date', 'fng_value', 'fng_classification']]
        except Exception as e:
            print(f"Error reading local FNG JSON: {e}")

    # Fallback to API
    url = "https://api.alternative.me/fng/?limit=0"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='s').dt.date
        df = df.rename(columns={'value': 'fng_value', 'value_classification': 'fng_classification'})
        return df[['date', 'fng_value', 'fng_classification']]
    except Exception as e:
        error_msg = f"Error fetching FNG data from API: {e}"
        print(error_msg)
        return None

def get_btc_data_from_binance(start_year=2018):
    """
    Loads BTC data from local JSON if available, otherwise fetches from Binance.
    """
    json_path = "btc_data.json"
    
    # Try local JSON first
    if os.path.exists(json_path):
        try:
            df = pd.read_json(json_path)
            df['date'] = pd.to_datetime(df['date']).dt.date
            return df[['date', 'price']]
        except Exception as e:
            print(f"Error reading local BTC JSON: {e}")

    # Fallback to API
    symbol = "BTCUSDT"
    interval = "1d"
    endpoints = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://api-gcp.binance.com"
    ]
    start_time = int(datetime(start_year, 1, 1).timestamp() * 1000)
    all_klines = []
    
    try:
        current_endpoint_idx = 0
        while True:
            params = {'symbol': symbol, 'interval': interval, 'startTime': start_time, 'limit': 1000}
            url = f"{endpoints[current_endpoint_idx]}/api/v3/klines"
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
            except Exception as e:
                current_endpoint_idx += 1
                if current_endpoint_idx >= len(endpoints):
                    raise Exception(f"All Binance endpoints failed: {e}")
                continue

            klines = response.json()
            if not klines: break
            all_klines.extend(klines)
            last_timestamp = klines[-1][0]
            start_time = last_timestamp + 86400000
            if start_time > int(time.time() * 1000): break
            time.sleep(0.1)
            
        df = pd.DataFrame(all_klines)
        df = df[[0, 4]].rename(columns={0: 'timestamp', 4: 'price'})
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df['price'] = pd.to_numeric(df['price'])
        df = df.groupby('date').last().reset_index()
        return df[['date', 'price']]
    except Exception as e:
        print(f"Error fetching BTC data from API: {e}")
        return None

def get_merged_data():
    """
    Fetches both and merges them on date.
    """
    fng_df = get_fng_data()
    btc_df = get_btc_data_from_binance()
    
    if fng_df is None or btc_df is None:
        return None
    
    merged_df = pd.merge(fng_df, btc_df, on='date', how='inner')
    merged_df = merged_df.sort_values('date')
    
    return merged_df

if __name__ == "__main__":
    df = get_merged_data()
    if df is not None:
        print(f"Data Loaded Successfully. Rows: {len(df)}")
        print(df.tail())
    else:
        print("Failed to load data.")
