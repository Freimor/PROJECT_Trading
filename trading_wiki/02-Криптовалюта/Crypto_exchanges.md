---
title: Криптобиржи
tags: [криптовалюта, биржи, CEX, DEX, Binance, API]
sources:
  - https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities
  - https://developers.binance.com/docs/binance-spot-api-docs/rest-api
  - https://testnet.binance.vision/
  - https://www.fatf-gafi.org/en/topics/virtual-assets.html
  - https://academy.binance.com/en/articles/what-is-a-cex
  - https://www.bis.org/publ/bppdf/bispap156.pdf
  - https://www.bis.org/publ/bppdf/bispap159.htm
  - https://www.bis.org/publ/work1146.pdf
updated: 2026-07-06
level: beginner
academic_sources: true
style: informational
---

# Криптобиржи

> Криптобиржа — площадка для обмена криптоактивами. CEX управляет order book и custody; DEX исполняет сделки через smart contracts. Для автоматической системы — Binance Spot API (production + testnet).

## Главное

- CEX: регистрация, KYC, торговля через order book, активы на exchange wallet.
- DEX: wallet + smart contract, self-custody, вы сами отвечаете за seed и gas.
- API-ключи для ботов: только trade, never withdraw.
- Testnet (testnet.binance.vision) — тестирование без реальных денег.
- Превышение rate limits → бан 429; нужен backoff в automation.

---

## Для новичка

### CEX

Регистрация, часто KYC. Пополнение, торговля через order book, активы на exchange wallet — биржа хранит ключи.

Investor.gov: платформы могут fail, assets могут быть lost ([Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)).

### DEX

