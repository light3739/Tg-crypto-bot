import logging
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def calculate_volatility(df):
    if df.empty:
        logger.error("DataFrame is empty. Cannot calculate volatility.")
        return None
    df['returns'] = df['price'].pct_change()
    volatility = df['returns'].std() * (30 ** 0.5)  # Monthly volatility
    logger.info(f"Calculated volatility: {volatility}")
    return volatility


def calculate_metrics(df):
    if df.empty:
        logger.error("DataFrame is empty. Cannot calculate metrics.")
        return df

    # Calculate Simple Moving Average (SMA)
    df['SMA'] = df['price'].rolling(window=10).mean()

    # Calculate Relative Strength Index (RSI)
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Calculate Bollinger Bands
    df['Middle Band'] = df['SMA']
    df['Upper Band'] = df['SMA'] + (df['price'].rolling(window=10).std() * 2)
    df['Lower Band'] = df['SMA'] - (df['price'].rolling(window=10).std() * 2)

    return df


def calculate_price_change(df):
    # Ensure the dataframe is sorted by timestamp
    df = df.sort_values(by='timestamp')

    # Get the latest timestamp
    latest_timestamp = df['timestamp'].iloc[-1]

    # Calculate the timestamp for 5 minutes ago
    five_minutes_ago = latest_timestamp - timedelta(minutes=5)

    # Filter the dataframe to get the prices from the last 5 minutes
    df_last_5_minutes = df[df['timestamp'] >= five_minutes_ago]

    if len(df_last_5_minutes) < 2:
        # Not enough data to calculate price change
        return 0

    # Get the latest price and the price from 5 minutes ago
    latest_price = df_last_5_minutes['price'].iloc[-1]
    previous_price = df_last_5_minutes['price'].iloc[0]

    # Calculate the price change
    price_change = ((latest_price - previous_price) / previous_price) * 100
    return price_change
