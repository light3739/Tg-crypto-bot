import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from data_fetcher import get_crypto_data
from metrics_calculator import calculate_volatility, calculate_metrics
from indicators_calculator import calculate_indicators
from plot_creator import create_plot, create_indicators_plot, create_gauge
import os
from config import IMAGES_DIR

logger = logging.getLogger(__name__)

# Define states for the conversation
SELECT_CRYPTO, SELECT_CHART = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Welcome! Use the /crypto command to select a cryptocurrency.')

async def select_crypto_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Bitcoin", callback_data='bitcoin')],
        [InlineKeyboardButton("Ethereum", callback_data='ethereum')],
        [InlineKeyboardButton("Tether", callback_data='tether')],
        [InlineKeyboardButton("Solana", callback_data='solana')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text('Please choose a cryptocurrency:', reply_markup=reply_markup)
    context.user_data['message_id'] = message.message_id  # Store the message ID to delete it later
    logger.debug(f"Stored message ID for deletion: {message.message_id}")
    return SELECT_CRYPTO

async def select_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['crypto'] = query.data

    keyboard = [
        [InlineKeyboardButton("Price Chart", callback_data='price')],
        [InlineKeyboardButton("Indicators Chart", callback_data='indicators')],
        [InlineKeyboardButton("Volatility Gauge", callback_data='volatility')],
        [InlineKeyboardButton("RSI Gauge", callback_data='rsi')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await query.edit_message_text(text=f'Selected cryptocurrency: {query.data}\nPlease choose a chart type:',
                                            reply_markup=reply_markup)
    context.user_data['message_id'] = message.message_id  # Store the message ID to delete it later
    logger.debug(f"Updated message ID for deletion: {message.message_id}")
    return SELECT_CHART

async def select_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chart_type = query.data
    crypto = context.user_data['crypto']

    logger.info(f"Fetching data for {crypto}")
    df = get_crypto_data(crypto)
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
                                             caption=f'Price chart for {crypto.capitalize()}\nVolatility: {volatility:.2%}')
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
