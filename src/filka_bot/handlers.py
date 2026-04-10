import logging
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandObject
from aiogram.utils.chat_action import ChatActionSender
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.types import CallbackQuery
from aiogram.types import Message

from filka_bot.config import Settings
from filka_bot.formatting import with_emoji_prefix
from filka_bot.keyboards import build_main_keyboard
from filka_bot.keyboards import build_mode_keyboard
from filka_bot.keyboards import build_start_inline_keyboard
from filka_bot.middlewares import build_subscription_keyboard
from filka_bot.services.access_registry import AccessRegistry
from filka_bot.services.analytics import AnalyticsService
from filka_bot.services.antispam import AntiSpamService
from filka_bot.services.document_parser import DocumentParser
from filka_bot.services.document_parser import DocumentParsingError
from filka_bot.services.gigachat_client import GigaChatService
from filka_bot.services.history import DialogHistory
from filka_bot.services.knowledge_base import KnowledgeBaseService
from filka_bot.services.moderation import ModerationService
from filka_bot.services.response_cache import ResponseCacheService
from filka_bot.services.user_profiles import UserProfileService

router = Router()
logger = logging.getLogger(__name__)

MODE_LABELS = {
    "default": "обычный",
    "hard": "жесткий",
    "business": "деловой",
    "sales": "продажи",
    "support": "поддержка",
}


async def download_to_tempfile(
    message: Message,
    file_id: str,
    suffix: str,
) -> Path:
    buffer = BytesIO()
    await message.bot.download(file_id, destination=buffer)
    buffer.seek(0)
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(buffer.read())
        temp_path = Path(temp_file.name)
    buffer.close()
    return temp_path


def is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.filka_allowed_user_ids


def format_knowledge_context(results: list[dict[str, str]]) -> str:
    if not results:
        return ""
    parts = []
    for index, item in enumerate(results, start=1):
        parts.append(f"[Источник {index}: {item['title']}]\n{item['content']}")
    return "\n\n".join(parts)


@router.message(Command("start"))
async def cmd_start(message: Message, user_profiles: UserProfileService) -> None:
    user_profiles.ensure_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )
    await message.answer(
        with_emoji_prefix(
            "Я Филька, бот от #Фил. Спрашивай, что нужно. 😏\n\n"
            "Что умею:\n"
            "- отвечаю на текстовые вопросы;\n"
            "- смотрю фото и помогаю разобрать, что на них;\n"
            "- разбираю документы: PDF, DOCX, TXT, CSV, XLSX;\n"
            "- пробую понять голосовые;\n"
            "- могу работать в разных режимах ответа;\n"
            "- помню до 30 сообщений в день.\n\n"
            "Если вдруг растеряешься:\n"
            "- жми кнопки ниже;\n"
            "- или просто пиши сообщением."
        ),
        reply_markup=build_start_inline_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        with_emoji_prefix(
            "Все просто:\n"
            "- отправь текстовый вопрос;\n"
            "- можно прислать фото с подписью или без нее;\n"
            "- можно прислать документ и попросить разобрать;\n"
            "- можно прислать голосовое;\n"
            "- /mode меняет режим ответа;\n"
            "- /clear очищает память за сегодня;\n"
            "- /status показывает краткий статус."
        ),
        reply_markup=build_main_keyboard(),
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message, history: DialogHistory) -> None:
    history.clear(message.from_user.id)
    await message.answer(
        with_emoji_prefix("Ладно, все стер. Начинай заново, раз уж так захотелось."),
        reply_markup=build_main_keyboard(),
    )


@router.message(Command("status"))
async def cmd_status(
    message: Message,
    history: DialogHistory,
    settings: Settings,
    user_profiles: UserProfileService,
) -> None:
    user_id = message.from_user.id
    stored_messages = history.count(user_id)
    mode = user_profiles.get_mode(user_id)
    await message.answer(
        with_emoji_prefix(
            "Коротко по статусу:\n"
            f"- твой user ID: `{user_id}`\n"
            f"- сообщений в памяти сегодня: {stored_messages}\n"
            f"- дневной лимит истории: {settings.filka_max_history}\n"
            f"- режим: {MODE_LABELS.get(mode, mode)}\n"
            f"- канал проверки: {settings.filka_required_chat_id or 'не задан'}"
        ),
        reply_markup=build_main_keyboard(),
    )


