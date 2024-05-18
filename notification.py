import logging
import psycopg2
from bot_instance import bot
from config import DATABASE_URL
from data_fetcher import get_crypto_data
from metrics_calculator import calculate_price_change
import datetime
from datetime import timedelta

logger = logging.getLogger('notifications')


def get_subscriptions():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT u.telegram_id, s.crypto, s.threshold, s.threshold_type, s.last_notified "
        "FROM subscriptions s "
        "JOIN users u ON s.user_id = u.user_id")
    subscriptions = cur.fetchall()
    cur.close()
    conn.close()
    return subscriptions


async def check_price_changes():
    logger.debug("Начало проверки изменения цен для всех подписок.")
    subscriptions = get_subscriptions()
    for telegram_id, crypto, threshold, threshold_type, last_notified in subscriptions:
        logger.debug(f"Проверка изменения цен для пользователя {telegram_id} и криптовалюты {crypto}.")
        df = get_crypto_data(crypto, 'm1', timedelta(minutes=5))
        if not df.empty:
            price_change = calculate_price_change(df)
            logger.debug(f"Изменение цены для {crypto}: {price_change:.2f}%")
            if (threshold_type == 'increase' and price_change >= threshold) or \
                    (threshold_type == 'decrease' and price_change <= -threshold):
                if should_notify(last_notified):
                    await send_notification(telegram_id, crypto, price_change, threshold_type)
                    update_last_notified(telegram_id, crypto)
        else:
            logger.warning(f"Данные для {crypto} не получены. Пропуск.")


def should_notify(last_notified):
    if last_notified is None:
        return True
    now = datetime.datetime.utcnow()
    last_notified_time = last_notified.replace(tzinfo=None)
    return (now - last_notified_time).total_seconds() > 300


async def send_notification(telegram_id, crypto, price_change, threshold_type):
    direction = "повысилась" if threshold_type == "increase" else "понизилась"
    message = f"Цена {crypto} {direction} на {price_change:.2f}%"
    await bot.bot.send_message(chat_id=telegram_id, text=message)
    logger.info(f"Отправлено уведомление пользователю {telegram_id} для {crypto}: {price_change:.2f}%")


def update_last_notified(telegram_id, crypto):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        UPDATE subscriptions
        SET last_notified = %s
        WHERE user_id = (SELECT user_id FROM users WHERE telegram_id = %s) AND crypto = %s
    """, (datetime.datetime.utcnow(), telegram_id, crypto))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Обновлено время последнего уведомления для {telegram_id} и {crypto}")
