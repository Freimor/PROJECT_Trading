# Python — вспомогательные модули

## Структура

```
python/
├── api/           # FastAPI sidecar для n8n (этап 1)
├── db/            # SQLite init и connection
├── indicators/    # RSI, MACD (этап 2)
├── bridges/       # T-Invest gRPC bridge (этап 5)
├── backtest/      # Исторический replay (этап 6)
└── evaluation/    # Сравнение LLM (этап 6)
```

## Локальная разработка

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m db.init_db
uvicorn api.main:app --reload --port 8000
```

## Docker

Собирается автоматически через `docker compose up --build` как сервис `db-api`.

## Когда использовать Python vs n8n

| Задача | Инструмент |
|--------|------------|
| Triggers, HTTP, ветвления | n8n |
| pandas, ta-lib, бэктест | Python |
| T-Invest gRPC | Python bridge → n8n HTTP |
| Запись в SQLite | DB API (FastAPI) |
