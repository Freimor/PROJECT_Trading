FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY db/ ./db/
COPY api/ ./api/
COPY indicators/ ./indicators/
COPY bridges/ ./bridges/
COPY evaluation/ ./evaluation/
COPY backtest/ ./backtest/
COPY config_loader.py guardrails.py utils.py event_log.py llm_client.py \
     binance_client.py news_service.py crypto_pipeline.py securities_pipeline.py \
     smoke_test.py runtime_settings.py effective_config.py admin_service.py \
     telegram_notify.py telegram_proxy.py testing_service.py bot_data_service.py automation_docs.py news_verification.py news_alert_service.py paper_trading_service.py n8n_service.py benchmark_service.py historical_benchmark_service.py market_data.py ohlcv_cache.py calibration_service.py charts_service.py llm_audit_service.py portfolio_snapshot_service.py portfolio_performance_service.py activity_feed_service.py strategy_service.py event_summary.py ./
COPY proxy_gateway/ ./proxy_gateway/

ENV TRADING_DB_PATH=/data/trading.db
ENV WIKI_CONFIG_PATH=/data/trading_wiki
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
