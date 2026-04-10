from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup

from filka_bot import copy_deck


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=copy_deck.BUTTON_HELP),
                KeyboardButton(text=copy_deck.BUTTON_STATUS),
            ],
            [
                KeyboardButton(text=copy_deck.BUTTON_CLEAR),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=copy_deck.PLACEHOLDER_MAIN_INPUT,
    )


def build_start_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_CONTINUE, callback_data="onboarding_2"),
            ],
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_SKIP, callback_data="onboarding_done")
            ],
        ]
    )


def build_onboarding_step_two_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_PICK_MODE, callback_data="onboarding_3"),
                InlineKeyboardButton(text=copy_deck.BUTTON_SKIP, callback_data="onboarding_done"),
            ]
        ]
    )


def build_onboarding_step_three_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_DEFAULT, callback_data="mode_default"),
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_BUSINESS, callback_data="mode_business"),
            ],
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_SALES, callback_data="mode_sales"),
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_SUPPORT, callback_data="mode_support"),
            ],
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_HARD, callback_data="mode_hard"),
                InlineKeyboardButton(text=copy_deck.BUTTON_DONE, callback_data="onboarding_done"),
            ],
        ]
    )


def build_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_DEFAULT, callback_data="mode_default"),
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_HARD, callback_data="mode_hard"),
            ],
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_BUSINESS, callback_data="mode_business"),
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_SALES, callback_data="mode_sales"),
            ],
            [
                InlineKeyboardButton(text=copy_deck.BUTTON_MODE_SUPPORT, callback_data="mode_support"),
            ],
        ]
    )
