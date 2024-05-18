import logging
import requests
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_crypto_data(crypto: str, interval: str, time_delta: timedelta):
    end_date = datetime.utcnow()
    start_date = end_date - time_delta
    url = f'https://api.coincap.io/v2/assets/{crypto}/history?interval={interval}&start={int(start_date.timestamp() * 1000)}&end={int(end_date.timestamp() * 1000)}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        logger.info(f"Код состояния ответа API: {response.status_code}")
        data = response.json()
        logger.info(f"Данные ответа API: {data}")
        prices = [{'timestamp': item['time'], 'price': item['priceUsd']} for item in data['data']]
        df = pd.DataFrame(prices)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['price'] = df['price'].astype(float)
        logger.info(f"Начало DataFrame: {df.head()}")
        return df
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении данных с CoinCap: {e}")
        return pd.DataFrame()
