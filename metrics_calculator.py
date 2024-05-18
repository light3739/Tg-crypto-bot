import logging
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def calculate_volatility(df):
    if df.empty:
        logger.error("DataFrame пуст. Невозможно рассчитать волатильность.")
        return None
    df['returns'] = df['price'].pct_change()
    volatility = df['returns'].std() * (30 ** 0.5)
    logger.info(f"Рассчитанная волатильность: {volatility}")
    return volatility


def calculate_metrics(df):
    if df.empty:
        logger.error("DataFrame пуст. Невозможно рассчитать метрики.")
        return df

    df['SMA'] = df['price'].rolling(window=10).mean()

    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['Middle Band'] = df['SMA']
    df['Upper Band'] = df['SMA'] + (df['price'].rolling(window=10).std() * 2)
    df['Lower Band'] = df['SMA'] - (df['price'].rolling(window=10).std() * 2)

    return df


def calculate_price_change(df):
    df = df.sort_values(by='timestamp')

    latest_timestamp = df['timestamp'].iloc[-1]

    five_minutes_ago = latest_timestamp - timedelta(minutes=5)

    df_last_5_minutes = df[df['timestamp'] >= five_minutes_ago]

    if len(df_last_5_minutes) < 2:
        return 0

    latest_price = df_last_5_minutes['price'].iloc[-1]
    previous_price = df_last_5_minutes['price'].iloc[0]

    price_change = ((latest_price - previous_price) / previous_price) * 100
    return price_change
