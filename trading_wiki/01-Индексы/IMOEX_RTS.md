---
title: IMOEX и RTS — индексы MOEX
tags: [индексы, MOEX, IMOEX, RTS, benchmark]
sources:
  - https://www.moex.com/a6231
  - https://www.moex.com/files/4c73xa32pfn18yqphareexvccg
  - https://www.moex.com/files/4r09wtqmn6b8b0w3x7epmc9fxe
  - https://iss.moex.com/iss/reference/
  - https://wp.hse.ru/en/fe/BRP/95/2024
  - https://www.hse.ru/ma/invest/
  - https://cfjournal.hse.ru/
updated: 2026-07-06
level: beginner
academic_sources: true
style: informational
---

# IMOEX и RTS — индексы MOEX

> IMOEX (MOEX Russia Index) и RTSI (RTS Index) — главные benchmark-индексы российского рынка на [Московской бирже](https://www.moex.com/a6231). Оба взвешиваются по free-float капитализации ликвидных акций крупных эмитентов.

## Главное

- Индекс — «температура» корзины акций; крупные компании влияют сильнее мелких.
- IMOEX в рублях, RTSI в долларах — при одних ценах акций индексы расходятся из‑за курса USD/RUB.
- Лимиты: одна бумага — макс. 15%, топ-5 — макс. 55% веса.
- Состав меняется в 3-ю пятницу марта, июня, сентября и декабря.
- Данные бесплатно — через MOEX ISS API; торговать индекс напрямую нельзя, только через БПИФ или фьючерс.

---

## Для новичка

Индекс показывает, как изменилась взвешенная корзина акций. IMOEX +2% за день — корзина в среднем подорожала; крупные эмитенты тянут индекс сильнее.

IMOEX в рублях, RTSI в долларах. При неизменных рублёвых ценах индексы расходятся из‑за курса: укрепление рубля обычно снижает RTSI относительно IMOEX.

Аналогия: корзина из десятков акций. Вес каждой — по free-float капитализации. Индекс — процентное изменение стоимости корзины от базового уровня.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | IMOEX — composite index с free-float взвешиванием по капитализации. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 2 | Первый расчёт IMOEX: 22.09.1997, база 100. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 3 | Расчёт IMOEX: 09:50–19:00 МСК, публикация раз в секунду. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 4 | Лимит веса одной бумаги в IMOEX: 15%. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 5 | Лимит суммарного веса топ-5 бумаг: 55%. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 6 | Смена состава — 3-я пятница марта, июня, сентября, декабря. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 7 | Коды IMOEX: Bloomberg IMOEX, Reuters .IMOEX, ISIN RU000A0JP7K5. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 8 | До декабря 2017 — MICEX Index; сейчас MOEX Russia Index. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 9 | RTSI — free-float cap-weighted, номинирован в USD (IMOEX — в RUB). | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 10 | Состав — ликвидные акции крупнейших российских эмитентов на бирже. | [MOEX: Moscow Exchange Indices](https://www.moex.com/a6231) |
| 11 | История IMOEX бесплатно — MOEX ISS API. | [MOEX ISS Reference](https://iss.moex.com/iss/reference/) |

---

## Ключевые понятия

### Free-float (доля в свободном обращении)

Free-float — часть акций компании, доступная для торговли на бирже **без учёта** блокирующих пакетов (государство, стратегические акционеры, insider lock-up). MOEX применяет коэффициенты free-float при расчёте весов — это стандартная практика для широких benchmark-индексов.

### Price Return vs Total Return

**Price Return** (IMOEX, RTSI в базовой версии) учитывает только изменение цен акций. **Total Return** индексы MOEX дополнительно реинвестируют дивидendы — см. семейство Total Return на странице MOEX. Для сравнения с вашим портфелем, где дивидendы реинвестируются, Total Return ближе к реальности.

### Ребалансировка и реконституция

**Реконституция** (смена списка бумаг) — 3-я пятница квартальных месяцев (март, июнь, сентябрь, декабрь). **Ребалансировка весов** происходит регулярно в рамках методологии; лимиты 15% / 55% предотвращают чрезмерную концентрацию.

### Связанные индексы MOEX

| Индекс | Код | Особенность |
|--------|-----|-------------|
| MOEX Blue Chip | MOEXBC / RTSSTD | 15 наиболее капитализированных бумаг |
| MOEX Broad Market | RUBMI | Топ-100 по ликвидности и капитализации |
| MOEX SMID | RTSSM и др. | Small/mid cap сегмент |
| MOEX 10 | MOEX10 | Узкая корзина из 10 бумаг |

Подробности — на [moex.com](https://www.moex.com/a6231) в разделе Equity indices.

---

## IMOEX vs RTSI: сравнение

| Параметр | IMOEX | RTSI |
|----------|-------|------|
| Валюта расчёта | RUB | USD |
| Метод взвешивания | Free-float cap-weighted | Free-float cap-weighted |
| Запуск (подтверждено MOEX для IMOEX) | 22.09.1997, база 100 | См. [RTS factsheet (PDF)](https://www.moex.com/files/4r09wtqmn6b8b0w3x7epmc9fxe) |
| Лимит одной бумаги | 15% | 15% (общая методология семейства) |
| Лимит топ-5 | 55% | 55% |
| Ребаланс состава | 3-я пятница мар/июн/сен/дек | 3-я пятница мар/июн/сен/дек |
| Время расчёта | 09:50–19:00 МСК | 09:50–19:00 МСK (см. factsheet RTS) |
| Типичное использование | Внутренний RUB benchmark РФ | Международные инвесторы, USD-отчётность |

---

## Как читать значение индекса

**Абсолютный уровень** (например, IMOEX = 3 200) сам по себе малоинформативен без контекста. Важнее:

1. **Изменение за период** (% от открытия, за неделю, YTD).
2. **Сравнение с вашим портфелем** — beat / match / lag benchmark.
3. **Волатильность** — дневные колебания IMOEX могут превышать 2–3% в стрессовые периоды.

### Пример расчёта дневного изменения

```
IMOEX_open = 3 150
IMOEX_current = 3 213
daily_change_pct = (3213 - 3150) / 3150 × 100 ≈ 2,0%
```

---

## Примеры использования

### Пример 1: Фильтр для long-only стратегии

Правило: не открывать новые long-позиции по отдельным акциям, если IMOEX упал более чем на **2%** от открытия сессии без явного сигнала по конкретной бумаге. Логика: в risk-off день даже «хорошие» акции часто падают вместе с рынком.

### Пример 2: Сравнение с БПИФ

Вы купили БПИФ на индекс MOEX (см. [[Index_ETF]], [[ETFs_and_funds]]). Если за квартал фонд отстаёт от IMOEX более чем на tracking error фонда — проверьте TER, дивидend policy и методику фонда у управляющей компании.

### Пример 3: Валютный эффект

IMOEX +1% за день, RTSI −0,5% за тот же день при неизменных рублёвых ценах акций → вероятно, **рубль укрепился** к USD. Для LLM-контекста полезно передавать оба индекса и курс USD/RUB.

### Пример 4: Ребалансировка

В 3-ю пятницу сентября в индекс может войти новая бумага, другая — выйти. Алгоритмы, торгующие «компонентами IMOEX», должны обновлять whitelist **до** открытия сессии после реконституции — данные состава публикует MOEX в methodology / rebalance schedule.

---

## Частые ошибки новичков

1. **Путать IMOEX и RTSI** — разная валюта; нельзя сравнивать абсолютные уровни напрямую.
2. **Игнорировать лимиты 15% / 55%** — индекс концентрирован; «диверсификация через IMOEX» не равна равновесию по 50 акциям.
3. **Ожидать, что индекс = «весь российский рынок»** — в корзину входят только ликвидные крупные бумаги; mid/small cap — отдельные индексы (RUBMI, SMID).
4. **Торговать вне окна 09:50–19:00** — вне расчёта индекса ликвидность и спреды могут отличаться; для MOEX акций см. [[MOEX_stocks]].
5. **Забывать про реконституцию** — веса и состав меняются; старый список «топ бумаг IMOEX» из прошлого года может быть неактуален.
6. **Считать индекс торговым сигналом** — падение IMOEX не означает автоматически «покупать» или «продавать» без правил стратегии.

---

## FAQ

### Сколько акций в IMOEX?

MOEX указывает, что число бумаг-конституентов **варьируется** (Varies) — точный актуальный список в [factsheet PDF](https://www.moex.com/files/4c73xa32pfn18yqphareexvccg) и на сайте биржи.

### Можно ли купить сам индекс?

Напрямую — нет. Можно купить **БПИФ/ETF**, реплицирующий индекс, или **фьючерс** на индекс (деривативы — отдельная тема, повышенный риск).

### Где взять бесплатные данные?

**MOEX ISS API** — свечи, история, состав. Пример endpoint см. раздел автоматизации ниже.

### Чем IMOEX отличается от MOEXBC (Blue Chip)?

MOEXBC — **15** наиболее капитализированных бумаг; лимит веса одной бумаги в Blue Chip Index — **20%** (см. [Blue Chip Index — MOEX](https://www.moex.com/a6232)). IMOEX — более широкая корзина с лимитом **15%** на одну бумагу.

### Влияют ли дивидendы на IMOEX?

Базовый **price return** IMOEX дивидendы не реинвестирует. Для учёта дивидendов используйте **total return** версии индексов MOEX.

---

## Проверенные источники

1. **[Moscow Exchange Indices (IMOEX & RTS) — MOEX](https://www.moex.com/a6231)** — официальные характеристики, коды, лимиты весов, расписание реконституции.
2. **[MOEX Russia Index Factsheet (PDF)](https://www.moex.com/files/4c73xa32pfn18yqphareexvccg)** — состав, методология, история.
3. **[RTS Index Factsheet (PDF)](https://www.moex.com/files/4r09wtqmn6b8b0w3x7epmc9fxe)** — параметры RTSI в USD.
4. **[MOEX ISS API Reference](https://iss.moex.com/iss/reference/)** — программный доступ к котировкам и истории.
5. **[Blue Chip Index — MOEX](https://www.moex.com/a6232)** — родственный индекс из 15 blue chips.

---

## Академические источники

Полный свод университетских курсов и научных публикаций (2021+) — в заметке [[Academic_sources]].

| Учреждение | Ресурс (2021+) | Что подтверждает для этой темы | Ссылка |
|-----------|----------------|--------------------------------|--------|
| ВШЭ | Manushkin — BRP 95/FE/2024 | Fama-French 5-factor модель на данных российского рынка (IMOEX) | [wp.hse.ru/en/fe/BRP/95/2024](https://wp.hse.ru/en/fe/BRP/95/2024) |
| ВШЭ | Магистратура «Инвестиции на финансовых рынках» | Индексы как benchmark, методология capitalization-weighted | [www.hse.ru/ma/invest/](https://www.hse.ru/ma/invest/) |
| ВШЭ | Журнал Corporate Finance Research | Эмпирические исследования российских индексов и blue chips | [cfjournal.hse.ru/](https://cfjournal.hse.ru/) |
| MIT | 15.481X Adaptive Markets (Fall 2022) | Индексы как прокси рыночного риска и факторов | [ocw.mit.edu/courses/15-481x-adaptive-markets-fi...](https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/) |

---

## В автоматической системе

### Архитектура `moex-index-monitor`

```
Cron (каждые 5 мин, 09:50–19:00 MSK)
  → HTTP Request: MOEX ISS (IMOEX + RTSI candles)
  → Code: daily % change, spread IMOEX vs RTSI implied FX
  → IF abs(IMOEX_change) > threshold → Ollama macro comment
  → Telegram alert + Obsidian daily note
```

### MOEX ISS — пример запросов

**Свечи IMOEX (дневные):**

```
GET https://iss.moex.com/iss/engines/stock/markets/index/securities/IMOEX/candles.json?from=2026-01-01&till=2026-07-05&interval=24
```

**Текущее значение и состав (reference):**

```
GET https://iss.moex.com/iss/engines/stock/markets/index/securities/IMOEX.json
GET https://iss.moex.com/iss/statistics/engines/stock/markets/index/analytics/IMOEX.json
```

**RTSI:**

```
GET https://iss.moex.com/iss/engines/stock/markets/index/securities/RTSI/candles.json
```

### Code node: дневное изменение от открытия

```javascript
const rows = $json.candles.data;
const last = rows[rows.length - 1];
const [open, close, high, low, value] = last.slice(1, 6).map(Number);
const changePct = ((close - open) / open) * 100;

return [{
  json: {
    index: 'IMOEX',
    open, close, high, low,
    change_pct: changePct.toFixed(2),
    session_active: true  // проверять timezone MSK 09:50–19:00
  }
}];
```

### LLM-контекст для фильтрации сигналов

Передавайте в Ollama структурированный JSON (не «сырой» новостной поток):

```yaml
macro_context:
  imoex_level: 3213.45
  imoex_change_pct: -1.8
  rtsi_change_pct: -0.9
  usd_rub: 92.15
  risk_regime: risk_off  # rule-based из порогов
  top_constituents_weight: 55  # напоминание о концентрации
```

**Правило [[LLM_rules_and_guardrails]]:** при `imoex_change_pct < -2` LLM может **reject** агрессивные long-сигналы по отдельным акциям, но **не** отменяет жёсткие stop-loss ордера.

### Реконституция: calendar workflow

| Дата | Действие n8n |
|------|----------------|
| 3-я пятница мар/июн/сен/дек | Workflow `imoex-rebalance-check` |
| T-5 дней | Скачать preview состава с MOEX |
| T-1 вечер | Обновить `imoex_constituents.yaml` в Obsidian |
| T+0 после открытия | Проверить, что whitelist в crypto/securities flows актуален |

### Obsidian: daily note template

```markdown
## MOEX Macro {{date}}

| Индекс | Open | Close | Δ% |
|--------|------|-------|-----|
| IMOEX  | {{imoex_open}} | {{imoex_close}} | {{imoex_d}} |
| RTSI   | {{rtsi_open}} | {{rtsi_close}} | {{rtsi_d}} |

Источник: MOEX ISS, moex.com/a6231
```

### Метрики для мониторинга

- Задержка ISS относительно realtime (должна быть секунды).
- Расхождение implied FX из IMOEX/RTSI vs официальный USD/RUB.
- Алерт при отсутствии данных в сессию (API down).

### Отличие от crypto-flow

| Параметр | MOEX index monitor | Crypto flow |
|----------|-------------------|-------------|
| Часы работы | 09:50–19:00 MSK | 24/7 |
| Settlement | T+1 для акций | Мгновенно |
| API | MOEX ISS (бесплатно) | Binance REST/WS |

---

## Связанные темы

- [[Global_indices]]
- [[Index_ETF]]
- [[MOEX_stocks]]
- [[MOEX_ISS_API]]
- [[ETFs_and_funds]]
- [[Securities_flow_design]]

---

### Дополнительный workflow: implied FX monitor

```javascript
// Compare IMOEX % change vs RTSI % change same session
const imoexCh = $json.imoex_change_pct;
const rtsiCh = $json.rtsi_change_pct;
const fxSignal = imoexCh - rtsiCh; // simplified diagnostic
return [{ json: { fx_diagnostic: fxSignal, note: 'Not trade signal' } }];
```

Логировать в Obsidian для macro research; **не** использовать как standalone FX trade signal без validated model.

---

## Глоссарий

| Термин | Определение |
|--------|-------------|
| Benchmark | Эталон сравнения доходности |
| Free-float | Акции в свободном обращении |
| Reconstitution | Плановая смена состава индекса |
| Price return | Индекс без реинвестирования дивидendов |
| Total return | С реинвестированием дивидendов |
| Factsheet | PDF с параметрами индекса MOEX |

---

## Практический чеклист для инвестора

Перед использованием IMOEX как ориентира пройдите пункты:

1. Открыть [moex.com/a6231](https://www.moex.com/a6231) и сверить актуальные **KEY CHARACTERISTICS**.
2. Скачать [factsheet PDF](https://www.moex.com/files/4c73xa32pfn18yqphareexvccg) — состав и веса на дату публикации.
3. Записать даты **3-й пятницы** текущего квартала в календарь (реконституция).
4. Если используете БПИФ — сравнить benchmark фонда с IMOEX в disclosure УК.
5. Настроить MOEX ISS запрос для daily close — не полагаться на «цифру из чата».

---

## Расширенный FAQ

### Почему IMOEX и RTSI расходятся в один день?

Три типичных фактора: (1) **валюта** — RTSI в USD; (2) **различия methodology** по FX conversion внутри расчёта RTS — детали в RTS factsheet; (3) **timing** последних сделок по отдельным бумагам. Не делайте вывод о «слабости рубля» только по одному дню без курса USD/RUB.

### Можно ли торговать «индексом» через фьючерс?

На срочном рынке MOEX есть контракты на индексы — **маржа, expiration, basis risk**. Это не spot ETF; см. отдельную тему деривативов в Wiki_structure.

### Как часто обновляются веса между реконституциями?

MOEX пересчитывает индекс **каждую секунду** в сессию; веса **плавают** с ценами. Лимиты 15%/55% **принудительно** ограничивают концентрацию по правилам methodology.

### Где официальный rebalance schedule?

На странице индекса MOEX — ссылка **Rebalance Schedule** рядом с Methodology ([a6231](https://www.moex.com/a6231)).

---

## Упражнение для самопроверки

1. IMOEX запущен в **1997** с базой **100**. Если сегодня IMOEX = 3 000, во сколько раз вырос индекс с запуска? (Ответ: в 30 раз по price return, без учёта дивидendов.)
2. Одна бумага имеет free-float cap 20% до capping — какой **максимальный** вес в IMOEX? (Ответ: **15%** по правилу MOEX.)
3. В какие месяцы происходит смена состава? (Ответ: **март, июнь, сентябрь, декабрь** — 3-я пятница.)

---

## Что изучить дальше

1. [[Index_ETF]] — как инвестировать в индекс через один инструмент.
2. [[Global_indices]] — IMOEX в контексте S&P 500 и MSCI.
3. [[MOEX_ISS_API]] — полный справочник endpoints для автоматизации.
4. [[Portfolio_diversification]] — лимиты 15%/55% и реальная концентрация риска.
