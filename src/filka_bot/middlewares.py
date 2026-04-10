from collections.abc import Awaitable
from collections.abc import Callable
import logging
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from filka_bot.config import Settings
from filka_bot.formatting import with_emoji_prefix
from filka_bot.services.access_registry import AccessRegistry

logger = logging.getLogger(__name__)


def build_subscription_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    buttons = []
    if channel_url:
        buttons.append(
            [InlineKeyboardButton(text="Подписаться на канал", url=channel_url)]
        )
    buttons.append(
        [InlineKeyboardButton(text="Проверить подписку", callback_data="check_subscription")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


class AccessMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings, access_registry: AccessRegistry) -> None:
        self._settings = settings
        self._access_registry = access_registry

    def _is_allowed(self, message: Message) -> bool:
        if not message.from_user:
            return False

        user_id = message.from_user.id
        if self._access_registry.is_allowed(user_id):
            return True

        if user_id in self._settings.filka_allowed_user_ids:
            self._access_registry.allow_user(user_id, source="env")
            return True

        if not self._settings.filka_required_chat_id:
            return self._settings.filka_allow_empty_whitelist

        return False

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if self._is_allowed(event):
            return await handler(event, data)

        if await self._try_whitelist_after_subscription(event):
            return await handler(event, data)

        reply_markup = None
        if self._settings.filka_required_chat_id:
            reply_markup = build_subscription_keyboard(self._settings.filka_required_chat_url)

        await event.answer(
            with_emoji_prefix(
                "Доступ закрыт. Сначала подпишись на нужный канал, потом приходи умничать сюда."
            ),
            reply_markup=reply_markup,
        )
        return None

    async def _try_whitelist_after_subscription(self, message: Message) -> bool:
        if not message.from_user or not self._settings.filka_required_chat_id:
            return False

        user_id = message.from_user.id
        channel_id = self._settings.filka_required_chat_id

        try:
            member = await message.bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id,
            )
            logger.info(
                "Subscription check: user_id=%s channel_id=%s status=%s",
                user_id,
                channel_id,
                member.status,
            )
        except TelegramBadRequest:
            logger.exception(
                "Subscription check failed: user_id=%s channel_id=%s",
                user_id,
                channel_id,
            )
            return False

        if member.status in {"creator", "administrator", "member", "restricted"}:
            self._access_registry.allow_user(user_id, source="subscription")
            logger.info(
                "User added to whitelist after subscription check: user_id=%s channel_id=%s",
                user_id,
                channel_id,
            )
            return True

        logger.info(
            "Subscription not confirmed: user_id=%s channel_id=%s status=%s",
            user_id,
            channel_id,
            member.status,
        )
        return False
