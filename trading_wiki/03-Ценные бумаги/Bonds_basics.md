---
title: Основы облигаций
tags: [ценные бумаги, облигации, ОФЗ, fixed income, YTM]
sources:
  - https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds
  - https://www.finra.org/investors/investing/investment-products/bonds
  - https://www.sec.gov/answers/bond.htm
  - https://www.moex.com/s1160
  - https://www.cbr.ru/hd_base/KeyRate/
  - https://wp.hse.ru/fe/BRP/86/2022
  - https://cfjournal.hse.ru/
  - https://bulletin.stanford.edu/courses/2090781
updated: 2026-07-06
level: beginner
academic_sources: true
style: informational
---

# Основы облигаций

> Облигация (bond) — долговая ценная бумага: инвестор одалживает деньги эмитенту, получает купон и номинал при погашении (если нет default).

## Главное

- Купон — периодические проценты; номинал — сумма при погашении.
- Цена на бирже колеблется: при росте ставок старые облигации обычно дешевеют.
- ОФЗ — облигации Минфина РФ; корпоративные — выше credit risk.
- При покупке платите цену + НКД (накопленный купонный доход).
- Для automation облигации — invest sleeve, не intraday trading.

---

## Для новичка

Упрощённо: вы даёте заём 1000 ₽ на 3 года. Каждые 6 месяцев — купон (например, 50 ₽). Через 3 года — возврат 1000 ₽ номинала.

На бирже облигация торгуется не всегда по номиналу. Если рынок требует более высокую доходность, цена падает ниже 100% от номинала.

