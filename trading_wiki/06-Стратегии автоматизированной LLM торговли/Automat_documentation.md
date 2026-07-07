---
title: Автомат — документация и связь с Wiki
tags: [автоматизация, n8n, telegram, документация]
sources:
  - https://docs.n8n.io/
  - https://github.com/ollama/ollama/blob/main/docs/api.md
updated: 2026-07-07
level: beginner
style: informational
---

# Автомат — документация

> Полное описание торгового автомата PROJECT Trading: как он работает, где смотреть статус в Telegram и как теория из Wiki превращается в код.

Также: `n8n_automation/docs/automat.md`, [[Automation_system]], [[n8n_architecture_overview]].

---

<!-- telegram:overview -->
## Обзор автомата

**Автомат** — полуавтоматическая система торговли на двух рынках:

- **₿ Крипто** — Binance Spot, 24/7, testnet → live
- **📈 MOEX** — T-Invest API, сессионная торговля, sandbox → live

**Главный принцип:** LLM (Ollama) **не торгует**. Она только отвечает approve/reject на уже отфильтрованный сигнал. Ордера, размер позиции, лимиты и kill switch — **детерминированный Python-код** и YAML-конфиги.

**Компоненты:**
| Компонент | Роль |
|-----------|------|
| n8n | Расписание, HTTP, ветвления workflow |
| Python DB API | Индикаторы, guardrails, ордера, логи |
| Ollama | Валидация сигнала (JSON) |
| SQLite | События, сделки, health, новости |
| Obsidian Wiki | Теория, промпты, guardrails.yaml |
| Telegram-бот | Мобильный пульт «Автомат» |

**Режимы исполнения** (`guardrails.yaml` → `trading.mode`):
- `dry_run` — pipeline без реальных ордеров (отладка)
- `paper` — testnet / sandbox с виртуальными деньгами
- `live` — только после checklist и `LIVE_TRADING_ENABLED=true`

**Telegram → 🤖 Автомат** показывает сводку: kill switch, режим, Ollama, воронку сигналов за 7 дней.

---

<!-- telegram:pipeline -->
## Конвейер сигнала

Каждый торговый flow проходит **одинаковые стадии** (логируются в `trade_events`):

```
биржа → signal → filter → llm → guardrails → risk → order → log
```

| Стадия | Что делает | Кто решает |
|--------|------------|------------|
| **signal** | Свечи OHLCV, расчёт RSI/MACD/EMA | Код (`indicators/technical.py`) |
| **filter** | Rule filter: RSI &lt;30 / &gt;70 и др. | YAML `crypto_config` |
| **news** | RSS → verify domain → match ticker (SBER, BTC…) | `news_sources.yaml`, `news_entities.yaml` |
| **llm** | approve/reject + confidence + counter_thesis + **verified news** | Ollama + промпт из Wiki |
| **guardrails** | G1–G12: kill switch, env, session, limits | `guardrails.yaml` |
| **risk** | Position sizing, daily loss cap | [[Position_sizing]], код |
| **order** | MARKET/LIMIT на биржу | Binance / T-Invest bridge |
| **log** | POST `/api/events`, audit LLM | SQLite |

**Важно:** если filter не прошёл (`no_rule_match`) — LLM **не вызывается**. Это экономит ресурсы и снижает «галлюцинации» модели.

**Где смотреть:** Telegram → **🧾 События** или **₿ Крипто → 🔄 Воронка**.

Wiki: [[Crypto_flow_design]], [[Securities_flow_design]], [[LLM_rules_and_guardrails]].

---

<!-- telegram:crypto -->
## Крипто-flow (Binance testnet)

**Workflow:** `crypto-signal-dry-run` / `crypto-execute-testnet` (n8n)

**Расписание:** cron из `crypto_config.yaml` (по умолчанию каждые 4h).

**Pipeline:**
1. `GET /api/v3/klines` — свечи BTCUSDT, ETHUSDT ([[Binance_API]])
2. Индикаторы RSI(14), MACD, EMA — [[Key_indicators_RSI_MACD]], [[Crypto_indicators]]
3. Rule filter — пороги из config (overbought/oversold)
4. LLM validate — промпт `prompts/crypto_validate_v1.md`
5. Guardrails + position size — [[Stop_loss_take_profit]], [[Position_sizing]]
6. Ордер на testnet — ключи `BINANCE_TESTNET_*` в `.env`

