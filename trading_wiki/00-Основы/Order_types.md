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
  - https://www.nber.org/papers/w28515
  - https://www.gsb.stanford.edu/experience/learning/experiential-learning/rail/curricular-integration
  - https://wp.hse.ru/en/prepfr_FE
updated: 2026-07-06
level: beginner
academic_sources: true
style: informational
---

# Типы заявок

> Заявка (order) — инструкция брокеру купить или продать актив: сколько, по какой цене, как долго и при каком условии. От типа зависят цена входа, риск проскальзывания и шанс исполнения.

## Главное

- Market order — купить/продать сейчас по лучшей цене; исполнение вероятно, цена — нет.
- Limit order — только по вашей цене или лучше; цена контролируется, исполнение не гарантировано.
- Stop order активируется при достижении stop price и становится market; в волатильности цена может сильно отличаться.
- Stop-limit после активации — limit: контроль цены, но при gap заявка может не исполниться.
- Набор типов зависит от брокера и биржи — всегда проверяйте у своего.

---

## Для новичка

### Что происходит при нажатии «Купить»

Биржа получает инструкцию: сколько купить, по какой цене (любой или не хуже заданной), когда (сейчас, до конца сессии, до отмены), при каком условии (например, если цена упадёт до X).

SEC и FINRA: доступные типы зависят от брокера и биржи.

### Market order

Рыночная заявка — купить или продать по лучшей доступной цене сейчас.

Плюс: высокая вероятность исполнения. Минус: цена не гарантирована, возможно проскальзывание.

FINRA: market order — самый распространённый тип; брокеры часто используют его по умолчанию ([FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types)).

SEC: обычно исполняется немедленно, но цена может отличаться от last-traded price ([Investor Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)).

### Limit order

Лимитная заявка — купить не дороже или продать не дешевле указанной limit price.

Buy limit исполняется на limit price или ниже; sell limit — на limit price или выше.