@router.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    await message.answer(
        with_emoji_prefix("Выбирай режим, раз уж настроение у тебя меняется чаще погоды."),
        reply_markup=build_mode_keyboard(),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, settings: Settings, analytics: AnalyticsService) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return

    stats = analytics.get_admin_stats()
    await message.answer(
        with_emoji_prefix(
            "Админ-статистика за сегодня:\n"
            f"- событий: {stats.get('total_events_today', 0)}\n"
            f"- уникальных пользователей: {stats.get('total_users', 0)}\n"
            f"- активных сегодня: {stats.get('active_today', 0)}\n"
            f"- ошибок: {stats.get('errors_today', 0)}\n"
            f"- текст: {stats.get('type_text', 0)}\n"
            f"- фото: {stats.get('type_photo', 0)}\n"
            f"- голосовые: {stats.get('type_voice', 0)}\n"
            f"- документы: {stats.get('type_document', 0)}\n"
            f"- onboarding: {stats.get('type_onboarding', 0)}"
        ),
        reply_markup=build_main_keyboard(),
    )


@router.message(Command("adminmode"))
async def cmd_adminmode(
    message: Message,
    settings: Settings,
    user_profiles: UserProfileService,
    command: CommandObject,
) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return

    enabled = (command.args or "").strip().lower() != "off"
    user_profiles.set_admin_mode(message.from_user.id, enabled)
    state = "включен" if enabled else "выключен"
    await message.answer(with_emoji_prefix(f"Админ-режим {state}. Ну вот, теперь ты при полном параде."))


@router.message(Command("exportstats"))
async def cmd_exportstats(message: Message, settings: Settings, analytics: AnalyticsService) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return

    payload = analytics.export_csv().encode("utf-8")
    file = BufferedInputFile(payload, filename="filka_stats.csv")
    await message.answer_document(file, caption=with_emoji_prefix("Вот экспорт статистики. Держи свой CSV."))


@router.message(Command("kbstats"))
async def cmd_kbstats(message: Message, settings: Settings, knowledge_base: KnowledgeBaseService) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return

    stats = knowledge_base.stats()
    await message.answer(
        with_emoji_prefix(
            "База знаний:\n"
            f"- документов: {stats['documents']}\n"
            f"- чанков: {stats['chunks']}\n"
            "Чтобы добавить документ в базу, пришли файл с подписью `/kb`."
        ),
        reply_markup=build_main_keyboard(),
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(
    callback: CallbackQuery,
    settings: Settings,
    access_registry: AccessRegistry,
    analytics: AnalyticsService,
) -> None:
    if not callback.from_user:
        await callback.answer("Не вышло понять, кто ты такой.", show_alert=True)
        return

    if not settings.filka_required_chat_id:
        text = with_emoji_prefix("Проверять пока нечего: канал для подписки не настроен.")
        if callback.message:
            await callback.message.edit_text(text)
        await callback.answer("Канал не настроен", show_alert=True)
        return

    try:
        member = await callback.bot.get_chat_member(
            chat_id=settings.filka_required_chat_id,
            user_id=callback.from_user.id,
        )
        is_subscribed = member.status in {"creator", "administrator", "member", "restricted"}
    except TelegramBadRequest:
        is_subscribed = False

    if is_subscribed:
        access_registry.allow_user(callback.from_user.id, source="subscription")
        analytics.log_event("onboarding", user_id=callback.from_user.id, success=True, details="subscription_ok")
        text = with_emoji_prefix(
            "Подписка подтверждена. Ну надо же, справился. Теперь доступ открыт.\n\n"
            "Я Филька, бот от #Фил. Можешь сразу писать вопрос обычным сообщением.\n"
            "Команды на случай внезапной растерянности:\n"
            "- /start\n"
            "- /help\n"
            "- /clear\n"
            "- /status\n"
            "- /mode"
        )
        if callback.message:
            await callback.message.edit_text(text)
            await callback.message.answer(
                with_emoji_prefix("Клавиатуру тоже вернул. Ну вдруг потеряешься."),
                reply_markup=build_main_keyboard(),
            )
        await callback.answer("Доступ открыт")
        return

    text = with_emoji_prefix(
        "Подписку я не вижу. Сначала подпишись на канал, потом уже жми проверку снова."
    )
    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=build_subscription_keyboard(settings.filka_required_chat_url),
        )
    await callback.answer("Подписка пока не найдена", show_alert=True)


