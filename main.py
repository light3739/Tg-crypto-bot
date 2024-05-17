import asyncio
import logging
import os

from telegram import BotCommand
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot_handlers import hello, SELECT_CRYPTO, SELECT_THRESHOLD_TYPE, SET_THRESHOLD, select_crypto, \
    select_threshold_type, set_threshold, subscribe, select_crypto_option, select_chart, SELECT_CHART, cancel, \
    select_subscribe_crypto, SELECT_SUBSCRIBE_CRYPTO, SELECT_UNSUBSCRIBE_TYPE, select_unsubscribe_type, \
    show_subscriptions
from config import IMAGES_DIR
from bot_instance import bot
from notification import check_price_changes

# Ensure the images directory exists
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


# Set bot commands
async def set_commands():
    await bot.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("crypto", "Select a cryptocurrency"),
        BotCommand("hello", "Say hello"),
        BotCommand("cancel", "Cancel the current operation"),
        BotCommand("subscribe", "Subscribe to cryptocurrency notifications"),
        BotCommand("subscriptions", "Show all your subscriptions")  # Add the new command
    ])


# Define the conversation handler for crypto charts
crypto_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('crypto', select_crypto_option)],
    states={
        SELECT_CRYPTO: [CallbackQueryHandler(select_crypto)],
        SELECT_CHART: [CallbackQueryHandler(select_chart)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False  # Ensure handlers are tracked for every message
)

# Define the conversation handler for subscriptions
# Define the conversation handler for subscriptions
subscription_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('subscribe', subscribe)],
    states={
        SELECT_SUBSCRIBE_CRYPTO: [CallbackQueryHandler(select_subscribe_crypto)],
        SELECT_THRESHOLD_TYPE: [CallbackQueryHandler(select_threshold_type)],
        SET_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_threshold)],
        SELECT_UNSUBSCRIBE_TYPE: [CallbackQueryHandler(select_unsubscribe_type)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

# Register command handlers
bot.add_handler(CommandHandler("hello", hello))
bot.add_handler(CommandHandler("subscriptions", show_subscriptions))
bot.add_handler(crypto_conv_handler)
bot.add_handler(subscription_conv_handler)  # Add the subscription conversation handler


async def periodic_check():
    while True:
        await check_price_changes()
        logger.info("Checked price")
        await asyncio.sleep(30)  # Wait for 5 minutes before the next check


async def main():
    await set_commands()
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()

    # Create the periodic check task and run it concurrently
    periodic_task = asyncio.create_task(periodic_check())

    try:
        # Keep the event loop running until you want to shutdown
        await asyncio.Event().wait()
    finally:
        # Stop the periodic check task
        periodic_task.cancel()
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()


# Start the bot
if __name__ == '__main__':
    logger.info("Starting bot")
    asyncio.run(main())
