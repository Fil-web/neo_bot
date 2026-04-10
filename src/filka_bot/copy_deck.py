from typing import Optional


MODE_LABELS = {
    "default": "обычный",
    "hard": "жесткий",
    "business": "деловой",
    "sales": "продажи",
    "support": "поддержка",
}

START_INTRO = (
    "Шаг 1/3\n\n"
    "Филька\n"
    "Персональный помощник от #Фил\n\n"
    "Что внутри:\n"
    "- ответы на вопросы без лишней воды\n"
    "- работа с фото, документами и голосовыми\n"
    "- режимы общения под задачу и настроение\n\n"
    "Остался один быстрый запускной прогон."
)

ONBOARDING_CAPABILITIES = (
    "Шаг 2/3\n\n"
    "Возможности\n\n"
    "- текстовые вопросы\n"
    "- фото и документы\n"
    "- голосовые сообщения\n"
    "- память в рамках дневного лимита\n\n"
    "Можно писать как есть, без специальных форматов."
)

ONBOARDING_MODE = (
    "Шаг 3/3\n\n"
    "Стиль общения\n\n"
    "Выбери режим ответа под себя.\n"
    "Позже его можно поменять в любой момент через /mode."
)

ONBOARDING_DONE = (
    "Настройка завершена.\n\n"
    "Филька готов к работе.\n"
    "Можешь сразу задать вопрос или использовать меню ниже."
)

MAIN_MENU_READY = "Главное меню уже внизу."
HELP_TEXT = (
    "Можно отправить текст, фото, документ или голосовое.\n"
    "/mode меняет стиль ответа.\n"
    "/clear очищает память за сегодня.\n"
    "/status показывает текущий лимит и режим."
)
CLEAR_DONE = "Память за сегодня очищена."
MODE_SELECT = "Выбери режим ответа."
ADMIN_UNAVAILABLE = "Команда недоступна."
ADMINMODE_UNAVAILABLE = "Эта команда доступна только админам."
EXPORT_STATS_READY = "Экспорт статистики готов."
EXPORT_USERS_READY = "Экспорт пользователей готов."
SUBSCRIPTION_CHECK_UNAVAILABLE = "Проверка подписки сейчас недоступна."
SUBSCRIPTION_REQUIRED = "Сначала подпишись на канал и затем нажми проверку еще раз."
SUBSCRIPTION_SUCCESS = "Готово. Доступ открыт.\n\nТеперь можешь сразу писать вопрос."
ACCESS_DENIED = "Доступ пока закрыт. Сначала подпишись на нужный канал, потом вернись сюда."
UNKNOWN_USER_ALERT = "Не удалось определить пользователя."
CHANNEL_NOT_CONFIGURED_ALERT = "Канал не настроен."
SUBSCRIPTION_SUCCESS_ALERT = "Доступ открыт."
SUBSCRIPTION_MISSING_ALERT = "Подписка пока не найдена."
OPENED_MODES_ALERT = "Режимы открыты."
UNKNOWN_CALLBACK_USER_ALERT = "Не удалось определить пользователя."
UNKNOWN_MODE_ALERT = "Неизвестный режим."
MODE_UPDATED_ALERT = "Режим обновлен."
OPENED_HELP_ALERT = "Подсказки открыты."
STATUS_SHOWN_ALERT = "Статус показан."
MEMORY_CLEARED_ALERT = "Память очищена."
EMPTY_TEXT = "Похоже, сообщение пустое. Пришли текст, и разберемся."
BANNED_TEXT = "Доступ закрыт."
ANTISPAM_TEXT = "Слишком быстро. Сделай короткую паузу и потом продолжим."
MODEL_ERROR = "Сейчас не получилось обработать запрос. Попробуй еще раз чуть позже."
PHOTO_ERROR = "С фото возникла заминка. Попробуй отправить его еще раз."
VOICE_EMPTY = "С голосовым что-то не так. Попробуй отправить его еще раз."
VOICE_ERROR = "С голосовым вышла заминка. Если хочешь, пришли текстом или повтори отправку."
DOCUMENT_UNSUPPORTED = "Пока поддерживаются PDF, DOCX, TXT, CSV и XLSX."
DOCUMENT_PARSE_ERROR = "С документом что-то пошло не так. Попробуй еще раз чуть позже."
DOCUMENT_KB_ADDED = "Документ добавлен в базу знаний. ID: {document_id}."
DOCUMENT_ANSWER_ERROR = "Документ прочитан, но ответ сейчас не собрался. Попробуй еще раз."
UNSUPPORTED_TEXT = "Пока работаю с текстом, фото, документами и голосовыми."
BROADCAST_USAGE = "Используй: `/broadcast segment|текст`"
BROADCAST_EMPTY = "Текст рассылки пустой."
BROADCAST_NO_RECIPIENTS = "По этому сегменту пока никого не найдено."
BAN_USAGE = "Используй: `/ban user_id причина`"
MUTE_USAGE = "Используй: `/mute user_id минуты причина`"
UNBAN_USAGE = "Используй: `/unban user_id`"
BUTTON_HELP = "Помощь"
BUTTON_STATUS = "Статус"
BUTTON_CLEAR = "Очистить память"
PLACEHOLDER_MAIN_INPUT = "Напиши вопрос Фильке..."
BUTTON_CONTINUE = "Продолжить"
BUTTON_SKIP = "Пропустить"
BUTTON_PICK_MODE = "Выбрать режим"
BUTTON_DONE = "Готово"
BUTTON_MODE_DEFAULT = "Обычный"
BUTTON_MODE_HARD = "Жесткий"
BUTTON_MODE_BUSINESS = "Деловой"
BUTTON_MODE_SALES = "Продажи"
BUTTON_MODE_SUPPORT = "Поддержка"
BUTTON_SUBSCRIBE = "Подписаться на канал"
BUTTON_CHECK_SUBSCRIPTION = "Проверить подписку"


def status_text(stored_messages: int, max_history: int, mode: str) -> str:
    return (
        "Статус:\n"
        f"- сообщений сегодня: {stored_messages}\n"
        f"- лимит в день: {max_history}\n"
        f"- режим: {MODE_LABELS.get(mode, mode)}"
    )


def admin_stats_text(stats: dict[str, int]) -> str:
    return (
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
    )


def kb_stats_text(stats: dict[str, int]) -> str:
    return (
        "База знаний:\n"
        f"- документов: {stats['documents']}\n"
        f"- чанков: {stats['chunks']}\n"
        f"- embeddings: {stats.get('embedded_chunks', 0)}"
    )


def admin_mode_text(enabled: bool) -> str:
    state = "включен" if enabled else "выключен"
    return f"Админ-режим {state}."


def mode_saved_text(mode: str) -> str:
    return f"Режим: `{MODE_LABELS[mode]}`."


def muted_text(reason: Optional[str]) -> str:
    suffix = f" Причина: {reason}." if reason else ""
    return f"Ты временно на паузе. Подожди немного.{suffix}"


def ban_success_text(target_user_id: int) -> str:
    return f"Пользователь `{target_user_id}` заблокирован."


def mute_success_text(target_user_id: int, minutes: int) -> str:
    return f"Пользователь `{target_user_id}` ограничен на {minutes} мин."


def unban_success_text(target_user_id: int) -> str:
    return f"Ограничения для `{target_user_id}` сняты."


def broadcast_done_text(sent: int, failed: int) -> str:
    return f"Рассылка отправлена. Доставлено: {sent}. Ошибок: {failed}."
