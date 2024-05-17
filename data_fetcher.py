import logging
import requests
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_crypto_data(crypto: str):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=90)  # Fetch 90 days of data
    url = f'https://api.coincap.io/v2/assets/{crypto}/history?interval=d1&start={int(start_date.timestamp() * 1000)}&end={int(end_date.timestamp() * 1000)}'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        logger.info(f"API response status code: {response.status_code}")
        data = response.json()
        logger.info(f"API response data: {data}")
        prices = [{'timestamp': item['time'], 'price': item['priceUsd']} for item in data['data']]
        df = pd.DataFrame(prices)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['price'] = df['price'].astype(float)
        logger.info(f"DataFrame head: {df.head()}")
        return df
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from CoinCap: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error
