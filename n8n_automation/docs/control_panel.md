# Управление системой

Два интерфейса с разным назначением:

| Интерфейс | URL | Назначение |
|-----------|-----|------------|
| **Web Console** | http://localhost:3000 | Полная панель: события, статистика, риск, checklist |
| **Telegram Bot** | `@YourBot` | Мобильный пульт: kill switch, stats, алерты, подтверждения |
| **n8n** | http://localhost:5678 | Workflows и расписание |

## Запуск

```bash
# Базовая инфраструктура
docker compose up -d

# Web console
docker compose --profile console up -d console

# Telegram bot + awesome-vpn proxy gateway
docker compose --profile telegram up -d proxy-gateway telegram-bot
```

## Переменные окружения

```env
TELEGRAM_BOT_TOKEN=...        # от @BotFather
TELEGRAM_CHAT_ID=...          # ваш chat id
TELEGRAM_ALLOWED_CHAT_IDS=... # allowlist (можно = CHAT_ID)
ADMIN_API_KEY=...             # опционально, для write-операций
```

## Прокси для Telegram

Если `api.telegram.org` недоступен напрямую, укажите список прокси — система **сама проверит** каждый и выберет первый рабочий (`getMe`).

```env
# Вариант 1: один прокси
TELEGRAM_PROXY=socks5://host.docker.internal:7890

# Вариант 2: несколько (автовыбор живого)
TELEGRAM_PROXY_LIST=socks5://host.docker.internal:7890,socks5://host.docker.internal:10808

# Вариант 3: файл (скопируйте data/telegram_proxies.txt.example → data/telegram_proxies.txt)
TELEGRAM_PROXY_FILE=/data/telegram_proxies.txt
```

**Docker на Windows:** локальный Clash/V2Ray слушает на `127.0.0.1`, из контейнера используйте `host.docker.internal`:

```
socks5://host.docker.internal:7890
```

Проверка: `GET http://localhost:8000/api/telegram/proxy/status`  
Переподбор: `POST /api/admin/telegram/proxy/reprobe` (header `X-Admin-Key`)

При сбое polling бот помечает прокси как мёртвый и переключается на следующий.

### awesome-vpn (встроено по умолчанию)

Источник: [awesome-vpn/awesome-vpn](https://github.com/awesome-vpn/awesome-vpn).

Сервис `proxy-gateway` скачивает `sing-box.json`, запускает **sing-box** с `urltest` на Telegram API и отдаёт `socks5://proxy-gateway:17890`. Локальные прокси (`TELEGRAM_PROXY_LIST`) проверяются **раньше** gateway.

```env
TELEGRAM_AWESOME_VPN_ENABLED=true
TELEGRAM_AWESOME_VPN_MAX_NODES=50
```

⚠️ Публичные ноды — только для алертов, не для банкинга.

## API (db-api)

| Endpoint | Описание |
|----------|----------|
| `GET /api/system/status` | Статус системы |
| `GET /api/stats/digest` | Статистика dry-run / live |
| `GET /api/live/checklist` | Готовность к live |
| `POST /api/admin/kill-switch` | Kill switch (header `X-Admin-Key`) |
| `POST /api/notify/telegram` | Исходящий алерт в Telegram |
| `GET /api/telegram/proxy/status` | Статус прокси |
| `POST /api/admin/telegram/proxy/reprobe` | Переподбор прокси |
| `GET /api/admin/confirmations/pending` | Ожидающие подтверждения |
| `GET /api/automation/overview` | Сводка для dashboard |
| `GET /api/crypto/testnet-dashboard` | Crypto funnel + LLM metrics |
| `GET /api/binance/balances` | Кошелёк testnet |
| `GET /api/testing/tinvest-sandbox` | MOEX sandbox портфель |
| `GET /api/charts/candles` | OHLCV для графика (`market`, `symbol`, `interval`) |
| `GET /api/charts/markers` | Маркеры LLM/ордеров на графике |
| `GET /api/charts/symbols` | Список пар/тикеров |
| `GET /api/events?symbol=` | Фильтр событий по символу |

## Telegram — меню

Постоянная клавиатура внизу чата:

| Кнопка | Действие |
|--------|----------|
| 📊 Статус | Состояние системы |
| 📈 Статистика | Dry-run / live за 7 дней |
| 📋 Checklist | Готовность к live |
| 🧾 События | Последние события |
| ⚠️ Риск | Kill switch (с подтверждением) |
| ✅ Подтверждения | Ожидающие approve/reject |
| 🔧 Сервис | Smoke test, ping |
| 🏠 Меню | Вернуться к главному экрану |

Команды `/status` и т.д. остаются как запасной вариант. Достаточно `/start` или кнопки **🏠 Меню**.

## Web Console — разделы

Постоянная **status bar**: kill switch, режим, Ollama, последнее событие.

| Раздел | Содержимое |
|--------|------------|
| **Обзор** | Карточки crypto/MOEX, кошелёк testnet, хост, LLM metrics |
| **₿ Crypto** | График (Lightweight Charts) + маркеры pipeline, баланс, события по паре |
| **📈 MOEX** | Дневной график + sandbox портфель |
| **События** | Журнал `trade_events` с фильтрами |
| **Управление** | Kill switch, smoke, checklist, confirmations |
| **LLM** | Аудит решений + replay |
| **Paper** | Сессии, snapshot, прогон crypto/MOEX |
| **Benchmark** | Outcome metrics + последняя калибровка |
| **n8n** | Workflows on/off + cron |

Маркеры на графике: LLM approve/reject, guardrails, order, fill (цвет/форма по `stage`).

Chart API пример:

```powershell
curl "http://localhost:8000/api/charts/candles?market=crypto&symbol=BTCUSDT&interval=4h&limit=200"
curl "http://localhost:8000/api/charts/markers?market=crypto&symbol=BTCUSDT&env=dry_run"
curl "http://localhost:8000/api/charts/equity?days=30"
curl "http://localhost:8000/api/llm/decisions?market=crypto&limit=20"
```

## Kill switch

Хранится в SQLite (`runtime_settings`), не требует записи в YAML (wiki смонтирован read-only).

Приоритет: runtime override → `guardrails.yaml`.

## n8n алерты

Workflow `shared-telegram-alert` вызывает `POST /api/notify/telegram` вместо прямого Telegram API.
