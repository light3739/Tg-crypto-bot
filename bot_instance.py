from telegram.ext import ApplicationBuilder
from config import TELEGRAM_BOT_TOKEN


class BotInstance:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        return cls._instance


bot = BotInstance.get_instance()