ОФЗ торгуются на MOEX. Корпоративные облигации — компании РФ.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | Bond — loan investor to borrower; interest и principal at maturity. | [Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |
| 2 | SEC: bond market price может отличаться от face value; при росте ставок цена обычно падает. | [SEC.gov: Bonds](https://www.sec.gov/answers/bond.htm) |
| 3 | FINRA: interest rate risk — при росте ставок цена облигаций падает. | [FINRA: Bonds](https://www.finra.org/investors/investing/investment-products/bonds) |
| 4 | FINRA: credit risk — эмитент может не выплатить interest или principal. | [FINRA: Bonds](https://www.finra.org/investors/investing/investment-products/bonds) |
| 5 | Ключевая ставка Банка России — на официальном сайте ЦБ. | [CBR: Key rate](https://www.cbr.ru/hd_base/KeyRate/) |
| 6 | MOEX — площадка торговли облигаций РФ. | [MOEX calendar](https://www.moex.com/s1160) |
| 7 | Default — эмитент не выполняет обязательные платежи. | [Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |

---

## Ключевые параметры

| Параметр | Описание |
|----------|----------|
| **Номинал (face/par value)** | Сумма погашения (напр. 1000 ₽) |
| **Купон (coupon rate)** | Годовой процент от номинала |
| **Дата погашения (maturity)** | Когда возвращается номинал |
| **Цена (% от номинала)** | Рыночная котировка на MOEX |
| **YTM (yield to maturity)** | Полная доходность при удержании до погашения |
| **Duration** | Чувствительность цены к изменению ставок |
| **Кредитный рейтинг** | Оценка надёжности эмитента (рейтинговые агencies) |

---

## Цена и процентные ставки

### Inverse relationship

Когда **новые** облигации выпускаются с **более высоким** купоном (из‑за роста ключевой ставки), **старые** с низким купоном становятся менее привлекательными → их **цена падает**, пока YTM не выровняется с рынком.

SEC и FINRA описывают это как fundamental **interest rate risk**.

### Пример (учебный)

| | Облигация A (старая) | Облигация B (новый выпуск) |
|---|---------------------|---------------------------|
| Купон | 8% | 12% |
| Номинал | 1000 ₽ | 1000 ₽ |
| Рыночная цена | ~833 ₽ (illustrative) | ~1000 ₽ |

Цифры иллюстративны; реальный YTM считайте по MOEX ISS или калькулятору брокера.

---

## Типы облигаций на MOEX

| Тип | Эмитент | Риск default |
|-----|---------|--------------|
| **ОФЗ** | Минфин РФ | Sovereign (не zero) |
| **Корпоративные** | Компании | Credit risk |
| **Субфедеральные / муниципальные** | Регионы | Выше ОФЗ, ниже many corporates |
| **Замещающие** | Спец. категории | Читать prospectus |

**НКД (накопленный купонный доход)** — часть купона, накопленная с last coupon date; при покупке платите **цена + НКД**.

---

## Риски

| Риск | Описание |
|------|----------|
| **Interest rate** | Падение цены при росте ставок |
| **Credit** | Default эмитента |
| **Inflation** | Real return ниже inflation |
| **Liquidity** | Wide spread на illiquid names |
| **Reinvestment** | Купоны реинвестируются по новым (возможно ниже) ставкам |

---

## ОФЗ и ключевая ставка ЦБ

**Ключевая ставка** Банка России — ориентир для денежно-кредитной политики. Изменения влияют на ожидания по доходности ОФЗ и корпоративного сегмента.

Automation: RSS/API ЦБ → trigger **review** bond ladder, не panic sell ([[Securities_flow_design]]).

---

## Примеры

### Пример 1: Bond ladder

Портфель ОФЗ с погашением 2026, 2027, 2028 — снижает **reinvestment risk** одной даты.

### Пример 2: Duration intuition

Duration 5 лет → при росте yields на **1 п.п.** цена ≈ −5% (упрощение; convexity уточняет).

### Пример 3: MOEX ISS quote

```
GET https://iss.moex.com/iss/engines/stock/markets/bonds/securities/SU26238RMFS4.json
```

SECID и ISIN — из актуального списка MOEX.

### Пример 4: Tax

Купонный доход облагается налогом — [[Russia_tax_basics]]; automation логирует gross/net.

---

## Частые ошибки новичков

1. **«Облигация = депозит»** — цена на бирже **колеблется**.
2. **Игнор НКД** — surprise на сумму сделки.
3. **Погоня за highest yield** — credit trap (default risk).
4. **Путать price % и абсолютную цену** — MOEX quotes often in % of face.
5. **Intraday LLM trading ОФЗ** — нецелевое use case; bonds = invest sleeve.
6. **Не diversifying issuers** — concentration в one corporate.

---

## FAQ

### ОФЗ могут default?

Sovereign default — low probability historically for major economies, **not impossible**; read risk disclosures.

### YTM где взять?

Broker terminal, MOEX ISS, fund factsheets.

### Облигации vs БПИФ облигаций?

БПИФ — diversification + management fee; см. [[ETFs_and_funds]].

### T+ settlement?

Аналогично акциям MOEX — проверяйте актуальные правила расчётов.

### LLM для bond picking?

**Conservative mode only:** LLM **report** on duration impact при изменении key rate; **не** intraday orders.

---

## Проверенные источники

1. **[Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds)**
2. **[FINRA: Bonds](https://www.finra.org/investors/investing/investment-products/bonds)**
3. **[SEC.gov: Bonds](https://www.sec.gov/answers/bond.htm)**
4. **[CBR: Key rate](https://www.cbr.ru/hd_base/KeyRate/)**
5. **[MOEX Trading calendar](https://www.moex.com/s1160)**
6. **[MOEX ISS Reference](https://iss.moex.com/iss/reference/)**

---

## Академические источники

Полный свод университетских курсов и научных публикаций (2021+) — в заметке [[Academic_sources]].

| Учреждение | Ресурс (2021+) | Что подтверждает для этой темы | Ссылка |
|-----------|----------------|--------------------------------|--------|
| ВШЭ | Dobrynskaya & Dubrovskiy — BRP 86/FE/2022 | Крипто vs акции: risk factors | [wp.hse.ru/fe/BRP/86/2022](https://wp.hse.ru/fe/BRP/86/2022) |
| Financial Analysts J. | Ivashchenko & Kosowski (2024) | Capacity облигационных стратегий; turnover | [doi.org/10.1080/0015198X.2024.2360390](https://doi.org/10.1080/0015198X.2024.2360390) |
| ВШЭ | Lapshin — BRP 88–89/FE/2022 | Иммунизация облигационного портфеля | [wp.hse.ru/en/prepfr_FE](https://wp.hse.ru/en/prepfr_FE) |

---

## В автоматической системе

### Режим `bond_invest` (не intraday)

Облигации — **conservative sleeve** портфеля; отдельный workflow от `moex-securities-flow`.

```yaml
strategy: bond_ladder
max_duration_years: 5
issuer_allowlist: [OFZ]  # conservative default
rebalance_trigger: key_rate_change
llm_role: report_only
```

### Workflow `bond-ladder-flow`

```
Cron: weekly + on CBR key rate publish
  → Fetch CBR key rate (HTML/RSS parse)
  → MOEX ISS: YTM, duration for watchlist SECIDs
  → Code: portfolio duration weighted avg
  → IF key_rate_change > threshold → flag review
  → Ollama: markdown report «impact on ladder»
  → Obsidian: bonds/YYYY-MM-DD.md
  → NO automatic market sell unless human rule enabled
```

### MOEX ISS bond data

```
GET https://iss.moex.com/iss/engines/stock/markets/bonds/securities.json
GET https://iss.moex.com/iss/engines/stock/markets/bonds/securities/{SECID}/candles.json
```

### bond_watchlist.yaml (Obsidian)

```yaml
bonds:
  - secid: SU26238RMFS4
    name: "ОФЗ пример — verify SECID"
    maturity: "2028-05-03"
    coupon_pct: 12.0
    face_value: 1000
    currency: RUB
    last_ytm: null  # fill from ISS
sources:
  - https://www.cbr.ru/hd_base/KeyRate/
  - https://iss.moex.com/iss/reference/
```

### Duration alert (Code)

```javascript
const oldDuration = $json.portfolio_duration;
const shockBp = 100; // 1% rate rise scenario
const priceChangePct = -oldDuration * (shockBp / 10000);
return [{ json: { scenario: 'rate_up_1pct', est_price_change_pct: priceChangePct } }];
```

### LLM prompt (report only)

```
Key rate: {{cbr_key_rate}}% (source: cbr.ru)
Portfolio duration: {{duration}} years
Task: Explain in plain Russian impact of +1pp rate hike on bond prices.
Do NOT recommend specific trades.
Output: markdown paragraph only.
```

### Integration with macro-flow

`macro-context-flow` passes `ru_key_rate`, `us_10y` (FRED) → bond report compares local vs global rates.

### Guardrails

- **G10** [[LLM_rules_and_guardrails]]: no bond market orders from LLM without `human_approved: true`.
- Validate SECID exists on MOEX before any manual order template.

---

## Связанные темы

- [[Finance_basics]]
- [[MOEX_stocks]]
- [[ETFs_and_funds]]
- [[Russia_tax_basics]]
- [[Securities_flow_design]]
- [[Global_indices]]

---

## Callable и amortizing bonds

**Callable bond** — эмитент может **досрочно погасить** по call date — investor faces **reinvestment risk**.

**Amortizing** — номинал возвращается частями по schedule, не только в maturity.

Читайте **bond terms** на MOEX card; automation watchlist хранит `callable: true/false`.

---

## Инфляционные ОФЗ (ОФЗ-ИН)

Российские **inflation-linked** bonds привязаны к inflation index — защита nominal cash flows в theory; pricing depends on breakeven inflation expectations. Separate SEC analog: TIPS in US ([Investor.gov bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds)).

---

### Key rate webhook (conceptual)

```
CBR publish key rate
  → n8n Webhook / RSS trigger
  → bond-ladder-flow: recalc duration
  → Ollama report only
  → Telegram summary with link cbr.ru/hd_base/KeyRate/
```

No auto-sell unless `human_approved: true` in config.

---

## Credit ratings (overview)

Rating agencies assign **investment grade** vs **high yield** — FINRA explains ratings influence required yield ([FINRA bonds](https://www.finra.org/investors/investing/investment-products/bonds)). MOEX corporate bonds — check issuer disclosures; **no** universal wiki rating table (changes over time).

### Yield curve shape (conceptual)

| Shape | Typical interpretation (simplified) |
|-------|-------------------------------------|
| Normal (upward) | Longer maturity → higher YTM |
| Inverted | Short rates > long — recession watch in US literature |
| Flat | Transition period |

Use CBR and MOEX data for **local** curve; не extrapolate US inversion rules blindly to RF market.

---

## Практический чеклист bond investor

1. Define allocation % fixed income in portfolio YAML.
2. Build ladder ≥3 maturities для OFZ sleeve.
3. Subscribe CBR key rate RSS/API.
4. Never use intraday price noise for sell rules.
5. Calculate portfolio duration quarterly.
6. Tax: track coupon dates for reporting.

---

## Расширенный FAQ

### Subordinated debt?

Higher yield, lower priority in bankruptcy — **not** same as senior OFZ.

### Bond fund vs direct bonds?

Fund = continuous maturity mix + TER; direct = control each line.

### MOEX bond halts?

Trading halts possible — automation must handle `TRADING_STATUS` from ISS/broker.

---

## Упражнение

Key rate +2 pp. Bond duration 4 years. Approx price change? (~−8% linear approx; convexity modifies.)

---

## Что изучить дальше

1. [[ETFs_and_funds]] — bond БПИФ.
2. [[Russia_tax_basics]] — купоны и НДФЛ.
3. [[Portfolio_diversification]] — allocation fixed income.
4. [[MOEX_ISS_API]] — bond endpoints.
