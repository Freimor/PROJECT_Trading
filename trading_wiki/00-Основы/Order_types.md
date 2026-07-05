---
title: Типы заявок
tags: [основы, ордера, исполнение]
sources:
  - https://www.finra.org/investors/investing/investment-products/stocks/order-types
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15
  - https://www.sec.gov/answers/limit.htm
  - https://www.moex.com/s1167
  - https://tinkoff.github.io/investAPI/orders/
updated: 2026-07-05
level: beginner
---

# Типы заявок

> **Заявка (order)** — инструкция брокеру или бирже купить или продать актив на определённых условиях: **количество**, **цена**, **срок действия** и **тип исполнения**. Правильный выбор типа заявки влияет на цену входа, риск проскальзывания и вероятность исполнения.

---

## Для новичка

### Что происходит, когда вы нажимаете «Купить»?

Биржа получает **инструкцию**. Она должна понять:

1. **Сколько** — количество лотов/акций;
2. **По какой цене** — любой (market) или не хуже заданной (limit);
3. **Когда** — сейчас, до конца сессии, до отмены;
4. **При каком условии** — например, «если цена упадёт до X» (stop).

От ответов зависит **тип заявки**. SEC и FINRA подчёркивают: **набор доступных типов зависит от брокера и биржи** — всегда проверяйте у своего брокера.

### Market order — «купить/продать сейчас»

**Рыночная заявка** — купить или продать по **лучшей доступной цене** прямо сейчас.

- **Плюс:** высокая вероятность **исполнения**.
- **Минус:** цена **не гарантирована**; в быстром рынке возможно **проскальзывание**.

FINRA: market order — **самый распространённый** тип; брокеры часто отправляют заявку как market, если вы не указали иное ([FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types)).

SEC: market order **обычно исполняется немедленно**, но цена может **отличаться** от last-traded price ([Investor Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)).

### Limit order — «только по моей цене или лучше»

**Лимитная заявка** — купить **не дороже** или продать **не дешевле** указанной **limit price**.

- **Buy limit** исполняется **на limit price или ниже**;
- **Sell limit** — **на limit price или выше**.

