---
title: Глоссарий
tags: [основы, справочник, глоссарий]
sources:
  - https://www.investor.gov/additional-resources/general-resources/glossary
  - https://www.investor.gov/introduction-investing/investing-basics/glossary/stock
  - https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order
  - https://www.finra.org/investors/investing/investing-basics
  - https://www.moex.com/s1167
updated: 2026-07-05
level: beginner
---

# Глоссарий

> Краткий справочник терминов трейдинга и инвестирования для новичков. Каждый термин ссылается на тематические статьи wiki и, где возможно, на официальные определения SEC/FINRA/MOEX. Подробные объяснения — в связанных заметках.

---

## Для новичка

### Как пользоваться глоссарием

1. **Ищите термин** по алфавиту (таблицы ниже) или через поиск Obsidian (`Ctrl+O`).
2. **Переходите по ссылкам** `[[...]]` к полным статьям.
3. **Не зубрите всё сразу** — возвращайтесь по мере изучения [[Finance_basics]], [[What_is_trading]], [[Order_types]].
4. В автоматической системе LLM использует этот файл через **RAG** — задавайте вопросы своими словами.

### Три группы терминов

| Группа | Примеры | Где изучать |
|--------|---------|-------------|
| **Инвестирование** | Акция, облигация, ETF, диверсификация | [[Finance_basics]] |
| **Трейдинг** | Long, short, spread, slippage | [[What_is_trading]] |
| **Исполнение** | Market order, limit, stop-loss | [[Order_types]] |

### Английский vs русский

На биржах и в API термины часто **на английском** (bid, ask, limit order). В российском брокерском приложении — **русские** названия («лимитная заявка», «рыночная»). Значение **одно и то же**.

### Официальные определения

