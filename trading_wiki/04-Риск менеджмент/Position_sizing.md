---
title: Размер позиции (Position Sizing)
tags: [риск, position sizing, капитал, концентрация]
sources:
  - https://www.investor.gov/introduction-investing/getting-started/asset-allocation
  - https://www.finra.org/investors/investing/investing-basics
  - https://www.finra.org/rules-guidance/notices/24-13
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72
  - https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order
updated: 2026-07-05
level: beginner
---

# Размер позиции (Position Sizing)

> **Position sizing (размер позиции)** — определение, **сколько капитала** (или сколько единиц актива) выделяется на одну сделку с учётом **риска на сделку**, **расстояния до стоп-лосса** и **лимитов концентрации** портфеля. Это мост между торговой идеей и выживанием счёта при серии убытков.

---

## Для новичка

Представьте: вы уверены, что акция вырастет. Покупаете на **весь депозит** — 500 000 ₽. Цена падает на 10% → минус 50 000 ₽ за одну сделку. Ещё две такие — и счёт потерял треть капитала.

**Position sizing** отвечает на другой вопрос: «Сколько я могу купить так, чтобы **один** стоп-лосс не разрушил мой план?»

Типичная логика (используется в профессиональном риск-менеджменте и автоматизации):

1. Решите, **сколько % капитала** готовы потерять, если сработает стоп (часто 1–2% — эвристика трейдеров; регуляторы задают рамку через **risk tolerance**, а не конкретный процент).
2. Определите **расстояние до стопа** (в ₽ или %).
3. Рассчитайте количество акций/контрактов так, чтобы убыток при стопе ≤ выбранному лимиту.

