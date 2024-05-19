import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from config import DATABASE_URL

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


def save_crypto_data(df, crypto, table_name):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    for index, row in df.iterrows():
        # Проверяем, существует ли запись с такой же комбинацией crypto и timestamp
        cur.execute(f"""
            SELECT 1 FROM {table_name} WHERE crypto = %s AND timestamp = %s
        """, (crypto, row['timestamp']))
        exists = cur.fetchone()

        if exists:
            # Обновляем существующую запись
            cur.execute(f"""
                UPDATE {table_name} SET price = %s WHERE crypto = %s AND timestamp = %s
            """, (row['price'], crypto, row['timestamp']))
        else:
            # Вставляем новую запись
            cur.execute(f"""
                INSERT INTO {table_name} (crypto, timestamp, price) VALUES (%s, %s, %s)
            """, (crypto, row['timestamp'], row['price']))

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Данные для {crypto} сохранены в таблицу {table_name}")


def save_crypto_sub_data(df, crypto):
    save_crypto_data(df, crypto, 'crypto_sub')


def save_crypto_charts_data(df, crypto):
    save_crypto_data(df, crypto, 'crypto_charts')


def get_crypto_data_last_5_minutes(crypto):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, price FROM crypto_sub
        WHERE crypto = %s AND timestamp >= NOW() - INTERVAL '5 minutes'
        ORDER BY timestamp
    """, (crypto,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df