SEC: если рынок **не достиг** limit price, заявка **может не исполниться** ([SEC: Limit Orders](https://www.sec.gov/answers/limit.htm)).

### Stop order — «активировать при достижении цены»

**Stop order (stop-loss)** — заявка активируется, когда цена достигает **stop price**, после чего становится **market order**.

- **Sell stop** — **ниже** текущей цены (ограничение убытка long);
- **Buy stop** — **выше** текущей цены (ограничение убытка short или вход на пробой).

FINRA: после срабатывания цена исполнения **может существенно отличаться** от stop price в волатильном рынке ([FINRA: Stop Orders](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)).

### Stop-limit — «стоп + контроль цены»

При достижении stop price заявка становится **limit order**, а не market. Контроль цены выше, но **исполнение не гарантировано** при быстром падении.

### Time in Force — как долго заявка «жива»

| Тип | Значение |
|-----|----------|
| **Day** | До конца торговой сессии |
| **GTC** | Good Till Cancelled — до отмены (если брокер поддерживает) |
| **IOC** | Immediate Or Cancel — исполнить сразу сколько возможно, остаток отменить |
| **FOK** | Fill Or Kill — исполнить полностью или отменить |

На криптобиржах IOC/FOK распространены; на MOEX — проверяйте API брокера ([T-Invest API](https://tinkoff.github.io/investAPI/orders/)).

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **Market order** — заявка купить/продать по **лучшей доступной цене**; исполнение **обычно немедленное**, но цена **не гарантирована**. | [SEC Investor Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| 2 | **Limit order** — buy limit исполняется **на limit price или ниже**; sell limit — **на limit price или выше**; исполнение **не гарантировано**. | [SEC: Limit Orders](https://www.sec.gov/answers/limit.htm) |
| 3 | FINRA: market order — **наиболее распространённый** тип; брокеры часто используют его **по умолчанию**, если не указано иное. | [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types) |
| 4 | FINRA: market order на US-рынке **обычно** исполняется около текущих bid/ask в **нормальные часы 9:30–16:00 Eastern Time**; вне сессии цена может сильно отличаться. | [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types) |
| 5 | **Stop order:** при достижении stop price заявка становится **market order**; sell stop — **ниже** текущей цены; buy stop — **выше**. | [SEC Investor Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| 6 | **Stop-limit order:** при stop price активируется **limit order**; исполнение только по limit price или лучше; **исполнение не гарантировано**. | [SEC Investor Bulletin 15](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15) |
| 7 | **Trailing stop** — stop price следует за рынком на заданном расстоянии (% или $); не все брокеры поддерживают. | [SEC Investor Bulletin 15](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15) |
| 8 | Stop, stop-limit и trailing stop **могут быть недоступны** у некоторых брокеров — проверяйте политику фирмы. | [SEC Investor Bulletin 15](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15) |
| 9 | **Основная сессия** акций MOEX (ТП): **10:00:00–18:54:59** МСК; аукцион открытия **09:50–09:59**, закрытия **18:55–18:59:30** (для бумаг без утренней сессии). | [MOEX: Расписание торгов](https://www.moex.com/s1167) |
| 10 | Заявки типа **Day** на MOEX действуют в рамках **торговой сессии**, в которой выставлены; между сессиями есть **перерывы** (1–2 сек), когда новые сделки невозможны. | [MOEX: Расписание торгов](https://www.moex.com/s1167) |

---

## Подробно

### Сравнение основных типов

| Тип | Приоритет | Гарантия цены | Гарантия исполнения |
|-----|-----------|---------------|---------------------|
| Market | Скорость | Нет | Высокая (при ликвидности) |
| Limit | Цена | Да (limit или лучше) | Нет |
| Stop → Market | Условие + скорость | Нет после активации | Высокая после trigger |
| Stop-limit | Условие + цена | Да после активации | Нет |

### Bid, Ask, Last, Spread

- **Bid** — лучшая цена, по которой покупатель готов купить;
- **Ask (offer)** — лучшая цена, по которой продавец готов продать;
- **Last** — цена последней сделки;
- **Spread** = Ask − Bid.

Market **buy** исполняется около **ask**; market **sell** — около **bid**. Last price **не обязательно** равна цене вашего market order ([SEC Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)).

### Partial fill (частичное исполнение)

Биржа может исполнить заявку **частично**, если в стакане недостаточно объёма по вашей цене. Остаток остаётся активным (для limit/GTC) или отменяется (FOK).

### Stop orders в волатильном рынке

FINRA предупреждает ([Stop Orders During Volatile Markets](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)):

- Stop → market может исполниться **значительно хуже** stop price;
- Краткосрочный «шум» может **случайно активировать** стоп;
- Stop-limit защищает от worst fill, но **может не исполниться** при gap down.

### Расписание MOEX и заявки Day

По [официальному расписанию MOEX](https://www.moex.com/s1167):

| Сессия | Время (МСК) | Примечание |
|--------|-------------|------------|
| Утренняя (доп.) | 06:50–09:49 | Не все бумаги |
| Основная | 09:50–18:59:30 | ТП 10:00–18:54:59 |
| Вечерняя (доп.) | 19:00:01–23:49:59 | Ряд инструментов |

Между сессиями — **перерывы** (09:49:59–09:50:00; 18:59:59–19:00:01), когда **новые сделки невозможны**.

### T-Invest API (российский брокер)

[T-Invest API](https://tinkoff.github.io/investAPI/orders/) поддерживает программное выставление:

- Лимитных заявок;
- Рыночных заявок;
- Стоп-заявок (stop orders);
- Отмену и статус (`FILLED`, `PARTIALLY_FILLED`, `REJECTED`).

Типы и enum **зависят от версии API** — проверяйте документацию перед автоматизацией.

---

## Ключевые понятия

| Термин | Определение |
|--------|-------------|
| **Market order** | Заявка по лучшей доступной цене |
| **Limit order** | Заявка по указанной цене или лучше |
| **Stop price** | Цена активации stop order |
| **Limit price** | Максимум (buy) или минимум (sell) для limit order |
| **Time in Force** | Срок действия заявки (Day, GTC, IOC, FOK) |
| **Partial fill** | Частичное исполнение |
| **Slippage** | Исполнение хуже ожидаемой цены |
| **GTC** | Good Till Cancelled |
| **Trailing stop** | Stop, следующий за ценой на заданном расстоянии |

---

## Примеры

### Пример 1: Limit buy

Акция: last = **100 ₽**, ask = **100,05 ₽**, bid = **99,95 ₽**.

Лимитная заявка: **Buy 100 шт. limit 98 ₽**.

```
Цена должна опуститься до 98 ₽ или ниже → исполнение
Пока ask = 100,05 → заявка НЕ исполняется
```

### Пример 2: Market buy и slippage

Market buy 500 шт. Стакан:

| Ask | Объём |
|-----|-------|
| 100,05 | 200 |
| 100,10 | 150 |
| 100,20 | 300 |

Исполнение: 200 @ 100,05 + 150 @ 100,10 + 150 @ 100,20. **Средняя цена выше** 100,05 — это slippage.

### Пример 3: Sell stop (stop-loss)

Купили по **250 ₽**. Stop sell **242,50 ₽**.

```
Цена падает → достигает 242,50 → активируется market sell
Фактическая цена может быть 242,30 или 241,00 (volatility)
```

### Пример 4: Stop-limit

Stop **242,50 ₽**, limit **242,00 ₽**.

```
При 242,50 → limit sell ≥ 242,00
Если gap через 242,00 без сделок → заявка НЕ исполняется, позиция открыта
```

### Пример 5: Day order на MOEX

Выставили limit buy **Day** в **17:00** МСК в основной сессии. Заявка активна до **18:54:59** (конец ТП). После — **автоматически снимается**, если не исполнена ([MOEX schedule](https://www.moex.com/s1167)).

### Пример 6: Расчёт стоимости с комиссией

Limit buy 100 акций @ **98 ₽** = 9 800 ₽. Комиссия брокера 0,04%:

```
Комиссия = 9 800 × 0.0004 = 3,92 ₽
Итого = 9 803,92 ₽
```

---

## Частые ошибки

1. **Market order «на всё»** — проскальзывание на крупных объёмах или illiquid активах.
2. **Limit слишком далеко от рынка** — заявка никогда не исполнится.
3. **Stop-limit без plan B** — при crash позиция «зависает» без выхода.
4. **Путать stop price и limit price** в stop-limit.
5. **Day order перед концом сессии** — не успевает исполниться (MOEX: проверяйте расписание).
6. **Игнорировать last vs ask/bid** — SEC: last ≠ guaranteed fill price для market.
7. **Trailing stop на illiquid** — stop может сработать на аномальном тике.
8. **Не проверять доступность типа у брокера** — SEC: не все брокеры поддерживают все типы.

---

## FAQ

### Market или limit для входа?

- **Market** — когда важна **скорость** (новость, breakout), допустимо slippage.
- **Limit** — когда важна **цена** (плановый вход, illiquid).
- Автоматическая система **предпочитает limit** для крупных позиций ([[LLM_rules_and_guardrails]]).

### Гарантирует ли limit точную цену?

**Да**, если исполнено — по limit **или лучше**. Но **исполнение не гарантировано** ([SEC](https://www.sec.gov/answers/limit.htm)).

### Чем stop отличается от stop-limit?

Stop → **market** после trigger (скорость > цена). Stop-limit → **limit** после trigger (цена > скорость).

### Работают ли stop orders вне сессии?

На MOEX — в рамках **торговых сессий**. Заявки, выставленные вне сессии, могут быть **отклонены** или **активированы** при открытии — проверяйте брокера.

### Какие типы поддерживает Binance?

Spot API: `LIMIT`, `MARKET`, `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT` — см. [Binance Spot API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade).

### Можно ли отменить заявку?

Да, пока она **не исполнена** полностью. Через интерфейс брокера или API (`cancelOrder`).

---

## Проверенные источники

1. **[Order Types — FINRA](https://www.finra.org/investors/investing/investment-products/stocks/order-types)** — market (default, 9:30–16:00 ET), limit, stop, stop-limit; bid/ask execution; риски market в fast markets.
2. **[Investor Bulletin: Understanding Order Types — SEC/OIEA](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)** — market, limit, stop, stop-limit, trailing stop; last price ≠ fill price; различия между брокерами.
3. **[Investor Bulletin: Stop, Stop-Limit, Trailing Stop — SEC/OIEA](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15)** — buy stop vs sell stop, stop-limit mechanics, availability у брокеров.
4. **[Limit Orders — SEC.gov](https://www.sec.gov/answers/limit.htm)** — buy limit ≤ limit price; sell limit ≥ limit price; no execution guarantee.
5. **[Stop Orders: Volatile Markets — FINRA](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)** — slippage после stop trigger, stop-limit trade-offs.
6. **[Расписание торгов — MOEX](https://www.moex.com/s1167)** — сессии, аукционы, перерывы, Day order context.
7. **[T-Invest API: Orders](https://tinkoff.github.io/investAPI/orders/)** — программные заявки для MOEX через брокера T-Bank.

---

## В автоматической системе

### Архитектурное правило

Автоматизация **предпочитает limit** и **stop-limit** — предсказуемее для риск-менеджмента. Market — только для **малых** позиций или **emergency flatten**.

```yaml
# Пример конфигурации ордера (Crypto flow)
order:
  type: limit
  side: buy
  price_source: last_close * 0.998
  time_in_force: GTC
  stop_loss:
    type: stop_limit
    trigger: entry_price * 0.97
    limit: entry_price * 0.965
```

### n8n pipeline

1. **Code node** — расчёт `limit_price`, `stop_price` из [[Position_sizing]] и ATR.
2. **HTTP Request** — POST `/order` (Binance или T-Invest API).
3. **Wait + Poll** — статус `FILLED` / `PARTIALLY_FILLED` / `REJECTED`.
4. **IF rejected** → Telegram alert + запись в Obsidian journal.
5. **IF partial** → решение: дождаться fill или отменить остаток.

### Code node: округление к tick size

```javascript
function roundTick(price, tick) {
  return Math.round(price / tick) * tick;
}
const limitPrice = roundTick(lastClose * 0.998, tickSize);
```

### LLM guardrails

Правило [[LLM_rules_and_guardrails]]: LLM **не выбирает market** для позиций > `config.max_market_order_notional`. Только limit или stop-limit.

### Session-aware scheduling (MOEX)

```javascript
// Проверка перед отправкой Day order
const moscow = DateTime.now().setZone('Europe/Moscow');
const sessionEnd = moscow.set({ hour: 18, minute: 54, second: 59 });
if (order.time_in_force === 'DAY' && moscow > sessionEnd.minus({ minutes: 5 })) {
  return { reject: true, reason: 'Слишком поздно для Day order — см. MOEX schedule' };
}
```

### Журнал

```yaml
order_id: "2026-07-05-btc-limit-001"
type: limit
side: buy
limit_price: 59880
time_in_force: GTC
status: FILLED
fill_price: 59850
slippage: -30
sources: [finra-order-types, sec-bulletin-14]
```

---

## Связанные темы

- [[Stop_loss_take_profit]]
- [[What_is_trading]]
- [[MOEX_stocks]]
- [[Binance_API]]
- [[Tinkoff_Invest_API]]
- [[Position_sizing]]

---

## Что изучить дальше

1. [[Stop_loss_take_profit]] — применение stop и limit для выхода.
2. [[Position_sizing]] — объём заявки и риск.
3. [[MOEX_stocks]] — лоты, шаг цены, режимы торгов MOEX.
4. [[Binance_API]] — типы ордеров на криптобирже.
5. [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types) — полный обзор для US-рынка.
6. [MOEX: Расписание торгов](https://www.moex.com/s1167) — когда действуют Day-заявки.
