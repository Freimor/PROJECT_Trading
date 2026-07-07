# Paper trading — тестирование автомата с виртуальными сделками

Режим **`paper`**: реальные ордера на **Binance testnet** и **T-Invest sandbox**, без live-денег.

## Включение

Конфиги (уже `mode: paper`):

- `trading_wiki/config/guardrails.yaml` → `trading.mode: paper`
- `trading_wiki/config/crypto_config.yaml` → `mode: paper`, `env: testnet`
- `trading_wiki/config/securities_config.yaml` → `mode: paper`, `env: sandbox`, `active_mode: swing_signals`

После правки: `docker compose up -d db-api`

## Сброс виртуального баланса

| Площадка | Можно обнулить? | Как |
|----------|-----------------|-----|
| **T-Invest sandbox** | ✅ Да | `POST /api/paper/session/reset` — закрывает демо-счёт, открывает новый с ~1M ₽ |
| **Binance testnet** | ❌ Нет вручную | Сброс ~раз в месяц на стороне Binance. PnL считаем от **baseline сессии** в SQLite |

Telegram: **🤖 Автомат → 🧪 Paper тест → 🔄 Сброс sandbox**

## Метрики эффективности LLM

`GET /api/paper/effectiveness?days=7`

- paper-ордера (executed / total)
- LLM approve rate (crypto + MOEX)
- воронка signal → filter → llm → order
- **PnL vs baseline** сессии (USDT, BTC, RUB)
- связь: LLM approve → исполненный ордер

Telegram: **📊 Эффективность**

## Ручной прогон

```powershell
# Начать сессию (зафиксировать baseline)
curl -X POST "http://localhost:8000/api/paper/session/start"

# Crypto: signal + LLM + testnet BUY
curl -X POST "http://localhost:8000/api/paper/crypto/run?symbol=BTCUSDT"

# MOEX swing: signal + LLM + sandbox BUY
curl -X POST "http://localhost:8000/api/paper/securities/swing?ticker=SBER"
```

## n8n

Workflow `crypto-execute-testnet` уже вызывает `env: paper` + `/api/binance/order`.

Активируйте workflow в n8n для автоматических прогонов по расписанию.

## Рекомендуемый цикл теста

1. `POST /api/paper/session/reset` — чистый MOEX sandbox + новая сессия
2. Торговля 1–4 недели в paper
3. `GET /api/paper/effectiveness` — оценка LLM и PnL
4. При необходимости — `POST /api/evaluation/replay` для сравнения промптов/моделей
