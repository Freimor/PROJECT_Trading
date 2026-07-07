---
title: Крипто-индикаторы
tags: [криптовалюта, индикаторы, RSI, MACD, on-chain, TA]
sources:
  - https://academy.binance.com/en/articles/what-is-the-rsi-indicator
  - https://www.investopedia.com/terms/r/rsi.asp
  - https://www.investopedia.com/terms/m/macd.asp
  - https://developers.binance.com/docs/binance-spot-api-docs/rest-api#kline-candlestick-data
  - https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities
  - https://doi.org/10.1109/access.2025.3624652
  - https://arxiv.org/html/2503.13544
  - https://www.gsb.stanford.edu/experience/learning/experiential-learning/rail/curricular-integration
updated: 2026-07-06
level: intermediate
academic_sources: true
style: informational
---

# Крипто-индикаторы

> Индикаторы на крипторынке: технические (из цены/объёма) и on-chain (из blockchain). Оба описывают прошлое и не гарантируют будущую доходность ([Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)).

## Главное

- TA строит индикаторы из OHLCV-свечей; Binance API отдаёт klines в JSON.
- RSI >70 — overbought, <30 — oversold; на crypto часто используют 80/20 из‑за волатильности.
- MACD показывает связь двух EMA; histogram выше нуля — bullish momentum.
- On-chain метрики (active addresses, exchange inflow) — macro context, не HFT-триггер.
- Правило automation: индикатор → rule → LLM validate → risk → order.

---

## Для новичка

