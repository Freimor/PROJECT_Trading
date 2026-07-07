---
title: RSI, MACD и скользящие средние
tags: [технический анализ, RSI, MACD, EMA, SMA, индикаторы]
sources:
  - https://academy.binance.com/en/articles/what-is-the-rsi-indicator
  - https://www.investopedia.com/terms/m/macd.asp
  - https://www.investopedia.com/terms/m/movingaverage.asp
  - https://www.investopedia.com/terms/r/rsi.asp
  - https://www.investopedia.com/terms/e/ema.asp
  - [[Academic_sources]]
updated: 2026-07-06
level: intermediate
academic_sources: true
style: informational
---

# RSI, MACD и скользящие средние

> Три базовых индикатора проекта: **RSI** (momentum), **MACD** (тренд + momentum), **EMA/SMA** (фильтр тренда). Считаются в Code/Python; LLM получает готовые числа.

## Главное

- RSI(14): >70 overbought, <30 oversold — не автоматический buy/sell.
- MACD = EMA(12)−EMA(26); Signal = EMA(9) MACD; cross — сигнал в TA-литературе.
- EMA50/EMA200 + golden/death cross — фильтр тренда в automation.
- Индикаторы **запаздывают** — нужны stop ([[Stop_loss_take_profit]]) и бэктест.
- Sub-workflow `calculate-indicators` — общий для crypto и securities flows.

---

## Для новичка

**Индикатор** — числа из цены и объёма. Формализует правила («RSI < 30»).

**RSI** — скорость и сила движения. **MACD** — разница короткой и длинной EMA. **EMA/SMA** — средняя цена за N периодов.

