# LLM Benchmark

Система оценки качества решений локальной LLM в торговом автомате.

## Два уровня тестирования модели

| Уровень | Данные | Назначение |
|---------|--------|------------|
| **🧪 Синтетика** | Заранее заданные индикаторы и новости в YAML | Быстрая регрессия промпта на свежей модели |
| **📜 История** | Реальные котировки Binance/MOEX на дату `as_of` + новости из БД или snapshot | Проверка на прошлых рыночных срезах |

Дополнительно: **Outcome** (live/paper) — precision/recall по forward return после реальных решений.

## Уровни оценки

| Уровень | Метрики | Источник |
|---------|---------|----------|
| Операционный | approve rate, latency, confidence | `llm_decisions` |
| Outcome | precision, recall, sim PnL | forward return после решения |
| Синтетика | pass rate на эталонных кейсах | `trading_wiki/benchmark/**/*.yaml` |
| История | pass rate на `as_of` срезах | `trading_wiki/benchmark/historical/*.yaml` |
| Champion/Challenger | agreement, смена action | replay двух моделей |

## API

```powershell
# Отчёт (sample + label + score + snapshots)
curl "http://localhost:8000/api/benchmark/report?days=30"

# Синтетика (известные входы)
curl "http://localhost:8000/api/benchmark/synthetic/cases"
curl -X POST "http://localhost:8000/api/benchmark/synthetic"

# История (реальные котировки на as_of)
curl "http://localhost:8000/api/benchmark/historical/cases"
curl -X POST "http://localhost:8000/api/benchmark/historical"

# Полный прогон outcome + синтетика
curl -X POST "http://localhost:8000/api/benchmark/run" -H "Content-Type: application/json" -d "{\"days\":30}"

# Offline-калибровка (см. раздел ниже)
curl "http://localhost:8000/api/benchmark/calibrate/plan"
curl -X POST "http://localhost:8000/api/benchmark/calibrate" -H "Content-Type: application/json" -d "{}"

# Черновик исторического кейса из live benchmark_cases
curl -X POST "http://localhost:8000/api/benchmark/historical/promote/{inputs_hash}?expected_action=reject&summary=..."
```

## Telegram

**🤖 Автомат → 📊 LLM Benchmark**

- **🧪 Синтетика** — 20 кейсов (v1 + v2), прогресс по шагам
- **📜 История** — 8 кейсов, котировки с биржи на дату
- **📊 Отчёт** — outcome + последние прогоны
- **▶️ Полный прогон** — outcome pipeline + синтетика
- **🎛 Калибровка** — offline-сетка `temperature` × `min_confidence` (долго, ~1–2 ч)

## Offline-калибровка

Подбор `temperature` и `min_confidence` без авто-применения в `guardrails.yaml`.

| Что | Как |
|-----|-----|
| LLM-вызовы | Только по осям **temperature** (4 значения × 28 кейсов) |
| `min_confidence` | Считается пост-фактум через `effective_llm_action()` — без повторных вызовов LLM |
| Holdout | 30% синтетики (по id) — защита от переобучения на фикстурах |
| Outcome | precision на размеченных `benchmark_cases` при каждом пороге |
| Composite | веса в `benchmark_config.yaml` → `calibration.weights` |

```powershell
# План сетки
curl "http://localhost:8000/api/benchmark/calibrate/plan"

# Полный прогон (долго)
curl -X POST "http://localhost:8000/api/benchmark/calibrate" -H "Content-Type: application/json" -d "{}"

# Пошагово (для Telegram / длинных таймаутов)
curl -X POST "http://localhost:8000/api/benchmark/calibrate/temperature" \
  -H "Content-Type: application/json" -d "{\"temperature\": 0.1}"
curl -X POST "http://localhost:8000/api/benchmark/calibrate/finalize"

# Последний снимок
curl "http://localhost:8000/api/benchmark/calibrate/last-snapshot"
```

Рекомендацию вручную перенесите в `trading_wiki/config/guardrails.yaml` → `llm.temperature` и `llm.min_confidence`.

## Конфигурация

`trading_wiki/config/benchmark_config.yaml`

Синтетика:
- `benchmark/crypto_golden_v1.yaml` + `benchmark/synthetic/crypto_extra_v2.yaml`
- `benchmark/moex_golden_v1.yaml` + `benchmark/synthetic/moex_extra_v2.yaml`

История:
- `benchmark/historical/crypto_historical_v1.yaml`
- `benchmark/historical/moex_historical_v1.yaml`

Котировки кэшируются в `ohlcv_candles`. Новости для истории: `news_context_as_of()` или `news_snapshot` в YAML.

После benchmark: `POST /api/benchmark/ollama/reset` (или автоматически при `benchmark_unload_after: true` в guardrails).

## Настройки модели

| Параметр | Файл | Значение |
|----------|------|----------|
| `ollama_model` | `crypto_config.yaml`, `securities_config.yaml` | `qwen3.5:9b` |
| `temperature`, `timeout_ms`, `min_confidence` | `guardrails.yaml` → `llm:` | 0.1, 900000ms, 0.7 |
| `prompt_version` | `crypto_config.yaml` | `crypto_validate_v1` |
| Новости (отдельно) | `news_alerts.yaml` | confidence 0.55, temp 0.15 |

Документация: `trading_wiki/09-LLM промпты и инструменты/LLM_rules_and_guardrails.md`

## Разметка исходов (Outcome)

Для каждого LLM-решения:
1. Entry = `close` из indicators на момент решения
2. Exit = цена через N баров (crypto 4h×6, MOEX 5 дней)
3. Label: good / bad / missed_opportunity / good_reject

Кейсы младше 30ч не размечаются (нет будущих баров).

## Промоушен challenger → champion

1. Синтетика pass rate ≥ 90%
2. История pass rate ≥ 85%
3. Precision approve выше на ≥5 п.п. (≥50 размеченных outcome-кейсов)
4. Paper-тест 2 недели без деградации

⚠️ Outcome metrics — образовательный бэктест, не инвестрекомендация.