Технический анализ строит индикаторы из OHLCV — Open, High, Low, Close, Volume. Binance API отдаёт klines ([Binance Kline Data](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#kline-candlestick-data)).

On-chain аналитика использует публичный ledger: active addresses, потоки на/с бирж. Интерпретация субъективна и часто запаздывает.

Индикатор alone не отправляет market buy. Цепочка: индикатор → rule → LLM validate → risk → order.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | RSI — momentum oscillator, scale 0–100; developed by J. Welles Wilder Jr. | [Investopedia: RSI](https://www.investopedia.com/terms/r/rsi.asp) |
| 2 | Binance Academy: RSI >70 overbought, <30 oversold; not perfect signals. | [Binance Academy: RSI](https://academy.binance.com/en/articles/what-is-the-rsi-indicator) |
| 3 | MACD — trend-following momentum indicator; relationship between two EMAs. | [Investopedia: MACD](https://www.investopedia.com/terms/m/macd.asp) |
| 4 | Binance kline array: [open time, open, high, low, close, volume, close time, ...]. | [Binance API: Klines](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#kline-candlestick-data) |
| 5 | Crypto markets trade 24/7 — нет overnight gap как на MOEX. | Market structure observation |
| 6 | SEC: crypto highly volatile — indicators based on past volatility may fail in regime change. | [Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities) |

---

## Технические индикаторы

### RSI (Relative Strength Index)

**Формула (Wilder):** RSI = 100 − (100 / (1 + RS)), где RS = average gain / average loss за period (typically **14**).

| Зона (classic) | Интерпретация (осторожно) |
|----------------|---------------------------|
| > 70 | Overbought — possible pullback |
| < 30 | Oversold — possible bounce |
| 40–60 | Neutral |

**Crypto adjustment:** многие strategies используют **80/20** из‑за higher volatility — document in `strategy.yaml`, не как universal truth.

**Divergence:** price higher high + RSI lower high → bearish divergence (hypothesis, not proof).

### MACD

Typical params: **12, 26, 9** EMA.

| Комponent | Meaning |
|-----------|---------|
| MACD line | EMA12 − EMA26 |
| Signal line | EMA9 of MACD |
| Histogram | MACD − Signal |

**Signal example (rule-based):** histogram crosses above zero → bullish momentum shift.

### Moving Averages

- **SMA** — simple average close.
- **EMA** — exponential weight recent prices.

**Golden cross:** SMA50 crosses above SMA200 (lagging, popular in media).

### Bollinger Bands

Middle = SMA(20); bands = ±2 standard deviations. **Squeeze** — low volatility before expansion (empirical pattern).

### Volume

Volume confirms price moves. **OBV** (On-Balance Volume) cumulative volume direction — см. [[Key_indicators_RSI_MACD]].

### ATR (Average True Range)

Volatility measure for **stop placement** — [[Stop_loss_take_profit]]:

```
stop_distance = ATR(14) × multiplier
```

---

## On-chain индикаторы (обзор)

| Metric | Что измеряет | Caveat |
|--------|--------------|--------|
| **Active addresses** | Network usage | Not equal unique users |
| **Exchange inflow** | Deposits to CEX | Large inflow ≠ instant sell |
| **Exchange outflow** | Withdrawals | Cold storage vs OTC |
| **MVRV** | Market cap / realized cap | Valuation heuristic |
| **NVT** | Network value / transaction volume | Noisy |

Data vendors: Glassnode, CryptoQuant, Coin Metrics — **license** for commercial automation.

**Project default:** on-chain — **weekly macro note** in Obsidian, not HFT trigger.

---

## Crypto-specific considerations

### 24/7 sessions

Indicators on **4h/1d** less noise than 1m. Align with sleep + ops: automation on **closed candles** only.

### BTC correlation

Altcoin RSI signal **filtered** when BTC trend down — см. [[Bitcoin_overview]] dominance filter.

### Stablecoin depeg

USDT/USDC off $1 distorts USD-denominated indicators — monitor peg in macro-flow.

### Funding rate (futures)

Not spot scope; if enabled later — separate module.

---

## Примеры

### Пример 1: RSI oversold + trend filter

```
Conditions:
  RSI(14, 4h) < 30
  Close > EMA200(1d)   # long only in uptrend
  BTCUSDT 1d not -5% day
Action candidate: LONG with 1% risk
```

### Пример 2: MACD histogram flip

Histogram crosses from negative to positive on ETHUSDT 4h → candidate; LLM checks macro `risk_off` flag.

### Пример 3: False RSI signal

Flash crash wick → RSI < 20 for one candle → recovers — stop hunted if entry on single tick. **Mitigation:** wait candle **close**.

### Пример 4: On-chain weekly

Exchange netflow positive 7 days → note «potential sell pressure» in Obsidian; **no auto trade**.

---

## Частые ошибки новичков

1. **RSI >70 = must sell** — trends can stay overbought long in bull run.
2. **Индикаторы на разных TF без иерархии** — conflict: 1h buy vs 1d sell.
3. **Look-ahead bias в backtest** — using future data in Code node.
4. **Overfitting** — 20 params tuned to past month.
5. **On-chain как gospel** — lag and interpretation risk.
6. **Игнор fees/slippage** — RSI edge erased by costs.

---

## FAQ

### Какой timeframe для bots?

Project default: **4h signal**, **1d trend filter**. Adjust in config after backtest.

### RSI(14) vs RSI(7)?

Shorter period — more sensitive, more false signals. Document choice.

### Нужен ли TradingView?

Optional for visual; automation uses Binance klines + Code/Python.

### LLM может «придумать» RSI?

No — RSI **always** computed in Code; LLM receives number only ([[LLM_rules_and_guardrails]] G2).

### On-chain бесплатно?

Raw blockchain data public; aggregated metrics often paid.

---

## Проверенные источники

1. **[Binance Academy: RSI](https://academy.binance.com/en/articles/what-is-the-rsi-indicator)**
2. **[Investopedia: RSI](https://www.investopedia.com/terms/r/rsi.asp)**
3. **[Investopedia: MACD](https://www.investopedia.com/terms/m/macd.asp)**
4. **[Binance API: Kline/Candlestick Data](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#kline-candlestick-data)**
5. **[Investor.gov: Crypto volatility](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)**

---

## Академические источники

Полный свод университетских курсов и научных публикаций (2021+) — в заметке [[Academic_sources]].

| Учреждение | Ресурс (2021+) | Что подтверждает для этой темы | Ссылка |
|-----------|----------------|--------------------------------|--------|
| IEEE Access | CVaR + DRL + LLM sentiment (2025) | Технические индикаторы + FinBERT sentiment для торговых сигналов | [doi.org/10.1109/access.2025.3624652](https://doi.org/10.1109/access.2025.3624652) |
| arXiv | Kim et al. — 2503.13544 (2025) | Deep Ensembles для robust portfolio optimization на крипторынке | [arxiv.org/html/2503.13544](https://arxiv.org/html/2503.13544) |
| Stanford GSB | FINANCE 562 — Financial Trading Strategies | Технический анализ и алгоритмические торговые стратегии | [www.gsb.stanford.edu/experience/learning/experi...](https://www.gsb.stanford.edu/experience/learning/experiential-learning/rail/curricular-integration) |
| MIT | 15.481X Adaptive Markets (Fall 2022) | Ограничения технического анализа в адаптивных рынках | [ocw.mit.edu/courses/15-481x-adaptive-markets-fi...](https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/) |

---

## В автоматической системе

### Pipeline `crypto-signal-flow`

```
Trigger: WebSocket kline close (BTCUSDT 4h)
  → HTTP fallback: GET /api/v3/klines limit=200
  → Code node: RSI, MACD, EMA200, ATR
  → IF rule_match → Ollama validate
  → Risk: position size, daily loss
  → Binance: LIMIT entry + OCO SL/TP
  → Obsidian log
```

### Code node: RSI(14)

```javascript
function calculateRSI(closes, period = 14) {
  if (closes.length < period + 1) return null;
  let gains = 0, losses = 0;
  for (let i = closes.length - period; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) gains += diff; else losses -= diff;
  }
  const avgGain = gains / period;
  const avgLoss = losses / period;
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

const closes = $json.klines.map(k => parseFloat(k[4]));
const rsi = calculateRSI(closes, 14);
return [{ json: { rsi, symbol: 'BTCUSDT', timeframe: '4h' } }];
```

### MACD (simplified EMA)

Use same Code node or Python microservice for Wilder-smoothed RSI if matching TradingView — document smoothing difference.

### Rule engine (YAML)

```yaml
long_setup:
  all:
    - rsi_4h: { lt: 30 }
    - close_4h: { gt: ema200_1d }
    - macro.risk_off: false
  action: LONG
  sl_atr_mult: 2.0
  tp_rr: 2.0
```

### Ollama input JSON

```json
{
  "rsi": 28.4,
  "macd_histogram": 12.5,
  "trend": "above_ema200",
  "macro": { "risk_off": false, "spx_1d": -0.3 },
  "rule_fired": "long_setup"
}
```

Output schema: `{ "action": "approve"|"reject", "reason": "string" }`

### Multi-timeframe fetch

Parallel klines: `interval=4h` and `interval=1d` — merge by symbol before rules.

### Backtest hook (future)

Export klines to CSV → Python backtest → metrics (win rate, max DD) → update thresholds **only** after human review.

### Monitoring

- Indicator NaN rate (bad data);
- Signal frequency (overtrading alert);
- Compare live RSI vs Binance chart spot check weekly.

---

## Связанные темы

- [[Key_indicators_RSI_MACD]]
- [[Technical_analysis_basics]]
- [[Bitcoin_overview]]
- [[Crypto_flow_design]]
- [[LLM_prompts_trading]]
- [[Stop_loss_take_profit]]

---

## Ichimoku и Fibonacci (кратко)

**Ichimoku Cloud** — multi-line system (Tenkan, Kijun, Senkou spans). Popular on crypto charts; automation может extract **price above cloud** boolean for trend filter.

**Fibonacci retracement** — 38,2% / 50% / 61,8% levels from swing high/low. **Subjective** anchor choice — LLM **не** выбирает swing points; only human-configured levels in YAML if used.

---

## Multi-timeframe analysis (MTF)

| Layer | Timeframe | Role |
|-------|-----------|------|
| Trend | 1d | EMA200 direction |
| Signal | 4h | RSI, MACD |
| Execution | 1h or 15m | Entry timing (optional) |

Rule: **higher TF wins** on conflict — 1d downtrend blocks 4h long unless strategy explicitly allows counter-trend with reduced size.

---

### Wilder smoothing note

TradingView RSI uses Wilder smoothing; simple average RSI differs slightly. Document which implementation Code node uses; align backtest with live.

```javascript
// Prefer Wilder for consistency with Binance Academy / TV
// See Key_indicators_RSI_MACD for full Wilder loop
```

---

## Signal quality metrics

Track monthly in Obsidian:

| Metric | Formula |
|--------|---------|
| Win rate | wins / total trades |
| Profit factor | gross profit / gross loss |
| Expectancy | avg win × WR − avg loss × LR |
| Max DD | peak-to-trough equity |

Indicators alone don't define these — execution and risk management matter.

---

## Практический чеклист indicator strategy

1. Define indicators in **YAML**, not in LLM prompt prose.
2. Use **closed candles** only (`k.x === true` on Binance WS).
3. Backtest minimum 100 trades or 2 years data before live.
4. Include fees 0,1% round-trip in expectancy calc.
5. Log every signal with indicator snapshot JSON in Obsidian.
6. Review false signal rate monthly.

---

## Расширенный FAQ

### Stochastic vs RSI?

Both oscillators; redundant if both fire same rules — avoid double-counting.

### VWAP для crypto?

VWAP intraday meaningful on CEX; reset at UTC 00:00 — document session anchor.

### Machine learning on indicators?

Out of default project scope; requires separate validation pipeline.

---

## Упражнение

RSI=28, MACD histogram positive, price below EMA200. Does default `long_setup` fire? (No — trend filter blocks.)

---

## Что изучить дальше

1. [[Key_indicators_RSI_MACD]] — углублённый RSI/MACD.
2. [[Stop_loss_take_profit]] — ATR stops.
3. [[LLM_prompts_trading]] — validation prompts.
4. [[Position_sizing]] — risk from stop distance.