Пользователь подключает wallet, swap через liquidity pool (AMM). Self-custody, но вы сами отвечаете за seed, gas, wrong contract.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | FATF: VASP (включая exchanges) должны соблюдать AML/CFT. | [FATF: Virtual Assets](https://www.fatf-gafi.org/en/topics/virtual-assets.html) |
| 2 | SEC Investor.gov: crypto platforms not all regulated same as securities exchanges. | [Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities) |
| 3 | Binance Spot REST API production: `https://api.binance.com`. | [Binance Spot API Docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api) |
| 4 | Binance Spot Testnet: `https://testnet.binance.vision/`. | [Binance Spot Testnet](https://testnet.binance.vision/) |
| 5 | API requests требуют API Key; signed endpoints — HMAC SHA256. | [Binance Spot API Docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api) |
| 6 | CEX — company-operated platform, often holds user funds. | [Binance Academy: What is a CEX](https://academy.binance.com/en/articles/what-is-a-cex) |
| 7 | Rate limits apply; превышение → HTTP 429 / disconnect. | [Binance Spot API Docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api) |

---

## CEX vs DEX — сравнение

| Критерий | CEX | DEX |
|----------|-----|-----|
| Custody | Биржа | Пользователь |
| KYC/AML | Обычно да | Variable |
| Fiat on-ramp | Часто | Редко |
| API для n8n | REST + WebSocket | RPC, subgraph |
| Latency | Низкая на major CEX | Зависит от chain |
| Listing risk | Delisting notice | Rug pull / scam token |
| Order types | Market, limit, stop, OCO (spot) | Swap, limit (DEX-specific) |

---

## Типы рынков на CEX

| Рынок | Описание | Risk level |
|-------|----------|------------|
| **Spot** | Покупка/продажа актива | Baseline project scope |
| **Margin** | Заём для leverage | Higher — liquidation |
| **Futures / Perps** | Derivatives | Highest — funding, liquidation |

**Проект automation:** по умолчанию **spot only**. Futures — только после отдельного risk review и config flag.

---

## Критерии выбора CEX для bots

| Критерий | Зачем |
|----------|-------|
| REST + WebSocket | n8n HTTP + WS nodes |
| Documented rate limits | Avoid 429 bans |
| Testnet | Paper trading parity |
| Spot OCO / stop orders | [[Stop_loss_take_profit]] |
| Stable API changelog | Version migration planning |
| Geo restrictions | Legal availability |

---

## Binance API — структура (spot)

### REST categories (упрощённо)

- **Market data** — public, no key (klines, depth, ticker).
- **Trading** — signed (new order, cancel, query order).
- **Account** — signed (balances).

### WebSocket

- **Streams:** kline, trade, depth, user data (execution reports).
- Для signal generation — **closed kline** event (`x: true`).

### Authentication

```
signature = HMAC_SHA256(queryString, secretKey)
Header: X-MBX-APIKEY: <apiKey>
```

Timestamp и `recvWindow` — см. official docs; clock skew ломает подпись.

---

## Order types на Binance Spot (overview)

| Type | Use |
|------|-----|
| LIMIT | TP, maker entries |
| MARKET | Fast entry/exit, slippage risk |
| STOP_LOSS / STOP_LOSS_LIMIT | SL |
| TAKE_PROFIT / TAKE_PROFIT_LIMIT | TP |
| OCO | SL + TP linked |

Детали enum — [Binance New Order](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade).

---

## Примеры

### Пример 1: Testnet workflow

Developer создаёт testnet keys на [testnet.binance.vision](https://testnet.binance.vision/) → n8n `BINANCE_ENV=testnet` → все orders на virtual balance → логи в Obsidian `paper_trades/`.

### Пример 2: IP whitelist

Production key restricted to home server IP → stolen key useless from other IP (не panacea, но layer).

### Пример 3: Withdraw scam

Attacker получает key **with withdraw** → drains account. **Policy:** withdraw permission **disabled** forever on bot keys.

### Пример 4: Rate limit storm

Loop bug sends 1000 req/min → ban 418/429 → missed SL. Fix: exponential backoff + central rate limiter Code node.

---

## Частые ошибки новичков

1. **API keys в GitHub** — instant drain bots scanning repos.
2. **Withdraw enabled on bot key** — unnecessary attack surface.
3. **Production keys on testnet URL** — confusing errors / wrong account.
4. **MARKET order на illiquid pair** — extreme slippage.
5. **Игнор MIN_NOTIONAL / LOT_SIZE** — rejected orders.
6. **Один API key для dev и prod** — невозможно rotate safely.

---

## FAQ

### Binance legal in my country?

Availability меняется; проверяйте ToS и local law ([[Crypto_regulation_RU]] для РФ). Automation не обходит geo blocks.

### Testnet = real market prices?

Prices similar but **liquidity fake**; slippage behavior differs. Testnet validates **code path**, not PnL realism.

### DEX для automation?

Possible (Uniswap SDK, etc.) but higher complexity (gas, MEV, nonce). Project default — CEX.

### Как хранить secret?

n8n Credentials encrypted at rest; не в Obsidian markdown.

### WebSocket vs REST polling?

WS для klines realtime; REST для account/orders. Hybrid — standard.

---

## Проверенные источники

1. **[Binance Spot API Documentation](https://developers.binance.com/docs/binance-spot-api-docs/rest-api)**
2. **[Binance Spot Testnet](https://testnet.binance.vision/)**
3. **[Investor.gov: Crypto risks](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)**
4. **[FATF: Virtual Assets](https://www.fatf-gafi.org/en/topics/virtual-assets.html)**
5. **[Binance Academy: What is a CEX](https://academy.binance.com/en/articles/what-is-a-cex)**

---

## Академические источники

Полный свод университетских курсов и научных публикаций (2021+) — в заметке [[Academic_sources]].

| Учреждение | Ресурс (2021+) | Что подтверждает для этой темы | Ссылка |
|-----------|----------------|--------------------------------|--------|
| BIS | Paper 156 (2024) — Crypto, DeFi | CEX/DEX, DeFi-протоколы, риски централизованных бирж | [www.bis.org/publ/bppdf/bispap156.pdf](https://www.bis.org/publ/bppdf/bispap156.pdf) |
| BIS | Paper 159 (2024) — CBDC survey | Регуляторный контекст цифровых активов и бирж | [www.bis.org/publ/bppdf/bispap159.htm](https://www.bis.org/publ/bppdf/bispap159.htm) |
| BIS | Working Paper 1146 (2023) — Stablecoins | Роль stablecoins на криптобиржах, риски ликвидности | [www.bis.org/publ/work1146.pdf](https://www.bis.org/publ/work1146.pdf) |
| ВШЭ | Dobrynskaya & Dubrovskiy — BRP 86/FE/2022 | Криптоактивы на биржах: pricing и risk factors | [wp.hse.ru/fe/BRP/86/2022](https://wp.hse.ru/fe/BRP/86/2022) |

---

## В автоматической системе

### Environment switch

```javascript
const env = $env.BINANCE_ENV || 'testnet';
const baseUrl = env === 'production'
  ? 'https://api.binance.com'
  : 'https://testnet.binance.vision';
const wsBase = env === 'production'
  ? 'wss://stream.binance.com:9443'
  : 'wss://testnet.binance.vision';
return [{ json: { baseUrl, wsBase, env } }];
```

### n8n workflow map

| Workflow | Trigger | Exchange action |
|----------|---------|-----------------|
| `crypto-klines-ws` | WebSocket | Subscribe BTCUSDT 4h kline |
| `crypto-signal-flow` | Kline close | Indicators → LLM → order |
| `crypto-reconcile` | Cron 1h | Balance vs expected positions |
| `crypto-key-rotate-reminder` | Cron 90d | Telegram admin |

### Security checklist

```yaml
api_key_permissions:
  read: true
  spot_trade: true
  margin: false
  futures: false
  withdraw: false
ip_whitelist: true
2fa_account: true
subaccount_isolated: recommended
```

### Signed order (pseudo)

```
POST /api/v3/order
symbol=BTCUSDT&side=BUY&type=LIMIT&timeInForce=GTC
&quantity=0.001&price=60000&timestamp=...&signature=...
```

Quantity/price — после `LOT_SIZE` / `PRICE_FILTER` from `exchangeInfo`.

### Error handling

| Code | Action |
|------|--------|
| -1021 | Sync NTP time |
| -2010 | Insufficient balance → halt |
| 429 | Backoff |
| -1013 | Filter failure → fix rounding |

### Reconciliation

```
expected_btc = sum(trades) - fees
actual_btc = account API
IF abs(diff) > epsilon → CRITICAL Telegram
```

### Obsidian

```yaml
exchange: binance
env: testnet
last_reconcile: 2026-07-05T12:00:00Z
pairs: [BTCUSDT]
docs: https://developers.binance.com/docs/binance-spot-api-docs/rest-api
```

---

## Связанные темы

- [[Crypto_basics]]
- [[Binance_API]]
- [[Order_types]]
- [[Stop_loss_take_profit]]
- [[Crypto_flow_design]]
- [[Crypto_regulation_RU]]

---

## Maker vs Taker fees

| Role | Описание | Impact on bots |
|------|----------|----------------|
| **Maker** | Добавляет liquidity (limit not crossing spread) | Lower fee tier |
| **Taker** | Забирает liquidity (market / aggressive limit) | Higher fee |

High-frequency strategies должны моделировать fees в backtest — Binance fee schedule в official docs (verify VIP tier).

---

## Sub-accounts и isolation

Binance supports **sub-accounts** для separation:

- Subaccount A: live bot spot only.
- Subaccount B: manual trading.

Limits blast radius при key compromise. API key scoped to subaccount.

---

## Geo-blocking и compliance

Exchanges enforce **restricted jurisdictions** in ToS. Automation server IP и KYC residency должны соответствовать ToS — обход geo-block нарушает terms и может freeze funds.

---

### Rate limit budget (example)

| Endpoint | Weight | Max/min |
|----------|--------|---------|
| GET /api/v3/klines | 2 | per IP limits |
| POST /api/v3/order | 1 | per account |

Centralize requests через single n8n «rate limiter» Code node with token bucket — prevents 429 during volatile sessions.

---

## Incident response playbook

1. **Unexpected balance drop** → halt all workflows, revoke API key on Binance.
2. **429 storm** → exponential backoff 1m/5m/15m.
3. **Open position no SL** → emergency market close workflow.
4. Document incident in Obsidian `incidents/`.
5. Post-mortem within 24h — update [[LLM_rules_and_guardrails]] if needed.

---

## Практический чеклист API setup

1. Create testnet account: [testnet.binance.vision](https://testnet.binance.vision/).
2. Generate HMAC keys; label `n8n-testnet-read-trade`.
3. Confirm **withdraw disabled**.
4. IP whitelist production keys.
5. Run `GET /api/v3/exchangeInfo` — cache LOT_SIZE filters.
6. Subscribe WS `btcusdt@kline_4h` — verify closed candle events.
7. Document in Obsidian `exchange_setup.md`.

---

## Расширенный FAQ

### Paper trading без testnet?

Possible via simulated Code node — **inferior** to testnet for API integration bugs.

### Binance US vs Binance.com?

Separate entities and APIs; project docs assume **.com** — verify your jurisdiction.

### WebSocket user data stream?

Listen key for execution reports — rotate before expiry ([Binance docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api)).

---

## Упражнение

Order rejected `-1013 LOT_SIZE`. Какие два поля проверить в `exchangeInfo` для BTCUSDT? (`LOT_SIZE.minQty`, `LOT_SIZE.stepSize`.)

---

## Что изучить дальше

1. [[Binance_API]] — детальные endpoints проекта.
2. [[Stop_loss_take_profit]] — OCO implementation.
3. [[Crypto_indicators]] — signal from klines.
4. [[LLM_rules_and_guardrails]] — no withdraw, no leverage by default.
