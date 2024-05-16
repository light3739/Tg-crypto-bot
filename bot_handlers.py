import logging
from telegram import Update
from telegram.ext import ContextTypes
from data_fetcher import get_crypto_data
from metrics_calculator import calculate_volatility, calculate_metrics
from indicators_calculator import calculate_indicators
from plot_creator import create_plot, create_indicators_plot, create_gauge
import os
from config import IMAGES_DIR

logger = logging.getLogger(__name__)


async def send_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        cryptos = ['bitcoin', 'ethereum', 'tether', 'solana']
        for crypto in cryptos:
            logger.info(f"Fetching data for {crypto}")
            df = get_crypto_data(crypto)
            if df.empty:
                await update.message.reply_text(f"Failed to fetch data for {crypto.capitalize()}")
                continue
            df = calculate_metrics(df)
            df = calculate_indicators(df)
            volatility = calculate_volatility(df)
            if volatility is None:
                await update.message.reply_text(f"Failed to calculate volatility for {crypto.capitalize()}")
                continue
            logger.info(f"Creating plot for {crypto}")
            create_plot(df, crypto)
            create_indicators_plot(df, crypto)
            file_path = os.path.join(IMAGES_DIR, f'{crypto}.png')
            indicators_file_path = os.path.join(IMAGES_DIR, f'{crypto}_indicators.png')
            if os.path.exists(file_path):
                logger.info(f"Sending plot for {crypto}")
                with open(file_path, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                                 caption=f'Price chart for {crypto.capitalize()}\nVolatility: {volatility:.2%}')
            else:
                logger.error(f"File {file_path} does not exist")
                await update.message.reply_text(f"Failed to create plot for {crypto.capitalize()}")

            if os.path.exists(indicators_file_path):
                logger.info(f"Sending indicators plot for {crypto}")
                with open(indicators_file_path, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                                 caption=f'Indicators chart for {crypto.capitalize()}')

            # Create and send volatility gauge
            volatility_gauge = create_gauge(volatility, "Volatility", max_value=1)
            volatility_gauge_file = os.path.join(IMAGES_DIR, f'{crypto}_volatility.png')
            volatility_gauge.write_image(volatility_gauge_file)
            if os.path.exists(volatility_gauge_file):
                with open(volatility_gauge_file, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                                 caption=f'Volatility gauge for {crypto.capitalize()}')

            # Create and send RSI gauge
            rsi_value = df['RSI'].iloc[-1]
            rsi_gauge = create_gauge(rsi_value, "RSI", max_value=100)
            rsi_gauge_file = os.path.join(IMAGES_DIR, f'{crypto}_rsi.png')
            rsi_gauge.write_image(rsi_gauge_file)
            if os.path.exists(rsi_gauge_file):
                with open(rsi_gauge_file, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                                 caption=f'RSI gauge for {crypto.capitalize()}')
    except Exception as e:
        logger.error(f"Error in send_chart: {e}")
        await update.message.reply_text("An error occurred while processing your request")


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')
