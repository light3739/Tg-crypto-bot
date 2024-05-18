import logging
from datetime import timedelta, datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import psycopg2
from data_fetcher import get_crypto_data
from metrics_calculator import calculate_volatility, calculate_metrics
from indicators_calculator import calculate_indicators
from news_fetcher import fetch_latest_news, save_news_to_db, get_last_fetched_news_time
from plot_creator import create_plot, create_indicators_plot, create_gauge
import os
from config import IMAGES_DIR, DATABASE_URL, NEWS_API_KEY

logger = logging.getLogger(__name__)

# Define states for the conversation
SELECT_CRYPTO, SELECT_CHART = range(2)
SELECT_SUBSCRIBE_CRYPTO, SELECT_THRESHOLD_TYPE, SET_THRESHOLD, SELECT_UNSUBSCRIBE_TYPE = range(4)

# Define common keyboard options
CRYPTO_KEYBOARD = [
    [InlineKeyboardButton("Bitcoin", callback_data='bitcoin')],
    [InlineKeyboardButton("Ethereum", callback_data='ethereum')],
    [InlineKeyboardButton("Tether", callback_data='tether')],
    [InlineKeyboardButton("Solana", callback_data='solana')],
]

THRESHOLD_TYPE_KEYBOARD = [
    [InlineKeyboardButton("Increase", callback_data='increase')],
    [InlineKeyboardButton("Decrease", callback_data='decrease')],
]

