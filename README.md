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

- **Академические источники** — курсы и публикации 2021+ (ВШЭ, MIT, Stanford, BIS, NBER); сводка в [`Academic_sources.md`](./trading_wiki/Academic_sources.md)

- Информация с официальных источников; эвристики трейдинга отделены от норм регуляторов.

- В каждой статье — блок **«В автоматической системе»** (n8n + Ollama + Obsidian).

- Папки: `00-Основы/` (дефис вместо `|` для Windows).



## Автоматизация



Документация системы: [`n8n_automation/README.md`](./n8n_automation/README.md)  

Wiki-обзор: [`Automation_system.md`](./trading_wiki/06-Стратегии%20автоматизированной%20LLM%20торговли/Automation_system.md)



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



**Этапы 1–8 реализованы** — [`roadmap`](./n8n_automation/docs/roadmap.md) · [`live checklist`](./n8n_automation/docs/live_promotion.md)

```powershell
docker exec trading-db-api python smoke_test.py
```

| Workflow | Этап |
|----------|------|
| `crypto-signal-dry-run` | 2 |
| `news-ingest` | 3 |
| `crypto-execute-testnet` | 4 |
| `securities-dca-sandbox` | 5 |
| `analysis-llm-report` | 6 |
| `securities-swing-dry-run` | 7 |



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


