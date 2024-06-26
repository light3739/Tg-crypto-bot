import logging
from datetime import timedelta, datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import psycopg2
from data_fetcher import get_crypto_data, save_crypto_sub_data, save_crypto_charts_data
from metrics_calculator import calculate_volatility, calculate_metrics
from indicators_calculator import calculate_indicators
from news_fetcher import fetch_latest_news, save_news_to_db, get_last_fetched_news_time
from plot_creator import create_plot, create_indicators_plot, create_gauge, get_crypto_chart_data
import os
from config import IMAGES_DIR, DATABASE_URL, NEWS_API_KEY

logger = logging.getLogger(__name__)

SELECT_CRYPTO, SELECT_CHART = range(2)
SELECT_SUBSCRIBE_CRYPTO, SELECT_THRESHOLD_TYPE, SET_THRESHOLD, SELECT_UNSUBSCRIBE_TYPE = range(4)

CRYPTO_KEYBOARD = [
    [InlineKeyboardButton("Bitcoin", callback_data='bitcoin')],
    [InlineKeyboardButton("Ethereum", callback_data='ethereum')],
    [InlineKeyboardButton("Tether", callback_data='tether')],
    [InlineKeyboardButton("Solana", callback_data='solana')],
]

THRESHOLD_TYPE_KEYBOARD = [
    [InlineKeyboardButton("Повышение", callback_data='increase')],
    [InlineKeyboardButton("Понижение", callback_data='decrease')],
]

CHART_TYPE_KEYBOARD = [
    [InlineKeyboardButton("График цен", callback_data='price')],
    [InlineKeyboardButton("График индикаторов", callback_data='indicators')],
    [InlineKeyboardButton("Индикатор волатильности", callback_data='volatility')],
    [InlineKeyboardButton("Индикатор RSI", callback_data='rsi')],
]


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api_key = NEWS_API_KEY
    last_fetched_time = get_last_fetched_news_time()
    if not last_fetched_time or (datetime.now() - last_fetched_time).total_seconds() > 86400:
        latest_news = fetch_latest_news(api_key)
        if latest_news:
            save_news_to_db(latest_news)
            await update.message.reply_text(latest_news["simplified_message"], parse_mode='Markdown')
        else:
            await update.message.reply_text("Новостные статьи не найдены.")
    else:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "SELECT title, summary, article_url, time_published, authors FROM crypto_news ORDER BY fetched_at DESC LIMIT 1")
        news_article = cur.fetchone()
        cur.close()
        conn.close()
        if news_article:
            title, summary, article_url, time_published, authors = news_article
            message = f"{title}\n\n{summary}\n\n[Читать далее]({article_url})\n\n{time_published}\n\n{authors}"
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("Новостные статьи не найдены.")


def get_user_id(telegram_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_markup = InlineKeyboardMarkup(CRYPTO_KEYBOARD)
    await update.message.reply_text('Пожалуйста, выберите криптовалюту для подписки:', reply_markup=reply_markup)
    return SELECT_SUBSCRIBE_CRYPTO


async def select_subscribe_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['crypto'] = query.data

    keyboard = THRESHOLD_TYPE_KEYBOARD + [[InlineKeyboardButton("Отписаться", callback_data='unsubscribe')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f'Выбрана криптовалюта: {query.data}\nВы хотите подписаться на повышение или понижение цены, или отписаться?',
        reply_markup=reply_markup
    )
    return SELECT_THRESHOLD_TYPE


async def select_threshold_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    threshold_type = query.data

    if threshold_type == 'unsubscribe':
        context.user_data['threshold_type'] = threshold_type
        reply_markup = InlineKeyboardMarkup(THRESHOLD_TYPE_KEYBOARD)
        await query.edit_message_text(
            text=f'Вы выбрали отписаться от {context.user_data["crypto"]}. Выберите тип подписки для отписки:',
            reply_markup=reply_markup
        )
        return SELECT_UNSUBSCRIBE_TYPE
    else:
        context.user_data['threshold_type'] = threshold_type
        await query.edit_message_text(
            text=f'Выбран тип порога: {threshold_type}\nПожалуйста, введите порог изменения цены (в %):'
        )
        return SET_THRESHOLD


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    threshold = float(update.message.text)
    crypto = context.user_data['crypto']
    threshold_type = context.user_data['threshold_type']
    telegram_id = update.message.from_user.id
    username = update.message.from_user.username

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users (telegram_id, username) VALUES (%s, %s) ON CONFLICT (telegram_id) DO NOTHING RETURNING user_id",
        (telegram_id, username))
    user_id = cur.fetchone()[0] if cur.rowcount > 0 else get_user_id(telegram_id)

    cur.execute("INSERT INTO subscriptions (user_id, crypto, threshold, threshold_type) VALUES (%s, %s, %s, %s)",
                (user_id, crypto, threshold, threshold_type))
    conn.commit()
    cur.close()
    conn.close()

    threshold_type_ru = "повышение" if threshold_type == "increase" else "понижение"
    await update.message.reply_text(f'Подписка на {crypto} с порогом {threshold_type_ru} в {threshold}% оформлена')
    return ConversationHandler.END


async def select_unsubscribe_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    threshold_type = query.data
    crypto = context.user_data['crypto']
    telegram_id = update.callback_query.from_user.id

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM subscriptions
        WHERE user_id = (SELECT user_id FROM users WHERE telegram_id = %s) AND crypto = %s AND threshold_type = %s
    """, (telegram_id, crypto, threshold_type))
    conn.commit()
    cur.close()
    conn.close()

    threshold_type_ru = "повышение" if threshold_type == "increase" else "понижение"
    await query.edit_message_text(f'Отписка от уведомлений {crypto} {threshold_type_ru} выполнена.')
    return ConversationHandler.END


async def show_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.message.from_user.id

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT crypto, threshold, threshold_type
        FROM subscriptions
        WHERE user_id = (SELECT user_id FROM users WHERE telegram_id = %s)
    """, (telegram_id,))
    subscriptions = cur.fetchall()
    cur.close()
    conn.close()

    if subscriptions:
        message = "Ваши подписки:\n"
        for crypto, threshold, threshold_type in subscriptions:
            threshold_type_ru = "повышение" if threshold_type == "increase" else "понижение"
            message += f"- {crypto.capitalize()}: порог {threshold_type_ru} в {threshold}%\n"
    else:
        message = "У вас нет подписок."

    await update.message.reply_text(message)