@router.callback_query(F.data == "menu_mode")
async def menu_mode_callback(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(
            with_emoji_prefix("Выбирай режим. Да, у меня тоже есть настройки характера."),
            reply_markup=build_mode_keyboard(),
        )
    await callback.answer("Открыл режимы")


@router.callback_query(F.data.startswith("mode_"))
async def mode_select_callback(
    callback: CallbackQuery,
    user_profiles: UserProfileService,
    analytics: AnalyticsService,
) -> None:
    if not callback.from_user:
        await callback.answer("Не понял, кто нажал", show_alert=True)
        return

    mode = callback.data.replace("mode_", "", 1)
    if mode not in MODE_LABELS:
        await callback.answer("Неизвестный режим", show_alert=True)
        return

    user_profiles.set_mode(callback.from_user.id, mode)
    analytics.log_event("onboarding", user_id=callback.from_user.id, success=True, details=f"mode:{mode}")
    if callback.message:
        await callback.message.answer(
            with_emoji_prefix(f"Режим переключил на `{MODE_LABELS[mode]}`. Ну все, держись."),
            reply_markup=build_main_keyboard(),
        )
    await callback.answer("Режим обновлен")


@router.message(F.text.casefold() == "помощь")
async def help_button(message: Message) -> None:
    await cmd_help(message)


@router.message(F.text.casefold() == "статус")
async def status_button(
    message: Message,
    history: DialogHistory,
    settings: Settings,
    user_profiles: UserProfileService,
) -> None:
    await cmd_status(message, history, settings, user_profiles)


@router.message(F.text.casefold() == "очистить память")
async def clear_button(message: Message, history: DialogHistory) -> None:
    await cmd_clear(message, history)


@router.message(Command("ban"))
async def cmd_ban(
    message: Message,
    settings: Settings,
    moderation: ModerationService,
    analytics: AnalyticsService,
    command: CommandObject,
) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return
    args = (command.args or "").split(maxsplit=1)
    if not args:
        await message.answer(with_emoji_prefix("Формат такой: `/ban user_id причина`"))
        return
    target_user_id = int(args[0])
    reason = args[1] if len(args) > 1 else ""
    moderation.ban(target_user_id, reason=reason)
    analytics.log_event("moderation", user_id=target_user_id, success=True, details="ban")
    await message.answer(with_emoji_prefix(f"Пользователь `{target_user_id}` забанен. Шалить меньше надо было."))


@router.message(Command("mute"))
async def cmd_mute(
    message: Message,
    settings: Settings,
    moderation: ModerationService,
    analytics: AnalyticsService,
    command: CommandObject,
) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return
    args = (command.args or "").split(maxsplit=2)
    if len(args) < 2:
        await message.answer(with_emoji_prefix("Формат такой: `/mute user_id минуты причина`"))
        return
    target_user_id = int(args[0])
    minutes = int(args[1])
    reason = args[2] if len(args) > 2 else ""
    moderation.mute(target_user_id, minutes=minutes, reason=reason)
    analytics.log_event("moderation", user_id=target_user_id, success=True, details=f"mute:{minutes}")
    await message.answer(with_emoji_prefix(f"Пользователь `{target_user_id}` замьючен на {minutes} мин."))


@router.message(Command("unban"))
async def cmd_unban(
    message: Message,
    settings: Settings,
    moderation: ModerationService,
    analytics: AnalyticsService,
    command: CommandObject,
) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return
    target = (command.args or "").strip()
    if not target:
        await message.answer(with_emoji_prefix("Формат такой: `/unban user_id`"))
        return
    target_user_id = int(target)
    moderation.unban(target_user_id)
    analytics.log_event("moderation", user_id=target_user_id, success=True, details="unban")
    await message.answer(with_emoji_prefix(f"Пользователь `{target_user_id}` снова на свободе."))


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message,
    settings: Settings,
    analytics: AnalyticsService,
    access_registry: AccessRegistry,
    command: CommandObject,
) -> None:
    if not is_admin(message.from_user.id, settings):
        await message.answer(with_emoji_prefix("Эта команда не для всех. И это нормально."))
        return
    text = (command.args or "").strip()
    if not text:
        await message.answer(with_emoji_prefix("Формат такой: `/broadcast текст_рассылки`"))
        return

    sent = 0
    failed = 0
    for user_id in access_registry.list_allowed_users():
        try:
            await message.bot.send_message(user_id, with_emoji_prefix(text))
            sent += 1
        except Exception:
            failed += 1
    analytics.log_event("broadcast", user_id=message.from_user.id, success=True, details=f"sent:{sent};failed:{failed}")
    await message.answer(with_emoji_prefix(f"Рассылка ушла. Отправлено: {sent}. Ошибок: {failed}."))


