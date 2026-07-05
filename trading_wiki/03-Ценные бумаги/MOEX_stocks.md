---
title: Акции на MOEX
tags: [ценные бумаги, MOEX, акции, T+1, ликвидность]
sources:
  - https://www.moex.com/s1160
  - https://www.moex.com/a6231
  - https://iss.moex.com/iss/reference/
  - https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks
  - https://tinkoff.github.io/investAPI/
updated: 2026-07-05
level: beginner
---

# Акции на MOEX

> **Московская биржа (MOEX)** — крупнейшая площадка для торговли российскими акциями, облигациями и деривативами. **Акция** — доля в компании с правами на дивидendы и участие в росте капитализации (с учётом класса акций и corporate actions).

---

## Для новичка

Чтобы купить акцию (например, тикер **SBER**, **LKOH** — проверяйте актуальный листинг на MOEX):

1. Открыть **брокерский счёт** у лицензированного брокера (ЦБ РФ).
2. Внести **денежные средства**.
3. Подать **заявку** — market/limit через приложение или API.

Вы **не** покупаете напрямую у MOEX — биржа matching orders участников через **брокеров** и **участников торгов**.

**IMOEX** ([moex.com/a6231](https://www.moex.com/a6231)) отражает basket наиболее ликвидных крупных акций — см. [[IMOEX_RTS]].

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **IMOEX** рассчитывается **09:50–19:00** MSK, free-float cap-weighted; ребаланс **3-я пятница** мар/июн/сен/дек; лимиты **15%** / **55%**. | [MOEX Indices](https://www.moex.com/a6231) |
| 2 | Расписание торговых сессий MOEX публикуется на официальном сайте (календарь и режимы). | [MOEX: Trading calendar](https://www.moex.com/s1160) |
| 3 | **MOEX ISS** — бесплатный Information & Statistical Server для котировок, истории, стаканов. | [MOEX ISS Reference](https://iss.moex.com/iss/reference/) |
| 4 | SEC Investor.gov: **stock** represents ownership share in corporation; stock prices **fluctuate**. | [Investor.gov: Stocks](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) |
| 5 | T-Invest API (T-Bank) документирует programmatic trading на MOEX через брокера. | [T-Invest API](https://tinkoff.github.io/investAPI/) |
| 6 | Индекс IMOEX first calculated **22.09.1997**, base **100**. | [MOEX Indices](https://www.moex.com/a6231) |

---

## Торговые сессии (ориентир)

| Режим | Время (МСК) | Примечание |
|-------|-------------|------------|
| Аукцион открытия | ~09:50–10:00 | Определение opening price |
| Основная сессия | ~10:00–18:50 | Непрерывные торги |
| Аукцион закрытия | ~18:50–19:00 | Closing price |
| Расчёт IMOEX | 09:50–19:00 | Совпадает с расширенным окном индекса |

**Точное расписание** — только [moex.com/s1160](https://www.moex.com/s1160); при automation проверяйте **праздники** (ISS calendar).

---

## Ключевые понятия

### Тикер и ISIN

- **Тикер (SECID)** — короткий код на MOEX (SBER, GAZP).
- **ISIN** — международный идентификатор (RU0009029540 и др.).

API и отчёты брокера могут использовать разные поля — mapping в `instruments.yaml`.

### Лот (lot size)

Минимальное количество акций в одной заявке. Заявка `quantity=1` при lot=10 → reject.

### T+1 settlement

Расчёты по сделке — **на следующий рабочий день** (режим может уточняться биржей — проверяйте актуальные правила MOEX). **Free cash** для новой покупки — учитывайте unsettled funds.

### Дивидendы

Компания может выплатить **дивидend** — calendar на сайте эмитента / MOEX. **Ex-dividend date** — после неё покупатель не получает ближайший dividend; цена часто корректируется.

### Спред и ликвидность

**Bid-ask spread** — разница лучшей покупки и продажи. Для automation предпочтительны бумаги из **IMOEX** с высоким дневным объёмом.

---

## Классы акций

| Тип | Права | Пример (иллюстрация) |
|-----|-------|----------------------|
| Обыкновенные | Голос + дивидend (по charter) | SBER |
| Привилегированные | Приоритет дивидend, ограниченное голосование | SBERP |

Права — **устав** и disclosure эмитента, не wiki.

---

## Связь с IMOEX

Бумаги входят в IMOEX если удовлетворяют **liquidity + capitalization + free-float** criteria methodology MOEX. Вес ограничен **15%** на одну бумагу, **55%** на топ-5.

После **реконституции** (3-я пятница квартала) состав меняется — automation whitelist обновлять из ISS.

---

## Примеры

### Пример 1: Limit buy SBER

Investor: limit 250 ₽, 100 акций (проверить lot). Исполнение только если ask ≤ 250 ₽. Неисполненный остаток висит в стакане.

### Пример 2: Фильтр ликвидности bot

```
avg_volume_20d > 100_000_000 RUB
AND spread_pct < 0.1
AND secid in imoex_constituents
```

### Пример 3: Торговля вне сессии

Заявка ночью — **не исполнится** до открытия (или queued per broker rules). Cron n8n **only** 09:55–18:45 MSK.

### Пример 4: Падение IMOEX −3%

Macro filter блокирует новые long по mid-cap, но **не** отменяет существующие SL.

---

## Частые ошибки новичков

1. **Market order на неликвид** — slippage на wide spread.
2. **Игнор lot size** — rejected orders в API loop.
3. **Торговля без учёта T+1** — insufficient funds.
4. **Путать тикеры одной компании** (SBER vs SBERP).
5. **Не обновлять whitelist после ребаланса IMOEX**.
6. **Забыть налоги** — [[Russia_tax_basics]].

---

## FAQ

### MOEX ISS бесплатен?

Да для market data в рамках ISS; commercial redistribution — license MOEX.

### Какой API для ордеров?

T-Invest API, другие брокеры — см. [[Tinkoff_Invest_API]]. MOEX ISS **не** исполняет сделки.

### Все акции MOEX в рублях?

Большинство RUB; есть USD/CNY listings — проверять board.

### Short selling?

Доступен qualified investors / margin rules broker — отдельный risk.

### Как узнать состав IMOEX?

MOEX factsheet + ISS analytics endpoint.

---

## Проверенные источники

1. **[MOEX Trading calendar](https://www.moex.com/s1160)**
2. **[MOEX Indices — IMOEX](https://www.moex.com/a6231)**
3. **[MOEX ISS API Reference](https://iss.moex.com/iss/reference/)**
4. **[Investor.gov: Stocks](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks)**
5. **[T-Invest API](https://tinkoff.github.io/investAPI/)**

---

## В автоматической системе

### Architecture `moex-securities-flow`

```
Cron (every 15 min, session window MSK)
  → MOEX ISS: candles + optional orderbook
  → macro-context: IMOEX change from moex-index-monitor
  → Code: indicators + liquidity filter
  → Ollama: approve/reject
  → T-Invest API: postOrder
  → Obsidian: trades/YYYY-MM-DD.md
```

### MOEX ISS examples

**Daily candles SBER:**

```
GET https://iss.moex.com/iss/engines/stock/markets/shares/securities/SBER/candles.json?interval=24&from=2026-01-01
```

**IMOEX constituents analytics:**

```
GET https://iss.moex.com/iss/statistics/engines/stock/markets/index/analytics/IMOEX.json
```

**Trading calendar:**

```
GET https://iss.moex.com/iss/engines/stock/markets/shares/dates.json
```

### Session gate (Code)

```javascript
const now = new Date();
const msk = new Date(now.toLocaleString('en-US', { timeZone: 'Europe/Moscow' }));
const h = msk.getHours(), m = msk.getMinutes();
const mins = h * 60 + m;
const open = 9 * 60 + 55;   // buffer after 09:50
const close = 18 * 60 + 45;
const inSession = mins >= open && mins <= close && [0,1,2,3,4].includes(msk.getDay());
return [{ json: { inSession, trade_allowed: inSession && !$json.holiday } }];
```

### T-Invest order (conceptual)

```
POST OrdersService/PostOrder
figi / instrument_id, quantity, direction, order_type, account_id
```

Map SECID → instrument_id via broker instruments sync (daily cron).

### Liquidity filter

```yaml
min_avg_volume_20d_rub: 50000000
max_spread_pct: 0.15
constituents_only: true  # IMOEX whitelist
```

### LLM context

```yaml
secid: LKOH
imoex_change_pct: -1.2
liquidity_score: high
position_risk_pct: 1.0
rules: no_trade_if_imoex_down_2pct
```

### vs crypto-flow

| | MOEX stocks | Crypto |
|---|-------------|--------|
| Hours | Session MSK | 24/7 |
| Settlement | T+1 | Instant |
| Data API | MOEX ISS free | Binance |
| Execution | Broker API | Exchange API |
| Index | IMOEX 09:50–19:00 | BTC benchmark |

### Obsidian trade log

```yaml
trade_id: moex-2026-07-05-001
secid: SBER
side: BUY
qty: 100
entry: 250.00
stop: 242.50
broker: tinkoff
sources: [moex.com/s1160, moex.com/a6231]
```

---

## Связанные темы

- [[IMOEX_RTS]]
- [[MOEX_ISS_API]]
- [[Tinkoff_Invest_API]]
- [[Order_types]]
- [[Stop_loss_take_profit]]
- [[Securities_flow_design]]
- [[Russia_tax_basics]]

---

## Corporate actions

| Event | Effect on holder |
|-------|------------------|
| **Stock split** | Больше акций, lower price per share |
| **Reverse split** | Меньше акций, higher price |
| **Dividend** | Cash payment; ex-date price adjustment |
| **Delisting** | Liquidity crisis — automation must halt |

MOEX ISS и broker API публикуют corporate action feeds — sync weekly.

---

## Уровни листинга и режимы

MOEX имеет разные **boards** (TQBR и др.) — listing requirements differ. Illiquid small caps могут быть **не** в IMOEX. Whitelist automation = **IMOEX constituents** by default.

---

### Broker sync job

```
Cron daily 08:00 MSK
  → T-Invest: GetInstruments(all)
  → Filter MOEX shares
  → Update instruments.yaml: secid, figi, lot, min_price_increment
  → Diff vs yesterday → Telegram if new/delisted
```

Prevents order rejects from stale figi after corporate actions.

---

## Order book basics (MOEX)

**Bid** — highest buy; **Ask** — lowest sell. **Depth** — volume at levels. ISS `/orderbook` endpoints for liquid names — use for spread filter, not HFT without colocation.

### T+1 и buying power

После покупки на сумму X **unsettled** до T+1 — следующая покупка должна учитывать `available_balance` из broker API, не total equity.

---

## Практический чеклист MOEX equity trader

1. Verify session on [moex.com/s1160](https://www.moex.com/s1160) (holidays).
2. Sync instrument lot/figi from broker daily.
3. Load IMOEX weights from ISS after each rebalance.
4. Set session gate in n8n (09:55–18:45 MSK).
5. Paper trade via broker sandbox if available.
6. Log every fill with SECID + ISIN.

---

## Расширенный FAQ

### Голосование по акциям?

Shareholder meetings — corporate governance; не влияет на intraday bot unless major event in news feed.

### ADR/GDR vs MOEX local?

Different instruments; automation scope — local MOEX tickers unless explicitly configured.

### Margin и short?

Requires broker agreement; default `moex-securities-flow` — **cash long only**.

---

## Упражнение

IMOEX down 2,5% от open. Rule `no_trade_if_imoex_down_2pct` active. Signal on LKOH long appears. Action? (Block new entry; existing positions follow SL/TP rules.)

---

## Что изучить дальше

1. [[IMOEX_RTS]] — benchmark и реконституция.
2. [[MOEX_ISS_API]] — полный справочник ISS.
3. [[ETFs_and_funds]] — БПИФ вместо отдельных акций.
4. [[Stop_loss_take_profit]] — SL через T-Invest.
