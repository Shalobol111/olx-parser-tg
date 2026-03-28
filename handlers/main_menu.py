from __future__ import annotations

from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, FSInputFile

PHOTO_PATH = Path(__file__).parent.parent / "arb.png"

router = Router()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Парсить", callback_data="parse_menu")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help_menu")],
        ]
    )


WELCOME_TEXT = (
    "👋 <b>Привет! Я бот-парсер OLX.</b>\n\n"
    "Я могу спарсить объявления с любой категории или страницы поиска OLX.\n\n"
    "Выбери действие:"
)

HELP_TEXT = (
    "ℹ️ <b>Помощь</b>\n\n"
    "Этот бот умеет парсить объявления с сайта OLX.\n\n"
    "<b>Как пользоваться:</b>\n"
    "1. Нажми <b>🚀 Парсить</b>\n"
    "2. Введи свою ссылку на категорию/поиск OLX или выбери готовую категорию\n"
    "3. Бот пришлёт тебе объявления с фото, ценой и ссылкой\n"
    "4. Нажми <b>📱 Показать номер</b>, чтобы получить телефон продавца\n\n"
    "<b>Настройки:</b>\n"
    "В меню ⚙️ Настройки ты можешь изменить количество объявлений "
    "и задержку между запросами."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer_photo(
        photo=FSInputFile(PHOTO_PATH),
        caption=WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer_photo(  # type: ignore[union-attr]
        photo=FSInputFile(PHOTO_PATH),
        caption=WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "help_menu")
async def help_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")]
        ]
    )
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        HELP_TEXT,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
