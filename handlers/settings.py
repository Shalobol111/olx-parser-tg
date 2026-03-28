from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.parsing import get_user_settings

router = Router()


class SettingsStates(StatesGroup):
    waiting_ads_count = State()
    waiting_delay = State()


def _settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить кол-во", callback_data="set_ads_count")],
            [InlineKeyboardButton(text="✏️ Изменить задержку", callback_data="set_delay")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")],
        ]
    )


def _settings_text(user_id: int) -> str:
    s = get_user_settings(user_id)
    return (
        "⚙️ <b>Текущие настройки:</b>\n\n"
        f"- Кол-во объявлений: <b>{int(s['ads_count'])}</b>\n"
        f"- Задержка (сек): <b>{s['delay']}</b>"
    )


@router.callback_query(F.data == "settings_menu")
async def settings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        _settings_text(callback.from_user.id),
        parse_mode="HTML",
        reply_markup=_settings_keyboard(),
    )


# ── Change ads count ────────────────────────────────────────────────────────

@router.callback_query(F.data == "set_ads_count")
async def ask_ads_count(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(SettingsStates.waiting_ads_count)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_menu")],
        ]
    )
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        "✏️ Введи новое <b>количество объявлений</b> (от 1 до 50):",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.message(SettingsStates.waiting_ads_count, F.text)
async def handle_ads_count(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (1 <= int(text) <= 50):
        await message.answer("❌ Введи целое число от 1 до 50.")
        return

    user_id = message.from_user.id  # type: ignore[union-attr]
    get_user_settings(user_id)["ads_count"] = int(text)
    await state.clear()
    await message.answer(
        f"✅ Кол-во объявлений установлено: <b>{text}</b>",
        parse_mode="HTML",
        reply_markup=_settings_keyboard(),
    )


# ── Change delay ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "set_delay")
async def ask_delay(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(SettingsStates.waiting_delay)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_menu")],
        ]
    )
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        "✏️ Введи новую <b>задержку</b> между запросами в секундах (от 0 до 30):",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.message(SettingsStates.waiting_delay, F.text)
async def handle_delay(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    try:
        value = float(text)
    except ValueError:
        await message.answer("❌ Введи число (допускаются дробные, например 1.5).")
        return

    if not (0 <= value <= 30):
        await message.answer("❌ Задержка должна быть от 0 до 30 секунд.")
        return

    user_id = message.from_user.id  # type: ignore[union-attr]
    get_user_settings(user_id)["delay"] = value
    await state.clear()
    await message.answer(
        f"✅ Задержка установлена: <b>{value}</b> сек.",
        parse_mode="HTML",
        reply_markup=_settings_keyboard(),
    )
