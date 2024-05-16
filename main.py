import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler
from bot_handlers import hello, send_chart
from config import TELEGRAM_BOT_TOKEN, IMAGES_DIR

# Ensure the images directory exists
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create application instance
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# Register command handlers
app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("chart", send_chart))

# Start the bot
if __name__ == '__main__':
    logger.info("Starting bot")
    app.run_polling()
