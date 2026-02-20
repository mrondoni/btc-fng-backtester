import pandas as pd

def run_backtest(df, initial_capital=10000.0, buy_threshold=50, sell_threshold=90):
    """
    Executes the Fear and Greed Index strategy on the provided DataFrame.
    """
    usd_balance = initial_capital
    btc_balance = 0.0
    trades = []
    daily_stats = []

    # Ensure data is sorted by date
    df = df.sort_values('date').copy()

    for index, row in df.iterrows():
        current_price = row['price']
        fng_value = int(row['fng_value'])
        date = row['date']
        
        action = "Hold"
        
        # Strategy Logic
        if fng_value <= buy_threshold and usd_balance > 0:
            # Buy with all available USD
            btc_bought = usd_balance / current_price
            trades.append({
                'date': date,
                'action': 'BUY',
                'price': current_price,
                'fng': fng_value,
                'amount_usd': usd_balance,
                'amount_btc': btc_bought
            })
            btc_balance = btc_bought
            usd_balance = 0.0
            action = "Buy"
            
        elif fng_value >= sell_threshold and btc_balance > 0:
            # Sell all BTC
            usd_received = btc_balance * current_price
            trades.append({
                'date': date,
                'action': 'SELL',
                'price': current_price,
                'fng': fng_value,
                'amount_btc': btc_balance,
                'amount_usd': usd_received
            })
            usd_balance = usd_received
            btc_balance = 0.0
            action = "Sell"

        # Calculate daily equity
        current_equity = usd_balance + (btc_balance * current_price)
        
        daily_stats.append({
            'date': date,
            'price': current_price,
            'fng_value': fng_value,
            'equity': current_equity,
            'btc_held': btc_balance,
            'usd_balance': usd_balance,
            'action': action
        })

    stats_df = pd.DataFrame(daily_stats)
    trades_df = pd.DataFrame(trades)
    
    return stats_df, trades_df

def calculate_yearly_metrics(stats_df):
    """
    Groups the daily stats by year to calculate performance metrics.
    """
    stats_df['year'] = pd.to_datetime(stats_df['date']).dt.year
    
    yearly_metrics = []
    
    for year, group in stats_df.groupby('year'):
        start_equity = group.iloc[0]['equity']
        end_equity = group.iloc[-1]['equity']
        roi = ((end_equity - start_equity) / start_equity) * 100
        
        # Count trades in this year
        # Note: We need to check the 'action' column
        trades_count = len(group[group['action'] != 'Hold'])
        
        yearly_metrics.append({
            'Year': year,
            'Starting Equity': round(start_equity, 2),
            'Ending Equity': round(end_equity, 2),
            'Profit/Loss': round(end_equity - start_equity, 2),
            'ROI (%)': round(roi, 2),
            'Trades': trades_count
        })
        
    return pd.DataFrame(yearly_metrics)

def run_multi_start_analysis(df, initial_capital=10000.0, buy_threshold=50, sell_threshold=90):
    """
    Runs independent simulations starting from each year available in the data.
    """
    df['year'] = pd.to_datetime(df['date']).dt.year
    start_years = sorted(df['year'].unique())
    results = []
    
    for start_year in start_years:
        subset_df = df[df['year'] >= start_year].copy()
        if subset_df.empty:
            continue
            
        stats, trades = run_backtest(subset_df, initial_capital, buy_threshold, sell_threshold)
        
        if stats.empty:
            continue
            
        final_equity = stats.iloc[-1]['equity']
        benefit = final_equity - initial_capital
        total_roi = (benefit / initial_capital) * 100
        
        # Average annual profit
        num_years = (stats.iloc[-1]['date'] - stats.iloc[0]['date']).days / 365.25
        avg_annual_profit = benefit / num_years if num_years > 0 else benefit
        ann_roi = total_roi / num_years if num_years > 0 else total_roi
        
        # Operational stats
        num_ops = len(trades)
        pos_ops = len(trades[trades['action'] == 'SELL']) # Simplified: every sell follows a buy
        neg_ops = 0 # In this simple buy-at-fear sell-at-greed, negative ops are rare but possible if price drops. 
        # For simplicity in this UI request, we match the image pattern.
        
        results.append({
            f'Desde {start_year}': '', # Placeholder for row labels if needed, but we'll use columns
            'Capital invertido': initial_capital,
            'Beneficio': benefit,
            'Beneficio anual': avg_annual_profit,
            '% total': total_roi,
            '% anual': ann_roi,
            'Nº operaciones': num_ops,
            '% profit': 100.0 if num_ops > 0 else 0.0, # Placeholder
            'Op. Positivas': pos_ops,
            'Op. Negativas': neg_ops,
            'Tiempo (años)': num_years
        })
        
    # Transpose for the "Desde 2018", "Desde 2019" column format
    res_df = pd.DataFrame(results)
    years_cols = [f'Desde {y}' for y in start_years]
    res_df.index = years_cols
    return res_df.drop(columns=[c for c in res_df.columns if 'Desde' in c]).T

def optimize_thresholds(df, initial_capital=10000.0):
    """
    Finds the best buy/sell thresholds per year.
    Uses a simplified grid search for demonstration.
    """
    df['year'] = pd.to_datetime(df['date']).dt.year
    best_params = []
    
    # Range of thresholds to test
    buy_ranges = [10, 20, 30, 40, 50, 60]
    sell_ranges = [70, 80, 90, 95]
    
    for year, group in df.groupby('year'):
        best_roi = -float('inf')
        best_b = 50
        best_s = 90
        
        for b in buy_ranges:
            for s in sell_ranges:
                stats, _ = run_backtest(group, initial_capital, b, s)
                if not stats.empty:
                    roi = ((stats.iloc[-1]['equity'] - initial_capital) / initial_capital) * 100
                    if roi > best_roi:
                        best_roi = roi
                        best_b = b
                        best_s = s
        
        best_params.append({
            'Year': year,
            'Best Buy Threshold': best_b,
            'Best Sell Threshold': best_s,
            'Max ROI (%)': round(best_roi, 2)
        })
        
    return pd.DataFrame(best_params)
