---
title: Bitcoin — обзор
tags: [криптовалюта, bitcoin, BTC, halving, PoW]
sources:
  - https://bitcoin.org/bitcoin.pdf
  - https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities
  - https://academy.binance.com/en/articles/what-is-bitcoin
  - https://academy.binance.com/en/articles/bitcoin-halving
  - https://mempool.space/
  - https://www.bis.org/publ/bppdf/bispap156.pdf
  - https://wp.hse.ru/fe/BRP/86/2022
  - https://www.bis.org/publ/work1146.pdf
updated: 2026-07-06
level: beginner
academic_sources: true
style: informational
---

# Bitcoin — обзор

> Bitcoin (BTC) — децентрализованная цифровая валюта из whitepaper Satoshi Nakamoto (2008). Сеть работает без центрального эмитента; правила эмиссии и консенсуса заданы протоколом.

## Главное

- BTC передаёт ценность через интернет без обязательного банка-посредника.
- Максимум 21 млн BTC; темп эмиссии снижается через halving каждые ~210 000 блоков (~4 года).
- Mining (Proof-of-Work) — майнеры включают транзакции в блоки за block reward + комиссии.
- Цена на биржах волатильна; SEC предупреждает о риске потери всего вложения.
- В automation BTCUSDT — основная пара; halving — macro context, не сигнал к покупке.

---

## Для новичка

Bitcoin решает задачу передачи ценности через интернет без банка. Вместо баланса на счёте — глобальный реестр транзакций, который поддерживают тысячи узлов.

Mining — включение транзакций в блоки через Proof-of-Work: майнеры ищут hash ниже target difficulty. За блок — block reward и комиссии.

