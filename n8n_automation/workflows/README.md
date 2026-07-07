# Workflows n8n

JSON-экспорты для импорта в n8n: **Settings → Import from File**.

## Структура

```
workflows/
├── shared/          # health, errors, telegram
├── crypto/          # signal dry_run, execute testnet, monitor
├── news/            # RSS ingest
├── securities/      # DCA, swing dry_run
└── analysis/        # weekly LLM report
```

## Порядок импорта

1. `shared/shared-global-error-handler.json`
2. `shared/shared-health-check.json`
3. `shared/shared-telegram-alert.json` (опционально)
4. `news/news-ingest.json`
5. `crypto/crypto-signal-dry-run.json`
6. `crypto/crypto-execute-testnet.json`
7. `crypto/crypto-monitor-testnet.json`
8. `securities/securities-dca-sandbox.json`
9. `securities/securities-swing-dry-run.json`
10. `analysis/analysis-llm-report.json`

**Settings → Error workflow** → `shared-global-error-handler`

## Активация по этапам

| Этап | Workflows для активации |
|------|-------------------------|
| 1 | `shared-health-check` |
| 2 | `crypto-signal-dry-run` |
| 3 | `news-ingest` |
| 4 | `crypto-execute-testnet`, `crypto-monitor-testnet` |
| 5 | `securities-dca-sandbox` |
| 6 | `analysis-llm-report` |
| 7 | `securities-swing-dry-run` |

## Теги

| Тег | Назначение |
|-----|------------|
| `shared` | Переиспользуемые workflows |
| `crypto` / `securities` / `analysis` | Рынок |
| `env/testnet` | Testnet / sandbox |
| `env/live` | Live (этап 8, после checklist) |

## Credentials

API-ключи — в `.env` (db-api) и n8n Credentials. Папка `credentials/` в `.gitignore`.

## Backend API

Все workflows вызывают `http://db-api:8000` — см. [docs/database.md](../docs/database.md) и Swagger `/docs`.