Не магия: строятся на прошлых ценах. Требуют бэктеста и stop.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | **RSI (Relative Strength Index)** — momentum oscillator 0–100; разработан J. Welles Wilder Jr. | [Investopedia: RSI](https://www.investopedia.com/terms/r/rsi.asp) |
| 2 | Классические уровни RSI: **>70** overbought, **<30** oversold — не автоматические сигналы buy/sell. | [Binance Academy: RSI](https://academy.binance.com/en/articles/what-is-the-rsi-indicator) |
| 3 | **MACD** = EMA(12) − EMA(26); Signal line = EMA(9) of MACD; Histogram = MACD − Signal. | [Investopedia: MACD](https://www.investopedia.com/terms/m/macd.asp) |
| 4 | **Bullish MACD cross:** MACD line crosses **above** signal line. **Bearish cross:** below. | [Investopedia: MACD](https://www.investopedia.com/terms/m/macd.asp) |
| 5 | **SMA** — simple moving average: arithmetic mean of last N closes. | [Investopedia: Moving Average](https://www.investopedia.com/terms/m/movingaverage.asp) |
| 6 | **EMA** — exponential moving average: more weight to recent prices; reacts faster than SMA. | [Investopedia: EMA](https://www.investopedia.com/terms/e/ema.asp) |
| 7 | **Golden cross:** shorter MA (e.g. 50) crosses **above** longer MA (e.g. 200) — bullish signal in TA literature. **Death cross** — opposite. | [Investopedia: Moving Average](https://www.investopedia.com/terms/m/movingaverage.asp) |

---

## Подробно: RSI

### Формула (Wilder smoothing, simplified description)

1. `change = close_t - close_{t-1}`
2. `gain = max(change, 0)`, `loss = max(-change, 0)`
3. Average gain/loss over N periods (typically N=14)
4. `RS = avg_gain / avg_loss`
5. `RSI = 100 - (100 / (1 + RS))`

### Интерпретация

| RSI zone | Typical label | Automation use |
|----------|---------------|----------------|
| > 70 | Overbought | Exit filter, not auto-short alone |
| 30–70 | Neutral | Context only |
| < 30 | Oversold | Entry **candidate** with trend filter |

**Divergence:** price makes new low, RSI doesn't — potential reversal. Hard to automate in v1; LLM may note if provided both series.

### Default parameters (project)

```yaml
rsi_period: 14
rsi_oversold: 30
rsi_overbought: 70
```

---

## Подробно: MACD

### Components

| Component | Calculation |
|-----------|-------------|
| MACD line | EMA(12) − EMA(26) |
| Signal line | EMA(9) of MACD line |
| Histogram | MACD − Signal |

### Signals (TA literature)

| Signal | Condition |
|--------|-----------|
| Bullish cross | MACD crosses above Signal |
| Bearish cross | MACD crosses below Signal |
| Histogram > 0 | MACD above Signal (bullish momentum) |
| Histogram rising | Momentum increasing |

### Default parameters (project)

```yaml
macd_fast: 12
macd_slow: 26
macd_signal: 9
```

---

## Подробно: Moving Averages

### SMA vs EMA

| | SMA | EMA |
|---|-----|-----|
| Weight | Equal all N periods | Exponential decay |
| Lag | More | Less |
| Use | Long-term trend | Responsive trend |

### Project EMAs

| EMA | Use |
|-----|-----|
| EMA50 | Medium trend, pullback target |
| EMA200 | Long trend filter |

**Trend rule (automation):**
```
trend = "up" if close > EMA200 and EMA50 > EMA200
trend = "down" if close < EMA200 and EMA50 < EMA200
else trend = "range"
```

### Golden / Death cross

```
golden_cross = EMA50 crosses above EMA200 (detect: prev EMA50 < EMA200, now EMA50 > EMA200)
death_cross = opposite
```

---

## Комбинированная стратегия (учебный шаблон)

```
Trend filter:    close > EMA200
Entry candidate: RSI crosses above 30 from below AND MACD histogram turns positive
Exit idea:       RSI > 70 OR stop-loss hit ([[Stop_loss_take_profit]])
Position size:   [[Position_sizing]] — 1% risk
```

> **Не рекомендация.** Требует бэктеста, учёта комиссий, slippage. LLM validates context, не заменяет backtest.

---

## Примеры

### Пример 1: Indicator output для BTCUSDT 4h

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "4h",
  "close": 60200,
  "rsi_14": 28.4,
  "macd": -120.5,
  "macd_signal": -95.2,
  "macd_histogram": -25.3,
  "macd_histogram_prev": -40.1,
  "ema50": 60100,
  "ema200": 58500,
  "trend": "up",
  "signals": {
    "rsi_oversold": true,
    "macd_histogram_rising": true,
    "above_ema200": true
  }
}
```

### Пример 2: Rule filter logic

```javascript
const d = $json;
const rules = [];
if (d.rsi_14 < 30 && d.trend === 'up') rules.push('rsi_oversold_in_uptrend');
if (d.macd_histogram > d.macd_histogram_prev && d.macd_histogram < 0) {
  rules.push('macd_histogram_turning_positive');
}
if (d.ema50 > d.ema200 && d.close > d.ema50) rules.push('golden_cross_context');
return [{ json: { ...d, rules, proceed: rules.length > 0 } }];
```

### Пример 3: SBER daily MOEX

| Indicator | Value | Interpretation |
|-----------|-------|----------------|
| RSI(14) | 31 | Near oversold |
| Close vs EMA50 | −4.2% | Pullback |
| EMA50 vs EMA200 | above | Uptrend intact |
| → Rule | rsi_oversold_in_uptrend | proceed to LLM |

### Пример 4: False signal rejection

RSI = 28 but trend = down (below EMA200) → rule filter **skip** — catching falling knife.

---

## FAQ

### RSI 29 — автоматически buy?

**Нет.** Oversold может стать «more oversold». Trend filter обязателен.

### Какой RSI period?

**14** — Wilder default, industry standard. Альтернативы (7, 21) — только после backtest comparison.

### MACD на crypto 4h vs stocks daily?

Same formula; different **noise profile**. Crypto needs wider stops ([[Stop_loss_take_profit]]).

### ta-lib vs custom Code node?

**ta-lib** (Python) — battle-tested, faster for backtest. **Code node** (JS) — sufficient for live n8n without Python sidecar.

### Как тестировать индикаторы?

Fixed CSV input → expected output vs manual calculation or ta-lib reference. Unit test in `python/tests/test_indicators.py`.

---

## Частые ошибки

1. **RSI alone** — без trend context.
2. **Repainting** — using future data in backtest (look-ahead bias).
3. **Different params live vs backtest** — RSI(14) in prod, RSI(7) in test.
4. **Ignoring warmup** — first 200 candles invalid for EMA200.
5. **Over-trading MACD crosses** — whipsaw in range market.

---

## Ключевые понятия

| Термин | Определение |
|--------|-------------|
| Oscillator | Индикатор с bounded range (RSI 0–100) |
| Lagging indicator | Based on past prices |
| Cross | One line crosses another |
| Histogram | MACD − Signal visual |
| Warmup period | Min candles before indicator valid |

---

## Проверенные источники

1. **[Binance Academy: RSI](https://academy.binance.com/en/articles/what-is-the-rsi-indicator)** — RSI explained.
2. **[Investopedia: RSI](https://www.investopedia.com/terms/r/rsi.asp)** — formula and usage.
3. **[Investopedia: MACD](https://www.investopedia.com/terms/m/macd.asp)** — MACD components.
4. **[Investopedia: Moving Average](https://www.investopedia.com/terms/m/movingaverage.asp)** — SMA, golden cross.
5. **[Investopedia: EMA](https://www.investopedia.com/terms/e/ema.asp)** — exponential MA.

---

## Академические источники

См. также: [[Academic_sources]].

| Категория | Что изучать | Почему полезно | URL |
|---|---|---|---|
| MIT / A. Lo (2022) | 15.481x Adaptive Markets: Financial Market Dynamics and Human Behavior (Fall 2022) | Про «режимы рынка» и адаптацию — важно для понимания, что параметры индикаторов не универсальны | https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/resources/mit-economist-andrew-w-lo-on-finance-ai-and-human-behavior/ |
| IEEE (2025) | Evolving Portfolio Heuristics: A Self-Correcting LLM Framework for Portfolio Optimization | Пример, где LLM/эвристики используются поверх сигналов; полезно как академический фон для связки «индикаторы → портфель» | https://ieeexplore.ieee.org/document/11200704/ |
| arXiv (2025) | Decision by Supervised Learning with Deep Ensembles (arXiv:2503.13544) | Устойчивость решений через ансамбли — можно применять к ансамблю сигналов/индикаторов | https://arxiv.org/abs/2503.13544 |
| ВШЭ (ВКР, 2024) | Hedging Derivatives Under Incomplete Markets with Deep Learning (VKR 929592108) | Показательный пример «модель → веса → сделки», полезно для понимания связки сигналов и исполнения | https://www.hse.ru/en/edu/vkr/929592108 |

---

## В автоматической системе

### Python implementation (`python/indicators/ta_lib.py`)

```python
import pandas as pd

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_all(candles: list[dict]) -> dict:
    df = pd.DataFrame(candles)
    close = df['c']
    rsi_val = rsi(close).iloc[-1]
    macd_l, sig_l, hist = macd(close)
    ema50 = ema(close, 50).iloc[-1]
    ema200 = ema(close, 200).iloc[-1]
    last = close.iloc[-1]
    trend = 'up' if last > ema200 and ema50 > ema200 else (
        'down' if last < ema200 and ema50 < ema200 else 'range')
    return {
        'rsi_14': round(rsi_val, 2),
        'macd': round(macd_l.iloc[-1], 4),
        'macd_signal': round(sig_l.iloc[-1], 4),
        'macd_histogram': round(hist.iloc[-1], 4),
        'macd_histogram_prev': round(hist.iloc[-2], 4),
        'ema50': round(ema50, 2),
        'ema200': round(ema200, 2),
        'trend': trend,
        'close': round(last, 2)
    }
```

### n8n Code node (JavaScript, no pandas)

```javascript
function emaSeries(values, span) {
  const k = 2 / (span + 1);
  let ema = values[0];
  const result = [ema];
  for (let i = 1; i < values.length; i++) {
    ema = values[i] * k + ema * (1 - k);
    result.push(ema);
  }
  return result;
}

function rsi(values, period = 14) {
  if (values.length < period + 1) return null;
  let gains = 0, losses = 0;
  for (let i = values.length - period; i < values.length; i++) {
    const change = values[i] - values[i - 1];
    if (change > 0) gains += change; else losses -= change;
  }
  const rs = (gains / period) / (losses / period || 1e-10);
  return 100 - (100 / (1 + rs));
}

const closes = $json.candles.map(c => c.c);
const ema50s = emaSeries(closes, 50);
const ema200s = emaSeries(closes, 200);
// ... MACD similar ...
return [{ json: { rsi_14: rsi(closes), ema50: ema50s.at(-1), /* ... */ } }];
```

### Sub-workflow: `calculate-indicators`

**Input:** `{ candles: Candle[] }`  
**Output:** indicator JSON schema (above)  
**Called from:** [[Crypto_flow_design]], [[Securities_flow_design]]

### LLM schema (pass to prompt)

Only numbers + trend + rule flags — см. [[LLM_prompts_trading]].

### Unit test fixture

```csv
date,close
2025-01-01,100
2025-01-02,102
...
```

Expected RSI(14) on last row = X.XX (verify vs TradingView or ta-lib).

### Performance

| Candles | JS Code node | Python |
|---------|--------------|--------|
| 100 | ~50ms | ~20ms |
| 500 | ~200ms | ~40ms |

For 20 tickers batch — use Python sidecar or Split In Batches with 200ms delay.

---

## Связанные темы

- [[Technical_analysis_basics]]
- [[Crypto_indicators]]
- [[Crypto_flow_design]]
- [[Securities_flow_design]]
- [[LLM_prompts_trading]]
- [[Stop_loss_take_profit]]
- [[Position_sizing]]

---

## Что изучить дальше

1. [[Technical_analysis_basics]] — OHLCV, trend, support/resistance.
2. [[Stop_loss_take_profit]] — ATR-based stops.
3. [[Position_sizing]] — связь stop distance и qty.
4. [[LLM_prompts_trading]] — передача indicators в LLM.
