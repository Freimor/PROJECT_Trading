---
title: Когнитивные искажения
tags: [психология, biases, FOMO, loss-aversion, prospect-theory]
sources:
  - https://www.jstor.org/stable/1914185
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-18
  - https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/say-no-go-fomo
  - https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/the-behavioral-biases-of-individuals
  - https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/rfbr-v2-n1-1-pdf.pdf
  - [[Academic_sources]]
updated: 2026-07-06
level: beginner
academic_sources: true
style: informational
---

# Когнитивные искажения

> **Cognitive biases** — систематические ошибки мышления на рынке. Kahneman, Tversky, CFA: инвесторы не всегда рациональны. Правила и автоматизация снижают влияние bias, но не убирают его.

## Главное

- Мозг использует heuristics — на рынке они часто дорого стоят (recency, anchoring, confirmation).
- **Loss aversion** и **disposition effect**: держим losers, режем winners — нужен stop до входа.
- CFA: cognitive errors частично лечатся чеклистами; emotional biases — только адаптация через процессы.
- LLM обязан выдавать `counter_thesis` и `biases_detected`; код reject при конфликте с rules.
- Осознание bias ≠ его исчезновение — нужен журнал с тегами `#bias/FOMO`.

---

## Для новичка

Три зелёные свечи — «тренд навсегда» (recency). Купили @ 100, цена 90 — «дешево» (anchoring). Ищете только новости «за» long (confirmation). Боитесь −5%, но фиксируете +2% (loss aversion / disposition).

SEC в Bulletin #72 — девять investing behaviors, многие совпадают с biases ([источник](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72)).

