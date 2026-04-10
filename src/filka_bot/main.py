import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand

from filka_bot.config import get_settings
from filka_bot.handlers import router
from filka_bot.middlewares import AccessMiddleware
from filka_bot.services.access_registry import AccessRegistry
from filka_bot.services.gigachat_client import GigaChatService
from filka_bot.services.history import DialogHistory


def configure_logging(log_path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)


async def configure_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить Фильку"),
            BotCommand(command="help", description="Подсказка по командам"),
            BotCommand(command="clear", description="Очистить память диалога"),
            BotCommand(command="status", description="Показать статус бота"),
        ]
    )


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.filka_log_path)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(),
    )
    try:
        await configure_bot_commands(bot)
        dp = Dispatcher()

        history = DialogHistory(
            db_path=settings.filka_db_path,
            max_messages=settings.filka_max_history,
        )
        access_registry = AccessRegistry(db_path=settings.filka_db_path)
        gigachat_service = GigaChatService(settings=settings)

        dp["history"] = history
        dp["access_registry"] = access_registry
        dp["gigachat_service"] = gigachat_service
        dp["settings"] = settings
        dp.message.middleware(AccessMiddleware(settings, access_registry))
        dp.include_router(router)

        await dp.start_polling(bot)
    except TelegramUnauthorizedError as error:
        logging.getLogger(__name__).error(
            "Telegram bot token is invalid or revoked. Update TELEGRAM_BOT_TOKEN in .env. Details: %s",
            error,
        )
        return
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(run())
