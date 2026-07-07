# База данных — PROJECT Trading

SQLite (`data/trading.db`) — **source of truth** для операционных данных. Obsidian хранит человекочитаемые сводки.

## Инициализация

```powershell
# Локально
cd python
python -m db.init_db

# Через API (после docker compose up)
curl -X POST http://localhost:8000/admin/init
```

Схема: [`data/schema.sql`](../../data/schema.sql)

## Таблицы

### `trade_events` — главный журнал

Каждый этап pipeline пишет одну запись.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | TEXT | UUID |
| `market` | crypto / securities / shared | Рынок |
| `env` | dry_run / paper / shadow / live | Режим |
| `stage` | signal / llm / order / ... | Этап |
| `inputs_hash` | TEXT | SHA-256 контекста для replay |
| `prompt_version` | TEXT | Версия промпта |
| `request_id` | TEXT | Idempotency key (UNIQUE) |
| `payload_json` | TEXT | Полный контекст |

### `llm_decisions` — аудит LLM

Детальные ответы модели для блока 4 (evaluation).

### `system_health_checks` — мониторинг

Записи от `shared-health-check` каждые 5 минут.

### `news_items` / `news_sources` — тактические новости

Готово для этапа 3. TTL и dedup через `dedup_hash`.

### `ohlcv_candles` — кэш свечей

Для бэктеста и replay без повторных запросов к API.

### `position_snapshots` — reconciliation

Сверка локального состояния с биржей.

### `wiki_page_meta` — метаданные wiki

Для pipeline актуализации (хеши, broken links, RAG index).

## API примеры

### Записать событие (из n8n HTTP Request)

```http
POST http://db-api:8000/api/events
Content-Type: application/json

{
  "market": "crypto",
  "env": "dry_run",
  "stage": "signal",
  "symbol": "BTCUSDT",
  "decision": "approve",
  "workflow_name": "crypto-signal-dry-run",
  "inputs_hash": "abc123...",
  "prompt_version": "crypto_validate_v1",
  "model": "llama3.2",
  "confidence": 0.82,
  "payload": {
    "rsi": 32.5,
    "macd_histogram": 0.0012
  }
}
```

### Batch health-check

```http
POST http://db-api:8000/api/health/batch
Content-Type: application/json

{
  "checks": [
    {
      "service_name": "ollama",
      "status": "ok",
      "latency_ms": 45,
      "details": { "http_code": 200 }
    }
  ]
}
```

### Список событий

```http
GET http://localhost:8000/api/events?market=crypto&limit=20
```

## Идемпотентность ордеров

Перед `POST /order` генерируйте `request_id` (UUID). Повторный POST с тем же `request_id` вернёт HTTP 409 — защита от дублирования при retry n8n.

## `inputs_hash` для replay

Code node в n8n:

```javascript
const crypto = require('crypto');
const canonical = JSON.stringify({
  symbol: $json.symbol,
  timeframe: $json.timeframe,
  indicators: $json.indicators,
  candles_ts: $json.candles?.map(c => c.time),
});
const inputs_hash = crypto.createHash('sha256').update(canonical).digest('hex');
return [{ json: { ...$json, inputs_hash } }];
```

Один и тот же `inputs_hash` + новый `prompt_version` → можно сравнить решения моделей на идентичных данных.

## Бэкапы

```powershell
# Рекомендуется cron/Task Scheduler
copy data\trading.db data\backups\trading-$(Get-Date -Format yyyy-MM-dd).db
```

Папка `data/backups/` в `.gitignore`.

## Миграции

Этап 1: `schema.sql` применяется целиком через `init_db`. При изменении схемы в будущем — версионированные миграции в `data/migrations/`.