**Новости для LLM:** RSS → SQLite → контекст в промпт ([[Crypto_flow_design#News context]]).

**Telegram-раздел ₿ Крипто (testnet):**
| Кнопка | Данные |
|--------|--------|
| 📋 Сводка | env, mode, LLM, cron |
| 🔄 Воронка | passed/total по стадиям |
| 🧾 События | последние crypto events |
| 💰 Баланс | Binance testnet account |

Wiki-теория → код: см. раздел «Wiki → код».

---

<!-- telegram:moex -->
## MOEX-flow (T-Invest sandbox)

**Два подрежима** (`securities_config.yaml` → `active_mode`):

### index_dca (БПИФ, без LLM)
- Cron 1-го числа месяца
- Покупка TMOS (или ticker из config) на фикс. сумму ₽
- Workflow: `securities-dca-sandbox`
- Теория: [[Index_ETF]], [[Portfolio_diversification]], [[Russia_tax_basics]]

### swing_signals (акции + LLM)
- Только в MOEX-сессии (~10:00–19:00 MSK) — [[MOEX_stocks]]
- Данные: MOEX ISS (свечи) — [[MOEX_ISS_API]]
- Ордера: T-Invest REST bridge — [[Tinkoff_Invest_API]]
- LLM: промпт `securities_validate_v1`, universe SBER, GAZP…
- Settlement T+1 учитывается в guardrails

**Telegram → 📈 MOEX (sandbox):**
| Кнопка | Данные |
|--------|--------|
| 📋 Сводка | connection, funnel, LLM stats |
| 👤 Демо-счёт | портфель sandbox (~1M ₽) |
| ⚙️ Автomat | DCA + swing config |
| 💼 Сделки | история ордеров |
| 📉 Эффективность | воронка + approve rate LLM |
| ▶️ Тест DCA | ручной sandbox-ордер TMOS |

Wiki: [[Securities_flow_design]], [[Bonds_basics]] (для fixed-income sleeve в будущем).

---

<!-- telegram:wiki_map -->
## Wiki → код: как применяется теория

| Тема Wiki | Файл | Где в автомате |
|-----------|------|----------------|
| RSI, MACD, EMA | [[Key_indicators_RSI_MACD]] | `indicators/technical.py` — rule_filter |
| OHLCV, таймфреймы | [[Technical_analysis_basics]] | `fetch_klines`, MOEX ISS candles |
| Position sizing | [[Position_sizing]] | `guardrails.position_size_dry_run()` |
| Stop-loss / TP | [[Stop_loss_take_profit]] | crypto OCO (paper/live), config limits |
| Risk / diversification | [[Portfolio_diversification]] | whitelist пар, max positions |
| LLM guardrails | [[LLM_rules_and_guardrails]] | `guardrails.yaml`, schema parse |
| Промпты | [[LLM_prompts_trading]] | `trading_wiki/prompts/*.md` |
| Binance API | [[Binance_API]] | `binance_client.py` |
| T-Invest API | [[Tinkoff_Invest_API]] | `bridges/tinvest_rest.py` |
| MOEX ISS | [[MOEX_ISS_API]] | `securities_pipeline._fetch_moex_candles` |
| Психология / bias | [[Cognitive_biases]] | LLM counter_thesis в промпте |
| Налоги РФ | [[Russia_tax_basics]] | tax stub, логирование для учёта |
| Новости | RSS + verify | `news_service.py`, config/news_*.yaml |

**Obsidian** = «учебник + правила». **SQLite** = «что реально произошло». LLM читает промпт и новости, но **не переписывает** Wiki.

**Конфиги** (приоритет: guardrails &gt; market yaml &gt; defaults):
- `trading_wiki/config/guardrails.yaml`
- `trading_wiki/config/crypto_config.yaml`
- `trading_wiki/config/securities_config.yaml`

---

<!-- telegram:bot_menu -->
## Меню Telegram «Автомат»

```
🤖 Автомат          ← сводка + подменю
├── ₿ Крипто (testnet)
├── 📈 MOEX (sandbox)
├── ₿ Крипто LIVE ⚠️    ← checklist, не торгует без флагов
├── 📈 MOEX LIVE ⚠️
├── ✅ Подтверждения    ← human-in-the-loop
├── 🧾 События
└── 📖 Как работает     ← эта документация (разделы)
```

**Команды:** `/start`, `/menu`, `/status` → Автomat; `/kill` → Kill Switch; `/smoke` → smoke test.

**Kill Switch** (`🛑` в главном меню): мгновенно блокирует все trading workflows. Проверяйте раз в месяц.

**Live ⚠️:** показывает checklist (`ready_for_live: false` пока не выполнены compliance, live keys, `LIVE_TRADING_ENABLED`).

**Подтверждения:** критичные действия (крупные ордера, смена режима) — approve/reject inline.

Полная wiki: **📚 База знаний → 📖 Wiki** (Obsidian vault).

Web-панель: http://localhost:3000 (console).

---

## Связанные темы

- [[Automation_system]]
- [[n8n_architecture_overview]]
- [[Crypto_flow_design]]
- [[Securities_flow_design]]
- [[Ollama_integration]]

## Дисклеймер

Материалы образовательные. Автомат не является инвестиционной рекомендацией. Оператор несёт ответственность за live-торговлю.
