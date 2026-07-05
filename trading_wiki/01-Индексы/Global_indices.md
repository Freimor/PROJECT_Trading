---
title: Мировые индексы
tags: [индексы, S&P500, NASDAQ, MSCI, benchmark]
sources:
  - https://www.spglobal.com/spdji/en/indices/equity/sp-500/
  - https://www.nasdaq.com/solutions/global-indexes/nasdaq-100
  - https://www.msci.com/indexes
  - https://www.moex.com/a6231
  - https://fred.stlouisfed.org/
updated: 2026-07-05
level: beginner
---

# Мировые индексы

> **Мировые индексы** — измерители сегментов глобального фондового рынка. Они служат benchmark для портфелей, базой для ETF и **макро-контекстом** для автоматических торговых систем — в том числе при торговле на MOEX и криптовалютами.

---

## Для новичка

Если **IMOEX** — «термометр» ликвидной части российского рынка (см. [[IMOEX_RTS]]), то **S&P 500** — один из главных benchmark **крупных компаний США**. **NASDAQ-100** отражает 100 крупнейших **нефинансовых** компаний, торгуемых на NASDAQ — с заметным перекосом в технологии.

Индексы **не торгуются напрямую**. На них ориентируются фонды (ETF), деривативы и аналитики. Для новичка важно понимать **метод расчёта** (cap-weighted vs price-weighted) и **что именно** входит в корзину.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **S&P 500** — индекс **500** leading companies США; широко используется как мера состояния **large-cap** сегмента US equity market. | [S&P Dow Jones Indices: S&P 500](https://www.spglobal.com/spdji/en/indices/equity/sp-500/) |
| 2 | S&P 500 рассчитывается **S&P Dow Jones Indices** (подразделение S&P Global). | [S&P 500 — Overview](https://www.spglobal.com/spdji/en/indices/equity/sp-500/) |
| 3 | **NASDAQ-100** включает **100** крупнейших domestic и international **non-financial** securities, listed on NASDAQ по market capitalization. | [Nasdaq-100 Index](https://www.nasdaq.com/solutions/global-indexes/nasdaq-100) |
| 4 | **MSCI** публикует семейства индексов для developed, emerging и других сегментов рынков — включая **MSCI World** и **MSCI Emerging Markets**. | [MSCI Indexes](https://www.msci.com/indexes) |
| 5 | **Dow Jones Industrial Average (DJIA)** — индекс **30** prominent US companies; метод **price-weighted** (редкий среди major benchmarks). | [S&P DJI: Dow Jones](https://www.spglobal.com/spdji/en/indices/equity/dow-jones-industrial-average/) |
| 6 | **IMOEX** (Россия) — free-float cap-weighted, расчёт 09:50–19:00 MSK, ребаланс 3-я пятница квартальных месяцев — для сравнения с global benchmarks. | [MOEX Indices](https://www.moex.com/a6231) |
| 7 | **FRED** (Federal Reserve Economic Data) — бесплатный источник макро- и рыночных time series, включая процентные ставки и индексы. | [FRED](https://fred.stlouisfed.org/) |
| 8 | SEC **Investor.gov** описывает ETF как инструмент, часто **tracking** stock или bond **indexes**. | [Investor.gov: ETFs](https://www.investor.gov/introduction-investing/investing-basics/investment-products/exchange-traded-funds-etfs) |

---

## Основные индексы: обзорная таблица

| Индекс | Провайдер | Регион / фокус | Метод (типично) |
|--------|-----------|----------------|-----------------|
| **S&P 500** | S&P DJI | США, large cap | Float-adjusted market cap weighted |
| **NASDAQ Composite** | Nasdaq | Все бумаги NASDAQ | Market cap weighted |
| **NASDAQ-100** | Nasdaq | US + intl non-financial на NASDAQ | Modified market cap |
| **DJIA** | S&P DJI | США, 30 blue chips | **Price-weighted** |
| **Russell 2000** | FTSE Russell | US small cap | Market cap weighted |
| **MSCI World** | MSCI | Developed markets | Market cap weighted |
| **MSCI EM** | MSCI | Emerging markets | Market cap weighted |
| **STOXX Europe 600** | STOXX | Европа | Market cap weighted |
| **IMOEX** | MOEX | Россия, liquid large cap | Free-float cap weighted |
| **RTSI** | MOEX | Россия (USD denominated) | Free-float cap weighted |

> Точные правила отбора и весов — только в официальной **methodology** каждого провайдера. Не используйте «запомненный состав» без проверки.

---

## Методы взвешивания

### Market capitalization weighted (cap-weighted)

Большие компании получают больший вес. **S&P 500**, **IMOEX**, **MSCI World** — cap-weighted (часто с float adjustment). Эффект: индекс чувствителен к движению **лидеров** (Magnificent Seven в US, топ-5 в IMOEX с лимитом 55%).

### Price-weighted

**DJIA**: дорогая акция влияет сильнее, независимо от размера компании. Исторический метод; для современного анализа чаще смотрят S&P 500.

### Equal-weight

Каждая бумага — одинаковый вес (пример: S&P 500 Equal Weight — отдельный индекс S&P DJI). Больше exposure к mid names внутри universe.

---

## Зачем знать мировые индексы трейдеру на MOEX / crypto

### 1. Корреляция и risk-on / risk-off

Падение **NASDAQ-100** или **S&P 500** часто совпадает с **risk-off** на emerging markets и высокорisk активах (включая crypto). Это **статистическая закономерность**, не правило без исключений.

### 2. Макро-контекст для LLM

Автоматическая система должна передавать LLM **структурированный** macro snapshot, а не заголовки новостей:

```yaml
global_macro:
  spx_1d_pct: -1.2
  ndx_1d_pct: -1.8
  dxy_5d_pct: +0.4
  us_10y_yield: 4.25
  imoex_1d_pct: -0.8
  regime: risk_off
```

### 3. Бенчмарк для «пассивной» части портфеля

Если часть капитала в US ETF (доступ зависит от брокера и юрисдикции), S&P 500 — стандарт сравнения. В РФ чаще сравнивают с **IMOEX** через БПИФ.

### 4. Сector rotation

Sector indices (S&P 500 sectors, MOEX sector indices) помогают понять, **куда** идёт поток капитала — tech vs energy vs financials.

---

## S&P 500 — подробнее

### Что измеряет

По S&P Global, S&P 500 охватывает **leading companies** US economy. Индекс используется институциональными и розничными инвесторами как core US equity benchmark.

### ETF на S&P 500 (иллюстрация, US)

| Ticker | Примечание |
|--------|------------|
| SPY | Один из старейших ETF на S&P 500 |
| IVV | iShares Core S&P 500 |
| VOO | Vanguard S&P 500 |

Проверяйте **expense ratio**, ликвидность и наличие у **вашего** брокера. SEC Investor.gov рекомендует читать prospectus ETF.

### Связь с процентными ставками

Рост **доходности** US Treasuries (данные — FRED) часто ассоциируют с давлением на growth-акции (NASDAQ) и на risk assets. Механизм обсуждается в учебниках по финансам; **направление и сила** связи меняются во времени — проверяйте на истории, не на одном дне.

---

## NASDAQ-100 — подробнее

### Отличие от NASDAQ Composite

**Composite** — все листинги NASDAQ (тысячи бумаг). **NASDAQ-100** — отфильтрованная корзина 100 non-financial names. Для tech-exposure чаще цитируют NDX / QQQ (US ETF).

### Почему важен для crypto-flow

Bitcoin и altcoins historically показывали **повышенную** корреляцию с tech/growth в отдельные периоды. Crypto-flow может использовать `ndx_5d_return` как **фильтр агрессивности**, не как единственный сигнал.

---

## MSCI — глобальный контекст

**MSCI World** — developed markets. **MSCI Emerging Markets (EM)** — emerging, включая отдельные страны с весами по methodology MSCI.

Для российского рынка статус классификации в MSCI **менялся** в связи с санкциями и доступностью данных — **всегда** проверяйте актуальный статус на [msci.com](https://www.msci.com/indexes), не полагайтесь на устаревшие wiki-заметки.

---

## Примеры

### Пример 1: Risk-on фильтр (rule-based)

```
risk_on = (SPX_5d_return > 0) AND (DXY_5d_return < 0) AND (IMOEX_5d_return > 0)
IF risk_on THEN max_position_size = 100%
ELSE max_position_size = 50%
```

Пороги — из `risk.yaml` в Obsidian; LLM **не** меняет max_position_size без human override.

### Пример 2: Дивергенция IMOEX vs S&P 500

IMOEX растёт 5 дней подряд, S&P 500 падает → возможна **локальная** сила RF market или sector-specific факторы (commodities, FX). LLM получает флаг `divergence: true` для осторожной интерпретации сигналов.

### Пример 3: Отчёт в Obsidian

Еженедельная заметка «Global vs Local» с таблицей 1W / 1M / YTD returns: IMOEX, RTSI, SPX, NDX, BTC — источники данных документируются в YAML frontmatter.

---

## Частые ошибки новичков

1. **Считать S&P 500 = «весь US рынок»** — это large-cap sample; small cap — Russell 2000 и др.
2. **Путать NASDAQ-100 и NASDAQ Composite** — разный universe.
3. **Игнорировать валюту** — доходность US индекса в USD ≠ доходность для инвестора в RUB без пересчёта FX.
4. **Экстраполировать один день** — один день risk-off не отменяет долгосрочный план DCA.
5. **Использовать Yahoo Finance как «официальный» источник** — для automation документируйте primary source (S&P, Nasdaq, MOEX ISS).
6. **Торговать по «корреляции навсегда»** — корреляции нестационарны; пересчитывайте rolling window.

---

## FAQ

### Где бесплатно взять данные S&P 500 для n8n?

- **FRED** — ряд `SP500` (ежедневное close, с лагом).
- **Alpha Vantage**, **Polygon.io** — API с лимитами (проверьте license).
- Для **IMOEX** — бесплатный [MOEX ISS](https://iss.moex.com/iss/reference/).

### Нужен ли paid доступ к S&P DJI?

Для личного обучения и delayed data часто хватает ETF prices и FRED. **Коммерческое** использование index data — по license S&P / MOEX.

### Как NASDAQ связан с Bitcoin?

Прямой causal link не доказан regulatorily. На практике оба класса активов могут реагировать на **liquidity** и **risk appetite**. Используйте как macro filter, не как oracle.

### Что такое DXY?

US Dollar Index — сила USD vs корзина валют. Данные — FRED / ICE. Сильный USD иногда сопровождает давление на commodities и EM.

---

## Проверенные источники

1. **[S&P 500 — S&P Dow Jones Indices](https://www.spglobal.com/spdji/en/indices/equity/sp-500/)**
2. **[NASDAQ-100 — Nasdaq](https://www.nasdaq.com/solutions/global-indexes/nasdaq-100)**
3. **[MSCI Indexes](https://www.msci.com/indexes)**
4. **[Dow Jones Industrial Average — S&P DJI](https://www.spglobal.com/spdji/en/indices/equity/dow-jones-industrial-average/)**
5. **[FRED — Federal Reserve Economic Data](https://fred.stlouisfed.org/)**
6. **[MOEX Indices — IMOEX](https://www.moex.com/a6231)** — локальный benchmark для сравнения
7. **[Investor.gov: ETFs](https://www.investor.gov/introduction-investing/investing-basics/investment-products/exchange-traded-funds-etfs)**

---

## В автоматической системе

### Workflow `macro-context-flow`

```
Schedule: 07:00 UTC daily (+ каждые 4h в US session)
  → Parallel HTTP:
      - FRED API: SP500, DGS10, DTWEXBGS (DXY proxy)
      - MOEX ISS: IMOEX, RTSI daily candles
      - CoinGecko: BTC 24h change (optional)
  → Code: returns 1d/5d, z-score, risk_on flag
  → Merge → Obsidian daily note + JSON для crypto/securities subflows
  → IF extreme move (|SPX_1d| > 2%) → Ollama one-paragraph summary → Telegram
```

### Code node: 5-day return

```javascript
const closes = $json.series.map(r => r.value);
const n = closes.length;
const ret5d = n >= 6 ? (closes[n-1] / closes[n-6] - 1) * 100 : null;
return [{ json: { symbol: 'SP500', return_5d_pct: ret5d?.toFixed(2) } }];
```

### Распространение контекста

| Subflow | Поля из macro-context |
|---------|----------------------|
| `crypto-signal-flow` | `risk_on`, `ndx_5d`, `btc_dominance` |
| `moex-securities-flow` | `imoex_1d`, `spx_1d`, `dxy_5d` |
| `bond-ladder-flow` | `us_10y`, `ru_key_rate` (CBR RSS) |

### LLM prompt fragment

```
Global macro (verified API, not news):
- S&P 500 1d: {{spx_1d}}%
- NASDAQ-100 proxy 1d: {{ndx_1d}}%
- IMOEX 1d: {{imoex_1d}}%
- Regime: {{risk_on ? 'risk_on' : 'risk_off'}}
Task: Approve/reject ONLY based on strategy rules; macro is filter, not signal.
```

### Obsidian: `macro_universe.yaml`

```yaml
indices:
  - id: SPX
    source: FRED
    series_id: SP500
  - id: IMOEX
    source: MOEX_ISS
    secid: IMOEX
  - id: RTSI
    source: MOEX_ISS
    secid: RTSI
refresh_cron: "0 7 * * *"
```

### Guardrails

- API keys FRED / data vendors — только n8n Credentials.
- При недоступности SPX data — **fail closed**: уменьшить size, не увеличивать leverage.
- Не смешивать **delayed** и **realtime** series в одном расчёте без пометки.

---

## Связанные темы

- [[IMOEX_RTS]]
- [[Index_ETF]]
- [[Portfolio_diversification]]
- [[Crypto_flow_design]]
- [[Securities_flow_design]]

---

## Сравнение методологий: IMOEX vs S&P 500

| Аспект | IMOEX | S&P 500 |
|--------|-------|---------|
| Провайдер | MOEX | S&P Dow Jones Indices |
| Universe | Liquid Russian equities on MOEX | US large-cap by committee + criteria |
| Weighting | Free-float cap | Float-adjusted market cap |
| Single name cap | 15% | S&P DJI methodology (sector constraints) |
| Top-5 cap | 55% | Нет прямого аналога 55% в public summary |
| Currency | RUB (IMOEX) | USD |
| Session | 09:50–19:00 MSK | US market hours |

Для automation: **не** смешивайте «S&P 500 up» с «все акции MOEX должны расти» — разные economies и flows.

---

## Sector и thematic indices

Помимо broad benchmarks существуют **sector indices**:

- **S&P 500 sectors** (11 GICS sectors) — S&P DJI.
- **MOEX sector indices** — energy, finance и др. на moex.com.
- **NASDAQ-100** — implicit tech overweight.

Thematic ETF (AI, clean energy) **не** равны broad index — higher concentration risk ([FINRA ETF warnings](https://www.finra.org/investors/investing/investment-products/etfs)).

---

### FRED series reference (automation)

| Series ID | Описание |
|-----------|----------|
| SP500 | S&P 500 index |
| DGS10 | 10-Year Treasury yield |
| DTWEXBGS | Trade-weighted USD index |

Документировать в `macro_universe.yaml`; при смене series — version bump config.

---

## Исторический контекст (без прогнозов)

Global indices используются decades как benchmarks в academic finance (CAPM, beta). **Past index performance does not guarantee future results** — стандартное disclosure SEC mutual fund/ETF materials.

IMOEX с базы 100 (1997) отражает **price return** российского liquid large-cap сегмента — не GDP, не inflation, not wage growth.

---

## Практический чеклист macro-trader

1. Ежедневно: SPX, NDX (или proxy), IMOEX, USD/RUB — в одной Obsidian таблице.
2. Еженедельно: rolling 30d correlation BTC vs NDX (Code node).
3. При |SPX_1d| > 2%: включить `macro_alert` в crypto/securities flows.
4. Документировать source URL каждого ряда в YAML.
5. Не торговать на **одном** macro print без правила в strategy.yaml.

---

## Расширенный FAQ

### Russell 2000 vs S&P 500?

Russell 2000 — **US small cap**; волатильность и liquidity profile другие. Для «US economy proxy» чаще S&P 500.

### STOXX 600 для EU exposure?

Broad European equity benchmark; полезен если портфель имеет EU ETF через иностранного брокера.

### Нужен ли paid Bloomberg terminal?

Для личной automation — **нет**; FRED + MOEX ISS + broker data достаточно для macro context.

---

## Упражнение

Рассчитайте 5-day return SPX и IMOEX из API. Если SPX −3% и IMOEX +1%, какой флаг установит `macro-context-flow`? (Зависит от rules; пример: `divergence_us_ru: true`, без auto trade.)

---

## Что изучить дальше

1. [[Index_ETF]] — как инвестировать в индексы через ETF/БПИФ.
2. [[IMOEX_RTS]] — локальный benchmark и MOEX ISS.
3. [[Finance_basics]] — связь ставок и цен активов.
4. [[LLM_rules_and_guardrails]] — macro как filter, не override risk.
