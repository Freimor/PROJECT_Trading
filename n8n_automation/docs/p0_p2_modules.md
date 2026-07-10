# P0–P2: активация новых модулей

Реализовано по отчёту [`docs/papers-research-report-2026-07.md`](../../docs/papers-research-report-2026-07.md).

## P0 — критичные

| Модуль | API | n8n workflow |
|--------|-----|--------------|
| FINSABER backtest | `POST /api/backtest/finsaber` | `finsaber-backtest-weekly` |
| DeepFund live-paper | `POST /api/deepfund/cycle` | `deepfund-live-paper` |
| LLM validate-only | `guardrails.yaml` → `llm.mode: validate_only` | — (встроено в crypto pipeline) |
| Retail guard (BIS) | встроено в `crypto_pipeline.py` | — |

## P1

| Модуль | API | n8n workflow |
|--------|-----|--------------|
| On-chain filter | `GET /api/onchain/context` | — (в crypto pipeline) |
| MOEX factor sleeve | `POST /api/factor-sleeve/rebalance` | `securities-factor-sleeve` |
| Regulatory monitor | `POST /api/regulatory/scan` | `regulatory-monitor` |
| NeuraTrade harness | `POST /api/neuratrade/cycle` | `neuratrade-harness` |

## P2

| Модуль | API | n8n workflow |
|--------|-----|--------------|
| TradingAgents | `POST /api/trading-agents/run` | — |
| Bond ladder | `GET /api/bond-ladder/evaluate` | `bond-ladder-flow` |
| Geopolitical overlay | `GET /api/geopolitical/score` | — (securities pipeline) |
| Papers automation | `POST /api/papers/monitor/ingest` | `papers-monitor-weekly` |

Источники papers monitor: **arXiv**, **CrossRef**, **OpenAlex**, **Semantic Scholar** (опц. `SEMANTIC_SCHOLAR_API_KEY`), **RSS BIS/IMF**.  
Web-console: `/research` — кандидаты + NeuraTrade leaderboard. Черновики → `papers/inbox/`.

## Конфиги (`trading_wiki/config/`)

- `deepfund_config.yaml`, `on_chain_config.yaml`, `factor_sleeve.yaml`
- `regulatory_monitor.yaml`, `neuratrade_config.yaml`, `trading_agents_config.yaml`
- `bond_ladder.yaml`, `geopolitical_risk.yaml`, `papers_monitor.yaml`

## Порядок активации

1. Перезапустить `db-api` (миграции SQLite автоматически).
2. Импортировать новые workflow в n8n (см. `workflows/README.md`).
3. Активировать по приоритету: `finsaber-backtest-weekly` → `deepfund-live-paper` → `regulatory-monitor`.
4. Проверить: `POST /api/deepfund/start`, затем `POST /api/deepfund/cycle`.
5. Papers: `POST /api/papers/monitor/ingest` → `GET /api/papers/monitor/pending` (human review).

## Автоматизация сбора публикаций

Workflow `papers-monitor-weekly` (понедельник 06:00 MSK):

- **arXiv API** — q-fin, cs.AI, trading, crypto
- **CrossRef API** — peer-reviewed DOI
- Кандидаты в SQLite `papers_candidates` (status: `pending`)
- Оператор проверяет URL и добавляет в `papers/` вручную

Расширение: добавить RSS BIS/ESRB в `papers_monitor.yaml`, Semantic Scholar API (ключ).
