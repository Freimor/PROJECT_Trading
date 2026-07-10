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
COPY on_chain/ ./on_chain/
COPY trading_agents/ ./trading_agents/
COPY *.py ./
COPY proxy_gateway/ ./proxy_gateway/

ENV TRADING_DB_PATH=/data/trading.db
ENV WIKI_CONFIG_PATH=/data/trading_wiki
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
