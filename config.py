import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

ADS_COUNT: int = int(os.getenv("ADS_COUNT", "10"))

REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

REQUEST_DELAY_SECONDS: float = float(os.getenv("REQUEST_DELAY_SECONDS", "2"))

PREDEFINED_CATEGORIES: dict[str, str] = {
    "🚗 Автомобили": "https://www.olx.ua/uk/transport/legkovye-avtomobili/",
    "🐶 Питомцы": "https://www.olx.ua/uk/zhivotnye/",
    "💻 Электроника": "https://www.olx.ua/uk/elektronika/",
    "⚽️ Спорттовары": "https://www.olx.ua/uk/hobbi-otdyh-i-sport/sport-otdyh/",
}

DEFAULT_USER_SETTINGS: dict[str, int | float] = {
    "ads_count": ADS_COUNT,
    "delay": REQUEST_DELAY_SECONDS,
}

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
