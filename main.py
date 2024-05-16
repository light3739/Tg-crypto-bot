import logging
import requests
import plotly.graph_objects as go
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

# Define the images directory path
IMAGES_DIR = 'images/'
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Function to get cryptocurrency data from CoinCap
def get_crypto_data(crypto: str):
    url = f'https://api.coincap.io/v2/assets/{crypto}/history?interval=d1'
    response = requests.get(url)
    logger.info(f"API response status code: {response.status_code}")
    data = response.json()
    logger.info(f"API response data: {data}")
    prices = [{'timestamp': item['time'], 'price': item['priceUsd']} for item in data['data']]
    df = pd.DataFrame(prices)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['price'] = df['price'].astype(float)
    logger.info(f"DataFrame head: {df.head()}")
    return df

# Function to create a plot
def create_plot(df, crypto):
    fig = go.Figure(data=[go.Scatter(x=df['timestamp'], y=df['price'], mode='lines', name=crypto)])
    fig.update_layout(title=f'Price of {crypto} over the last 30 days', xaxis_title='Date', yaxis_title='Price (USD)')
    file_path = os.path.join(IMAGES_DIR, f'{crypto}.png')
    try:
        fig.write_image(file_path)
        logger.info(f"Plot created and saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving plot to {file_path}: {e}")

# Command handler for /chart
async def send_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        cryptos = ['bitcoin', 'ethereum','litecoin', 'bitcoin-cash']
        for crypto in cryptos:
            logger.info(f"Fetching data for {crypto}")
            df = get_crypto_data(crypto)
            logger.info(f"Creating plot for {crypto}")
            create_plot(df, crypto)
            file_path = os.path.join(IMAGES_DIR, f'{crypto}.png')
            if os.path.exists(file_path):
                logger.info(f"Sending plot for {crypto}")
                with open(file_path, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo,
                                                 caption=f'Price chart for {crypto.capitalize()}')
            else:
                logger.error(f"File {file_path} does not exist")
                await update.message.reply_text(f"Failed to create plot for {crypto.capitalize()}")
    except Exception as e:
        logger.error(f"Error in send_chart: {e}")
        await update.message.reply_text("An error occurred while processing your request.")

# Command handler for /hello
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

# Create application instance
app = ApplicationBuilder().token("SECRET").build()

# Register command handlers
app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("chart", send_chart))

# Start the bot
if __name__ == '__main__':
    logger.info("Starting bot")
    app.run_polling()