SEC (Investor.gov) и FINRA публикуют **глоссарии** с юридически точными формулировками. Этот справочник **упрощает** их для новичков, но не заменяет первоисточник при спорных случаях.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **Stock (акция)** — инструмент, означающий **долю владения (equity)** в корпорации и пропорциональное право на активы и прибыль; большинство акций дают **право голоса**. | [Investor.gov: Stock](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock) |
| 2 | **Bond (облигация)** — **долговая ценная бумага (debt security)**, «IOU»: эмитент занимает деньги и обещает проценты и возврат номинала. | [Investor.gov: Bonds FAQs](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |
| 3 | **Stop order** — заявка купить/продать, когда цена достигает **stop price**; затем становится **market order**; цена исполнения **может отличаться** от stop price. | [Investor.gov: Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| 4 | **Limit order** — заявка купить/продать по **конкретной цене или лучше**; исполнение **не гарантировано**. | [SEC: Limit Orders](https://www.sec.gov/answers/limit.htm) |
| 5 | FINRA: **equity securities** = акции (доля в компании); **debt securities** = облигации (вы даёте в долг, получаете interest/yield). | [FINRA: Investing Basics](https://www.finra.org/investors/investing/investing-basics) |
| 6 | **Asset allocation** — распределение инвестиций между классами активов (акции, облигации, cash) с учётом риска и горизонта. | [Investor.gov: Introduction](https://www.investor.gov/introduction-investing) |
| 7 | **Diversification** — распределение между разными активами; «не кладите все яйца в одну корзину». | [Investor.gov: Introduction](https://www.investor.gov/introduction-investing) |
| 8 | **IPO** — первичное публичное размещение акций; компания **впервые** продаёт акции широкой публике. | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |
| 9 | **MOEX** — Московская биржа; основная торговая сессия акций (ТП): **10:00–18:54:59** МСК (для ряда бумаг). | [MOEX: Расписание](https://www.moex.com/s1167) |
| 10 | Investor.gov Glossary содержит **сотни терминов** — официальный справочник SEC для розничных инвесторов. | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |

---

## Подробно: алфавитный справочник

### А–В

| Термин | Определение | Wiki / источник |
|--------|-------------|-----------------|
| **API** | Application Programming Interface — программный интерфейс для автоматического доступа к данным и торгам | [[Binance_API]], [[Tinkoff_Invest_API]] |
| **Ask (offer)** | Минимальная цена, по которой продавец готов продать | [[Order_types]] |
| **Asset allocation** | Распределение портфеля между классами активов | [[Finance_basics]] |
| **Beta (β)** | Мера чувствительности доходности актива к движению рынка (β=1 — как рынок) | [[Key_indicators_RSI_MACD]] |
| **Bid** | Максимальная цена, по которой покупатель готов купить | [[Order_types]] |
| **Bid-ask spread** | Ask − Bid; индикатор ликвидности | [[What_is_trading]] |
| **Blue-chip** | Акции крупных известных компаний с устойчивой историей | [Investor.gov: Stocks](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) |
| **Bond (облигация)** | Долговая ценная бумага; кредиторские отношения с эмитентом | [[Finance_basics]] |
| **Broker (брокер)** | Лицензированный посредник, исполняющий заявки на бирже | [[What_is_trading]] |
| **Bull market** | Рынок с **устойчивым ростом** цен («бычий») | — |
| **Bear market** | Рынок с **устойчивым падением** цен («медвежий») | — |
| **Volatility (волатильность)** | Степень изменчивости цены актива | [[Finance_basics]] |

### Г–Д

| Термин | Определение | Wiki / источник |
|--------|-------------|-----------------|
| **Gap (гэп)** | Разрыв цены между закрытием и открытием без сделок между уровнями | [[Technical_analysis_basics]] |
| **Dividend (дивиденд)** | Выплата акционерам из прибыли компании (не гарантирована) | [[Finance_basics]] |
| **Diversification (диверсификация)** | Распределение риска между разными активами, секторами, странами | [[Portfolio_diversification]] |
| **Drawdown (просадка)** | Падение equity от пика до минимума; max drawdown — худшая историческая просадка | [[Position_sizing]] |
| **Day order** | Заявка, действующая до конца торговой сессии | [[Order_types]] |
| **Depository (депозитарий)** | Организация, ведущая учёт прав на ценные бумаги | [[What_is_trading]] |

### Е–З

| Термин | Определение | Wiki / источник |
|--------|-------------|-----------------|
| **Equity (equity security)** | Доля владения; синоним «акции» в контексте FINRA | [FINRA](https://www.finra.org/investors/investing/investing-basics) |
| **ETF** | Exchange-Traded Fund — биржевой фонд, торгуется как акция | [[Finance_basics]] |
| **Execution (исполнение)** | Фактическое заключение сделки по заявке | [[Order_types]] |
| **Face value (номинал)** | Сумма, которую эмитент обязан вернуть при погашении облигации | [Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |

### И–К

| Термин | Определение | Wiki / источник |
|--------|-------------|-----------------|
| **Index fund** | Фонд, отслеживающий рыночный индекс («корзину» бумаг) | [Investor.gov](https://www.investor.gov/introduction-investing) |
| **IPO** | Initial Public Offering — первичное публичное размещение акций | [[What_is_trading]] |
| **Issuer (эмитент)** | Компания или государство, выпустившее ценные бумаги | [[What_is_trading]] |
| **Leverage (плечо, margin)** | Торговля с заёмными средствами; усиливает прибыль **и** убыток | [[Risk_management]] |
| **Limit order** | Лимитная заявка — исполнение по указанной цене или лучше | [[Order_types]] |
| **Liquidity (ликвидность)** | Лёгкость покупки/продажи без сильного влияния на цену | [[Finance_basics]] |
| **Long** | Позиция на рост: купил актив, ждёшь роста | [[What_is_trading]] |
| **Lot (лот)** | Стандартный минимальный объём сделки на бирже | [[MOEX_stocks]] |
| **Market cap** | Рыночная капитализация = цена × количество акций в обращении | [[Finance_basics]] |
| **Market order** | Рыночная заявка — по лучшей доступной цене | [[Order_types]] |
| **MOEX** | Московская биржа — главная площадка России для акций и облигаций | [[MOEX_stocks]] |

### М–П

| Термин | Определение | Wiki / источник |
|--------|-------------|-----------------|
| **MACD** | Moving Average Convergence Divergence — индикатор тренда | [[Key_indicators_RSI_MACD]] |
| **Margin call** | Требование брокера пополнить счёт при недостатке обеспечения | [FINRA: Margin](https://www.finra.org/investors/investing/investment-products/stocks/margin-accounts) |
| **Mutual fund** | Паевой инвестиционный фонд (ПИФ в РФ) | [[Finance_basics]] |
| **OHLCV** | Open, High, Low, Close, Volume — формат свечных данных | [[Technical_analysis_basics]] |
| **Order (заявка)** | Инструкция брокеру купить/продать на условиях | [[Order_types]] |
| **P/E ratio** | Price/Earnings — цена акции / прибыль на акцию | [[Finance_basics]] |
| **Portfolio (портфель)** | Совокупность всех активов инвестора | [[Portfolio_diversification]] |
| **Position** | Открытая позиция — актив, которым вы владеете (long) или должны (short) | [[What_is_trading]] |
| **Position sizing** | Определение размера позиции с учётом риска | [[Position_sizing]] |
| **Preferred stock** | Привилегированная акция — приоритет дивидендов, обычно без голоса | [Investor.gov: Stocks](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) |

### Р–Т

| Термин | Определение | Wiki / источник |
|--------|-------------|-----------------|
| **RAG** | Retrieval-Augmented Generation — LLM + поиск по базе знаний (Obsidian) | [[n8n_architecture_overview]] |
| **Rebalancing** | Ребалансировка — возврат портфеля к целевой аллокации | [[Portfolio_diversification]] |
| **ROI** | Return on Investment — доходность вложений в процентах | — |
| **RSI** | Relative Strength Index — осциллятор перекупленности/перепроданности | [[Key_indicators_RSI_MACD]] |
| **Short** | Позиция на падение: продал заёмное, ждёшь снижения | [[What_is_trading]] |
| **Slippage (проскальзывание)** | Исполнение по цене хуже ожидаемой | [[Order_types]] |
| **Spread** | Bid-ask spread или разница ставок | [[What_is_trading]] |
| **Stop-loss** | Заявка на ограничение убытка при достижении stop price | [[Stop_loss_take_profit]] |
| **Stop price** | Цена активации stop order | [[Order_types]] |
| **Take-profit** | Заявка на фиксацию прибыли при достижении целевой цены | [[Stop_loss_take_profit]] |
| **Ticker (тикер)** | Биржевой код инструмента (SBER, AAPL, BTCUSDT) | [[MOEX_stocks]] |
| **Time in Force** | Срок действия заявки (Day, GTC, IOC, FOK) | [[Order_types]] |
| **Trailing stop** | Stop order, где stop price следует за ценой на заданном расстоянии | [SEC Bulletin 15](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15) |

### Ф–Я

| Термин | Определение | Wiki / источник |
|--------|-------------|-----------------|
| **FOMO** | Fear Of Missing Out — страх упустить прибыль; когнитивное искажение | [[Trader_psychology]] |
| **FUD** | Fear, Uncertainty, Doubt — распространение негатива для давления на цену | [[Crypto_exchanges]] |
| **Yield (доходность)** | Доход от инвестиции в % (купон облигации, дивидендная yield) | [[Finance_basics]] |
| **Volume (объём)** | Количество акций/контрактов, сменивших владельца за период | [[Technical_analysis_basics]] |
| **VWAP** | Volume Weighted Average Price — средневзвешенная цена по объёму | [[Technical_analysis_basics]] |
| **Wash sale** | Продажа в убыток и повторная покупка того же актива в короткий срок (налоговое правило США) | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |
| **Yield to maturity (YTM)** | Полная доходность облигации при удержании до погашения | [[Bonds_basics]] |

---

## Примеры

### Пример 1: Расшифровка котировки

```
SBER: 250.10 / 250.30 (bid / ask)
Last: 250.25 | Volume: 1 250 000
```

- **Bid 250,10** — лучшая цена покупателя;
- **Ask 250,30** — лучшая цена продавца;
- **Spread** = 0,20 ₽;
- Market **buy** ≈ 250,30 ₽; market **sell** ≈ 250,10 ₽.

### Пример 2: Long vs Short

**Long:** купил BTC @ 60 000 → продал @ 63 000 → **+3 000**.

**Short:** одолжил и продал @ 60 000 → купил обратно @ 57 000 → **+3 000** (минус borrow fee).

### Пример 3: Market cap

Компания: **1 млрд акций** × **250 ₽** = **250 млрд ₽** market cap.

### Пример 4: Drawdown

Equity: 100 000 → 130 000 (peak) → 91 000 (trough).

```
Drawdown = (130 000 - 91 000) / 130 000 = 30%
```

### Пример 5: P/E

Цена акции **500 ₽**, EPS (прибыль на акцию) **50 ₽**:

```
P/E = 500 / 50 = 10
```

Инвестор «платит» 10× годовую прибыль на акцию (упрощённо).

---

## Частые ошибки

1. **Путать bid и ask** — покупаете по ask, продаёте по bid.
2. **«Last = моя цена»** — SEC: last traded price **≠** guaranteed fill для market order.
3. **Путать ticker и название компании** — SBER ≠ «Сбер» в API (проверяйте ISIN/FIGI).
4. **Leverage без понимания margin call** — убытки могут превысить депозит.
5. **FOMO как стратегия** — см. [[Trader_psychology]].
6. **Игнорировать spread на illiquid** — «бумажная» прибыль съедается спредом.
7. **Путать ETF и акцию эмитента** — ETF — фонд, не компания.

---

## FAQ

### Где официальный глоссарий SEC?

[Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) — сотни терминов с определениями от SEC.

### Чем отличается equity от stock?

В практике — **синонимы**. Equity — более широкий термин «доля владения»; stock — конкретная ценная бумага.

### Что такое «лот» на MOEX?

Минимальное количество акций в одной сделке. Для SBER — обычно **1 акция** (проверяйте спецификацию инструмента на [MOEX](https://www.moex.com/)).

### Beta = 1.5 — что это значит?

Актив **на 50% волатильнее** рынка в среднем (упрощённо). β < 1 — менее волатилен, β > 1 — более.

### Как LLM использует глоссарий?

При неизвестном термине в запросе — RAG-поиск по `Glossary.md` и связанным статьям; ответ с цитатой wiki и источника.

### Нужно ли знать все термины?

**Нет.** Начните с [[Finance_basics]] → [[What_is_trading]] → [[Order_types]]; возвращайтесь к глоссарию по мере необходимости.

---

## Проверенные источники

1. **[Glossary — Investor.gov (SEC)](https://www.investor.gov/additional-resources/general-resources/glossary)** — официальный справочник SEC: сотни терминов от 401(k) до yield, с определениями для розничных инвесторов.
2. **[Stock — Investor.gov Glossary](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock)** — определение акции как equity, voting rights, claim on assets/profits.
3. **[Stop Order — Investor.gov Glossary](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)** — stop price, conversion to market, slippage risk.
4. **[Limit Orders — SEC.gov](https://www.sec.gov/answers/limit.htm)** — limit order mechanics, no execution guarantee.
5. **[Investing Basics — FINRA](https://www.finra.org/investors/investing/investing-basics)** — equity vs debt, ETF/mutual fund, disclosure, transparency.
6. **[Bonds FAQs — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds)** — bond, face value, coupon, maturity.
7. **[Расписание торгов — MOEX](https://www.moex.com/s1167)** — торговые сессии, контекст для Day order и ticker trading hours.

---

## В автоматической системе

### Obsidian: теги и перекрёстные ссылки

```markdown
#term/RSI в [[Key_indicators_RSI_MACD]]
#term/limit-order в [[Order_types]]
```

Dataview-запрос для «все статьи с термином»:

```dataview
LIST FROM #term/limit-order
```

### RAG (Ollama + n8n)

1. Пользователь спрашивает: «Что такое slippage?»
2. n8n → embedding search по `Glossary.md` + связанным файлам.
3. Top-3 chunks → context в Ollama prompt.
4. Ответ с ссылкой на [[Order_types]] и [FINRA](https://www.finra.org/investors/investing/investment-products/stocks/order-types).

### Нормализация тикеров

```yaml
# tickers.yaml (Obsidian)
SBER:
  exchange: MOEX
  figi: BBG004730N88
  aliases: [Сбер, Sberbank]
BTCUSDT:
  exchange: BINANCE
  base: BTC
  quote: USDT
```

n8n Code node: `resolveTicker(userInput)` → canonical ticker для API.

### LLM prompt snippet

```
При объяснении терминов:
1. Дай простое определение (1–2 предложения).
2. Ссылайся на wiki: [[...]].
3. Если термин регуляторный — укажи источник SEC/FINRA/MOEX с URL.
4. Не выдумывай статистику.
```

### Журнал lookup

```yaml
query: "что такое bid-ask spread"
rag_hits: [Glossary.md#bid-ask-spread, Order_types.md]
response_sources: [finra-order-types]
```

---

## Связанные темы

- [[Finance_basics]]
- [[What_is_trading]]
- [[Order_types]]
- [[Wiki_structure]]
- [[Stop_loss_take_profit]]
- [[Portfolio_diversification]]

---

## Что изучить дальше

1. [[Finance_basics]] — акции, облигации, аллокация.
2. [[What_is_trading]] — участники рынка, long/short.
3. [[Order_types]] — market, limit, stop.
4. [[Stop_loss_take_profit]] — практика выхода из позиции.
5. [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) — полный официальный справочник SEC.
6. [Школа MOEX](https://school.moex.com/) — термины российского рынка в контексте.
