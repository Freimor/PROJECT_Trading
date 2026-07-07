---
title: Диверсификация портфеля
tags: [риск, диверсификация, портфель, asset-allocation]
sources:
  - https://www.investor.gov/introduction-investing/getting-started/asset-allocation
  - https://www.investor.gov/introduction-investing
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72
  - https://www.finra.org/investors/investing/investing-basics
  - https://www.finra.org/investors/investing/investing-basics/volatility
  - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4068889
  - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4840399
  - https://doi.org/10.1038/s41598-025-26337-x
updated: 2026-07-06
level: beginner
academic_sources: true
style: informational
---

# Диверсификация портфеля

> Диверсификация — распределение инвестиций между разными активами, секторами и рынками, чтобы снизить влияние неудачи одной позиции. SEC: «Don't put all your eggs in one basket».

## Главное

- Одна компания на весь капитал — банкротство уничтожает счёт; несколько бумаг ограничивают ущерб.
- Диверсификация внутри класса (секторы) и между классами (акции / облигации / cash).
- 10 altcoin с корреляцией к BTC ≈ одна BTC-позиция с лишними комиссиями.
- ETF упрощают диверсификацию, но sector ETF не равен broad index.
- Rebalancing возвращает портфель к целевым весам после движения рынка.

---

## Для новичка

Купили акции одной компании на весь капитал. Банкротство — потеря всего счёта.

Распределите между несколькими компаниями, облигациями и cash — падение одной бумаги ограничит, но не уничтожит портфель.

Investor.gov: факторы, ухудшающие один класс, могут улучшить другой. Диверсификация внутри класса дополняет диверсификацию между классами.

