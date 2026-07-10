# PROJECT Trading



Автоматическая система трейдинга на базе **n8n**, локальных **LLM (Ollama)**, **SQLite** и базы знаний в **Obsidian**.



## Trading Wiki



Папка [`trading_wiki/`](./trading_wiki/) — полная база знаний для новичков и для автоматизированной торговли:



- **Основы финансов** — акции, облигации, типы заявок, глоссарий

- **Индексы** — IMOEX, RTS, мировые бенчмарки, ETF

- **Криптовалюта** — блокчейн, биржи, индикаторы

- **Ценные бумаги** — MOEX, облигации, БПИФы

- **Риск-менеджмент и психология** — размер позиции, стопы, когнитивные искажения

- **Автоматизация** — архитектура n8n-flow для crypto и securities

- **API** — MOEX ISS, T-Invest, Binance, Ollama

- **LLM** — промпты и guardrails для локальных моделей

- **Налоги и регулирование (РФ)**



### С чего начать



1. Откройте [`trading_wiki/Wiki_structure.md`](./trading_wiki/Wiki_structure.md) — карта всех разделов.

2. Новичкам: [`00-Основы/Finance_basics.md`](./trading_wiki/00-Основы/Finance_basics.md) → [`04-Риск менеджмент/`](./trading_wiki/04-Риск%20менеджмент/).

3. Для Obsidian: укажите vault на папку `trading_wiki/`.



### Принципы Wiki



- **Подтверждённые факты** — в каждой статье таблица с конкретными утверждениями и ссылками на первоисточники (MOEX, SEC Investor.gov, FINRA, ЦБ РФ и др.).

- В каждой статье — блок **«Главное»** (суть за 30 секунд) и правила ясного текста по [[Writing_style_guide]]

- **Глоссарий** — [`Financial_glossary.md`](./trading_wiki/Financial_glossary.md) (~150+ терминов); краткая версия в [`00-Основы/Glossary.md`](./trading_wiki/00-Основы/Glossary.md)

- **Академические источники** — **74 работы** (2021–2026) в [`papers/`](./papers/README.md) с анализом достоверности; сводка в Wiki: [`Academic_sources.md`](./trading_wiki/Academic_sources.md); отчёт: [`docs/papers-research-report-2026-07.md`](./docs/papers-research-report-2026-07.md); мониторинг новых публикаций — web-console **Research** (`/research`)

- Информация с официальных источников; эвристики трейдинга отделены от норм регуляторов.

- В каждой статье — блок **«В автоматической системе»** (n8n + Ollama + Obsidian).

- Папки: `00-Основы/` (дефис вместо `|` для Windows).



## Автоматизация



Документация системы: [`n8n_automation/README.md`](./n8n_automation/README.md)  

Wiki-обзор: [`Automation_system.md`](./trading_wiki/06-Стратегии%20автоматизированной%20LLM%20торговли/Automation_system.md)

**Roadmap развития (вехи):** [`docs/roadmap-razvitiya.md`](./docs/roadmap-razvitiya.md)



### Быстрый старт



```powershell

copy .env.example .env

.\scripts\init.ps1

docker exec -it trading-ollama ollama pull llama3.2

```



| Сервис | URL |

|--------|-----|

| n8n | http://localhost:5678 |

| Ollama | http://localhost:11434 |

| DB API | http://localhost:8000/docs |
| **Web Console** | http://localhost:3000 (`docker compose --profile console up -d console`) |

**Этапы 1–8 реализованы** — [`roadmap`](./n8n_automation/docs/roadmap.md) · [`live checklist`](./n8n_automation/docs/live_promotion.md)

### Paper-тестирование (виртуальные сделки)

Режим **`paper`**: полный пайплайн signal → filter → LLM → guardrails → risk → **ордер** на Binance testnet и T-Invest sandbox.

- Документация: [`n8n_automation/docs/paper_testing.md`](./n8n_automation/docs/paper_testing.md)
- Telegram: **🤖 Автомат → 🧪 Paper тест** (эффективность, сброс MOEX sandbox, ручной прогон)
- API: `GET /api/paper/status`, `GET /api/paper/effectiveness`, `POST /api/paper/session/reset`

**Сброс баланса:** MOEX sandbox — да (новый демо-счёт ~1M ₽). Binance testnet — только baseline сессии в SQLite (полный сброс ~раз в месяц на стороне Binance).

```powershell
curl -X POST "http://localhost:8000/api/paper/session/reset"
curl "http://localhost:8000/api/paper/effectiveness?days=7"
```

```powershell
docker exec trading-db-api python smoke_test.py
```

### Управление n8n workflow из Telegram

В Telegram: **🖥 Управление → 🧩 Workflows** можно:

- включать/выключать workflow
- менять cron для `Schedule Trigger` (пресеты 15m/1h/4h) или вручную через `/cron`

Для этого нужен **n8n Public API key**:

- В n8n UI откройте **Settings → API keys**, создайте ключ со scope:
  `workflow:list`, `workflow:read`, `workflow:update`, `workflow:activate`
- Добавьте в `.env` переменную `N8N_API_KEY` (см. `.env.example`)
- Перезапустите `db-api`: `docker compose up -d --build db-api`

### LLM Benchmark

Оценка качества решений LLM: precision/recall, sim PnL, golden set.

- Документация: [`n8n_automation/docs/llm_benchmark.md`](n8n_automation/docs/llm_benchmark.md)
- Telegram: **🤖 Автомат → 📊 LLM Benchmark**
curl "http://localhost:8000/api/benchmark/report", `POST /api/benchmark/run`

### Web Console (админ-панель)

Операционный центр: обзор портфеля, графики с маркерами LLM, журнал событий, управление риском.

- Документация: [`n8n_automation/docs/control_panel.md`](n8n_automation/docs/control_panel.md)
- Запуск: `docker compose --profile console up -d console` → http://localhost:3000
- Разделы: **Обзор** · **₿ Crypto** · **📈 MOEX** · **События** · **LLM** · **Paper** · **Benchmark** · **n8n** · **Управление**
- Chart API: `GET /api/charts/candles`, `/markers`, `/equity`
- LLM: `GET /api/llm/decisions`, `POST /api/evaluation/replay`

| Workflow | Этап |
|----------|------|
| `crypto-signal-dry-run` | 2 (демо) |
| `news-ingest` | 3 |
| `crypto-signal-paper` | 4 (paper) |
| `crypto-monitor-testnet` | 4 |
| `securities-dca-sandbox` | 5 |
| `analysis-llm-report` | 6 |
| `securities-swing-dry-run` | 7 (демо) |
| `securities-swing-paper` | 7 (paper) |
| `llm-benchmark-weekly` | 6+ |



## Стек



| Компонент | Назначение |

|-----------|------------|

| n8n | Оркестрация workflow |

| Ollama | Локальный LLM |

| Obsidian | Wiki, config, промпты |

| SQLite + FastAPI | Операционные логи, health, replay |

| Python | Индикаторы, бэктест, T-Invest bridge |



---



> **Дисклеймер:** материалы Wiki носят образовательный характер и не являются инвестиционной, налоговой или юридической рекомендацией.


