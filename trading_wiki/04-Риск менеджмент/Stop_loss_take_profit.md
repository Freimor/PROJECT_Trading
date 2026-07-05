---
title: Стоп-лосс и тейк-профит
tags: [риск, stop-loss, take-profit, ордера]
sources:
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14
  - https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order
  - https://www.sec.gov/answers/limit.htm
  - https://www.finra.org/investors/investing/investment-products/stocks/order-types
  - https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade
  - https://tinkoff.github.io/investAPI/orders/
updated: 2026-07-05
level: beginner
---

# Стоп-лосс и тейк-профит

> **Stop-loss (стоп-лосс)** — заранее заданное условие выхода из позиции при неблагоприятном движении цены. **Take-profit (тейк-профит)** — заранее заданная цель для фиксации прибыли. Оба инструмента формализуют правила выхода до входа в сделку и снижают влияние эмоций.

---

## Для новичка

Представьте, что вы купили акцию за 100 ₽. Вы **не знаете**, куда пойдёт цена завтра. Но вы **можете решить заранее**:

- «Если цена упадёт до 95 ₽ — продам и ограничу убыток» → это **stop-loss**.
- «Если цена вырастет до 110 ₽ — продам и зафиксирую прибыль» → это **take-profit**.

Без этих правил трейдер часто держит убыточную позицию в надежде «отыграться» (см. [[Cognitive_biases]], [[Trader_psychology]]) или закрывает прибыль слишком рано от страха.

