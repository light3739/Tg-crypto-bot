import asyncio
import logging
import os
from datetime import datetime

from telegram import BotCommand
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot_handlers import hello, SELECT_CRYPTO, SELECT_THRESHOLD_TYPE, SET_THRESHOLD, select_crypto, \
    select_threshold_type, set_threshold, subscribe, select_crypto_option, select_chart, SELECT_CHART, cancel, \
    select_subscribe_crypto, SELECT_SUBSCRIBE_CRYPTO, SELECT_UNSUBSCRIBE_TYPE, select_unsubscribe_type, \
    show_subscriptions, news
from config import IMAGES_DIR, NEWS_API_KEY
from bot_instance import bot
from news_fetcher import get_last_fetched_news_time, fetch_latest_news, save_news_to_db
from notification import check_price_changes

if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def set_commands():
    await bot.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("crypto", "Выбрать криптовалюту"),
        BotCommand("hello", "Поздороваться"),
        BotCommand("cancel", "Отменить текущую операцию"),
        BotCommand("subscribe", "Подписаться на уведомления о криптовалюте"),
        BotCommand("subscriptions", "Показать все ваши подписки"),
        BotCommand("news", "Получить последние новости о блокчейне")
    ])


crypto_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('crypto', select_crypto_option)],
    states={
        SELECT_CRYPTO: [CallbackQueryHandler(select_crypto)],
        SELECT_CHART: [CallbackQueryHandler(select_chart)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False
)

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

bot.add_handler(CommandHandler("news", news))
bot.add_handler(CommandHandler("hello", hello))
bot.add_handler(CommandHandler("subscriptions", show_subscriptions))
bot.add_handler(crypto_conv_handler)
bot.add_handler(subscription_conv_handler)


async def periodic_check():
    while True:
        await check_price_changes()
        logger.info("Проверка цен завершена")

        last_fetched_time = get_last_fetched_news_time()
        if not last_fetched_time or (datetime.now() - last_fetched_time).total_seconds() > 86400:
            latest_news = fetch_latest_news(NEWS_API_KEY)
            if latest_news:
                save_news_to_db(latest_news)
                logger.info("Последние новости получены и сохранены")

        await asyncio.sleep(30)


async def main():
    await set_commands()
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()

    periodic_task = asyncio.create_task(periodic_check())

    try:
        await asyncio.Event().wait()
    finally:
        periodic_task.cancel()
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()


if __name__ == '__main__':
    logger.info("Запуск бота")
    asyncio.run(main())