Для трейдера: 10 altcoin, движущихся с BTC, не снижают риск — нужна корреляция, не только количество тикеров.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | Diversification — распределение денег между инвестициями для снижения риска. | [Investor.gov: Asset Allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| 2 | Внутри класса: несколько акций/облигаций, разные отрасли. | [Investor.gov: Asset Allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| 3 | ETF упрощают диверсификацию; узкий sector ETF не гарантирует её. | [Investor.gov: Asset Allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| 4 | Inadequate diversification — портфель слишком сконцентрирован; повышает risk exposure. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 5 | Naïve diversification — равные доли без учёта риска каждой опции. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 6 | Familiarity bias — предпочтение знакомых инвестиций; ведёт к недостаточной диверсификации. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 7 | Rebalancing — возврат к целевым весам; «buy low, sell high» через дисциплину. | [Investor.gov: Asset Allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| 8 | FINRA: diversification помогает управлять волатильностью и тревогой. | [FINRA: Volatility](https://www.finra.org/investors/investing/investing-basics/volatility) |
| 9 | SEC: не класть все деньги в 1–2 акции; смесь stocks/bonds/cash снижает impact volatility. | [Investor.gov: Say NO GO to FOMO](https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/say-no-go-fomo) |

---

## Подробно: уровни диверсификации

### Уровень 1 — Внутри одного класса активов

**Акции MOEX:**
- Несколько эмитентов (не только SBER).
- Разные сектора: финансы, нефтегаз, IT, потребительский.
- Ликвидные бумаги из IMOEX top — [[MOEX_stocks]], [[IMOEX_RTS]].

**Криптовалюты:**
- BTC + ETH + ограниченный набор alt — но помните: многие alt **коррелируют** с BTC.
- Stablecoins как «cash-like» leg (с отдельными рисками эмитента).

### Уровень 2 — Между классами активов

| Класс | Роль в портфеле | Пример |
|-------|-----------------|--------|
| Акции | Рост, волатильность | IMOEX ETF, отдельные blue chips |
| Облигации | Доход, снижение volatility | ОФЗ, корпоративные |
| Cash / MMF | Ликвидность, резерв | Рублёвый остаток, USDT (осторожно) |
| Альтернативы | Опционально, высокий риск | Crypto allocation cap |

Investor.gov: allocation — **личное** решение, зависит от **time horizon** и **risk tolerance**.

### Уровень 3 — Между рынками и валютами

- MOEX (рубль) + глобальные индексы ([[Global_indices]]) — если доступно через брокера.
- Валютный риск: RTSI vs IMOEX расходятся при изменении USD/RUB — [[IMOEX_RTS]].

### Уровень 4 — Между стратегиями

| Стратегия | Горизонт | Риск |
|-----------|----------|------|
| DCA в ETF | Годы | Низкий-средний |
| Swing (LLM signals) | Дни-недели | Средний |
| Day trading | Часы | Высокий |

Разделение **капитала** между стратегиями предотвращает, чтобы агрессивный swing «съел» весь long-term портфель.

---

## Корреляция: когда «много активов» ≠ диверсификация

**Корреляция** — статистическая мера, насколько доходности двух активов движутся **вместе** (от −1 до +1).

| Корреляция | Интерпретация | Диверсификация |
|------------|---------------|----------------|
| +0.8 … +1.0 | Движутся почти синхронно | **Слабая** |
| +0.3 … +0.7 | Частичная связь | Умеренная |
| −0.3 … +0.3 | Слабая связь | **Хорошая** |
| Отрицательная | Часто в противофазе | Сильная (редко стабильна) |

**Пример crypto:** 5 altcoin с корреляцией 0,9 к BTC ≈ **одна** BTC-позиция с 5× fees.

**Расчёт (упрощённо, для monitor flow):**
```
returns_i = daily_pct_change(price_i)
correlation_matrix = corr(returns) over window N days
avg_pairwise_corr = mean of upper triangle
diversification_score = 1 - avg_pairwise_corr   // эвристика, не регуляторная метрика
```

> SEC **не** публикует пороги корреляции для розницы. Пороги 0,85 в автоматизации — **инженерное** правило системы, не норма SEC.

---

## Asset Allocation vs Diversification vs Rebalancing

| Концепция | Вопрос | Пример |
|-----------|--------|--------|
| **Asset allocation** | Сколько % в stocks/bonds/cash? | 60/30/10 |
| **Diversification** | Как **распределить** внутри каждого %? | 15 акций, 3 сектора |
| **Rebalancing** | Как **вернуть** целевые веса после рынка? | Продать акции после ралли |

Rebalancing «заставляет» продавать winners и покупать losers — дисциплина против [[Cognitive_biases]] (disposition effect, recency).

**Частота:** Investor.gov — rebalancing по интервалу (6–12 мес) или при отклонении веса **> preset %**; слишком частый rebalancing увеличивает costs.

---

## ETF и индексные продукты

Investor.gov: ETF/mutual funds **упрощают** владение «малой долей многих инвестиций».

**Проверки перед покупкой ETF:**
1. Top 10 holdings — не дублируют ваши прямые акции.
2. Sector concentration — tech-heavy ETF + tech stocks = double bet.
3. Expense ratio и tracking error — [[Index_ETF]].

**IMOEX ETF** — прокси диверсификации по российскому рынку с cap 15% на бумагу в индексе.

---

## Примеры

### Пример 1: Недиверсифицированный vs диверсифицированный (учебный)

**Портфель A — 100% одна акция:**
- 500 000 ₽ в GAZP.
- Падение GAZP на 20% → **−100 000 ₽** (−20% портфеля).

**Портфель B — 5 акций по 20%:**
- SBER, GAZP, LKOH, YNDX, PLZL — по 100 000 ₽.
- GAZP −20%, остальные 0% → **−20 000 ₽** (−4% портфеля).

> Упрощение: в реальности акции **коррелируют** (особенно на MOEX при stress). B лучше A, но не «безрисковый».

### Пример 2: Naïve diversification в crypto

| Актив | Вес |
|-------|-----|
| SOL | 20% |
| ADA | 20% |
| DOT | 20% |
| MATIC | 20% |
| LINK | 20% |

SEC классифицирует **naïve diversification**: равные доли без анализа риска. Если все alt падают с BTC на −30% — «5 корзин» не спасли.

**Улучшение:** cap crypto leg 10–15% total equity; внутри — BTC/ETH core + limited alt; monitor correlation.

### Пример 3: Rebalancing

| | Начало года | После ралли |
|---|-------------|-------------|
| Акции | 60% (300k) | 80% (400k) |
| Облигации | 30% (150k) | 15% (75k) |
| Cash | 10% (50k) | 5% (25k) |

Rebalance: продать акций на ~100k, купить облигации/cash до target 60/30/10.

### Пример 4: Familiarity bias (SEC)

Инвестор из Москвы держит только «знакомые» русские blue chips + employer stock. SEC: familiarity bias → **inadequate diversification** по географии и секторам.

---

## Частые ошибки новичков

1. **«У меня 10 монет — я диверсифицирован»** — игнор корреляции ([[Cognitive_biases]]: naïve diversification).
2. **Дублирование через ETF + акции** — двойной вес в одни и те же бумаги.
3. **Игнор rebalancing** — equity drift → портфель рискованнее, чем планировали.
4. **Диверсификация без position sizing** — много мелких позиций, но каждая с огромным стопом ([[Position_sizing]]).
5. **Home bias** — только домашний рынок; SEC: familiarity bias.
6. **Секторный concentration** — «все AI-акции» или «все DeFi».
7. **Over-diversification для active trading** — 30 позиций × комиссия = drag; для swing достаточно 5–10 **некоррелированных** идей.
8. **Забыли cash leg** — нет резерва на margin call / DCA / психологический buffer.

---

## FAQ

### Сколько акций нужно для диверсификации?

SEC не даёт магического числа. Через ETF — сотни бумаг в одном продукте. При прямом владении — **несколько секторов**, не 1–2 тикера ([Investor.gov: FOMO](https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/say-no-go-fomo)).

### Диверсификация убирает риск полностью?

**Нет.** Systematic risk (рынок в целом) остаётся. Diversification снижает **specific risk** (одна компания, один сектор).

### Crypto + MOEX — это диверсификация?

**Частично.** Разные классы и регуляторика, но в crisis корреляции могут **вырости**. Нужен monitor и caps.

### Как часто rebalance в автоматизации?

Investor.gov: не слишком часто. В n8n v1 — **weekly alert**, rebalance только с human approval.

### IMOEX 15% cap — применять к портфелю?

Это правило **индекса**, не закон для частного инвестора. Разумный **ориентир** max single stock weight — см. [[Position_sizing]] `max_single_asset`.

### LLM может «предложить» новый актив вне universe?

Только если проходит whitelist + concentration check. Иначе reject — [[LLM_rules_and_guardrails]].

---

## Ключевые понятия

| Термин | Определение | Источник |
|--------|-------------|----------|
| Diversification | Распределение между инвестициями для снижения риска | [Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| Asset allocation | Доли классов активов | [Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| Inadequate diversification | Избыточная концентрация | [SEC Bulletin #72](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| Naïve diversification | Равные доли без учёта риска | [SEC Bulletin #72](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| Rebalancing | Возврат к target weights | [Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| Correlation | Совместное движение доходностей | Статистика / risk management |
| Familiarity bias | Предпочтение «знакомого» | [SEC Bulletin #72](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |

---

## Проверенные источники

1. **[Asset Allocation and Diversification — Investor.gov (SEC/OIEA)](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)** — определения, rebalancing, ETF, risk tolerance.
2. **[Introduction to Investing — Investor.gov](https://www.investor.gov/introduction-investing)** — базовые принципы для розничных инвесторов.
3. **[Investor Bulletin: Behavioral Patterns — SEC](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72)** — inadequate/naïve diversification, familiarity bias.
4. **[Say NO GO to FOMO — Investor.gov](https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/say-no-go-fomo)** — диверсификация vs impulsive trend chasing.
5. **[Investing Basics — FINRA](https://www.finra.org/investors/investing/investing-basics)** — allocation, не ставить всё на одну сделку.
6. **[Volatility — FINRA](https://www.finra.org/investors/investing/investing-basics/volatility)** — diversification как управление volatility и эмоциями.
7. **[[IMOEX_RTS]]**, **[[Index_ETF]]** — инструменты диверсификации на MOEX.

---

## Академические источники

Полный свод университетских курсов и научных публикаций (2021+) — в заметке [[Academic_sources]].

| Учреждение | Ресурс (2021+) | Что подтверждает для этой темы | Ссылка |
|-----------|----------------|--------------------------------|--------|
| SSRN | Jaeger & Marinelli (2022) — abstract 4068889 | Network-based diversification через multilayer graphs | [papers.ssrn.com/sol3/papers.cfm?abstract_id=406...](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4068889) |
| SSRN | Torrente & Uberti (2024) — abstract 4840399 | Диверсификация из risk measures, long-short стратегии | [papers.ssrn.com/sol3/papers.cfm?abstract_id=484...](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4840399) |
| Nature Scientific Reports | Agal, Raulji, Odedra (2025) | ML + risk-based asset allocation для диверсификации | [doi.org/10.1038/s41598-025-26337-x](https://doi.org/10.1038/s41598-025-26337-x) |
| MIT | 15.481X Adaptive Markets (Fall 2022) | Динамическая аллокация в адаптивных рынках | [ocw.mit.edu/courses/15-481x-adaptive-markets-fi...](https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/) |

---

## В автоматической системе

### Portfolio monitor flow (n8n, weekly)

```
Schedule (Sunday 10:00 MSK)
  → Fetch positions (T-Invest API + Binance)
  → Fetch prices / returns 60d
  → Python/Code: weights, correlation matrix, sector map
  → IF alerts → Ollama summary → Obsidian note
  → Telegram digest (read-only)
```

### Pre-trade concentration check

```javascript
const totalEquity = $json.total_equity;
const currentValue = $json.positions[$json.symbol]?.value || 0;
const orderValue = $json.quantity * $json.price;
const newWeight = (currentValue + orderValue) / totalEquity;

if (newWeight > $json.config.max_single_asset) {
  throw new Error(`Concentration: ${$json.symbol} would be ${(newWeight*100).toFixed(1)}%`);
}

// Crypto cluster: sum all crypto weights
const cryptoWeight = $json.positions
  .filter(p => p.asset_class === 'crypto')
  .reduce((s, p) => s + p.value, 0) + 
  ($json.asset_class === 'crypto' ? orderValue : 0);
if (cryptoWeight / totalEquity > $json.config.max_crypto_allocation) {
  throw new Error('Crypto allocation cap exceeded');
}
```

### Correlation alert (engineering rule)

```javascript
const THRESHOLD = 0.85;  // system config, not SEC mandate
for (const [a, b] of highCorrPairs) {
  const combined = weights[a] + weights[b];
  if (corr[a][b] > THRESHOLD && combined > 0.25) {
    alerts.push({ type: 'CORR_CLUSTER', a, b, corr: corr[a][b], combined });
  }
}
```

### Target allocation template (Obsidian `portfolio.yaml`)

```yaml
targets:
  equities_moex: 0.50
  bonds: 0.25
  crypto: 0.10
  cash: 0.15
rebalance_band: 0.05      # alert if drift > 5%
max_single_asset: 0.15
max_crypto_allocation: 0.15
correlation_window_days: 60
correlation_alert_threshold: 0.85
auto_rebalance: false     # v1: human approval only
```

### LLM report prompt (fragment)

```
Summarize portfolio diversification status for a beginner.
Cite only facts from input JSON. Do not invent performance numbers.
Flag: concentration, correlation clusters, drift from targets.
Recommend: rebalance review if drift > rebalance_band (no auto-trade).
```

### Obsidian weekly note

```yaml
week: 2026-W27
total_equity: 1250000
weights:
  equities_moex: 0.58
  crypto: 0.12
  cash: 0.30
drift_alerts: [equities_moex +8% vs target]
correlation_alerts: [SOL-BTC 0.91, combined 18%]
diversification_actions: manual_review
sources_checked: [investor.gov-asset-allocation, sec-behavioral-patterns-72]
```

### Rebalancing policy (v1)

- **Alert only** — оператор решает.
- v2 (optional): auto-rebalance **cash leg** only (least disruptive).
- Never rebalance on **intraday** volatility spike without cooldown — [[Trader_psychology]].

---

## Связанные темы

- [[Position_sizing]]
- [[Stop_loss_take_profit]]
- [[Finance_basics]]
- [[Index_ETF]]
- [[IMOEX_RTS]]
- [[Global_indices]]
- [[MOEX_stocks]]
- [[Cognitive_biases]]
- [[Trader_psychology]]

---

## Что изучить дальше

1. [[Finance_basics]] — классы активов и risk/return tradeoff.
2. [[Index_ETF]] — пассивная диверсификация через один продукт.
3. [[Position_sizing]] — лимиты концентрации на уровне сделки.
4. [[Cognitive_biases]] — familiarity, naïve diversification.
5. [[Global_indices]] — межрыночная диверсификация.
