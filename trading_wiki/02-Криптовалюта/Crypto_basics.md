---
title: Основы криптовалют
tags: [криптовалюта, блокчейн, криптоактив, новичок]
sources:
  - https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities
  - https://www.ecb.europa.eu/paym/digital_euro/html/index.en.html
  - https://www.cbr.ru/finmarkets/supervision/supervision_pif/
  - https://academy.binance.com/en/articles/what-is-bitcoin
  - https://www.fatf-gafi.org/en/topics/virtual-assets.html
updated: 2026-07-05
level: beginner
---

# Основы криптовалют

> **Криптоактив** — цифровое представление ценности или прав, использующее **криптографию** и часто **распределённый реестр** (DLT, blockchain). **Криптовалюта** — подмножество криптоактивов, используемых как средство обмена и/или спекулятивный актив. Регуляторы предупреждают о **высоких рисках** и волатильности.

---

## Для новичка

**Блокчейн** — тип распределённого реестра, где транзакции группируются в **блоки**, связанные криптографически. Участники сети (ноды) проверяют правила консенсуса; центральный банк как единственный эмитент **не** требуется для публичных сетей вроде Bitcoin.

**Bitcoin (BTC)** — первая широко известная децентрализованная криптовалюта (whitepaper 2008, запуск сети 2009). Алгоритм ограничивает общую эмиссию **~21 млн BTC** — см. [[Bitcoin_overview]].

**Важно:** криптоактивы **не** застрахованы FDIC/SIPC как банковские депозиты в США ([Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)). Потеря ключей или взлом биржи может быть **необратимой**.

---

## Подтверждённые факты

