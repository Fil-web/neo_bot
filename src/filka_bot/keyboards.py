from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Помощь"),
                KeyboardButton(text="Статус"),
            ],
            [
                KeyboardButton(text="Очистить память"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напиши вопрос Фильке...",
    )


def build_start_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Помощь", callback_data="menu_help"),
                InlineKeyboardButton(text="Статус", callback_data="menu_status"),
            ],
            [
                InlineKeyboardButton(
                    text="Очистить память",
                    callback_data="menu_clear",
                )
            ],
            [
                InlineKeyboardButton(text="Режим", callback_data="menu_mode")
            ],
        ]
    )


def build_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Обычный", callback_data="mode_default"),
                InlineKeyboardButton(text="Жесткий", callback_data="mode_hard"),
            ],
            [
                InlineKeyboardButton(text="Деловой", callback_data="mode_business"),
                InlineKeyboardButton(text="Продажи", callback_data="mode_sales"),
            ],
            [
                InlineKeyboardButton(text="Поддержка", callback_data="mode_support"),
            ],
        ]
    )
