# LLM Benchmark

Система оценки качества решений локальной LLM в торговом автомате.

## Уровни оценки

| Уровень | Метрики | Источник |
|---------|---------|----------|
| Операционный | approve rate, latency, confidence | `llm_decisions` |
| Outcome | precision, recall, sim PnL | forward return после решения |
| Golden set | pass rate на эталонных кейсах | `trading_wiki/benchmark/*.yaml` |
| Champion/Challenger | agreement, смена action | replay двух моделей |

## API

```powershell
# Отчёт (sample + label + score)
curl "http://localhost:8000/api/benchmark/report?days=30"

# Только golden set (регрессия промпта)
curl -X POST "http://localhost:8000/api/benchmark/golden"

# Полный прогон
curl -X POST "http://localhost:8000/api/benchmark/run" -H "Content-Type: application/json" -d "{\"days\":30}"
```

## Telegram

**🤖 Автомат → 📊 LLM Benchmark**

- **📊 Отчёт** — precision/recall + sim PnL
- **🏅 Golden set** — 10 эталонных кейсов
- **▶️ Полный прогон** — отчёт + golden

## Конфигурация

`trading_wiki/config/benchmark_config.yaml` — горизонты, пороги good/bad return.

Golden sets:
- `trading_wiki/benchmark/crypto_golden_v1.yaml`
- `trading_wiki/benchmark/moex_golden_v1.yaml`

## Разметка исходов

Для каждого LLM-решения:
1. Entry = `close` из indicators на момент решения
2. Exit = цена через N баров (crypto 4h×6, MOEX 5 дней)
3. Label:
   - `approve` + return ≥ good% → **good**
   - `approve` + return ≤ bad% → **bad**
   - `reject` + рост ≥ good% → **missed_opportunity**
   - `reject` + падение ≤ bad% → **good_reject**

Кейсы младше 30ч не размечаются (нет будущих баров).

## n8n

Workflow `llm-benchmark-weekly` — воскресенье 09:00 MSK, полный прогон + Telegram summary.

Активируйте в **🖥 Управление → 🧩 Workflows**.

## Промоушен challenger → champion

Перед сменой модели/промпта:
1. Golden pass rate ≥ 90%
2. Precision approve выше на ≥5 п.п. (≥50 размеченных кейсов)
3. Paper-тест 2 недели без деградации

⚠️ Outcome metrics — образовательный бэктест, не инвестрекомендация.