| # | Факт | Источник |
|---|------|----------|
| 1 | SEC / Investor.gov: crypto investments могут быть **extremely volatile**; fraud и scams — significant risk. | [Investor.gov: Cautionary Tale](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities) |
| 2 | ECB различает **central bank digital currency (CBDC)** и **private crypto-assets**; цифровой евро — отдельный проект CBDC, не Bitcoin. | [ECB: Digital euro](https://www.ecb.europa.eu/paym/digital_euro/html/index.en.html) |
| 3 | **FATF** рекомендует странам регулировать **Virtual Asset Service Providers (VASP)** — включая биржи — по AML/CFT. | [FATF: Virtual Assets](https://www.fatf-gafi.org/en/topics/virtual-assets.html) |
| 4 | Bitcoin whitepaper описывает **peer-to-peer electronic cash** без financial institution. | [Bitcoin whitepaper (PDF)](https://bitcoin.org/bitcoin.pdf) |
| 5 | На **CEX** (centralized exchange) пользователь часто передаёт **custody** активов бирже — counterparty risk. | [Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities) |
| 6 | **DEX** исполняет сделки через **smart contracts**; пользователь держит ключи в своём wallet (self-custody), но риски контрактов и ошибок пользователя выше. | Общепринятая индustry taxonomy; см. [[Crypto_exchanges]] |
| 7 | Binance Academy определяет Bitcoin как **decentralized digital currency** на blockchain. | [Binance Academy: What is Bitcoin](https://academy.binance.com/en/articles/what-is-bitcoin) |

---

## Типы криптоактивов (упрощённая классификация)

| Тип | Описание | Примеры (иллюстрация) |
|-----|----------|------------------------|
| **Криптовалюта (coin)** | Native unit публичной blockchain | BTC, ETH (native gas) |
| **Token** | Актив на базе smart contract platform | ERC-20 tokens на Ethereum |
| **Stablecoin** | Заявленная привязка к фиату/активу | USDT, USDC (проверять резервы и issuer) |
| **NFT** | Уникальный token (non-fungible) | Не фокус trading wiki |

Регуляторы (SEC и др.) спорят о классификации отдельных token как **securities** — статус зависит от фактов и юрисдикции. Не предполагайте «все token = валюта».

---

## Блокчейн и консенсус — базовые понятия

### Блок и цепочка

Транзакции упаковываются в блок. Каждый блок содержит hash предыдущего — изменение истории требует пересчёта цепочки, что экономически затруднено в крупных PoW-сетях.

### Proof-of-Work (Bitcoin)

Майнеры конкурируют за право добавить блок, решая cryptographic puzzle. **Energy consumption** — известный trade-off; детали — [[Bitcoin_overview]].

### Proof-of-Stake (Ethereum после Merge)

Валидаторы блокируют stake вместо mining hash power. Другие параметры риска (slashing, concentration).

### Wallet vs «монеты на счёте»

**Wallet** хранит **private keys**, подписывающие транзакции. «Монеты» — записи в ledger. Потеря seed phrase = потеря доступа **без** службы поддержки «вернуть пароль».

---

## CEX vs DEX

| Аспект | CEX | DEX |
|--------|-----|-----|
| Custody | Биржа (обычно) | Self-custody |
| KYC | Часто обязателен | Часто нет / partial |
| Ликвидность | Высокая на major pairs | Зависит от pool |
| API для bots | REST/WebSocket | RPC + contract calls |
| Регуляция | VASP licensing | Сложнее, jurisdiction-dependent |

Для **автоматической системы** проекта базовый путь — **CEX API** (Binance) с жёсткими guardrails — см. [[Crypto_exchanges]], [[Binance_API]].

---

## Stablecoins

Stablecoin заявляет привязку к USD или другому активу. Риски:

- **Depeg** — цена на бирже отклоняется от $1;
- **Reserve transparency** — зависит от issuer;
- **Regulatory action** — статус меняется.

Для учёта PnL в automation часто используют **USDT/USDC** как quote currency, понимая counterparty риск issuer.

---

## Ключевые термины

| Термин | Определение |
|--------|-------------|
| **Private key** | Секрет для подписи; не передавать никому |
| **Public address** | Адрес для получения |
| **Gas fee** | Комиссия сети (Ethereum и др.) |
| **Cold / hot wallet** | Offline vs online storage |
| **Market cap** | Price × circulating supply (осторожно с methodology) |
| **Halving** | Снижение block reward Bitcoin ~каждые 4 года |

---

## Примеры

### Пример 1: Перевод BTC on-chain

Alice отправляет 0,01 BTC Bob. Транзакция broadcast в сеть → попадает в mempool → включается в блок → после **confirmations** Bob может считать получение надёжным (число confirmations — policy биржи/wallet).

### Пример 2: Покупка на CEX

User пополняет USDT → market buy BTCUSDT → BTC на **spot balance** биржи. Вывод on-chain — отдельная операция с fee и AML checks.

### Пример 3: Ошибка новичка

User отправляет ERC-20 token на **Bitcoin address** — средства могут быть **безвозвратно** потеряны. Automation должна **whitelist** сети и адресов.

---

## Частые ошибки новичков

1. **Хранить seed в облаке / чате** — компрометация = кража.
2. **Путать network** (ERC-20 vs TRC-20 USDT) — wrong chain deposits.
3. **Считать stablecoin = cash** — depeg и issuer risk.
4. **Leverage без понимания liquidation** — см. [[Position_sizing]].
5. **FOMO по meme tokens** — fraud risk ([Investor.gov](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)).
6. **API keys с withdraw permission** — для bots только trade, never withdraw.

---

## FAQ

### Криптовалюта = анонимные деньги?

Публичные blockchains **прозрачны**; биржи с KYC связывают identity. FATF требует Travel Rule для VASP. «Полная анонимность» — миф для regulated CEX.

### Нужен ли wallet для торговли через Binance API?

Средства на **exchange balance** — custody у биржи. Wallet нужен для self-custody / on-chain.

### Легальны ли криптовалюты в РФ?

Регulatory framework меняется; см. [[Crypto_regulation_RU]] (отдельная wiki). Не используйте wiki как legal advice.

### Чем crypto-flow отличается от MOEX-flow?

24/7, нет T+1, другие API, выше волатильность, другие tax rules.

---

## Проверенные источники

1. **[Investor.gov: Cautionary Tale — Crypto Asset Securities](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities)**
2. **[ECB: Digital euro (CBDC context)](https://www.ecb.europa.eu/paym/digital_euro/html/index.en.html)**
3. **[FATF: Virtual Assets](https://www.fatf-gafi.org/en/topics/virtual-assets.html)**
4. **[Bitcoin whitepaper](https://bitcoin.org/bitcoin.pdf)**
5. **[Binance Academy: What is Bitcoin](https://academy.binance.com/en/articles/what-is-bitcoin)**

---

## В автоматической системе

### Архитектура crypto-flow (24/7)

```
Binance WebSocket (klines BTCUSDT, ETHUSDT)
  → n8n buffer / dedupe
  → Code + Python: indicators (RSI, MACD)
  → Merge macro-context from global flow (SPX, risk_on)
  → Ollama: validate signal JSON (approve/reject)
  → Risk node: position size, daily loss limit
  → Binance REST: place order + SL/TP (OCO where supported)
  → Obsidian: trade log + daily PnL
```

### Guardrails (обязательные)

```yaml
# Obsidian: crypto_config.yaml
allowed_pairs:
  - BTCUSDT
  - ETHUSDT
max_daily_loss_pct: 2.0
max_open_positions: 3
api_permissions:
  enable_spot: true
  enable_withdraw: false   # NEVER true for automation
environment: testnet       # testnet.binance.vision until validated
```

### Credentials

- API keys **только** в n8n Credentials;
- IP whitelist на Binance;
- Rotate keys каждые 90 дней (Schedule reminder);
- Separate keys testnet vs production (`BINANCE_ENV`).

### LLM boundaries

| LLM делает | Code делает |
|------------|-------------|
| Interpret news summary vs rules | Calculate RSI, size, prices |
| approve/reject with reason string | POST orders |
| Flag «unusual volatility» | Circuit breaker halt |

Правило **G1** [[LLM_rules_and_guardrails]]: LLM output **не** исполняет ордер без JSON schema validation.

### Obsidian trade log

```yaml
trade_id: crypto-2026-07-05-001
pair: BTCUSDT
side: BUY
entry: 60000
stop: 58200
sources: [binance-api, academy.binance.com-rsi]
testnet: true
```

### Testnet → production checklist

1. 30+ days paper with same code path;
2. Max drawdown within limits;
3. SL/TP fill tested;
4. Manual sign-off in Obsidian `go_live_checklist.md`.

---

## Связанные темы

- [[Bitcoin_overview]]
- [[Crypto_exchanges]]
- [[Crypto_indicators]]
- [[Binance_API]]
- [[Crypto_flow_design]]
- [[Crypto_regulation_RU]]
- [[LLM_rules_and_guardrails]]

---

## Регуляторный ландшафт (обзор, не legal advice)

| Юрисдикция | Орган | Фокус |
|------------|-------|-------|
| США | SEC / CFTC | Securities vs commodities, investor protection |
| EU | ECB, ESMA | MiCA framework evolving |
| РФ | ЦБ РФ | См. [[Crypto_regulation_RU]] |
| Global | FATF | AML для VASP |

Investor.gov: многие crypto **investment schemes** — fraud vectors. Automation **не** торгует новые token без listing age + liquidity rules.

---

## Smart contracts и риски

**Smart contract** — код on-chain. Риски:

- **Bug** в contract → потеря funds (historical DeFi exploits).
- **Upgradeable proxy** — admin key risk.
- **Phishing** — fake contract address.

DEX automation требует **verified contract addresses** в whitelist — не copy from Telegram.

---

### Wallet types matrix

| Wallet | Custody | Bot compatibility |
|--------|---------|-------------------|
| Exchange custodial | CEX | API trading |
| Hot software | Self | Manual / DEX |
| Hardware | Self cold | Long-term hold |
| Multisig | Shared | Institutional |

Project automation: **exchange custodial** for execution + optional cold for savings **outside** bot balance.

---

## Layer-2 overview (Lightning)

**Lightning Network** — payment channels поверх Bitcoin. Не используется в default spot bot; relevant для merchants, not 4h swing strategy.

---

## Практический чеклист перед первой сделкой

1. Прочитать [Investor.gov crypto caution](https://www.investor.gov/additional-resources/spotlight/directors-take/cautionary-tale-crypto-asset-securities).
2. Enable 2FA на бирже.
3. Создать API key **без withdraw**.
4. Пройти testnet 30+ дней ([[Crypto_exchanges]]).
5. Записать seed offline — **never** digital photo.
6. Определить max daily loss в `crypto_config.yaml`.

---

## Расширенный FAQ

### CBDC vs Bitcoin?

ECB **digital euro** — liability central bank, not Bitcoin ([ECB digital euro](https://www.ecb.europa.eu/paym/digital_euro/html/index.en.html)).

### NFT для trading wiki?

Out of scope active strategies — illiquid, unique pricing.

### Staking rewards?

Tax and protocol risk; отдельная тема; default automation — spot only.

---

## Упражнение

Опишите разницу custody при хранении BTC на CEX vs hardware wallet. Какой вариант использует `crypto-flow` project и почему? (CEX для API execution; withdraw disabled.)

---

## Что изучить дальше

1. [[Bitcoin_overview]] — PoW, halving, supply cap.
2. [[Crypto_exchanges]] — CEX/DEX, API, security.
3. [[Crypto_indicators]] — TA + on-chain overview.
4. [[Stop_loss_take_profit]] — выходы на Binance API.