async def select_crypto_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_markup = InlineKeyboardMarkup(CRYPTO_KEYBOARD)
    message = await update.message.reply_text('Пожалуйста, выберите криптовалюту:', reply_markup=reply_markup)
    context.user_data['message_id'] = message.message_id
    logger.debug(f"ID сообщения для удаления сохранен: {message.message_id}")
    return SELECT_CRYPTO


async def select_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['crypto'] = query.data

    reply_markup = InlineKeyboardMarkup(CHART_TYPE_KEYBOARD)
    message = await query.edit_message_text(
        text=f'Выбрана криптовалюта: {query.data}\nПожалуйста, выберите тип графика:',
        reply_markup=reply_markup)
    context.user_data['message_id'] = message.message_id
    logger.debug(f"ID сообщения для удаления обновлен: {message.message_id}")
    return SELECT_CHART


async def select_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chart_type = query.data
    crypto = context.user_data['crypto']

    logger.info(f"Получение данных для {crypto}")

    df = get_crypto_data(crypto, 'd1', timedelta(days=90))
    if not df.empty:
        save_crypto_charts_data(df, crypto) 

    df = get_crypto_chart_data(crypto)
    if df.empty:
        await query.edit_message_text(f"Не удалось получить данные для {crypto.capitalize()}")
        return ConversationHandler.END

    df = calculate_metrics(df)
    df = calculate_indicators(df)
    volatility = calculate_volatility(df)

    if volatility is None:
        await query.edit_message_text(f"Не удалось рассчитать волатильность для {crypto.capitalize()}")
        return ConversationHandler.END

    message_id = context.user_data.get('message_id')
    logger.debug(f"ID сообщения для удаления: {message_id}")

    if chart_type == 'price':
        logger.info(f"Создание графика цен для {crypto}")
        create_plot(df, crypto)
        file_path = os.path.join(IMAGES_DIR, f'{crypto}.png')
        if os.path.exists(file_path):
            with open(file_path, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'График цен для {crypto.capitalize()}')
                logger.debug(f"Фото для {crypto} отправлено")
        else:
            logger.error(f"Файл {file_path} не существует")
            await query.edit_message_text(f"Не удалось создать график для {crypto.capitalize()}")

    elif chart_type == 'indicators':
        logger.info(f"Создание графика индикаторов для {crypto}")
        create_indicators_plot(df, crypto)
        indicators_file_path = os.path.join(IMAGES_DIR, f'{crypto}_indicators.png')
        if os.path.exists(indicators_file_path):
            with open(indicators_file_path, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'График индикаторов для {crypto.capitalize()}')
                logger.debug(f"Фото индикаторов для {crypto} отправлено")
        else:
            logger.error(f"Файл {indicators_file_path} не существует")
            await query.edit_message_text(f"Не удалось создать график индикаторов для {crypto.capitalize()}")

    elif chart_type == 'volatility':
        logger.info(f"Создание индикатора волатильности для {crypto}")
        volatility_gauge = create_gauge(volatility, "Волатильность", max_value=1)
        volatility_gauge_file = os.path.join(IMAGES_DIR, f'{crypto}_volatility.png')
        volatility_gauge.write_image(volatility_gauge_file)
        if os.path.exists(volatility_gauge_file):
            with open(volatility_gauge_file, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'Индикатор волатильности для {crypto.capitalize()}')
                logger.debug(f"Фото индикатора волатильности для {crypto} отправлено")
        else:
            logger.error(f"Файл {volatility_gauge_file} не существует")
            await query.edit_message_text(f"Не удалось создать индикатор волатильности для {crypto.capitalize()}")

    elif chart_type == 'rsi':
        logger.info(f"Создание индикатора RSI для {crypto}")
        rsi_value = df['RSI'].iloc[-1]
        rsi_gauge = create_gauge(rsi_value, "RSI", max_value=100)
        rsi_gauge_file = os.path.join(IMAGES_DIR, f'{crypto}_rsi.png')
        rsi_gauge.write_image(rsi_gauge_file)
        if os.path.exists(rsi_gauge_file):
            with open(rsi_gauge_file, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'Индикатор RSI для {crypto.capitalize()}')
                logger.debug(f"Фото индикатора RSI для {crypto} отправлено")
        else:
            logger.error(f"Файл {rsi_gauge_file} не существует")
            await query.edit_message_text(f"Не удалось создать индикатор RSI для {crypto.capitalize()}")

    if message_id:
        try:
            logger.debug(f"Попытка удалить сообщение с ID: {message_id}")
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
            logger.debug(f"Сообщение с ID: {message_id} удалено")
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение с ID {message_id}: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Операция отменена.')
    return ConversationHandler.END


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Привет, {update.effective_user.first_name}')
