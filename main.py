import logging
import os

from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, CallbackQueryHandler
from bot_handlers import hello, start, SELECT_CRYPTO, SELECT_CHART, select_crypto, select_chart, cancel, select_crypto_option
from config import TELEGRAM_BOT_TOKEN, IMAGES_DIR

# Ensure the images directory exists
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Create application instance
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# Set bot commands
async def set_commands():
    await app.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("crypto", "Select a cryptocurrency"),
        BotCommand("hello", "Say hello"),
        BotCommand("cancel", "Cancel the current operation")
    ])

# Define the conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('crypto', select_crypto_option)],
    states={
        SELECT_CRYPTO: [CallbackQueryHandler(select_crypto)],
        SELECT_CHART: [CallbackQueryHandler(select_chart)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False  # Ensure handlers are tracked for every message
)

# Register command handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("hello", hello))
app.add_handler(conv_handler)

# Start the bot
if __name__ == '__main__':
    logger.info("Starting bot")
    app.run_polling()
    app.loop.run_until_complete(set_commands())
