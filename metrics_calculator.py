import logging
import pandas as pd

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
