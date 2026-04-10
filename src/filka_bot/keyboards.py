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
        ]
    )