CHART_TYPE_KEYBOARD = [
    [InlineKeyboardButton("Price Chart", callback_data='price')],
    [InlineKeyboardButton("Indicators Chart", callback_data='indicators')],
    [InlineKeyboardButton("Volatility Gauge", callback_data='volatility')],
    [InlineKeyboardButton("RSI Gauge", callback_data='rsi')],
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
    await update.message.reply_text('Please choose a cryptocurrency to subscribe to:', reply_markup=reply_markup)
    return SELECT_SUBSCRIBE_CRYPTO


async def select_subscribe_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['crypto'] = query.data

    keyboard = THRESHOLD_TYPE_KEYBOARD + [[InlineKeyboardButton("Unsubscribe", callback_data='unsubscribe')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f'Selected cryptocurrency: {query.data}\nDo you want to subscribe for an increase or decrease in price, or unsubscribe?',
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
            text=f'Selected to unsubscribe from {context.user_data["crypto"]}. Choose the type of subscription to unsubscribe from:',
            reply_markup=reply_markup
        )
        return SELECT_UNSUBSCRIBE_TYPE
    else:
        context.user_data['threshold_type'] = threshold_type
        await query.edit_message_text(
            text=f'Selected threshold type: {threshold_type}\nPlease enter the price change threshold (in %):'
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

    # Insert user if not exists and get user_id
    cur.execute(
        "INSERT INTO users (telegram_id, username) VALUES (%s, %s) ON CONFLICT (telegram_id) DO NOTHING RETURNING user_id",
        (telegram_id, username))
    user_id = cur.fetchone()[0] if cur.rowcount > 0 else get_user_id(telegram_id)

    # Insert subscription
    cur.execute("INSERT INTO subscriptions (user_id, crypto, threshold, threshold_type) VALUES (%s, %s, %s, %s)",
                (user_id, crypto, threshold, threshold_type))
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(f'Subscribed to {crypto} with a {threshold_type} threshold of {threshold}%')
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

    await query.edit_message_text(f'Unsubscribed from {crypto} {threshold_type} notifications.')
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
        message = "Your subscriptions:\n"
        for crypto, threshold, threshold_type in subscriptions:
            message += f"- {crypto.capitalize()}: {threshold_type.capitalize()} threshold of {threshold}%\n"
    else:
        message = "You have no subscriptions."

    await update.message.reply_text(message)


async def select_crypto_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_markup = InlineKeyboardMarkup(CRYPTO_KEYBOARD)
    message = await update.message.reply_text('Please choose a cryptocurrency:', reply_markup=reply_markup)
    context.user_data['message_id'] = message.message_id
    logger.debug(f"Stored message ID for deletion: {message.message_id}")
    return SELECT_CRYPTO


async def select_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['crypto'] = query.data

    reply_markup = InlineKeyboardMarkup(CHART_TYPE_KEYBOARD)
    message = await query.edit_message_text(text=f'Selected cryptocurrency: {query.data}\nPlease choose a chart type:',
                                            reply_markup=reply_markup)
    context.user_data['message_id'] = message.message_id
    logger.debug(f"Updated message ID for deletion: {message.message_id}")
    return SELECT_CHART


async def select_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chart_type = query.data
    crypto = context.user_data['crypto']

    logger.info(f"Fetching data for {crypto}")
    df = get_crypto_data(crypto, 'd1', timedelta(days=90))
    if df.empty:
        await query.edit_message_text(f"Failed to fetch data for {crypto.capitalize()}")
        return ConversationHandler.END

    df = calculate_metrics(df)
    df = calculate_indicators(df)
    volatility = calculate_volatility(df)
    if volatility is None:
        await query.edit_message_text(f"Failed to calculate volatility for {crypto.capitalize()}")
        return ConversationHandler.END

    # Store the message ID to delete it later
    message_id = context.user_data.get('message_id')
    logger.debug(f"Message ID to delete: {message_id}")

    if chart_type == 'price':
        logger.info(f"Creating price plot for {crypto}")
        create_plot(df, crypto)
        file_path = os.path.join(IMAGES_DIR, f'{crypto}.png')
        if os.path.exists(file_path):
            with open(file_path, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'Price chart for {crypto.capitalize()}')
                logger.debug(f"Sent photo for {crypto}")
        else:
            logger.error(f"File {file_path} does not exist")
            await query.edit_message_text(f"Failed to create plot for {crypto.capitalize()}")

    elif chart_type == 'indicators':
        logger.info(f"Creating indicators plot for {crypto}")
        create_indicators_plot(df, crypto)
        indicators_file_path = os.path.join(IMAGES_DIR, f'{crypto}_indicators.png')
        if os.path.exists(indicators_file_path):
            with open(indicators_file_path, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'Indicators chart for {crypto.capitalize()}')
                logger.debug(f"Sent indicators photo for {crypto}")
        else:
            logger.error(f"File {indicators_file_path} does not exist")
            await query.edit_message_text(f"Failed to create indicators plot for {crypto.capitalize()}")

    elif chart_type == 'volatility':
        logger.info(f"Creating volatility gauge for {crypto}")
        volatility_gauge = create_gauge(volatility, "Volatility", max_value=1)
        volatility_gauge_file = os.path.join(IMAGES_DIR, f'{crypto}_volatility.png')
        volatility_gauge.write_image(volatility_gauge_file)
        if os.path.exists(volatility_gauge_file):
            with open(volatility_gauge_file, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'Volatility gauge for {crypto.capitalize()}')
                logger.debug(f"Sent volatility gauge photo for {crypto}")
        else:
            logger.error(f"File {volatility_gauge_file} does not exist")
            await query.edit_message_text(f"Failed to create volatility gauge for {crypto.capitalize()}")

    elif chart_type == 'rsi':
        logger.info(f"Creating RSI gauge for {crypto}")
        rsi_value = df['RSI'].iloc[-1]
        rsi_gauge = create_gauge(rsi_value, "RSI", max_value=100)
        rsi_gauge_file = os.path.join(IMAGES_DIR, f'{crypto}_rsi.png')
        rsi_gauge.write_image(rsi_gauge_file)
        if os.path.exists(rsi_gauge_file):
            with open(rsi_gauge_file, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                             caption=f'RSI gauge for {crypto.capitalize()}')
                logger.debug(f"Sent RSI gauge photo for {crypto}")
        else:
            logger.error(f"File {rsi_gauge_file} does not exist")
            await query.edit_message_text(f"Failed to create RSI gauge for {crypto.capitalize()}")

    # Delete the previous message
    if message_id:
        try:
            logger.debug(f"Attempting to delete message with ID: {message_id}")
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
            logger.debug(f"Deleted message with ID: {message_id}")
        except Exception as e:
            logger.error(f"Failed to delete message with ID {message_id}: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')
