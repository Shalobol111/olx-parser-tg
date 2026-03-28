# 🚀 OLX Parser Telegram Bot

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**A powerful Telegram bot for parsing OLX.ua listings** with Cloudflare bypass and user-friendly interface.

![Main menu screenshot](docs/screenshot_main.png)

---

## ✨ Key Features

- 🎯 **Interactive Menu** — full control via Inline buttons with FSM (Finite State Machine)
- 🔗 **Flexible Parsing** — enter your own category/search link or choose from predefined categories (Cars, Electronics, Pets, Sports)
- 📱 **Lazy Phone Loading** — seller phone numbers are loaded on demand via separate API endpoint ("Show phone" button)
- ⚙️ **Customizable Settings** — adjust ads count (1-50) and request delay (0-30 sec) directly in the bot
- 🛡️ **Cloudflare Bypass** — uses `curl_cffi` with Chrome 120 browser fingerprint impersonation
- 🌐 **DNS-over-HTTPS** — automatic DNS resolution via Cloudflare DoH API (1.1.1.1) to bypass blocks
- 📸 **Ad Photos** — automatic loading and display of product images
- 🔄 **Multi-regional** — supports various OLX domains (`.ua`, `.pl`, `.ro`, etc.)
- 💾 **Per-user Settings** — each user can customize the bot for themselves

---

## 🛠 Tech Stack

- **Python 3.10+** — modern syntax with type hints
- **aiogram 3.x** — async framework for Telegram Bot API
- **curl_cffi** — HTTP client with browser fingerprint impersonation for bypass
- **BeautifulSoup4** — HTML parsing and data extraction
- **python-dotenv** — environment variables management
- **asyncio** — asynchronous request processing

---

## 🚀 Installation and Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/olx-parser-bot.git
cd olx-parser-bot
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root (you can copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
BOT_TOKEN=your_telegram_bot_token_here
ADS_COUNT=10
REQUEST_TIMEOUT=30
REQUEST_DELAY_SECONDS=2
```

**How to get BOT_TOKEN:**
1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send the `/newbot` command
3. Follow the instructions and copy the received token
4. Paste the token into the `.env` file

### Step 5: Run the Bot

```bash
python bot.py
```

If everything is configured correctly, you'll see:
```
Bot is starting…
Run polling for bot @your_bot_name
```

---

## ⚙️ Environment Configuration (.env)

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | **Required** |
| `ADS_COUNT` | Number of ads to parse | `10` |
| `REQUEST_TIMEOUT` | HTTP request timeout (seconds) | `30` |
| `REQUEST_DELAY_SECONDS` | Delay between requests (seconds) | `2` |

---

## 💻 Usage

### Starting the Bot

1. Find your bot in Telegram
2. Send the `/start` command
3. Choose an action from the main menu:

**🚀 Parse**
- **🔗 Enter custom link** — paste any OLX category or search link
- **🗂 Choose category** — select from predefined categories (Cars, Electronics, etc.)

**⚙️ Settings**
- Change ads count (1-50)
- Adjust request delay (0-30 sec)

**ℹ️ Help**
- Detailed information about bot features

### Usage Example

```
1. /start
2. Click "🚀 Parse"
3. Select "🗂 Choose category"
4. Click "💻 Electronics"
5. Bot will send ads with photos, prices, and links
6. Click "📱 Show phone number" to get seller's contact
```

![Bot usage example](docs/screenshot_parsing.png)

---

## 📁 Project Structure

```
olx-parser-bot/
├── bot.py                  # Entry point, dispatcher initialization
├── config.py               # Configuration and environment variables
├── scraper.py              # OLX parsing logic (OLXScraper)
├── handlers/
│   ├── __init__.py         # Router exports
│   ├── main_menu.py        # Main menu, help, navigation
│   ├── parsing.py          # Parsing: links, categories, phones
│   └── settings.py         # User settings (FSM)
├── requirements.txt        # Project dependencies
├── .env.example            # Environment file example
├── .env                    # Your environment variables (not committed)
└── README.md               # Documentation
```

---

## 🔧 How It Works

### Cloudflare Bypass

OLX uses Cloudflare to protect against bots. The bot bypasses this using:

1. **curl_cffi** — impersonates Chrome 120 browser fingerprints (TLS fingerprint, User-Agent, headers)
2. **DNS-over-HTTPS** — resolves DNS via Cloudflare API (1.1.1.1) to bypass local blocks
3. **CurlOpt.RESOLVE** — forces the use of resolved IP for requests

### Data Parsing

The bot extracts data from `window.__PRERENDERED_STATE__` — a JSON object embedded in the OLX HTML page. This allows retrieving:
- Ad ID
- Title
- Price
- URL
- Photos

Phone numbers are loaded separately via API:
```
GET https://www.olx.ua/api/v1/offers/{id}/limited-phones/
```

---

## ⚠️ Important Disclaimer

**⚡ OLX actively fights against scraping and automation.**

- Frequent requests without delay may result in IP blocking (HTTP 403/429)
- It's recommended to use delays between requests (2+ seconds)
- For large-scale scraping, use proxies and IP rotation
- **This project is created for educational purposes only**
- The author is not responsible for blocks or violations of OLX ToS
- Use at your own risk

**Recommendations:**
- Don't make more than 10-20 requests per minute
- Use delay `REQUEST_DELAY_SECONDS >= 2`
- Don't run multiple bot instances from the same IP
- Consider using VPN/proxy for production

---
