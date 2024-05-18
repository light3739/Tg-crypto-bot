import logging
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_indicators(df):
    if df.empty:
        logger.error("DataFrame пуст. Невозможно рассчитать индикаторы.")
        return df

    df['EMA12'] = df['price'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['price'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    logger.info(f"Начало MACD: {df[['timestamp', 'MACD', 'Signal Line']].head()}")

    df['L14'] = df['price'].rolling(window=14).min()
    df['H14'] = df['price'].rolling(window=14).max()
    df['%K'] = 100 * ((df['price'] - df['L14']) / (df['H14'] - df['L14']))
    df['%D'] = df['%K'].rolling(window=3).mean()

    logger.info(f"Начало стохастического осциллятора: {df[['timestamp', '%K', '%D']].head()}")

    return df