@router.callback_query(F.data == "menu_help")
async def menu_help_callback(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(
            with_emoji_prefix(
                "Все просто:\n"
                "- отправь текстовый вопрос;\n"
                "- можно прислать фото с подписью или без нее;\n"
                "- можно прислать документ и попросить разобрать;\n"
                "- можно прислать голосовое;\n"
                "- /mode меняет режим ответа;\n"
                "- /clear очищает память за сегодня;\n"
                "- /status показывает краткий статус."
            ),
            reply_markup=build_main_keyboard(),
        )
    await callback.answer("Открыл помощь")


@router.callback_query(F.data == "menu_status")
async def menu_status_callback(
    callback: CallbackQuery,
    history: DialogHistory,
    settings: Settings,
    user_profiles: UserProfileService,
) -> None:
    if not callback.from_user:
        await callback.answer("Не понял, кто нажал", show_alert=True)
        return

    user_id = callback.from_user.id
    stored_messages = history.count(user_id)
    mode = user_profiles.get_mode(user_id)
    if callback.message:
        await callback.message.answer(
            with_emoji_prefix(
                "Коротко по статусу:\n"
                f"- твой user ID: `{user_id}`\n"
                f"- сообщений в памяти сегодня: {stored_messages}\n"
                f"- дневной лимит истории: {settings.filka_max_history}\n"
                f"- режим: {MODE_LABELS.get(mode, mode)}\n"
                f"- канал проверки: {settings.filka_required_chat_id or 'не задан'}"
            ),
            reply_markup=build_main_keyboard(),
        )
    await callback.answer("Показал статус")


@router.callback_query(F.data == "menu_clear")
async def menu_clear_callback(
    callback: CallbackQuery,
    history: DialogHistory,
) -> None:
    if not callback.from_user:
        await callback.answer("Не понял, кто нажал", show_alert=True)
        return

    history.clear(callback.from_user.id)
    if callback.message:
        await callback.message.answer(
            with_emoji_prefix("Ладно, все стер. Начинай заново, раз уж так захотелось."),
            reply_markup=build_main_keyboard(),
        )
    await callback.answer("Память очищена")


@router.message(F.text)
async def handle_text(
    message: Message,
    gigachat_service: GigaChatService,
    history: DialogHistory,
    analytics: AnalyticsService,
    antispam: AntiSpamService,
    knowledge_base: KnowledgeBaseService,
    response_cache: ResponseCacheService,
    user_profiles: UserProfileService,
    moderation: ModerationService,
) -> None:
    user_id = message.from_user.id
    user_profiles.ensure_user(
        user_id=user_id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )
    user_text = message.text.strip()

    if not user_text:
        await message.answer(with_emoji_prefix("Пустое сообщение. Сильно информативно, конечно."))
        return

    moderation_status, moderation_reason = moderation.check_status(user_id)
    if moderation_status == "banned":
        await message.answer(with_emoji_prefix("Доступ закрыт. Тебя заблокировали."))
        return
    if moderation_status == "muted":
        suffix = f" Причина: {moderation_reason}." if moderation_reason else ""
        await message.answer(with_emoji_prefix(f"Ты временно на паузе. Подожди немного.{suffix}"))
        return

    allowed, _ = antispam.is_allowed(user_id, request_type="text")
    if not allowed:
        analytics.log_event("text", user_id=user_id, success=False, details="antispam_block")
        await message.answer(
            with_emoji_prefix("Не так быстро. Сделай короткую паузу и потом спрашивай дальше.")
        )
        return

    dialog_history = history.get(user_id)
    knowledge_results = knowledge_base.search(user_text)
    knowledge_context = format_knowledge_context(knowledge_results)
    mode = user_profiles.get_mode(user_id)
    cache_key = response_cache.build_key(
        mode=mode,
        user_text=user_text,
        knowledge_context=knowledge_context,
    )
    cached_response = response_cache.get(cache_key)
    if cached_response:
        history.add(user_id, "user", user_text)
        history.add(user_id, "assistant", cached_response)
        analytics.log_event("text", user_id=user_id, success=True, details="cache_hit")
        await message.answer(with_emoji_prefix(cached_response))
        return

    try:
        async with ChatActionSender.typing(
            bot=message.bot,
            chat_id=message.chat.id,
        ):
            answer = await gigachat_service.ask(
                dialog_history,
                user_text,
                mode=mode,
                knowledge_context=knowledge_context,
            )
    except Exception:
        logger.exception("Failed to get model response")
        analytics.log_event("text", user_id=user_id, success=False)
        await message.answer(
            with_emoji_prefix(
                "Что-то пошло не так на моей стороне. Мир не рухнул, попробуй еще раз чуть позже."
            )
        )
        return

    history.add(user_id, "user", user_text)
    history.add(user_id, "assistant", answer)
    response_cache.set(cache_key, answer)
    analytics.log_event("text", user_id=user_id, success=True)
    await message.answer(with_emoji_prefix(answer))


@router.message(F.photo)
async def handle_photo(
    message: Message,
    gigachat_service: GigaChatService,
    history: DialogHistory,
    analytics: AnalyticsService,
    user_profiles: UserProfileService,
    moderation: ModerationService,
) -> None:
    user_id = message.from_user.id
    user_profiles.ensure_user(
        user_id=user_id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )
    prompt = (message.caption or "").strip() or (
        "Опиши, что на фото, и помоги пользователю разобраться по изображению."
    )
    moderation_status, moderation_reason = moderation.check_status(user_id)
    if moderation_status == "banned":
        await message.answer(with_emoji_prefix("Доступ закрыт. Тебя заблокировали."))
        return
    if moderation_status == "muted":
        suffix = f" Причина: {moderation_reason}." if moderation_reason else ""
        await message.answer(with_emoji_prefix(f"Ты временно на паузе. Подожди немного.{suffix}"))
        return
    photo = message.photo[-1]

    try:
        suffix = ".jpg"
        temp_path = await download_to_tempfile(message, photo.file_id, suffix)

        dialog_history = history.get(user_id)
        mode = user_profiles.get_mode(user_id)

        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            attachment_id = await gigachat_service.upload_general_file(temp_path)
            answer = await gigachat_service.ask(
                dialog_history,
                prompt,
                attachments=[attachment_id],
                mode=mode,
            )
    except Exception:
        logger.exception("Failed to handle photo message")
        analytics.log_event("photo", user_id=user_id, success=False)
        await message.answer(
            with_emoji_prefix(
                "С фото возникла заминка. Да, даже картинка решила усложнить нам жизнь. Попробуй еще раз."
            )
        )
        return
    finally:
        if "temp_path" in locals():
            temp_path.unlink(missing_ok=True)

    history.add(user_id, "user", f"[photo] {prompt}")
    history.add(user_id, "assistant", answer)
    analytics.log_event("photo", user_id=user_id, success=True)
    await message.answer(with_emoji_prefix(answer))


@router.message(F.voice | F.audio)
async def handle_voice(
    message: Message,
    gigachat_service: GigaChatService,
    history: DialogHistory,
    analytics: AnalyticsService,
    user_profiles: UserProfileService,
    moderation: ModerationService,
) -> None:
    user_id = message.from_user.id
    user_profiles.ensure_user(
        user_id=user_id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )
    media = message.voice or message.audio
    moderation_status, moderation_reason = moderation.check_status(user_id)
    if moderation_status == "banned":
        await message.answer(with_emoji_prefix("Доступ закрыт. Тебя заблокировали."))
        return
    if moderation_status == "muted":
        suffix = f" Причина: {moderation_reason}." if moderation_reason else ""
        await message.answer(with_emoji_prefix(f"Ты временно на паузе. Подожди немного.{suffix}"))
        return
    if media is None:
        await message.answer(with_emoji_prefix("Тут что-то странное с голосовым. Попробуй еще раз."))
        return

    file_name = getattr(media, "file_name", None) or "voice.ogg"
    suffix = Path(file_name).suffix or ".ogg"
    prompt = (
        "Расшифруй голосовое сообщение пользователя. "
        "Сначала кратко передай смысл сказанного, потом ответь по делу."
    )

    try:
        temp_path = await download_to_tempfile(message, media.file_id, suffix)
        dialog_history = history.get(user_id)
        mode = user_profiles.get_mode(user_id)
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            attachment_id = await gigachat_service.upload_general_file(temp_path)
            answer = await gigachat_service.ask(
                dialog_history,
                prompt,
                attachments=[attachment_id],
                mode=mode,
            )
    except Exception:
        logger.exception("Failed to handle voice message")
        analytics.log_event("voice", user_id=user_id, success=False)
        await message.answer(
            with_emoji_prefix(
                "С голосовым вышла заминка. Если что, пришли текстом или попробуй еще раз."
            )
        )
        return
    finally:
        if "temp_path" in locals():
            temp_path.unlink(missing_ok=True)

    history.add(user_id, "user", "[voice]")
    history.add(user_id, "assistant", answer)
    analytics.log_event("voice", user_id=user_id, success=True)
    await message.answer(with_emoji_prefix(answer))


@router.message(F.document)
async def handle_document(
    message: Message,
    gigachat_service: GigaChatService,
    history: DialogHistory,
    document_parser: DocumentParser,
    settings: Settings,
    analytics: AnalyticsService,
    knowledge_base: KnowledgeBaseService,
    user_profiles: UserProfileService,
    moderation: ModerationService,
) -> None:
    user_id = message.from_user.id
    user_profiles.ensure_user(
        user_id=user_id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )
    document = message.document
    moderation_status, moderation_reason = moderation.check_status(user_id)
    if moderation_status == "banned":
        await message.answer(with_emoji_prefix("Доступ закрыт. Тебя заблокировали."))
        return
    if moderation_status == "muted":
        suffix = f" Причина: {moderation_reason}." if moderation_reason else ""
        await message.answer(with_emoji_prefix(f"Ты временно на паузе. Подожди немного.{suffix}"))
        return
    file_name = document.file_name or "document"
    suffix = Path(file_name).suffix or ".bin"
    prompt = (message.caption or "").strip()

    try:
        temp_path = await download_to_tempfile(message, document.file_id, suffix)
        extracted_text = document_parser.parse(
            file_path=temp_path,
            file_name=document.file_name,
            mime_type=document.mime_type,
        )
    except DocumentParsingError:
        await message.answer(
            with_emoji_prefix(
                "Этот файл я пока нормально не разбираю. Пришли PDF, DOCX, TXT, CSV или XLSX."
            )
        )
        return
    except Exception:
        logger.exception("Failed to parse document")
        await message.answer(
            with_emoji_prefix("С документом что-то пошло не так. Попробуй еще раз чуть позже.")
        )
        return
    finally:
        if "temp_path" in locals():
            temp_path.unlink(missing_ok=True)

    if is_admin(user_id, settings) and prompt.startswith("/kb"):
        document_id = knowledge_base.add_document(
            title=file_name,
            content=extracted_text,
            source_type="telegram_document",
            source_ref=file_name,
            added_by=user_id,
        )
        analytics.log_event("document", user_id=user_id, success=True, details="kb_add")
        await message.answer(
            with_emoji_prefix(f"Документ добавил в базу знаний. ID: {document_id}. Ну хоть какая-то польза."))
        return

    dialog_history = history.get(user_id)
    question = prompt or "Разбери документ, кратко перескажи суть и выдели главное."
    mode = user_profiles.get_mode(user_id)
    model_prompt = (
        f"{question}\n\n"
        f"Название файла: {file_name}\n"
        "Содержимое документа:\n"
        f"{extracted_text}"
    )

    try:
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            answer = await gigachat_service.ask(dialog_history, model_prompt, mode=mode)
    except Exception:
        logger.exception("Failed to answer on document")
        analytics.log_event("document", user_id=user_id, success=False)
        await message.answer(
            with_emoji_prefix("Документ я прочитал, а вот с ответом вышла заминка. Попробуй еще раз.")
        )
        return

    history.add(user_id, "user", f"[document] {file_name} {question}".strip())
    history.add(user_id, "assistant", answer)
    analytics.log_event("document", user_id=user_id, success=True)
    await message.answer(with_emoji_prefix(answer))


@router.message()
async def handle_unsupported(message: Message) -> None:
    await message.answer(
        with_emoji_prefix("Я пока работаю с текстом. Стикеры потом, если доживем до этого.")
    )
