from __future__ import annotations

import asyncio
import logging
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import DEFAULT_USER_SETTINGS, PREDEFINED_CATEGORIES
from scraper import Ad, OLXBlockedError, OLXScraper, OLXScraperError

logger = logging.getLogger(__name__)

router = Router()
scraper = OLXScraper()

OLX_URL_RE = re.compile(r"https?://(?:www\.)?olx\.\w{2,3}(?:\.\w{2})?/")

_ad_cache: dict[str, Ad] = {}

_user_settings: dict[int, dict[str, int | float]] = {}


def get_user_settings(user_id: int) -> dict[str, int | float]:
    if user_id not in _user_settings:
        _user_settings[user_id] = dict(DEFAULT_USER_SETTINGS)
    return _user_settings[user_id]


class ParseStates(StatesGroup):
    waiting_for_link = State()


def _back_button() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")]


def _ad_keyboard(ad_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Показать номер телефона",
                    callback_data=f"phone:{ad_id}",
                )
            ]
        ]
    )


def _ad_text(ad: Ad) -> str:
    return (
        f"<b>{ad.title}</b>\n"
        f"💰 {ad.price}\n"
        f'🔗 <a href="{ad.url}">Открыть на OLX</a>'
    )


# ── Parse menu ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "parse_menu")
async def parse_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Ввести свою ссылку", callback_data="parse_custom_link")],
            [InlineKeyboardButton(text="🗂 Выбрать категорию", callback_data="parse_predefined_category")],
            _back_button(),
        ]
    )
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        "🚀 <b>Парсинг OLX</b>\n\nВыбери способ:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ── Custom link (FSM) ──────────────────────────────────────────────────────

@router.callback_query(F.data == "parse_custom_link")
async def ask_for_link(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ParseStates.waiting_for_link)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="parse_menu")],
        ]
    )
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        "🔗 Отправь мне ссылку на категорию или поиск OLX.\n\n"
        "Пример:\n<code>https://www.olx.ua/uk/elektronika/</code>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.message(ParseStates.waiting_for_link, F.text)
async def handle_custom_link(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    match = OLX_URL_RE.search(text)
    if not match:
        await message.answer(
            "🤔 Это не похоже на ссылку OLX.\n"
            "Пожалуйста, отправь корректную ссылку на категорию или поиск.",
        )
        return

    url_match = re.search(r"https?://\S+", text)
    url = url_match.group(0) if url_match else text
    await state.clear()
    await _run_parsing(message, url, message.from_user.id)  # type: ignore[union-attr]


# ── Predefined categories ──────────────────────────────────────────────────

@router.callback_query(F.data == "parse_predefined_category")
async def show_categories(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=name, callback_data=f"cat:{name}")]
        for name in PREDEFINED_CATEGORIES
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="parse_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        "🗂 <b>Выбери категорию:</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("cat:"))
async def handle_category_choice(callback: CallbackQuery) -> None:
    await callback.answer()
    cat_name = (callback.data or "").removeprefix("cat:")
    url = PREDEFINED_CATEGORIES.get(cat_name)
    if not url:
        await callback.message.answer("❌ Категория не найдена.")  # type: ignore[union-attr]
        return

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"🚀 Парсю категорию: <b>{cat_name}</b>...",
        parse_mode="HTML",
    )
    await _run_parsing(
        callback.message,  # type: ignore[arg-type]
        url,
        callback.from_user.id,
    )


# ── Phone callback ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("phone:"))
async def handle_phone_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    ad_id = (callback.data or "").removeprefix("phone:")
    if not ad_id:
        await callback.message.answer("❌ Не удалось определить ID объявления.")  # type: ignore[union-attr]
        return

    ad = _ad_cache.get(ad_id)
    ad_url = ad.url if ad else ""

    wait_msg = await callback.message.answer("⏳ Запрашиваю номер телефона...")  # type: ignore[union-attr]

    try:
        phone = await scraper.get_phone(ad_id, ad_url)
    except OLXBlockedError:
        await wait_msg.edit_text(
            "⚠️ OLX временно заблокировал запрос телефона.\n"
            "Попробуй ещё раз через пару минут."
        )
        return
    except OLXScraperError as exc:
        await wait_msg.edit_text(f"❌ Ошибка: {exc}")
        return
    except Exception:
        logger.exception("Unexpected error fetching phone for ad %s", ad_id)
        await wait_msg.edit_text("❌ Произошла непредвиденная ошибка при получении номера.")
        return

    await wait_msg.edit_text(
        f"📱 Номер телефона: <b>{phone}</b>",
        parse_mode="HTML",
    )


# ── Shared parsing logic ───────────────────────────────────────────────────

async def _run_parsing(message: Message, url: str, user_id: int) -> None:
    settings = get_user_settings(user_id)
    ads_count = int(settings["ads_count"])
    delay = float(settings["delay"])

    wait_msg = await message.answer("⏳ Парсю объявления, подожди немного...")

    try:
        ads = await scraper.get_ads(url, limit=ads_count, delay=delay)
    except OLXBlockedError as exc:
        logger.warning("OLX blocked request: %s", exc)
        await wait_msg.edit_text(
            "⚠️ OLX временно заблокировал запрос.\n"
            "Попробуй ещё раз через пару минут."
        )
        return
    except OLXScraperError as exc:
        logger.error("Scraper error: %s", exc)
        await wait_msg.edit_text(f"❌ Ошибка: {exc}")
        return
    except Exception:
        logger.exception("Unexpected error during scraping")
        await wait_msg.edit_text("❌ Произошла непредвиденная ошибка. Попробуй позже.")
        return

    await wait_msg.edit_text(
        f"✅ Готово! Вот первые <b>{len(ads)}</b> объявлений:",
        parse_mode="HTML",
    )

    for ad in ads:
        _ad_cache[ad.id] = ad
        keyboard = _ad_keyboard(ad.id)

        try:
            if ad.photo_url:
                await message.answer_photo(
                    photo=ad.photo_url,
                    caption=_ad_text(ad),
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            else:
                await message.answer(
                    text=_ad_text(ad),
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
        except Exception as exc:
            logger.warning("Failed to send ad %s with photo, retrying without: %s", ad.id, exc)
            try:
                await message.answer(
                    text=_ad_text(ad),
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            except Exception:
                logger.exception("Failed to send ad %s entirely", ad.id)

        await asyncio.sleep(0.3)
