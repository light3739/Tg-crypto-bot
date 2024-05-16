import logging
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_indicators(df):
    if df.empty:
        logger.error("DataFrame is empty. Cannot calculate indicators.")
        return df

    # Calculate MACD
    df['EMA12'] = df['price'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['price'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Log MACD and Signal Line calculations
    logger.info(f"MACD head: {df[['timestamp', 'MACD', 'Signal Line']].head()}")

    # Calculate Stochastic Oscillator
    df['L14'] = df['price'].rolling(window=14).min()
    df['H14'] = df['price'].rolling(window=14).max()
    df['%K'] = 100 * ((df['price'] - df['L14']) / (df['H14'] - df['L14']))
    df['%D'] = df['%K'].rolling(window=3).mean()

    # Log Stochastic Oscillator calculations
    logger.info(f"Stochastic Oscillator head: {df[['timestamp', '%K', '%D']].head()}")

    return df
