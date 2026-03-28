from __future__ import annotations

import asyncio
import json
import re
import logging
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from curl_cffi.const import CurlOpt
from curl_cffi.requests import Session

from config import DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class Ad:
    id: str
    title: str
    price: str
    url: str
    photo_url: str | None = None


class OLXScraperError(Exception):
    """Base exception for scraper errors."""


class OLXBlockedError(OLXScraperError):
    """Raised when OLX returns 403 / 429 (blocked or rate-limited)."""


class OLXScraper:
    """Async scraper for OLX listings using curl_cffi to bypass Cloudflare."""

    _PRERENDERED_RE = re.compile(
        r'window\.__PRERENDERED_STATE__\s*=\s*"((?:[^"\\]|\\.)*)"',
        re.DOTALL,
    )

    def __init__(self) -> None:
        self._session: Session | None = None
        self._resolved: dict[str, str] = {}

    def _resolve_host(self, hostname: str) -> str:
        """Resolve hostname via Cloudflare DNS-over-HTTPS (DoH) JSON API."""
        if hostname in self._resolved:
            return self._resolved[hostname]
        doh_url = f"https://1.1.1.1/dns-query?name={hostname}&type=A"
        req = urllib.request.Request(doh_url, headers={"Accept": "application/dns-json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            for answer in data.get("Answer", []):
                if answer.get("type") == 1:
                    ip = answer["data"]
                    self._resolved[hostname] = ip
                    logger.info("DoH resolved %s -> %s", hostname, ip)
                    return ip
        except Exception as exc:
            logger.warning("DoH resolution failed for %s: %s", hostname, exc)
        raise OLXScraperError(f"Не удалось разрешить DNS для {hostname}")

    def _get_session(self, url: str) -> Session:
        """Get or create a sync Session with DNS RESOLVE set for the target host."""
        parsed = urlparse(url)
        hostname = parsed.hostname or "www.olx.ua"

        if self._session is None:
            self._session = Session(
                impersonate="chrome120",
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

        ip = self._resolve_host(hostname)
        self._session.curl.setopt(
            CurlOpt.RESOLVE,
            [f"{hostname}:443:{ip}".encode(), f"{hostname}:80:{ip}".encode()],
        )
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract base domain from a URL (e.g. 'www.olx.ua' -> 'olx.ua')."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")

    @staticmethod
    def _build_api_base(url: str) -> str:
        """Build API base URL from a listing URL."""
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        hostname = parsed.hostname or "www.olx.ua"
        return f"{scheme}://{hostname}"

    def _decode_prerendered(self, raw: str) -> dict:
        """Decode the escaped __PRERENDERED_STATE__ string into a dict."""
        # The raw value is a JS string literal content with \" for quotes,
        # \\uXXXX for unicode escapes, etc. Wrapping it back in quotes and
        # parsing as a JSON string correctly unescapes everything.
        json_string: str = json.loads('"' + raw + '"')
        return json.loads(json_string)

    def _parse_ads_from_state(self, state: dict, limit: int) -> list[Ad]:
        """Extract ad objects from the prerendered state dict."""
        ads: list[Ad] = []

        listing_data = (
            state.get("listing", {})
            or state.get("searchPage", {})
            or {}
        )

        items: list[dict] = []
        if "listing" in listing_data:
            items = listing_data["listing"].get("ads", [])
        elif "ads" in listing_data:
            items = listing_data["ads"]
        elif "data" in listing_data:
            data = listing_data["data"]
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("ads", []) or data.get("items", [])

        if not items:
            for key, val in state.items():
                if isinstance(val, dict):
                    for inner_key, inner_val in val.items():
                        if isinstance(inner_val, dict) and "ads" in inner_val:
                            items = inner_val["ads"]
                            break
                        if isinstance(inner_val, list) and len(inner_val) > 0:
                            first = inner_val[0]
                            if isinstance(first, dict) and "id" in first:
                                items = inner_val
                                break
                if items:
                    break

        for item in items[:limit]:
            ad_id = str(item.get("id", ""))
            if not ad_id:
                continue

            title = item.get("title", "Без названия")

            price_obj = item.get("price", {})
            if isinstance(price_obj, dict):
                regular = price_obj.get("regularPrice", {})
                if isinstance(regular, dict):
                    amount = regular.get("value", "")
                    currency = regular.get("currencyCode", "")
                    price = f"{amount} {currency}".strip() if amount else "Цена не указана"
                else:
                    display = price_obj.get("displayValue", "") or price_obj.get("label", "")
                    price = display if display else "Цена не указана"
            elif isinstance(price_obj, str):
                price = price_obj
            else:
                price = "Цена не указана"

            url = item.get("url", "")

            photos = item.get("photos", []) or item.get("images", [])
            photo_url: str | None = None
            if photos:
                first_photo = photos[0]
                if isinstance(first_photo, dict):
                    photo_url = (
                        first_photo.get("link", "")
                        or first_photo.get("url", "")
                        or first_photo.get("src", "")
                    )
                elif isinstance(first_photo, str):
                    photo_url = first_photo
                if photo_url:
                    photo_url = photo_url.replace("{width}", "800").replace("{height}", "600")

            ads.append(
                Ad(id=ad_id, title=title, price=price, url=url, photo_url=photo_url)
            )

        return ads

    def _fetch_page(self, category_url: str) -> str:
        """Sync helper: fetch HTML from an OLX category page."""
        session = self._get_session(category_url)
        response = session.get(category_url)

        if response.status_code in (403, 429):
            raise OLXBlockedError(
                f"OLX заблокировал запрос (HTTP {response.status_code}). "
                "Попробуйте позже."
            )
        if response.status_code != 200:
            raise OLXScraperError(f"OLX вернул HTTP {response.status_code}.")
        return response.text

    async def get_ads(
        self,
        category_url: str,
        limit: int = 10,
        delay: float = 0.0,
    ) -> list[Ad]:
        """Fetch and parse ads from an OLX category / search page.

        Args:
            category_url: Full URL to the OLX category or search page.
            limit: Max number of ads to return.
            delay: Seconds to wait before the request (rate-limit friendly).

        Returns:
            List of Ad dataclasses.

        Raises:
            OLXBlockedError: When OLX responds with 403/429.
            OLXScraperError: On any other scraping failure.
        """
        if delay > 0:
            await asyncio.sleep(delay)

        try:
            html = await asyncio.to_thread(self._fetch_page, category_url)
        except (OLXBlockedError, OLXScraperError):
            raise
        except Exception as exc:
            raise OLXScraperError(f"Ошибка сети: {exc}") from exc

        match = self._PRERENDERED_RE.search(html)

        if not match:
            soup = BeautifulSoup(html, "html.parser")
            script_tags = soup.find_all("script")
            for tag in script_tags:
                text = tag.string or ""
                if "__PRERENDERED_STATE__" in text:
                    inner = re.search(
                        r'window\.__PRERENDERED_STATE__\s*=\s*"((?:[^"\\]|\\.)*)"',
                        text,
                        re.DOTALL,
                    )
                    if inner:
                        match = inner
                        break

        if not match:
            raise OLXScraperError(
                "Не удалось найти данные объявлений на странице. "
                "Убедитесь, что ссылка ведёт на страницу категории или поиска OLX."
            )

        try:
            state = self._decode_prerendered(match.group(1))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise OLXScraperError(
                f"Ошибка декодирования данных страницы: {exc}"
            ) from exc

        ads = self._parse_ads_from_state(state, limit)

        if not ads:
            raise OLXScraperError(
                "На странице не найдено объявлений. "
                "Возможно, категория пуста или ссылка некорректна."
            )

        api_base = self._build_api_base(category_url)
        for ad in ads:
            if ad.url and not ad.url.startswith("http"):
                ad.url = f"{api_base}{ad.url}"

        return ads

    def _fetch_phone(self, ad_id: str, ad_url: str) -> str:
        """Sync helper: fetch phone number from OLX API."""
        api_base = self._build_api_base(ad_url) if ad_url else "https://www.olx.ua"
        phone_url = f"{api_base}/api/v1/offers/{ad_id}/limited-phones/"

        session = self._get_session(phone_url)
        headers = {
            **DEFAULT_HEADERS,
            "Referer": ad_url or f"{api_base}/",
            "Accept": "application/json",
        }
        response = session.get(phone_url, headers=headers)

        if response.status_code in (403, 429):
            raise OLXBlockedError(
                f"OLX заблокировал запрос телефона (HTTP {response.status_code}). "
                "Попробуйте позже."
            )
        if response.status_code != 200:
            return "Номер телефона недоступен."

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            return "Не удалось прочитать ответ с номером телефона."

        phones: list[str] = data.get("phones", [])
        if not phones:
            return "Продавец не указал номер телефона."
        return ", ".join(phones)

    async def get_phone(self, ad_id: str, ad_url: str) -> str:
        """Fetch phone number for a specific ad via OLX internal API.

        Args:
            ad_id: The OLX ad ID.
            ad_url: The full ad URL (used to derive the API domain).

        Returns:
            Phone number string, or a message if unavailable.

        Raises:
            OLXBlockedError: When OLX responds with 403/429.
            OLXScraperError: On any other failure.
        """
        try:
            return await asyncio.to_thread(self._fetch_phone, ad_id, ad_url)
        except (OLXBlockedError, OLXScraperError):
            raise
        except Exception as exc:
            raise OLXScraperError(f"Ошибка сети при запросе телефона: {exc}") from exc
