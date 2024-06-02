import yfinance as yf
import numpy as np
import pandas as pd 

def get_data(start_date:str,end_date:str) -> pd.DataFrame:
    
    """
    start,end: %Y-%m-%d string 

    Returns OHLC DF for BTC prices 
    """

    btc = pd.DataFrame(yf.download("BTC-USD",period="1d",start=start_date,end=end_date))
    
    return btc

def calculate_strat(df:pd.DataFrame, n_loss_days:int) -> pd.DataFrame:

    df['pct_change'] = df['Close'].pct_change()
    df['down'] = np.where(df['pct_change'] < 0 ,1,0)

    df['candle_change'] = (df['down'] != df['down'].shift(1)).cumsum()
    df['consecutive_count'] = df.groupby('candle_change').cumcount()+1 #cuentas cuanta ocurrencias consecutivas ha habido del candle change
    df['consecutive_count'] = np.where(df['down']==1,-df['consecutive_count'],df['consecutive_count']) #fix for red candles
    df = df.reset_index()

    df['buy_signal'] = (df['down'] == 1) & (df['consecutive_count']==-n_loss_days)
    df['holding_position'] = df['buy_signal'].shift().replace(False,np.nan).ffill()
    
    df['Sell_Signal_Long'] = df['holding_position'] & (df['down'] == 1)
    df['Buy_Price'] = np.where(df['buy_signal'], df['Close'], np.nan)
    df['Sell_Price'] = np.where(df['Sell_Signal_Long'], df['Close'], np.nan)
    df['Buy_Price'] = df['Buy_Price'].ffill() 

    df['buy_return'] = np.where(df['Sell_Signal_Long'], df['Sell_Price'] /df['Buy_Price'] - 1, 0)    

    return df 

def calculate_strat_returns(df:pd.DataFrame,initial_investment:int) -> pd.DataFrame:
    
    initial_investment = initial_investment
    df['investment_value'] = initial_investment
    investment_value = initial_investment
    invested = True #empieza invertido por estructura de df
    
    for i in range(len(df)):
        if df['Sell_Signal_Long'].iloc[i]: #este if statement esta mal porque no esta acompañado de un flag que indique que tengo un long position
            if invested:
                # print(f"dia: {df['Date'].iloc[i]} - Investment value Pre: {df['investment_value'].iloc[i]} - Return {df['buy_return'].iloc[i]}")
                investment_value *= (1+df['buy_return'].iloc[i])
                # print("New investment value: ",investment_value)
                df.loc[i:,'holding_position'] = False 
                df.loc[i:,'investment_value'] = investment_value
                invested=False
                continue
        
        if not df['holding_position'].iloc[i] and df['buy_signal'].iloc[i]:
            df.loc[i:,'investment_value'] = investment_value
            df.loc[i:,'holding_position'] = True
            invested = True
                
    return df 

def generate_hold_df(start_date:str,end_date:str,initial_investment:int) -> pd.DataFrame:
    
    hold_df = pd.DataFrame(yf.download("BTC-USD",period="1d",start=start_date,end=end_date))
    hold_df = hold_df.reset_index()
    hold_df['pct_change'] = hold_df['Close'].pct_change()
    
    hold_df = hold_df[['Date','Close','pct_change']]
    
    initial_investment = 10000
    investment = [initial_investment]

    for i in range(1,len(hold_df)):
        daily_return = investment[-1] * (1+hold_df['pct_change'].iloc[i])
        investment.append(daily_return)

    hold_df['returns'] = investment

    return hold_df