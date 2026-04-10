import logging
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.chat_action import ChatActionSender
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import Message

from filka_bot.config import Settings
from filka_bot.formatting import with_emoji_prefix
from filka_bot.keyboards import build_main_keyboard
from filka_bot.keyboards import build_start_inline_keyboard
from filka_bot.middlewares import build_subscription_keyboard
from filka_bot.services.access_registry import AccessRegistry
from filka_bot.services.gigachat_client import GigaChatService
from filka_bot.services.history import DialogHistory

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        with_emoji_prefix(
            "Я Филька, бот от #Фил. Спрашивай, что нужно. 😏\n\n"
            "Что умею:\n"
            "- отвечаю на текстовые вопросы;\n"
            "- смотрю фото и помогаю разобрать, что на них;\n"
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
    access_registry: AccessRegistry,
) -> None:
    user_id = message.from_user.id
    stored_messages = history.count(user_id)
    await message.answer(
        with_emoji_prefix(
            "Коротко по статусу:\n"
            f"- твой user ID: `{user_id}`\n"
            f"- сообщений в памяти сегодня: {stored_messages}\n"
            f"- дневной лимит истории: {settings.filka_max_history}\n"
            f"- доступ к боту активен: да\n"
            f"- канал проверки: {settings.filka_required_chat_id or 'не задан'}"
        ),
        reply_markup=build_main_keyboard(),
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(
    callback: CallbackQuery,
    settings: Settings,
    access_registry: AccessRegistry,
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
        text = with_emoji_prefix(
            "Подписка подтверждена. Ну надо же, справился. Теперь доступ открыт.\n\n"
            "Я Филька, бот от #Фил. Можешь сразу писать вопрос обычным сообщением.\n"
            "Команды на случай внезапной растерянности:\n"
            "- /start\n"
            "- /help\n"
            "- /clear\n"
            "- /status"
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


@router.message(F.text.casefold() == "помощь")
async def help_button(message: Message) -> None:
    await cmd_help(message)


@router.message(F.text.casefold() == "статус")
async def status_button(
    message: Message,
    history: DialogHistory,
    settings: Settings,
    access_registry: AccessRegistry,
) -> None:
    await cmd_status(message, history, settings, access_registry)


@router.message(F.text.casefold() == "очистить память")
async def clear_button(message: Message, history: DialogHistory) -> None:
    await cmd_clear(message, history)


@router.callback_query(F.data == "menu_help")
async def menu_help_callback(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(
            with_emoji_prefix(
                "Все просто:\n"
                "- отправь текстовый вопрос;\n"
                "- можно прислать фото с подписью или без нее;\n"
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
    access_registry: AccessRegistry,
) -> None:
    if not callback.from_user:
        await callback.answer("Не понял, кто нажал", show_alert=True)
        return

    user_id = callback.from_user.id
    stored_messages = history.count(user_id)
    if callback.message:
        await callback.message.answer(
            with_emoji_prefix(
                "Коротко по статусу:\n"
                f"- твой user ID: `{user_id}`\n"
                f"- сообщений в памяти сегодня: {stored_messages}\n"
                f"- дневной лимит истории: {settings.filka_max_history}\n"
                f"- доступ к боту активен: да\n"
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
) -> None:
    user_id = message.from_user.id
    user_text = message.text.strip()

    if not user_text:
        await message.answer(with_emoji_prefix("Пустое сообщение. Сильно информативно, конечно."))
        return

    dialog_history = history.get(user_id)

    try:
        async with ChatActionSender.typing(
            bot=message.bot,
            chat_id=message.chat.id,
        ):
            answer = await gigachat_service.ask(dialog_history, user_text)
    except Exception:
        logger.exception("Failed to get model response")
        await message.answer(
            with_emoji_prefix(
                "Что-то пошло не так на моей стороне. Мир не рухнул, попробуй еще раз чуть позже."
            )
        )
        return

    history.add(user_id, "user", user_text)
    history.add(user_id, "assistant", answer)
    await message.answer(with_emoji_prefix(answer))


@router.message(F.photo)
async def handle_photo(
    message: Message,
    gigachat_service: GigaChatService,
    history: DialogHistory,
) -> None:
    user_id = message.from_user.id
    prompt = (message.caption or "").strip() or (
        "Опиши, что на фото, и помоги пользователю разобраться по изображению."
    )
    photo = message.photo[-1]
    buffer = BytesIO()

    try:
        await message.bot.download(photo.file_id, destination=buffer)
        buffer.seek(0)
        suffix = Path(photo.file_id).suffix or ".jpg"
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(buffer.read())
            temp_path = Path(temp_file.name)

        dialog_history = history.get(user_id)

        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            attachment_id = await gigachat_service.upload_general_file(temp_path)
            answer = await gigachat_service.ask(
                dialog_history,
                prompt,
                attachments=[attachment_id],
            )
    except Exception:
        logger.exception("Failed to handle photo message")
        await message.answer(
            with_emoji_prefix(
                "С фото возникла заминка. Да, даже картинка решила усложнить нам жизнь. Попробуй еще раз."
            )
        )
        return
    finally:
        buffer.close()
        if "temp_path" in locals():
            temp_path.unlink(missing_ok=True)

    history.add(user_id, "user", f"[photo] {prompt}")
    history.add(user_id, "assistant", answer)
    await message.answer(with_emoji_prefix(answer))


@router.message(F.voice | F.audio)
async def handle_voice(message: Message) -> None:
    await message.answer(
        with_emoji_prefix(
            "Голосовые я пока не расшифровываю автоматически. Да, трагедия века. "
            "Пришли текстом или кинь краткую подпись, что именно нужно разобрать."
        )
    )


@router.message()
async def handle_unsupported(message: Message) -> None:
    await message.answer(
        with_emoji_prefix("Я пока работаю с текстом. Стикеры потом, если доживем до этого.")
    )
