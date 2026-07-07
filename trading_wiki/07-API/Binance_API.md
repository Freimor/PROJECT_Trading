---
title: Binance API
tags: [API, Binance, криптовалюта, REST, WebSocket]
sources:
  - https://developers.binance.com/docs/binance-spot-api-docs/rest-api
  - https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams
  - https://developers.binance.com/docs/binance-spot-api-docs/testnet
  - https://developers.binance.com/docs/binance-spot-api-docs/rest-api#signed-trade-and-user_data-endpoint-security
  - https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/
  - [[Academic_sources]]
updated: 2026-07-06
level: intermediate
academic_sources: true
style: informational
---

# Binance API

> **Binance Spot API** — REST и WebSocket для данных и spot-торговли. В проекте: klines → indicators → orders в crypto-flow.

## Главное

- Production: `api.binance.com`; testnet: `testnet.binance.vision` — **разные keys**.
- Signed endpoints: HMAC SHA256 + `X-MBX-APIKEY`; withdrawals **disabled**.
- `GET /api/v3/klines` — OHLCV; `POST /api/v3/order` — заявка.
- Rate limits: HTTP 429 → backoff; кэшируйте `exchangeInfo` (LOT_SIZE, MIN_NOTIONAL).
- WebSocket v2: `btcusdt@kline_4h`; v1 достаточно REST по Schedule.

---

## Для новичка

| | REST | WebSocket |
|---|------|-----------|
| Когда | Запрос по требованию | Поток обновлений |
| Пример | GET `/api/v3/klines` | `btcusdt@kline_4h` |