FINRA напоминает: изучайте **asset allocation и diversification**, чтобы **не ставить всё на одну инвестицию** («don't bet the ranch on a single investment») — см. [[Portfolio_diversification]].

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **Risk tolerance** — способность и готовность инвестора **потерять часть или весь** первоначальный капитал ради потенциально более высокой доходности; при росте риска инвесторы обычно требуют большей компенсации. | [Investor.gov: Asset Allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| 2 | **Asset allocation** — распределение инвестиций между классами активов (акции, облигации, cash); решение **личное** и меняется с горизонтом и tolerance. | [Investor.gov: Asset Allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| 3 | FINRA: успешное инвестирование — это **цели, информированные действия и баланс рисков**; важно изучать allocation/diversification и **не ставить всё на одну сделку**. | [FINRA: Investing Basics](https://www.finra.org/investors/investing/investing-basics) |
| 4 | **Inadequate diversification** — портфель **слишком сконцентрирован** в одном типе инвестиций; повышает риск-exposure (SEC Investor Bulletin по отчёту Library of Congress). | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 5 | FINRA Rule 2270 (day trading disclosure): day trading **может быть крайне рискованным**; торговля **с маржой** может привести к **убыткам сверх** первоначальных вложений. | [FINRA Regulatory Notice 24-13](https://www.finra.org/rules-guidance/notices/24-13) |
| 6 | **Stop order** после активации становится market order; цена исполнения **может отличаться** от stop price — это влияет на **фактический** убыток и должен учитываться при sizing. | [Investor.gov: Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| 7 | **Rebalancing** — возврат портфеля к целевым весам; при росте одного класса (например, акции 60% → 80%) нужно **продать часть** «победителей» и докупить другие классы. | [Investor.gov: Asset Allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |

> **Важно:** SEC и FINRA **не устанавливают** обязательный «1% на сделку» для всех инвесторов. Конкретный процент риска — **ваше правило** (или правило автоматической системы), согласованное с tolerance, горизонтом и регуляторными лимитами брокера.

---

## Подробно: методы расчёта размера позиции

### 1. Fixed fractional (фиксированная доля риска)

**Суть:** на каждую сделку рискуете **фиксированным % equity**, независимо от «уверенности» в сигнале.

```
risk_amount     = account_equity × risk_percent
risk_per_unit   = |entry_price - stop_price|    // для long
position_units  = risk_amount / risk_per_unit
position_value  = position_units × entry_price
```

**Пример:**
- Equity: 500 000 ₽
- Risk 1% → risk_amount = 5 000 ₽
- Entry 250 ₽, stop 242,50 ₽ → risk_per_unit = 7,50 ₽
- Units = 5 000 / 7,50 ≈ 666 → с учётом лота 10 → **660 акций**
- Position value = 660 × 250 = **165 000 ₽** (33% equity в номинале, но **риск** только 1%)

**Почему это работает:** при серии убытков equity сжимается → автоматически **меньше** units на следующей сделке (защита от «лестницы вниз»).

### 2. Fixed monetary risk (фиксированная сумма в валюте)

```
position_units = fixed_risk_rub / risk_per_unit
```

Удобно, если equity стабилен; при просадке **не адаптируется** — хуже для автоматизации, чем fractional.

### 3. Fixed percentage of equity (без привязки к стопу)

```
position_value = account_equity × allocation_percent
```

**Риск:** allocation 20% без стопа ≠ контроль риска на сделку. FINRA/SEC предупреждают о **концентрации** — см. inadequate diversification. Используйте только вместе со [[Stop_loss_take_profit]] или для долгосрочных ETF-позиций с другим горизонтом.

### 4. Volatility-based sizing (ATR)

```
stop_distance = ATR(14) × multiplier
position_units = (equity × risk_pct) / stop_distance
```

Стоп шире на волатильных активах → **меньше** units при том же % риска. Метод расчёта, не биржевой тип ордера; ATR — классический индикатор волатильности (Wilder).

### 5. Kelly criterion (теоретический максимум роста)

```
f* = (p × b - q) / b
```
где `p` = win rate, `q` = 1-p, `b` = reward/risk.

Kelly (1956) — академическая формула оптимального доли ставки при известных `p` и `b`. **На практике:** полный Kelly агрессивен; трейдеры часто используют **half-Kelly** или фиксированный fractional. **Не** заменяет stop-loss и лимиты концентрации.

### 6. Лимиты концентрации (portfolio-level)

| Лимит | Типичное значение в системе | Обоснование |
|-------|----------------------------|-------------|
| Max single asset | 10–20% equity | SEC: inadequate diversification; IMOEX cap 15% на бумагу — [[IMOEX_RTS]] |
| Max sector/crypto cluster | 25–30% | Коррелированные активы ≈ один риск |
| Max open risk (portfolio heat) | 4–6% суммарно | Несколько позиций × 1% каждая |
| Daily loss limit | 2–3% equity | Circuit breaker в автоматизации |

---

## Связь Position Sizing ↔ Stop-Loss ↔ R:R

Три параметра **связаны mathematically**:

```
risk_per_trade = position_size × stop_distance_pct
```

Если фиксируете **risk 1%** и **stop 3%**, максимальный номинал позиции ≈ **33% equity** (1% / 3%). Если stop **1%** — номинал до **100%** (опасно без diversification).

**R:R** (см. [[Stop_loss_take_profit]]) не определяет размер позиции напрямую, но влияет на **ожидаемую** прибыльность при заданном win rate.

---

## Примеры

### Пример 1: Акция SBER (MOEX), учебный

| Параметр | Значение |
|----------|----------|
| Equity | 500 000 ₽ |
| Risk per trade | 1% = 5 000 ₽ |
| Entry | 250 ₽ |
| Stop | 242,50 ₽ (−3%) |
| Risk/share | 7,50 ₽ |
| Shares | floor(5000/7.50/10)×10 = **660** |
| Position value | 165 000 ₽ |
| Max loss at stop | ~4 950 ₽ (< 5 000) |

Проверка концентрации: 165 000 / 500 000 = **33%** в одной бумаге — выше ориентира 15% IMOEX. **Решение:** снизить risk до 0,5% или ужесточить stop, или увеличить equity.

### Пример 2: BTCUSDT, волатильный актив

| Параметр | Значение |
|----------|----------|
| Equity | 10 000 USDT |
| Risk | 1% = 100 USDT |
| Entry | 60 000 |
| Stop (ATR×2) | 58 200 (−3%) |
| Units | 100 / 1800 ≈ **0,055 BTC** |
| Notional | ~3 300 USDT |

Slippage на stop-market может увеличить фактический loss — заложите buffer в бэктест ([Investor.gov: Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)).

### Пример 3: Серия из 5 убытков подряд (fixed fractional 1%)

| Сделка | Equity до | Risk 1% | Убыток | Equity после |
|--------|-----------|---------|--------|--------------|
| 1 | 500 000 | 5 000 | −5 000 | 495 000 |
| 2 | 495 000 | 4 950 | −4 950 | 490 050 |
| 3 | 490 050 | 4 901 | −4 901 | 485 149 |
| 4 | 485 149 | 4 851 | −4 851 | 480 298 |
| 5 | 480 298 | 4 803 | −4 803 | 475 495 |

Суммарная просадка ≈ **4,9%**, не 5% — fractional **самозащищается**. Без sizing (полный депозит −3% stop × 5) просадка была бы **~14%** и хуже.

### Пример 4: Day trading с маржой (предупреждение)

FINRA Rule 2270: day trading с маржой может привести к убыткам **сверх** депозита. Position sizing **не отменяет** маржинальный риск — нужны отдельные лимиты leverage и compliance с disclosure брокера.

---

## Частые ошибки новичков

1. **«Уверен на 100%» → весь депозит** — нарушает принцип diversification (SEC: inadequate diversification).
2. **Размер без стопа** — нет верхней границы убытка; см. [[Stop_loss_take_profit]].
3. **Одинаковый номинал на все активы** — BTC и облигация с одинаковым ₽-размером ≠ одинаковый риск (volatility ignored).
4. **Увеличение размера после убытка (revenge sizing)** — эмоциональное решение; см. [[Trader_psychology]], [[Cognitive_biases]].
5. **Игнорирование slippage и комиссий** — фактический risk > расчётного.
6. **Пять altcoin по 5% каждый** — naïve diversification при высокой корреляции с BTC ([SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72)).
7. **Забыли portfolio heat** — пять позиций по 1% = 5% одновременного риска; при корреляции 1.0 это один «мега-риск».
8. **Округление до нуля** — малый equity + дорогой инструмент → quantity = 0; система должна skip trade.

---

## FAQ

### Сколько % капитала рисковать на сделку?

SEC/FINRA **не фиксируют** единый процент. Эвристика **1–2%** широко используется в профессиональном риск-менеджменте для активной торговли. Начните с **0,5–1%**, пока нет статистики стратегии. Согласуйте с [[Portfolio_diversification]] и risk tolerance ([Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)).

### Position sizing = % от депозита в актив?

**Не обязательно.** Fixed fractional задаёт **риск при стопе**, а не номинал. Номинал может быть 10–40% equity при узком стопе.

### Как учесть плечо (margin)?

Effective exposure = notional × leverage. FINRA предупреждает: убытки могут **превысить** initial investment. Лимитируйте **notional exposure**, не только cash equity.

### LLM может задавать quantity?

**Нет** в нашей архитектуре. LLM — direction/confidence; quantity — **детерминированный Code node** ([[LLM_rules_and_guardrails]] G8).

### Что если стоп не выставлен?

Position sizing **бессмысленен** без исполняемого exit. Pre-trade check: no stop → reject order.

### Kelly vs fixed fractional?

Kelly требует точных `p` и `b` (редко известны live). Fixed fractional проще, робастнее к ошибкам оценки. Для автоматизации — **fractional + caps**.

---

## Ключевые понятия

| Термин | Определение | Источник / контекст |
|--------|-------------|---------------------|
| Risk per trade | Макс. убыток при срабатывании стопа | Практика риск-менеджмента |
| Fixed fractional | Фиксированный % equity на риск | Стандарт algo-trading |
| Portfolio heat | Сумма рисков открытых позиций | Risk management |
| Concentration | Доля одного актива в портфеле | [SEC Bulletin #72](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| Risk tolerance | Готовность терять капитал ради return | [Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| Slippage | Разница ожидаемой и фактической цены stop | [Investor.gov: Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |

---

## Проверенные источники

1. **[Asset Allocation — Investor.gov (SEC/OIEA)](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)** — risk tolerance, allocation, rebalancing, diversification.
2. **[Investing Basics — FINRA](https://www.finra.org/investors/investing/investing-basics)** — цели, риски, «не ставить всё на одну инвестицию».
3. **[Investor Bulletin: Behavioral Patterns — SEC](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72)** — inadequate diversification, naïve diversification.
4. **[FINRA Regulatory Notice 24-13 (Rule 2270)](https://www.finra.org/rules-guidance/notices/24-13)** — риски day trading и маржи, убытки сверх депозита.
5. **[Stop Order — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)** — исполнение stop, slippage.
6. **Kelly, J. L. (1956).** *A New Interpretation of Information Rate.* — теоретическая основа optimal bet sizing (Bell System Technical Journal).
7. **[[IMOEX_RTS]]** — лимит веса бумаги 15% в индексе MOEX как ориентир концентрации.

---

## В автоматической системе

### Архитектурное правило

**Ни один ордер** в n8n не проходит без sub-workflow `calculate-position-size`:
1. Fetch `account_equity` (T-Invest / Binance).
2. Load `risk.yaml` из Obsidian.
3. Compute quantity from entry + stop distance.
4. Run concentration + heat checks.
5. Pass `quantity` to `place-bracket-order` ([[Stop_loss_take_profit]]).

### Code node (ядро)

```javascript
const equity = $json.account_equity;
const riskPct = $input.first().json.config.risk_per_trade; // 0.01
const entry = $json.entry_price;
const stop = $json.stop_price;
const lot = $json.lot_size || 1;
const tick = $json.tick_size || 0.01;

const riskPerUnit = Math.abs(entry - stop);
if (riskPerUnit <= 0) throw new Error('Invalid stop distance');

const riskAmount = equity * riskPct;
let units = Math.floor(riskAmount / riskPerUnit / lot) * lot;
const notional = units * entry;

// Concentration cap
const maxSingle = equity * $input.first().json.config.max_single_asset;
if (notional > maxSingle) {
  units = Math.floor(maxSingle / entry / lot) * lot;
}

// Min notional / zero check
if (units <= 0) {
  return [{ json: { status: 'SKIP', reason: 'quantity_zero_after_sizing' } }];
}

return [{
  json: {
    quantity: units,
    notional: units * entry,
    risk_rub: Math.min(riskAmount, units * riskPerUnit),
    risk_pct_effective: (units * riskPerUnit) / equity
  }
}];
```

### Portfolio heat check

```javascript
const openRisk = $json.open_positions.reduce((s, p) => s + p.risk_amount, 0);
const newRisk = $json.proposed_risk;
const maxHeat = $json.config.max_portfolio_heat * $json.equity;
if (openRisk + newRisk > maxHeat) throw new Error('Portfolio heat limit');
```

### LLM vs код

| Решает LLM | Решает код |
|------------|------------|
| Направление, confidence | quantity, notional |
| Предложение stop distance (ATR mult) | Финальный risk после caps |
| counter_thesis | reject if heat/concentration fail |

**G8** в [[LLM_rules_and_guardrails]]: LLM **никогда** не output `quantity` или `order_value`.

### Obsidian config `risk.yaml`

```yaml
risk_per_trade: 0.01          # 1% equity at stop
max_single_asset: 0.15        # 15% notional cap
max_portfolio_heat: 0.05      # 5% aggregate open risk
daily_loss_limit: 0.03        # circuit breaker
min_equity_to_trade: 50000    # RUB equivalent
```

### Circuit breaker

```
IF daily_pnl <= -daily_loss_limit × equity:
  → halt all trading flows until next calendar day (UTC+3)
  → Telegram CRITICAL + Obsidian incident note
```

### Журнал сделки

```yaml
trade_id: "2026-07-05-sber-002"
equity_at_entry: 500000
risk_pct_config: 0.01
risk_amount_planned: 5000
quantity: 660
notional: 165000
concentration_pct: 0.33
portfolio_heat_after: 0.02
sizing_method: fixed_fractional
sources_checked: [investor.gov-asset-allocation, finra-investing-basics]
```

### Мониторинг (weekly)

- Distribution `risk_pct_effective` vs config.
- Trades where concentration cap **clipped** quantity (signal quality vs limits).
- Correlation clusters inflating effective heat.

---

## Связанные темы

- [[Stop_loss_take_profit]]
- [[Portfolio_diversification]]
- [[Trader_psychology]]
- [[Cognitive_biases]]
- [[LLM_rules_and_guardrails]]
- [[Crypto_flow_design]]
- [[Securities_flow_design]]
- [[IMOEX_RTS]]

---

## Что изучить дальше

1. [[Stop_loss_take_profit]] — как stop distance входит в формулу sizing.
2. [[Portfolio_diversification]] — лимиты концентрации и корреляция.
3. [[Order_types]] — исполнение стопов и влияние на фактический risk.
4. [[Key_indicators_RSI_MACD]] — ATR для volatility-based sizing.
5. [[Finance_basics]] — risk tolerance и горизонт инвестирования.
