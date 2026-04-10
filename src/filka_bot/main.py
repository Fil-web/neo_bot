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
from filka_bot.services.analytics import AnalyticsService
from filka_bot.services.antispam import AntiSpamService
from filka_bot.services.document_parser import DocumentParser
from filka_bot.services.gigachat_client import GigaChatService
from filka_bot.services.history import DialogHistory
from filka_bot.services.knowledge_base import KnowledgeBaseService
from filka_bot.services.moderation import ModerationService
from filka_bot.services.response_cache import ResponseCacheService
from filka_bot.services.user_profiles import UserProfileService


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
            BotCommand(command="mode", description="Сменить режим Фильки"),
            BotCommand(command="admin", description="Статистика для админа"),
            BotCommand(command="kbstats", description="Статистика базы знаний"),
            BotCommand(command="exportstats", description="Экспорт статистики"),
            BotCommand(command="adminmode", description="Включить или выключить админ-режим"),
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
        analytics = AnalyticsService(db_path=settings.filka_db_path)
        antispam = AntiSpamService(
            db_path=settings.filka_db_path,
            window_seconds=settings.filka_spam_window_seconds,
            max_requests=settings.filka_spam_max_requests,
        )
        document_parser = DocumentParser(max_chars=settings.filka_max_document_chars)
        knowledge_base = KnowledgeBaseService(db_path=settings.filka_db_path)
        moderation = ModerationService(db_path=settings.filka_db_path)
        response_cache = ResponseCacheService(
            db_path=settings.filka_db_path,
            ttl_seconds=settings.filka_cache_ttl_seconds,
        )
        user_profiles = UserProfileService(db_path=settings.filka_db_path)
        gigachat_service = GigaChatService(settings=settings)

        dp["history"] = history
        dp["access_registry"] = access_registry
        dp["analytics"] = analytics
        dp["antispam"] = antispam
        dp["document_parser"] = document_parser
        dp["knowledge_base"] = knowledge_base
        dp["moderation"] = moderation
        dp["gigachat_service"] = gigachat_service
        dp["response_cache"] = response_cache
        dp["settings"] = settings
        dp["user_profiles"] = user_profiles
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