Testnet — отдельные keys, без реальных денег.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | Production REST base URL: `https://api.binance.com`. | [Binance Spot REST API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api) |
| 2 | Testnet REST base URL: `https://testnet.binance.vision`. | [Binance Spot Testnet](https://developers.binance.com/docs/binance-spot-api-docs/testnet) |
| 3 | Production WebSocket base: `wss://stream.binance.com:9443`. Testnet WS: `wss://testnet.binance.vision`. | [Binance WebSocket Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams) |
| 4 | Signed endpoints (trade, user data) требуют HMAC SHA256 подпись query string + header `X-MBX-APIKEY`. | [Binance Signed Endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#signed-trade-and-user_data-endpoint-security) |
| 5 | `GET /api/v3/klines` — OHLCV свечи; params: `symbol`, `interval`, `limit` (max 1000), optional `startTime`, `endTime`. | [Binance Klines](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#klinecandlestick-data) |
| 6 | `POST /api/v3/order` — новая заявка; params: `symbol`, `side`, `type`, `quantity`, `price` (для LIMIT), `timestamp`. | [Binance New Order](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade) |
| 7 | Rate limits через weight; заголовки `X-MBX-USED-WEIGHT-1M`; HTTP 429 при превышении. | [Binance Limits](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#limits) |
| 8 | `GET /api/v3/exchangeInfo` — фильтры символа: `LOT_SIZE`, `MIN_NOTIONAL`, `PRICE_FILTER`. | [Binance Exchange Info](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#exchange-information) |

---

## Подробно: базовые URL

| Среда | REST | WebSocket |
|-------|------|-----------|
| Production | `https://api.binance.com` | `wss://stream.binance.com:9443` |
| Testnet | `https://testnet.binance.vision` | `wss://testnet.binance.vision` |

### Аутентификация

**Public endpoints** (klines, ticker, exchangeInfo) — без подписи.

**Signed endpoints** (order, account, openOrders):
1. Query string с `timestamp` (ms since epoch).
2. HMAC SHA256(query, API_SECRET) → `signature`.
3. Header: `X-MBX-APIKEY: {API_KEY}`.

**Рекомендации по ключу:**
- Enable **Reading** + **Spot Trading**
- **Disable Withdrawals** — критично для безопасности

### Ключевые REST endpoints

| Method | Path | Security | Описание |
|--------|------|----------|----------|
| GET | `/api/v3/ping` | NONE | Проверка connectivity |
| GET | `/api/v3/time` | NONE | Server time (для sync timestamp) |
| GET | `/api/v3/exchangeInfo` | NONE | Символы, фильтры, limits |
| GET | `/api/v3/klines` | NONE | OHLCV свечи |
| GET | `/api/v3/ticker/24hr` | NONE | 24h статистика |
| GET | `/api/v3/ticker/price` | NONE | Текущая цена |
| GET | `/api/v3/depth` | NONE | Order book |
| POST | `/api/v3/order` | TRADE | Новая заявка |
| DELETE | `/api/v3/order` | TRADE | Отмена заявки |
| GET | `/api/v3/openOrders` | USER_DATA | Открытые заявки |
| GET | `/api/v3/account` | USER_DATA | Балансы |
| GET | `/api/v3/myTrades` | USER_DATA | История сделок |

Документация: [Binance Spot REST API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api).

### Интервалы свечей (interval)

`1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`.

### Типы ордеров (type parameter)

| Type | Описание |
|------|----------|
| `LIMIT` | Лимитная; требует `price`, `timeInForce` (GTC/IOC/FOK) |
| `MARKET` | Рыночная; исполнение по best available |
| `STOP_LOSS` | Stop-market sell/buy |
| `STOP_LOSS_LIMIT` | Stop-limit |
| `TAKE_PROFIT` | Take-profit market |
| `TAKE_PROFIT_LIMIT` | Take-profit limit |

См. [[Stop_loss_take_profit]], [[Order_types]].

### WebSocket streams

**Single stream:**
```
wss://stream.binance.com:9443/ws/btcusdt@kline_4h
```

**Combined streams:**
```
wss://stream.binance.com:9443/stream?streams=btcusdt@kline_4h/ethusdt@kline_4h
```

**User data stream** (fills, balances): требует `listenKey` через REST `POST /api/v3/userDataStream`.

Документация: [WebSocket Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams).

### Rate limits

- Weight-based system; разные endpoints — разный weight.
- Заголовки: `X-MBX-USED-WEIGHT-1M`, `X-MBX-ORDER-COUNT-10S`.
- HTTP **429** — backoff обязателен.
- HTTP **418** — IP ban (нарушение limits).

---

## Примеры

### Пример 1: GET klines (curl)

```bash
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=5"
```

**Ответ (сокращённо):**
```json
[
  [1710000000000, "60000.00", "60500.00", "59800.00", "60200.00", "1234.56", ...]
]
```

### Пример 2: Signed POST order (testnet)

```bash
TIMESTAMP=$(date +%s000)
QUERY="symbol=BTCUSDT&side=BUY&type=LIMIT&timeInForce=GTC&quantity=0.001&price=60000&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$API_SECRET" | awk '{print $2}')

curl -X POST "https://testnet.binance.vision/api/v3/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}"
```

### Пример 3: exchangeInfo — LOT_SIZE для BTCUSDT

```bash
curl "https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT"
```

**Фильтр LOT_SIZE:**
```json
{
  "filterType": "LOT_SIZE",
  "minQty": "0.00001000",
  "maxQty": "9000.00000000",
  "stepSize": "0.00001000"
}
```

Quantity должна быть кратна `stepSize`.

### Пример 4: WebSocket kline event (структура)

```json
{
  "e": "kline",
  "E": 1710000000000,
  "s": "BTCUSDT",
  "k": {
    "t": 1710000000000,
    "o": "60000.00",
    "h": "60500.00",
    "l": "59800.00",
    "c": "60200.00",
    "v": "1234.56",
    "x": true
  }
}
```

`k.x === true` — свеча **закрыта** (важно для signal trigger).

---

## FAQ

### Testnet keys работают на production?

**Нет.** Отдельные keys, отдельный URL. Keys testnet на `testnet.binance.vision`.

### Как синхронизировать timestamp?

`GET /api/v3/time` → `serverTime`. Разница с local clock > 1000 ms → ошибка `-1021 TIMESTAMP`.

**Code node:**
```javascript
const serverTime = $('Get Server Time').first().json.serverTime;
return [{ json: { timestamp: serverTime } }];
```

### Чем LIMIT лучше MARKET для automation?

LIMIT контролирует цену входа; MARKET рискует slippage. Для swing 4h — LIMIT preferred. MARKET — для DCA с малым slippage tolerance.

### Как выставить OCO (SL + TP)?

Binance Spot поддерживает `POST /api/v3/order/oco` — one-cancels-other. Проверяйте актуальную документацию: [OCO Orders](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-list---oco-trade).

### Что при HTTP 429?

Exponential backoff: 5s → 10s → 20s. Max 3 retries. Затем skip cycle + alert.

---

## Ключевые понятия

| Термин | Определение |
|--------|-------------|
| HMAC SHA256 | Алгоритм подписи signed requests |
| stepSize | Минимальный шаг quantity |
| MIN_NOTIONAL | Минимальная сумма ордера (qty × price) |
| timeInForce GTC | Good Till Cancelled |
| listenKey | Ключ для user data WebSocket stream |
| Weight | Единица rate limit |

---

## Проверенные источники

1. **[Binance Spot REST API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api)** — полный справочник REST.
2. **[Binance Klines](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#klinecandlestick-data)** — GET `/api/v3/klines`.
3. **[Binance New Order](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade)** — POST `/api/v3/order`.
4. **[Binance Signed Endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#signed-trade-and-user_data-endpoint-security)** — HMAC подпись.
5. **[Binance WebSocket Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams)** — kline, trade streams.
6. **[Binance Spot Testnet](https://developers.binance.com/docs/binance-spot-api-docs/testnet)** — testnet URLs.
7. **[n8n HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)** — интеграция в n8n.

---

## Академические источники

См. также: [[Academic_sources]].

| Категория | Что изучать | Почему полезно | URL |
|---|---|---|---|
| BIS (крипто, 2023) | The crypto ecosystem: key elements and risks | Формулирует ключевые риски крипто-экосистемы; полезно для консервативных ограничений API-торговли и risk manager | https://www.bis.org/publ/othp72.pdf |
| ESRB (крипто, 2025) | Crypto-assets and decentralised finance | Макро-риски (stablecoins, CIPs, MFGs); помогает обосновать ограничения по продуктам и custody | https://www.esrb.europa.eu/pub/pdf/reports/esrb.report202510_cryptoassets.en.pdf |
| IEEE (2025) | Evolving Portfolio Heuristics: A Self-Correcting LLM Framework for Portfolio Optimization | Академический контекст LLM в контуре портфеля/стратегий; полезно для постановки требований к аудиту и бэктесту | https://ieeexplore.ieee.org/document/11200704/ |
| arXiv (2025) | Decision by Supervised Learning with Deep Ensembles (arXiv:2503.13544) | Устойчивость решений через ансамбли — идея для «двойного» approve/reject в автоматизации | https://arxiv.org/abs/2503.13544 |
| ВШЭ (ВКР, 2024) | Hedging Derivatives Under Incomplete Markets with Deep Learning (VKR 929592108) | Иллюстрирует pipeline «weights → orders», релевантно при автоматизации хеджирования/ребалансировки | https://www.hse.ru/en/edu/vkr/929592108 |

---

## В автоматической системе

### n8n workflow: fetch-klines (sub-workflow)

**Input:** `{ symbol, interval, limit, env }`

**HTTP Request node:**
```
URL: {{ $json.env === 'testnet' 
  ? 'https://testnet.binance.vision' 
  : 'https://api.binance.com' }}/api/v3/klines
Query Parameters:
  symbol: {{ $json.symbol }}
  interval: {{ $json.interval }}
  limit: {{ $json.limit }}
```

**Code node — parse + validate:**
```javascript
const klines = $input.first().json;
if (!Array.isArray(klines) || klines.length === 0) {
  throw new Error('Empty klines response');
}
const candles = klines.map(k => ({
  t: k[0], o: +k[1], h: +k[2], l: +k[3], c: +k[4], v: +k[5]
}));
return [{ json: { symbol: $('Input').first().json.symbol, candles } }];
```

### n8n workflow: place-order-signed

**Execute Workflow** called from [[Crypto_flow_design]] after risk check.

**Nodes:**
1. **Get Server Time** — GET `/api/v3/time`
2. **Build Signature** — Code node (HMAC)
3. **POST Order** — HTTP Request
4. **Validate Response** — IF `orderId` exists
5. **On Error** — route to global error handler

**Guardrails before POST:**
- Verify symbol in whitelist
- Round quantity to stepSize from cached exchangeInfo
- Verify MIN_NOTIONAL

### Caching exchangeInfo

**Schedule workflow (daily 00:05 UTC):**
- GET `/api/v3/exchangeInfo`
- Save filters to Obsidian `config/binance_symbols.json` or n8n static data
- Avoid calling exchangeInfo on every signal (weight 20)

### Testnet promotion checklist

- [ ] Workflow tag `#env/testnet` only
- [ ] Separate credentials `Binance Testnet`
- [ ] ≥ 4 weeks paper results logged
- [ ] Manual flip `crypto_config.yaml` env → live
- [ ] New credentials `Binance Live` with withdrawals disabled

### Error codes (частые)

| Code | Meaning | Action |
|------|---------|--------|
| -1021 | Timestamp out of sync | Re-fetch serverTime |
| -2010 | Insufficient balance | Reject + alert |
| -1013 | MIN_NOTIONAL | Adjust qty |
| -1111 | Precision over maximum | Round to stepSize |
| 429 | Rate limit | Backoff |

---

## Связанные темы

- [[Crypto_flow_design]]
- [[Crypto_exchanges]]
- [[Order_types]]
- [[Stop_loss_take_profit]]
- [[Ollama_integration]]
- [[Key_indicators_RSI_MACD]]

---

## Что изучить дальше

1. [[Crypto_flow_design]] — полный pipeline с Binance.
2. [[Stop_loss_take_profit]] — типы SL/TP ордеров.
3. [[Order_types]] — market, limit, stop на биржах.
4. [[LLM_rules_and_guardrails]] — безопасность API keys.