**Важно:** стоп-лосс на бирже — это **тип заявки**, а не абстрактное «обещание себе». На MOEX и криптобиржах его можно выставить через брокера/API; условия исполнения зависят от типа ордера.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **Stop order (stop-loss):** заявка на покупку или продажу активируется, когда цена достигает указанной **stop price**; после этого заявка становится **рыночной (market order)**. | [Investor.gov: Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| 2 | **Sell stop** выставляют **ниже** текущей рыночной цены — обычно чтобы ограничить убыток по уже открытой long-позиции или защитить прибыль по short. | [SEC Investor Bulletin: Order Types](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| 3 | **Stop-limit order:** при достижении stop price активируется не market, а **limit order** — исполнение только по limit price или лучше; цена исполнения контролируется, но **исполнение не гарантировано**. | [SEC Investor Bulletin: Order Types](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| 4 | **Limit order** исполняется только по указанной цене или лучше; **не гарантирует** исполнение, если рынок не дошёл до limit price. | [SEC: Limit Orders](https://www.sec.gov/answers/limit.htm) |
| 5 | Недостаток stop order: цена исполнения **может отличаться** от stop price, особенно в **быстро движущемся рынке**; краткосрочные колебания могут **случайно активировать** стоп. | [Investor.gov: Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| 6 | FINRA: **sell stop** помогает ограничить убытки, если акция падает сильнее, чем вы готовы терпеть; после срабатывания — market order по текущей рыночной цене. | [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types) |
| 7 | **Trailing stop** — разновидность stop order, где stop price **следует за ценой** при благоприятном движении (описан в SEC Investor Bulletin среди типов заявок). | [SEC Investor Bulletin: Order Types](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |

---

## Подробно: типы заявок для SL и TP

### 1. Stop-market (классический stop-loss)

**Механизм (по SEC/FINRA):**
1. Вы задаёте stop price (например, 95 ₽ при покупке за 100 ₽).
2. Когда рынок **достигает** 95 ₽, заявка превращается в **market sell**.
3. Исполнение — по **лучшей доступной** цене в стакане, не обязательно ровно 95 ₽.

**Когда использовать:** нужна **гарантия попытки выхода**; допустимо небольшое проскальзывание.

### 2. Stop-limit

**Механизм:**
1. Stop price = 95 ₽, limit price = 94,50 ₽.
2. При достижении 95 ₽ выставляется limit sell ≥ 94,50 ₽.
3. Если цена «пролетает» 94,50 без сделок — позиция **может остаться открытой**.

**Когда использовать:** illiquid активы, где market stop опасен большим slippage; **не** для паники на crash без доп. мониторинга.

### 3. Limit take-profit

**Механизм (SEC):** limit sell на 110 ₽ исполнится **только** по 110 ₽ или выше.

**Риск:** в резком ралли цена может коснуться 109,90 и развернуться — TP не исполнится.

### 4. OCO (One-Cancels-Other)

На многих криптобиржах (Binance Spot API поддерживает связанные ордера через отдельные endpoints / OCO) одновременно выставляют SL и TP: исполнение одного **отменяет** другой. Проверяйте актуальную документацию биржи: [Binance New Order](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade).

### 5. Trailing stop

Stop price автоматически подтягивается на фиксированное расстояние (₽ или %) ниже **максимума** с момента активации. Защищает «накопленную» прибыль при тренде вверх.

### 6. Time stop (время)

Не биржевой тип, а **правило стратегии:** «закрыть позицию через N баров / N дней, если TP не достигнут». Реализуется в n8n/Code, не на бирже.

### 7. ATR-based stop

**Не официальный тип ордера**, а метод **расчёта stop price**:

```
stop_distance = ATR(14) × multiplier   // multiplier часто 1.5–3
stop_price_long = entry_price - stop_distance
```

ATR (Average True Range) отражает волатильность; стоп шире на волатильных активах. Источник концепции ATR — классический ТА (Wilder); для автоматизации см. [[Key_indicators_RSI_MACD]].

---

## Связь соотношения Risk/Reward

**Risk/Reward (R:R)** — отношение потенциального убытка к потенциальной прибыли **на одну сделку**.

**Пример расчёта:**
- Вход long: 100 ₽
- Stop: 97 ₽ → риск = 3 ₽ на акцию
- Take-profit: 106 ₽ → награда = 6 ₽ на акцию
- **R:R = 6 / 3 = 2:1**

> SEC и FINRA **не гарантируют**, что соотношение 2:1 или любое другое обеспечит прибыльность стратегии. R:R — инструмент **планирования**, а не доказанное правило доходности. Обязательно сочетайте с [[Position_sizing]] и статистикой стратегии (win rate).

**Минимальный win rate** при R:R 2:1 для «нулевой» матемatics (без комиссий):

```
breakeven_win_rate = risk / (risk + reward) = 1 / (1 + 2) ≈ 33.3%
```

При win rate 40% и R:R 2:1 стратегия **может** быть прибыльной — но только после бэктеста и учёта комиссий.

---

## Примеры

### Пример 1: Акция SBER на MOEX (учебный)

| Параметр | Значение |
|----------|----------|
| Покупка | 250 ₽ × 100 акций = 25 000 ₽ |
| Stop-loss 3% | 242,50 ₽ (sell stop или stop-limit через T-Invest API) |
| Take-profit 6% | 265 ₽ (limit sell) |
| R:R | 2:1 |
| Риск на сделку | 750 ₽ (3% от 25 000) |

Если капитал 500 000 ₽ и правило [[Position_sizing]] — риск 1% = 5 000 ₽, то позиция 25 000 ₽ **укладывается** в лимит (750 < 5 000).

### Пример 2: BTCUSDT на Binance

| Параметр | Значение |
|----------|----------|
| Entry | 60 000 USDT |
| Stop 3% | 58 200 USDT |
| TP 6% | 63 600 USDT |
| Slippage risk | При stop-market fill может быть 58 150 или хуже — заложите в бэктест |

### Пример 3: Проскальзывание stop-market

Stop sell на 95 ₽. Новость → gap open 90 ₽. Market order исполняется около **90 ₽**, не 95 ₽. Это **подтверждённый риск** stop-market ордеров ([Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)).

---

## Частые ошибки новичков

1. **Стоп слишком близко** — случайный шум выбивает из позиции до движения (FINRA/SEC предупреждают о краткосрочных колебаниях).
2. **Стоп слишком далеко** — нарушает [[Position_sizing]]; один убыток съедает много капитала.
3. **Нет TP** — прибыль «тает» при развороте; см. loss aversion и disposition effect в [[Cognitive_biases]].
4. **Stop-limit на illiquid** без plan B — позиция зависает при crash.
5. **Двигают стоп «от отчаяния»** вниз — отменяет смысл риск-менеджмента.
6. **Забывают про комиссии** — R:R на бумаге vs в реальности.

---

## FAQ

### Гарантирует ли stop-loss точную цену выхода?

**Нет.** Stop-market после активации = market order; цена может отличаться от stop price ([Investor.gov: Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)).

### Чем stop-limit лучше stop-market?

Контроль **минимальной** цены продажи; но при быстром падении ордер **может не исполниться** ([SEC Investor Bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)).

### Нужен ли take-profit, если есть trailing stop?

Зависит от стратегии. TP фиксирует план; trailing защищает extended trend. Можно комбинировать (частичный TP + trailing на остаток).

### Как выставить SL/TP через API?

- **MOEX / T-Bank:** [T-Invest OrdersService](https://tinkoff.github.io/investAPI/orders/) — типы `STOP_ORDER`, `STOP_LIMIT`, лимитные заявки.
- **Binance Spot:** [REST New Order](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade), параметры `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT` (проверяйте актуальные enum в документации).

---

## Ключевые понятия

| Термин | Определение | Источник |
|--------|-------------|----------|
| Stop price | Цена активации stop order | [Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| Limit price | Мин./макс. цена для limit order | [SEC](https://www.sec.gov/answers/limit.htm) |
| Slippage | Разница ожидаемой и фактической цены исполнения | Практика + [Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| Bracket order | Entry + SL + TP как набор | Брокер/API-специфично |
| R:R | Risk/Reward ratio | Термин стратегии, не регуляторный |

---

## Проверенные источники

1. **[Investor Bulletin: Understanding Order Types — SEC/OIEA](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14)** — официальное описание market, limit, stop, stop-limit, trailing stop.
2. **[Stop Order — Investor.gov Glossary](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)** — определение, плюсы/минусы stop order.
3. **[Limit Orders — SEC.gov](https://www.sec.gov/answers/limit.htm)** — limit order, отсутствие гарантии исполнения.
4. **[Order Types — FINRA](https://www.finra.org/investors/investing/investment-products/stocks/order-types)** — sell stop, buy stop, stop-limit для розничных инвесторов.
5. **[T-Invest API: Orders](https://tinkoff.github.io/investAPI/orders/)** — программное выставление стоп- и лимитных заявок на MOEX через брокера.
6. **[Binance Spot API: New Order](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade)** — типы ордеров для crypto-flow.

---

## В автоматической системе

### Архитектурное правило

**Каждый live-ордер** в n8n проходит через sub-workflow `place-bracket-order`:
1. Entry исполнен (status `FILLED`).
2. Немедленно выставляются SL и TP (или OCO на Binance).
3. Если SL/TP reject → **emergency flatten** + Telegram `CRITICAL`.

### Расчёт уровней (Code node)

```javascript
const entry = $json.entry_price;
const riskPct = 0.03;      // из Obsidian risk.yaml
const rewardPct = 0.06;    // R:R = 2:1
const tick = $json.tick_size;

function roundTick(price, tick) {
  return Math.round(price / tick) * tick;
}

return [{
  json: {
    stop_price: roundTick(entry * (1 - riskPct), tick),
    take_profit_price: roundTick(entry * (1 + rewardPct), tick),
    risk_reward: rewardPct / riskPct
  }
}];
```

### LLM vs код

| Решает LLM (Ollama) | Решает код (n8n) |
|---------------------|------------------|
| `stop_distance_atr_mult` (предложение) | Финальные цены после округления |
| approve/reject setup | quantity из [[Position_sizing]] |
| counter_thesis | post order API |

Правило [[LLM_rules_and_guardrails]]: **G9** — LLM не override stop distance ниже minimum из config.

### Журнал Obsidian

```yaml
trade_id: "2026-07-05-btc-001"
entry: 60000
stop: 58200
take_profit: 63600
risk_reward: 2.0
stop_type: stop_market
tp_type: limit
exit_reason: null  # take_profit | stop_loss | time_stop | manual
slippage_stop: null
sources_checked: [investor.gov-stop-order, finra-order-types]
```

### Мониторинг

- n8n Schedule: проверка «open position without SL» каждые 15 мин → alert.
- Metrics: avg slippage on stops, % stops hit vs TP.

---

## Связанные темы

- [[Order_types]]
- [[Position_sizing]]
- [[Trader_psychology]]
- [[Key_indicators_RSI_MACD]]
- [[Crypto_flow_design]]
- [[Binance_API]]
- [[Tinkoff_Invest_API]]

---

## Что изучить дальше

1. [[Order_types]] — полный список типов заявок с цитатами SEC.
2. [[Position_sizing]] — как размер позиции связан с расстоянием до стопа.
3. [[Technical_analysis_basics]] — ATR и уровни для постановки стопов.
4. Backtesting.md (планируется в Wiki_structure) — проверка R:R на истории.