SEC: если рынок не достиг limit price, заявка может не исполниться ([SEC: Limit Orders](https://www.sec.gov/answers/limit.htm)).

### Stop order

Stop order (stop-loss) активируется при достижении stop price, затем становится market order.

Sell stop — ниже текущей цены (ограничение убытка long). Buy stop — выше (вход на пробой или защита short).

FINRA: после срабатывания цена может существенно отличаться от stop price ([FINRA: Stop Orders](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)).

### Stop-limit

При достижении stop price заявка становится limit, не market. Контроль цены выше, исполнение не гарантировано при быстром падении.

### Time in Force

| Тип | Значение |
|-----|----------|
| Day | До конца торговой сессии |
| GTC | Good Till Cancelled — до отмены |
| IOC | Immediate Or Cancel — исполнить сразу сколько возможно |
| FOK | Fill Or Kill — полностью или отменить |

На криптобиржах IOC/FOK распространены; на MOEX — проверяйте API брокера ([T-Invest API](https://tinkoff.github.io/investAPI/orders/)).

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | Market order — купить/продать по лучшей доступной цене; исполнение обычно немедленное, цена не гарантирована. | [SEC Investor Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| 2 | Limit order: buy limit на limit price или ниже; sell limit на limit price или выше; исполнение не гарантировано. | [SEC: Limit Orders](https://www.sec.gov/answers/limit.htm) |
| 3 | FINRA: market order — наиболее распространённый тип; брокеры часто используют по умолчанию. | [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types) |
| 4 | FINRA: market order на US-рынке обычно исполняется около bid/ask в 9:30–16:00 ET; вне сессии цена может сильно отличаться. | [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types) |
| 5 | Stop order: при stop price заявка становится market; sell stop ниже текущей цены, buy stop выше. | [SEC Investor Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| 6 | Stop-limit: при stop price активируется limit order; исполнение только по limit price или лучше; не гарантировано. | [SEC Investor Bulletin 15](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15) |
| 7 | Trailing stop — stop price следует за рынком на заданном расстоянии; не все брокеры поддерживают. | [SEC Investor Bulletin 15](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15) |
| 8 | Stop, stop-limit и trailing stop могут быть недоступны у некоторых брокеров. | [SEC Investor Bulletin 15](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15) |
| 9 | Основная сессия акций MOEX (ТП): 10:00:00–18:54:59 МСК; аукцион открытия 09:50–09:59, закрытия 18:55–18:59:30. | [MOEX: Расписание торгов](https://www.moex.com/s1167) |
| 10 | Заявки Day на MOEX действуют в рамках сессии, в которой выставлены; между сессиями перерывы 1–2 сек. | [MOEX: Расписание торгов](https://www.moex.com/s1167) |

---

## Подробно

### Сравнение типов

| Тип | Приоритет | Гарантия цены | Гарантия исполнения |
|-----|-----------|---------------|---------------------|
| Market | Скорость | Нет | Высокая (при ликвидности) |
| Limit | Цена | Да (limit или лучше) | Нет |
| Stop → Market | Условие + скорость | Нет после активации | Высокая после trigger |
| Stop-limit | Условие + цена | Да после активации | Нет |

### Bid, Ask, Last, Spread

- Bid — лучшая цена покупателя; Ask — лучшая цена продавца.
- Last — цена последней сделки; Spread = Ask − Bid.

Market buy исполняется около ask; market sell — около bid. Last price не обязательно равна цене вашего market order ([SEC Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)).

### Partial fill

Биржа может исполнить заявку частично. Остаток остаётся активным (limit/GTC) или отменяется (FOK).

### Stop orders в волатильном рынке

FINRA ([Stop Orders During Volatile Markets](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)):

- Stop → market может исполниться значительно хуже stop price.
- Краткосрочный шум может случайно активировать стоп.
- Stop-limit защищает от worst fill, но может не исполниться при gap down.

### Расписание MOEX и Day order

| Сессия | Время (МСК) | Примечание |
|--------|-------------|------------|
| Утренняя | 06:50–09:49 | Не все бумаги |
| Основная | 09:50–18:59:30 | ТП 10:00–18:54:59 |
| Вечерняя | 19:00:01–23:49:59 | Ряд инструментов |

Между сессиями — перерывы, когда новые сделки невозможны.

### T-Invest API

[T-Invest API](https://tinkoff.github.io/investAPI/orders/) поддерживает лимитные, рыночные, стоп-заявки, отмену и статус (`FILLED`, `PARTIALLY_FILLED`, `REJECTED`). Типы зависят от версии API.

---

## Ключевые понятия

| Термин | Определение |
|--------|-------------|
| Market order | Заявка по лучшей доступной цене |
| Limit order | Заявка по указанной цене или лучше |
| Stop price | Цена активации stop order |
| Limit price | Максимум (buy) или минимум (sell) для limit order |
| Time in Force | Срок действия заявки (Day, GTC, IOC, FOK) |
| Partial fill | Частичное исполнение |
| Slippage | Исполнение хуже ожидаемой цены |
| GTC | Good Till Cancelled |
| Trailing stop | Stop, следующий за ценой на заданном расстоянии |

---

## Примеры

### Пример 1: Limit buy

Акция: last = 100 ₽, ask = 100,05 ₽, bid = 99,95 ₽. Buy 100 шт. limit 98 ₽ — исполнение, когда ask ≤ 98 ₽.

### Пример 2: Market buy и slippage

Market buy 500 шт. при стакане 100,05 (200) / 100,10 (150) / 100,20 (300) — средняя цена выше 100,05.

### Пример 3: Sell stop (stop-loss)

Купили по 250 ₽. Stop sell 242,50 ₽ — при достижении активируется market sell; фактическая цена может быть 242,30 или 241,00.

### Пример 4: Stop-limit

Stop 242,50 ₽, limit 242,00 ₽. При gap через 242,00 без сделок — заявка не исполняется, позиция открыта.

### Пример 5: Day order на MOEX

Limit buy Day в 17:00 МСК активна до 18:54:59. После — снимается, если не исполнена ([MOEX schedule](https://www.moex.com/s1167)).

### Пример 6: Стоимость с комиссией

Limit buy 100 акций @ 98 ₽ = 9 800 ₽. Комиссия 0,04%: 9 800 × 0.0004 = 3,92 ₽. Итого 9 803,92 ₽.

---

## Частые ошибки

1. Market order «на всё» — проскальзывание на крупных объёмах.
2. Limit слишком далеко от рынка — заявка не исполнится.
3. Stop-limit без plan B — при crash позиция «зависает».
4. Путать stop price и limit price в stop-limit.
5. Day order перед концом сессии — не успевает исполниться.
6. Игнорировать last vs ask/bid — last ≠ guaranteed fill price.
7. Trailing stop на illiquid — срабатывание на аномальном тике.
8. Не проверять доступность типа у брокера.

---

## FAQ

### Market или limit для входа?

Market — когда важна скорость. Limit — когда важна цена. Автоматическая система предпочитает limit для крупных позиций ([[LLM_rules_and_guardrails]]).

### Гарантирует ли limit точную цену?

Да, если исполнено — по limit или лучше. Исполнение не гарантировано ([SEC](https://www.sec.gov/answers/limit.htm)).

### Чем stop отличается от stop-limit?

Stop → market после trigger (скорость > цена). Stop-limit → limit после trigger (цена > скорость).

### Работают ли stop orders вне сессии?

На MOEX — в рамках торговых сессий. Проверяйте брокера.

### Какие типы поддерживает Binance?

Spot API: `LIMIT`, `MARKET`, `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT` — [Binance Spot API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade).

### Можно ли отменить заявку?

Да, пока не исполнена полностью. Через интерфейс брокера или API (`cancelOrder`).

---

## Проверенные источники

1. **[Order Types — FINRA](https://www.finra.org/investors/investing/investment-products/stocks/order-types)**
2. **[Investor Bulletin: Understanding Order Types — SEC/OIEA](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)**
3. **[Investor Bulletin: Stop, Stop-Limit, Trailing Stop — SEC/OIEA](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15)**
4. **[Limit Orders — SEC.gov](https://www.sec.gov/answers/limit.htm)**
5. **[Stop Orders: Volatile Markets — FINRA](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)**
6. **[Расписание торгов — MOEX](https://www.moex.com/s1167)**
7. **[T-Invest API: Orders](https://tinkoff.github.io/investAPI/orders/)**

---

## Академические источники

Полный свод университетских курсов и научных публикаций (2021+) — в заметке [[Academic_sources]].

| Учреждение | Ресурс (2021+) | Что подтверждает для этой темы | Ссылка |
|-----------|----------------|--------------------------------|--------|
| NBER | Li, Ye, Zheng — w28515 (2021) | Классификация market/limit/stop; ~57% объёма — non-routable ордера | [www.nber.org/papers/w28515](https://www.nber.org/papers/w28515) |
| Stanford GSB | FINANCE 562 — Financial Trading Strategies | Алгоритмы исполнения, выбор типа заявки | [www.gsb.stanford.edu/experience/learning/experi...](https://www.gsb.stanford.edu/experience/learning/experiential-learning/rail/curricular-integration) |
| MIT | 15.481X Adaptive Markets (Fall 2022) | Микроструктура рынка, ликвидность, исполнение сделок | [ocw.mit.edu/courses/15-481x-adaptive-markets-fi...](https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/) |
| ВШЭ | Financial Economics WP — microstructure | Академический контекст микроструктуры финансовых рынков | [wp.hse.ru/en/prepfr_FE](https://wp.hse.ru/en/prepfr_FE) |

---

## В автоматической системе

### Архитектурное правило

Автоматизация предпочитает limit и stop-limit. Market — только для малых позиций или emergency flatten.

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

1. Code node — расчёт `limit_price`, `stop_price` из [[Position_sizing]] и ATR.
2. HTTP Request — POST `/order` (Binance или T-Invest API).
3. Wait + Poll — статус `FILLED` / `PARTIALLY_FILLED` / `REJECTED`.
4. IF rejected → Telegram alert + запись в Obsidian journal.
5. IF partial → дождаться fill или отменить остаток.

### Code node: округление к tick size

```javascript
function roundTick(price, tick) {
  return Math.round(price / tick) * tick;
}
const limitPrice = roundTick(lastClose * 0.998, tickSize);
```

### LLM guardrails

Правило [[LLM_rules_and_guardrails]]: LLM не выбирает market для позиций > `config.max_market_order_notional`. Только limit или stop-limit.

### Session-aware scheduling (MOEX)

```javascript
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
3. [[MOEX_stocks]] — лоты, шаг цены, режимы MOEX.
4. [[Binance_API]] — типы ордеров на криптобирже.
5. [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types)
6. [MOEX: Расписание торгов](https://www.moex.com/s1167)