В системе: LLM → `counter_thesis` + `biases_detected`; код reject — [[LLM_prompts_trading]], [[LLM_rules_and_guardrails]].

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **Prospect Theory (1979):** люди принимают решения в рамках **value function**, где **потери** обрабатываются иначе, чем **прибыли** — функция **круче для losses** (loss aversion); choices depend on **reference point**. | [Kahneman & Tversky, Econometrica (JSTOR)](https://www.jstor.org/stable/1914185) |
| 2 | **Disposition effect:** tendency **hold losing investments too long** and **sell winning investments too soon**; sold winners often **continue to outperform** held losers. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 3 | **Familiarity bias:** favor investments from own country/company or **glamour/popular** names → **inadequately diversified** portfolio, **higher risk exposure**. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 4 | **Momentum investing:** belief that large price **increases will be followed by additional gains** (and declines by further declines) — behavioral pattern identified in investor research for SEC. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 5 | **Naïve diversification:** equal allocation across N options **without** regard to each option's risk — may **increase** risk exposure. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 6 | **Noise trading:** buy/sell **without fundamental data**; poor timing, trend-following, **overreaction** to news. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 7 | **Manias and panics:** rapid price rise (collective enthusiasm) → contraction/panic selling — collective behavioral dynamic. | [SEC: Behavioral Patterns](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| 8 | Social sentiment tools may lead to **emotionally-driven, impulsive** decisions — **risky** approach to investing. | [SEC/FINRA: Social Sentiment Bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-18) |
| 9 | CFA Institute: biases split into **cognitive errors** (faulty reasoning, **easier to moderate**) and **emotional biases** (feelings, **harder to correct**, adapt only). Emotional include **loss aversion, overconfidence, self-control, status quo, endowment, regret aversion**. | [CFA: Behavioral Biases of Individuals](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/the-behavioral-biases-of-individuals) |
| 10 | CFA (Risk Profiling brief): **loss aversion** — conservative investors feel **pain of losses more than pleasure of gains** vs other client types; may **hold losing investments too long**. | [CFA: Risk Profiling through Behavioral Finance Lens (PDF)](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/rfbr-v2-n1-1-pdf.pdf) |

---

## Подробно: таксономия CFA + SEC mapping

### Cognitive errors (CFA — можно частично «исправить»)

| Bias | Суть в трейдинге | SEC-related pattern |
|------|------------------|---------------------|
| **Anchoring** | Фиксация на purchase price, «круглой» цифре, старом high | — |
| **Confirmation bias** | Только аргументы «за» позицию | Noise trading (ignore contradicting data) |
| **Representativeness** | «Похоже на 2021 → будет так же» | Momentum / manias |
| **Availability** | Решение по последней яркой новости | Noise trading, recency |
| **Hindsight bias** | «Я знал, что упадёт» после факта | Overconfidence follow-on |

### Emotional biases (CFA — adapt, not eliminate)

| Bias | Суть в трейдинге | SEC-related pattern |
|------|------------------|---------------------|
| **Loss aversion** | Боль от −X > радость от +X (prospect theory) | Disposition effect |
| **Overconfidence** | Слишком крупные позиции, overtrading | Active trading underperformance |
| **Self-control** | Нарушение long-term plan ради short-term thrill | FOMO, social sentiment |
| **Status quo** | Не rebalance, не закрыть loser | Inadequate diversification |
| **Endowment** | «Мой» актив кажется лучше рынка | Familiarity bias |
| **Regret aversion** | Не войти из страха regret / не выйти из страха «продам — вырастет» | Disposition effect |

---

## Ключевые искажения в трейдинге (детально)

### 1. Loss aversion (Prospect Theory)

Kahneman & Tversky (1979): потери «весят» больше прибыли → hold losers, sell winners early, skip stop.

**Mitigation:** pre-set stop ([[Stop_loss_take_profit]]); exit по правилам, не «когда почувствую».

### 2–10. Остальные bias

| Bias | Mitigation |
|------|------------|
| Disposition effect | Симметричные SL/TP, time stop |
| FOMO | Entry rules, cooldown, `#bias/FOMO` |
| Anchoring | SL от market structure, не от purchase price |
| Confirmation | LLM `counter_thesis` обязателен |
| Recency | Backtest ≥ 60–90 дней |
| Overconfidence | Fixed sizing ([[Position_sizing]]) |
| Momentum/Mania | Vol filter, no chase после >N% day |
| Familiarity | Whitelist, caps ([[Portfolio_diversification]]) |
| Naïve diversification | Risk-parity, correlation monitor |
| Noise trading | Checklist, no social-only signals |

---

## Таблица: Bias → Проявление → Противоядие

| Bias | Проявление | Противоядие в системе |
|------|------------|----------------------|
| FOMO | Chase после pump | Cooldown, extension filter, SEC-style plan |
| Loss aversion | No stop, hold loser | Bracket orders mandatory |
| Anchoring | SL от purchase price | market_structure reference |
| Confirmation | Ignore bear case | LLM counter_thesis |
| Recency | Overweight last week | Long backtest window |
| Overconfidence | Size ↑ after wins | Fixed fractional sizing |
| Disposition | Cut winners, hug losers | Symmetric rules, time stop |
| Familiarity | Only «known» stocks | Diversification caps |
| Naïve div. | 5 equal alts | Correlation cluster alert |
| Noise trading | Trade on rumor | Fundamental/technical checklist |

---

## Примеры

### Пример 1: Loss aversion + disposition (классика)

| Позиция | Entry | Now | Действие трейдера | Rational rule |
|---------|-------|-----|-------------------|---------------|
| Winner | 100 | 115 | Sell @ 110 (too early) | TP @ 120 or trail |
| Loser | 100 | 82 | Hold «until breakeven» | Stop @ 95 |

SEC: sold winner may **continue outperform** held loser.

### Пример 2: FOMO на social hype

Twitter/X trend «$TICKER to moon» → buy at +40% day.

SEC/FINRA Social Sentiment Bulletin: emotionally-driven, impulsive — **risky**; create **long-term financial plan**.

**System:** `signal_source: social` → reject; require `confidence` from multi-factor model.

### Пример 3: Anchoring к «старой цене BTC»

«BTC был $100k, сейчас $60k — cheap» → DCA без stop.

Anchoring на ** irrelevant reference**. Decision должен быть по **current setup** + risk limits.

### Пример 4: Confirmation в LLM workflow

LLM output только bullish bullets → operator excited.

**Fix:** structured JSON with mandatory `counter_thesis`:
```json
{
  "signal": "long",
  "confidence": 0.72,
  "counter_thesis": "Funding rate elevated; macro event Thursday",
  "biases_detected": ["recency — 5d rally", "confirmation — only bullish news cited"],
  "recommendation": "reject"
}
```

### Пример 5: Naïve diversification (SEC)

Portfolio: 5 altcoins 20% each. All drop with BTC −25%.

SEC: naïve diversification **may increase risk** depending on options — here correlated options.

---

## Частые ошибки новичков

1. **Думать «я осознал bias → он исчез»** — CFA: emotional biases **persist**; нужны processes.
2. **LLM как oracle без counter_thesis** — усиливает confirmation.
3. **Journal без tags** — не видите повторяющийся FOMO.
4. **Разный стандарт для «любимой» акции** — endowment bias.
5. **Покупка на mania** — SEC manias/panics pattern.
6. **Игнор fees в momentum chasing** — SEC: focus past performance, ignore fees.
7. **Статистика «у меня 80% win rate» на 10 сделках** — overconfidence + small sample.
8. **Отключить bias filter «один раз»** — slippery slope to noise trading.

---

## FAQ

### Чем cognitive отличается от emotional bias (CFA)?

**Cognitive** — ошибки **мышления** (можно обучением/чеклистами частично снизить). **Emotional** — **чувства** (loss aversion, overconfidence); **adapt** через rules, не «переубедить себя».

### Loss aversion = всегда плохо?

Prospect theory описывает **как люди decide**, не moral judgment. Проблема — когда bias **ломает** risk management (no stop, disposition effect).

### Какой коэффициент loss/gain (2:1, 2.5:1)?

Kahneman & Tversky (1979) доказывают **asymmetry**; exact ratio **зависит от контекста** эксперимента. **Не цитируйте** точное число как universal law без указания источника эксперимента. CFA описывает qualitatively: pain of losses **more than** pleasure of gains.

### Может ли LLM «обнаружить» bias?

**Partially** — pattern in prompt text (recency language). Code: `biases_detected.length > 0 AND confidence < 0.75` → reject. **Не** заменяет human review.

### Все 9 SEC behaviors = biases?

SEC называет их **investing behaviors**, не clinical biases — но overlap высокий (disposition, momentum, noise, diversification).

### Автоматизация убирает biases?

**Снижает** execution gaps (stop hesitation). **Не убирает** design-time bias (overfit backtest, cherry-picked universe).

---

## Ключевые понятия

| Термин | Определение | Источник |
|--------|-------------|----------|
| Prospect theory | Reference-dependent choices, loss aversion | [Kahneman & Tversky, 1979](https://www.jstor.org/stable/1914185) |
| Loss aversion | Losses weigh heavier than gains | Prospect theory; CFA |
| Disposition effect | Hold losers, sell winners early | [SEC Bulletin #72](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |
| Cognitive error | Faulty reasoning | [CFA Institute](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/the-behavioral-biases-of-individuals) |
| Emotional bias | Feeling-driven | [CFA Institute](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/the-behavioral-biases-of-individuals) |
| FOMO | Fear of missing out | [Investor.gov](https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/say-no-go-fomo) |
| Noise trading | Trade without fundamentals | [SEC Bulletin #72](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72) |

---

## Проверенные источники

1. **Kahneman, D., & Tversky, A. (1979).** *Prospect Theory: An Analysis of Decision under Risk.* Econometrica, 47(2), 263–291. [JSTOR](https://www.jstor.org/stable/1914185)
2. **[Investor Bulletin: Behavioral Patterns of U.S. Investors — SEC/OIEA](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-72)** — disposition effect, momentum, naïve diversification, noise trading, manias, familiarity, active trading.
3. **[Social Sentiment Investing Tools — SEC/FINRA](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-18)** — impulsive emotionally-driven decisions.
4. **[Say NO GO to FOMO — Investor.gov](https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/say-no-go-fomo)** — FOMO, influencers, stick to long-term plan.
5. **[The Behavioral Biases of Individuals — CFA Institute](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/the-behavioral-biases-of-individuals)** — cognitive vs emotional taxonomy, mitigation framework.
6. **[Risk Profiling through a Behavioral Finance Lens — CFA Institute Research Foundation (PDF)](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/rfbr-v2-n1-1-pdf.pdf)** — loss aversion in client profiling.
7. **Library of Congress Report** (2010, cited in SEC Bulletin #72) — primary behavioral investor research.

---

## Академические источники

См. также: [[Academic_sources]].

| Категория | Ресурс | Что подтверждает | URL |
|---|---|---|---|
| JFE | Liu et al. (2022) — Taming the bias zoo | 156 behavioral biases → 13 meta-factors | https://doi.org/10.1016/j.jfineco.2021.06.001 |
| Review of Behavioral Finance | MOEX herding (2023) | Стадное поведение при падениях после 02.2022 | https://doi.org/10.1108/rbf-01-2023-0014 |
| BIS Bulletin 69 | Retail crypto losses | ~75% розницы в убытке при BTC > $20k | https://www.bis.org/publ/bisbull69.pdf |
| MIT / A. Lo (2022) | 15.481x | Режимность рынков, anti-overfit guardrails | https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/ |

---

## В автоматической системе

### LLM structured output schema

```json
{
  "signal": "long | short | flat",
  "confidence": 0.0,
  "thesis": "string",
  "counter_thesis": "required — min 1 bear argument for long",
  "biases_detected": ["array of strings"],
  "reference_points_ignored": ["purchase_price", "52w_high"],
  "recommendation": "approve | reject | human_review"
}
```

### n8n rejection rules

```javascript
const o = $json.llm_output;
const rules = [];

if (!o.counter_thesis || o.counter_thesis.length < 20) {
  rules.push('MISSING_COUNTER_THESIS');
}
if (o.biases_detected?.length > 0 && o.confidence < 0.75) {
  rules.push('BIAS_LOW_CONFIDENCE');
}
if (/moon|guaranteed|100%|sure thing/i.test(o.thesis)) {
  rules.push('HYPE_LANGUAGE');
}
if ($json.signal_source === 'social_sentiment') {
  rules.push('SEC_SOCIAL_SENTIMENT_RISK');
}

return [{ json: { approved: rules.length === 0, reject_reasons: rules } }];
```

### Anchoring guard (Code node)

```javascript
// SL/TP from market structure only
const { swing_low, atr_stop } = $json.structure;
const stop = Math.min(swing_low, $json.entry - atr_stop);
// Explicitly DO NOT use: $json.user_avg_entry, $json.fifty_two_week_high
return [{ json: { stop_price: stop, anchor_bias_blocked: true } }];
```

### Obsidian bias analytics

```yaml
# Tag trades for monthly review
tags: [bias/FOMO, bias/anchoring]
trade_id: 2026-07-05-btc-003
biases_detected_at_entry: [recency]
outcome: loss
lesson: "Wait for pullback rule violated"
```

Weekly script: count trades by `bias/*` tag vs PnL — **internal metric only**.

### Prompt fragment (Ollama)

```
You are a risk-aware trading analyst. Apply CFA behavioral finance taxonomy.
List biases_detected honestly (recency, confirmation, FOMO, anchoring, overconfidence).
counter_thesis is MANDATORY and must contradict thesis.
Do not use hype language. Cite no performance statistics unless in input data.
```

### Integration map

| Bias | System component |
|------|------------------|
| Loss aversion | [[Stop_loss_take_profit]] bracket |
| Overconfidence | [[Position_sizing]] fixed % |
| FOMO | Cooldown + extension filter |
| Confirmation | LLM counter_thesis |
| Familiarity | Portfolio whitelist |
| Naïve div. | [[Portfolio_diversification]] correlation |
| Noise | Checklist + no social-only signals |

---

## Связанные темы

- [[Trader_psychology]]
- [[Stop_loss_take_profit]]
- [[Position_sizing]]
- [[Portfolio_diversification]]
- [[LLM_rules_and_guardrails]]
- [[LLM_prompts_trading]]

---

## Что изучить дальше

1. [[Trader_psychology]] — дисциплина, journal, cooldown.
2. [[Stop_loss_take_profit]] — mechanical counter to loss aversion.
3. [[Position_sizing]] — counter to overconfidence.
4. [[Portfolio_diversification]] — familiarity & naïve diversification.
5. Prospect Theory — полный текст [Kahneman & Tversky, 1979](https://www.jstor.org/stable/1914185) для углублённого чтения.