Протокол ограничивает эмиссию 21 000 000 BTC. Темп снижается через halving — см. таблицу фактов ниже.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | Whitepaper предлагает peer-to-peer electronic cash без financial institution. | [Bitcoin whitepaper (PDF)](https://bitcoin.org/bitcoin.pdf) |
| 2 | Сеть использует Proof-of-Work и timestamp server (blockchain) для ordering транзакций. | [Bitcoin whitepaper](https://bitcoin.org/bitcoin.pdf) |
| 3 | Максимальный supply Bitcoin — 21 million coins. | [Binance Academy: What is Bitcoin](https://academy.binance.com/en/articles/what-is-bitcoin) |
| 4 | Halving: block reward уменьшается вдвое примерно каждые four years (210 000 blocks). | [Binance Academy: Bitcoin Halving](https://academy.binance.com/en/articles/bitcoin-halving) |
| 5 | SEC: crypto assets highly volatile; investors могут lose entire investment. | [Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities) |
| 6 | Подтверждённые транзакции публичны в blockchain (pseudonymity addresses). | [Bitcoin whitepaper](https://bitcoin.org/bitcoin.pdf) |
| 7 | Block time target ~10 minutes (adjustment difficulty каждые 2016 blocks). | [Bitcoin.org / Core docs](https://bitcoin.org/en/developer-documentation) |

---

## Ключевые свойства

| Свойство | Практический смысл |
|----------|-------------------|
| **Capped supply** | Нет central bank inflation schedule; последний BTC по модели — после многих halvings |
| **Decentralization** | Нет single operator; изменения протокола — social + developer consensus |
| **Transparency** | Explorers (mempool.space и др.) показывают txs, fees, mempool |
| **Volatility** | Цена BTC на биржах может меняться резко за часы |
| **Irreversibility** | Confirmed on-chain txs нельзя «отменить» как chargeback карты |

---

## Halving — механизм эмиссии

### Что происходит

Каждые **210 000** блоков (~4 года при ~10 min/block) **block subsidy** делится пополам. Binance Academy описывает это как встроенный **deflationary mechanism** для темпа новых монет.

### Исторические halvings (публичные данные сети)

| Период (approx) | Block reward после события |
|-----------------|----------------------------|
| 2009 launch | 50 BTC |
| 1st halving (2012) | 25 BTC |
| 2nd (2016) | 12,5 BTC |
| 3rd (2020) | 6,25 BTC |
| 4th (2024) | 3,125 BTC |

Точные block heights — blockchain explorers и [Binance Academy: Halving](https://academy.binance.com/en/articles/bitcoin-halving).

> **Не доказано** regulatorily, что halving **предсказывает** цену. Используйте halving как **macro context** в LLM, не как deterministic buy signal.

---

## UTXO модель (упрощённо)

Bitcoin не хранит «баланс счёта», а набор **Unspent Transaction Outputs (UTXO)**. Когда вы «тратите» BTC, вы создаёте новые outputs; сдача возвращается на change address.

Для automation on-chain не критично; для **withdrawals** и audit — понимать fees и input sizing полезно.

---

## Bitcoin vs другие активы

| Аспект | BTC | IMOEX basket | USD cash |
|--------|-----|--------------|----------|
| Часы торговли | 24/7 CEX | MOEX session | N/A |
| Volatility | Высокая | Умеренная–высокая | Низкая (номинал) |
| Custody | Self or CEX | Broker/clearing | Bank |
| Regulator | Evolving | CBR + MOEX | Central bank |

Корреляция BTC с **NASDAQ** / **S&P 500** **нестабильна** — пересчитывайте rolling correlation в macro-flow ([[Global_indices]]).

---

## Примеры

### Пример 1: Комиссия сети

При congestion mempool растёт → miners приоритизируют txs с **высокей fee rate** (sat/vB). Automation withdrawals должна query **recommended fee**, не fixed fee.

### Пример 2: Confirmations policy

Биржа зачисляет BTC после **N confirmations** (N зависит от биржи). Не считайте tx final после 0-conf для крупных сумм.

### Пример 3: BTC как benchmark crypto-flow

```
IF btc_24h_change < -5% THEN altcoin_long_signals = disabled
```

Rule-based; LLM получает флаг `btc_stress: true`.

### Пример 4: Dominance

**BTC dominance** = BTC market cap / total crypto market cap (данные CoinGecko/CMC). Рост dominance часто сопровождает **flight to BTC** из altcoins — эмпирическое наблюдение, не закон.

---

## Частые ошибки новичков

1. **«Bitcoin anonymous»** — chain analysis существует; CEX KYC связывает identity.
2. **Хранить BTC только on exchange** — counterparty risk FTX-style collapses history.
3. **Игнорировать fees** — small UTXO expensive to spend.
4. **Trade halving narrative без risk rules** — volatility around events.
5. **Путать BTC и Bitcoin Cash / другие forks** — разные tickers и chains.
6. **BIP-39 seed на фото** — social engineering + malware risk.

---

## FAQ

### Кто создал Bitcoin?

Pseudonym **Satoshi Nakamoto**; identity не подтверждена публично. Whitepaper — [bitcoin.org/bitcoin.pdf](https://bitcoin.org/bitcoin.pdf).

### Сколько BTC уже mined?

Circulating supply — live metric на explorers ([mempool.space](https://mempool.space/)) и data APIs. Wiki не фиксирует число — оно меняется каждый блок.

### Можно ли купить долю BTC?

Да — BTC **divisible** до 8 decimal places (1 satoshi = 0,00000001 BTC). На Binance minimum notional зависит от pair rules.

### Spot Bitcoin ETF (US)?

SEC одобрила spot Bitcoin ETF issuers в 2024 — продукты для инвесторов через brokerage, не замена on-chain BTC. Читайте prospectus конкретного ETF ([SEC EDGAR](https://www.sec.gov/edgar)).

### Lightning Network?

Layer-2 для faster/smaller payments — отдельная инфраструктура; trading automation обычно on CEX spot, не Lightning.

---

## Проверенные источники

1. **[Bitcoin whitepaper (PDF)](https://bitcoin.org/bitcoin.pdf)**
2. **[Binance Academy: What is Bitcoin](https://academy.binance.com/en/articles/what-is-bitcoin)**
3. **[Binance Academy: Bitcoin Halving](https://academy.binance.com/en/articles/bitcoin-halving)**
4. **[Investor.gov: Crypto risks](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)**
5. **[Bitcoin Developer Documentation](https://bitcoin.org/en/developer-documentation)**
6. **[Mempool.space — explorer](https://mempool.space/)**

---

## Академические источники

Полный свод университетских курсов и научных публикаций (2021+) — в заметке [[Academic_sources]].

| Учреждение | Ресурс (2021+) | Что подтверждает для этой темы | Ссылка |
|-----------|----------------|--------------------------------|--------|
| BIS | Paper 156 (2024) — Crypto, DeFi | Bitcoin в контексте криптоэкосистемы и финансовой стабильности | [www.bis.org/publ/bppdf/bispap156.pdf](https://www.bis.org/publ/bppdf/bispap156.pdf) |
| ВШЭ | Dobrynskaya & Dubrovskiy — BRP 86/FE/2022 | Bitcoin как актив: факторы риска, корреляция с акциями | [wp.hse.ru/fe/BRP/86/2022](https://wp.hse.ru/fe/BRP/86/2022) |
| BIS | Working Paper 1146 (2023) | Сравнение Bitcoin со stablecoins: ликвидность и риски | [www.bis.org/publ/work1146.pdf](https://www.bis.org/publ/work1146.pdf) |
| BIS | Paper 159 (2024) — CBDC survey | Место Bitcoin на фоне цифровых валют ЦБ | [www.bis.org/publ/bppdf/bispap159.htm](https://www.bis.org/publ/bppdf/bispap159.htm) |

---

## В автоматической системе

### BTC как primary pair

**BTCUSDT** — default pair проекта: highest liquidity, tightest spread на Binance spot.

```yaml
# crypto_pairs.yaml
primary: BTCUSDT
secondary: ETHUSDT
timeframes:
  signal: 4h
  trend_filter: 1d
```

### Indicators pipeline

```
WebSocket kline closed (4h BTCUSDT)
  → RSI(14), MACD(12,26,9), EMA200
  → btc_dominance (CoinGecko HTTP daily)
  → halving_context from btc_halving.yaml (days_since_last)
  → bundle → Ollama validator
```

### btc_halving.yaml (Obsidian)

```yaml
halvings:
  - date: "2024-04-20"
    block: 840000
    reward_btc: 3.125
    source: "https://academy.binance.com/en/articles/bitcoin-halving"
next_halving_estimate_blocks: 210000  # protocol constant
note: "Estimate date requires live block height — query API, do not hardcode date"
```

### LLM prompt context

```
Asset: BTCUSDT
Timeframe: 4h
Supply cap: 21M (protocol)
Last halving: 2024-04 (public record)
Regime: {{trend_filter}}  # above/below EMA200
Macro: SPX_1d={{spx_1d}}%, risk_on={{risk_on}}
Constraints: max_risk 1% equity, SL required
Output JSON only: {action, confidence, reason}
```

### Dominance filter (Code)

```javascript
const dom = parseFloat($json.btc_dominance);
const domChange7d = parseFloat($json.btc_dominance_change_7d);
const altcoinLongOk = domChange7d <= 0 || dom < 55; // example threshold from config
return [{ json: { altcoinLongOk, dom } }];
```

### On-chain (optional, not HFT)

Weekly job: mempool fees median, active addresses (Glassnode/CryptoQuant if licensed) → Obsidian macro note. **Не** для sub-minute trading.

### Risk

- BTC gap moves на news (ETF flows, macro) — widen stops or reduce size ([[Stop_loss_take_profit]]).
- **Never** auto-withdraw BTC to external wallet without human MFA step.

---

## Связанные темы

- [[Crypto_basics]]
- [[Crypto_indicators]]
- [[Crypto_exchanges]]
- [[Binance_API]]
- [[Global_indices]]
- [[Crypto_flow_design]]

---

## Энергопотребление и ESG (контекст)

Bitcoin **Proof-of-Work** потребляет электроэнергию для mining — публично обсуждаемый topic в regulatory hearings. Это **не** price predictor; для macro notes можно ссылаться на Cambridge Bitcoin Electricity Consumption Index (CBECI) как independent estimate — verify current URL before automation.

Ethereum post-Merge использует **Proof-of-Stake** — другой energy profile.

---

## Hard forks и сетевые изменения

**Hard fork** — изменение protocol rules; может создать **новую chain** (Bitcoin Cash и др.). Holders на fork date могут получить новые coins — tax и custody complexity.

Automation: торгует только **canonical** pair на Binance listing (BTCUSDT); forks — manual process.

---

### Node operation (optional advanced)

Running Bitcoin Core full node даёт self-verified chain data — **не** required for CEX trading. Useful for on-chain analytics without third-party trust.

Resource requirements документированы на [bitcoin.org](https://bitcoin.org/en/full-node) — significant disk/bandwidth.

---

## Supply schedule (conceptual)

Block subsidy halving каждые 210 000 blocks → asymptotic approach to 21M cap. **Circulating supply** live metric — query mempool.space API для automation macro notes, не hardcode in wiki.

---

## Практический чеклист BTC investor

1. Прочитать [whitepaper](https://bitcoin.org/bitcoin.pdf) (минимум abstract + section 1–5).
2. Verify halving history на [Binance Academy Halving](https://academy.binance.com/en/articles/bitcoin-halving).
3. Настроить CoinGecko/CoinMetrics **только** для dominance macro — не для execution.
4. Paper trade BTCUSDT 4h strategy 30 days.
5. Document max drawdown tolerance **до** live.

---

## Расширенный FAQ

### Сколько confirmations безопасно?

Зависит от суммы и policy. Exchanges publish own thresholds — не универсальное число в wiki.

### Bitcoin vs «digital gold» narrative?

Marketing metaphor; SEC treats crypto as **speculative investment** with volatility ([Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)).

### Taproot / технические апgrades?

Protocol upgrades меняют capabilities; trading automation на CEX **не** требует node operation.

---

## Упражнение

После 4th halving (2024) block reward = 3,125 BTC. Сколько BTC theoretically mined per day при ~144 blocks/day? (≈ 450 BTC/day — illustrative; verify with live block count API.)

---

## Что изучить дальше

1. [[Crypto_indicators]] — RSI/MACD на BTCUSDT.
2. [[Crypto_exchanges]] — API и testnet.
3. [[Stop_loss_take_profit]] — OCO на Binance.
4. [[Position_sizing]] — 1% risk на volatile BTC.
