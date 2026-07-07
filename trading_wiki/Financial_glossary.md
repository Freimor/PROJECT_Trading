---
title: Полный финансовый глоссарий
tags: [глоссарий, справочник, moc, термины]
sources:
  - https://www.investor.gov/additional-resources/general-resources/glossary
  - https://www.finra.org/investors/investing/investing-basics
  - https://www.moex.com/a6231
  - https://www.cbr.ru/finmarkets/digital/
updated: 2026-07-06
level: reference
style: informational
---

# Полный финансовый глоссарий

> Справочник **всех финансовых и биржевых терминов** Trading Wiki: от акции и облигации до RSI, FIGI и ЦФА. Краткое определение + ссылка на статью и первоисточник.

Краткая версия для старта: [[Glossary]] в разделе «Основы».

---

## Главное

- Ищите термин через **Ctrl+F** или поиск Obsidian (`Ctrl+O`).
- Русские и английские названия в одной таблице; в API и на биржах чаще — английский.
- Колонка **«Подробнее»** ведёт в статью wiki; **«Источник»** — SEC, FINRA, MOEX, ЦБ и др.
- Не нужно учить всё сразу — возвращайтесь по мере чтения курса.

---

## Навигация по разделам

| Раздел | Термины |
|--------|---------|
| [А–В](#а–в) | Акция, аллокация, ask, API, beta… |
| [Г–Д](#г–д) | Гэп, диверсификация, дивиденд, drawdown… |
| [Е–З](#е–з) | ETF, equity, эмитент, free-float… |
| [И–К](#и–к) | Индекс, IPO, купон, leverage, limit… |
| [Л–О](#л–о) | Ликвидность, лот, MACD, MOEX, номинал… |
| [П–Р](#п–р) | Портфель, P/E, RSI, R:R, stop-loss… |
| [С–Т](#с–т) | Спред, slippage, тикер, take-profit… |
| [У–Я](#у–я) | Volatility, VWAP, yield, ЦФА, ОФЗ… |
| [Криптовалюта](#криптовалюта) | Blockchain, CEX, gas, halving… |
| [Технический анализ](#технический-анализ) | Свечи, тренд, поддержка, ATR… |
| [Российский рынок](#российский-рынок) | БПИФ, ОФЗ, ИИС, T+1, FIGI… |
| [Психология и риск](#психология-и-риск) | FOMO, loss aversion, position sizing… |
| [Английский A–Z](#английский-индекс-a–z) | Быстрый поиск латиницей |

---

## А–В

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **Акция (stock, share)** | Доля владения в компании; право на часть прибыли и обычно голос на собрании | [[Finance_basics]] | [Investor.gov: Stock](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock) |
| **Аллокация активов (asset allocation)** | Распределение портфеля между акциями, облигациями и «наличными» | [[Finance_basics]] | [Investor.gov](https://www.investor.gov/introduction-investing) |
| **AMH (Adaptive Markets Hypothesis)** | Рынки адаптивны: рациональность и ошибки сосуществуют; риск-политика должна меняться | [[Trader_psychology]] | [MIT 15.481X](https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/) |
| **API** | Программный интерфейс для автоматического доступа к котировкам и торгам | [[Binance_API]] | — |
| **Ask (offer)** | Минимальная цена, по которой продавец готов продать прямо сейчас | [[Order_types]] | [FINRA: Order Types](https://www.finra.org/investors/investing/investment-products/stocks/order-types) |
| **ATR (Average True Range)** | Индикатор волатильности; средний диапазон свечи за N периодов | [[Key_indicators_RSI_MACD]] | — |
| **Базисный пункт (bp, bps)** | 0,01 процентного пункта; 100 bp = 1% | [[Bonds_basics]] | — |
| **Бенчмарк (benchmark)** | Эталон для сравнения доходности (IMOEX, S&P 500) | [[IMOEX_RTS]] | [MOEX](https://www.moex.com/a6231) |
| **Beta (β)** | Чувствительность актива к рынку: β=1 — как индекс, β>1 — волатильнее | [[Key_indicators_RSI_MACD]] | — |
| **Bid** | Максимальная цена, по которой покупатель готов купить | [[Order_types]] | [FINRA](https://www.finra.org/investors/investing/investment-products/stocks/order-types) |
| **Bid-ask spread (спред)** | Ask − bid; чем уже, тем ликвиднее инструмент | [[What_is_trading]] | — |
| **Блокчейн (blockchain)** | Распределённый реестр транзакций, защищённый криптографией | [[Crypto_basics]] | [ECB](https://www.ecb.europa.eu/ecb/educational/explainers/tell-me/html/what_is_a_crypto_asset.en.html) |
| **БПИФ** | Биржевой паевой инвестиционный фонд; торгуется на MOEX как одна бумага | [[ETFs_and_funds]] | [ЦБ: ПИФы](https://www.cbr.ru/finmarkets/supervision/supervision_pif/) |
| **Брокер (broker)** | Лицензированный посредник: подаёт ваши заявки на биржу | [[What_is_trading]] | [FINRA](https://www.finra.org/investors/investing/investing-basics) |
| **Бычий рынок (bull market)** | Длительный рост цен | [[What_is_trading]] | — |
| **Волатильность (volatility)** | Насколько сильно и быстро меняется цена | [[Finance_basics]] | [FINRA: Volatility](https://www.finra.org/investors/investing/investing-basics/volatility) |

---

## Г–Д

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **Гэп (gap)** | Разрыв цены между закрытием и открытием без сделок между уровнями | [[Technical_analysis_basics]] | — |
| **Голубые фишки (blue chips)** | Акции крупнейших ликвидных компаний с устойчивой историей | [[Finance_basics]] | [Investor.gov: Stocks](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) |
| **Депозитарий (depository)** | Ведёт учёт прав на ценные бумаги (в РФ — НРД, Регистратор и др.) | [[What_is_trading]] | — |
| **Диверсификация (diversification)** | Распределение вложений между разными активами, чтобы снизить риск одной ошибки | [[Portfolio_diversification]] | [Investor.gov](https://www.investor.gov/introduction-investing) |
| **Дивиденд (dividend)** | Выплата акционерам из прибыли; не гарантирована | [[Finance_basics]] | [Investor.gov: Stocks](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) |
| **Долгосрочный инвестор (buy and hold)** | Держит активы годами, редко торгует | [[What_is_trading]] | [FINRA](https://www.finra.org/investors/investing/investing-basics) |
| **Drawdown (просадка)** | Падение капитала от пика до минимума; max drawdown — худшая историческая | [[Position_sizing]] | — |
| **Day order** | Заявка действует до конца торговой сессии | [[Order_types]] | [SEC Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| **DCA (dollar-cost averaging)** | Регулярные покупки на фиксированную сумму независимо от цены | [[Index_ETF]] | — |
| **DeFi (decentralized finance)** | Финансовые протоколы на блокчейне без традиционного посредника | [[Crypto_basics]] | [BIS Paper 156](https://www.bis.org/publ/bppdf/bispap156.pdf) |
| **Доходность (yield)** | Доход от вложения в %: купон, дивидендная yield, YTM | [[Finance_basics]] | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |

---

## Е–З

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **EMH (Efficient Market Hypothesis)** | Гипотеза: цены отражают всю доступную информацию (упрощённо) | [[Trader_psychology]] | [MIT 15.481X](https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/) |
| **Equity (акции, долевые бумаги)** | Доля владения в компании; противоположность debt | [[Finance_basics]] | [FINRA](https://www.finra.org/investors/investing/investing-basics) |
| **ETF (биржевой фонд)** | Фонд, чьи паи торгуются на бирже; внутри — корзина активов | [[Index_ETF]] | [Investor.gov: ETF](https://www.investor.gov/introduction-investing/investing-basics/investment-products/exchange-traded-funds-etfs) |
| **ETP (exchange-traded product)** | Общий термин: ETF, ETN и похожие биржевые продукты | [[ETFs_and_funds]] | [FINRA](https://www.finra.org/investors/investing/investing-basics) |
| **Эмитент (issuer)** | Тот, кто выпустил бумагу: компания, государство, фонд | [[What_is_trading]] | — |
| **Ex-dividend date** | Дата, после которой покупатель не получит объявленный дивиденд | [[MOEX_stocks]] | — |
| **Execution (исполнение)** | Факт заключения сделки по заявке | [[Order_types]] | — |
| **Expense ratio (TER)** | Годовая комиссия фонда за управление в % от активов | [[Index_ETF]] | [Investor.gov: ETFs](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-2) |
| **Face value (номинал облигации)** | Сумма, которую эмитент обязан вернуть при погашении | [[Bonds_basics]] | [Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |
| **FIGI** | Financial Instrument Global Identifier — ID инструмента в API брокеров | [[Tinkoff_Invest_API]] | [T-Invest API](https://tinkoff.github.io/investAPI/) |
| **Free-float** | Доля акций в свободном обращении; учитывается в индексах MOEX | [[IMOEX_RTS]] | [MOEX](https://www.moex.com/a6231) |
| **Futures (фьючерс)** | Контракт на покупку/продажу актива в будущем по оговорённой цене | [[Glossary]] | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |

---

## И–К

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **ИИС** | Индивидуальный инвестиционный счёт; особый налоговый режим в РФ (тип А или Б) | [[Russia_tax_basics]] | [ФНС](https://www.nalog.gov.ru/rn77/fl/interest/taxation/investment/) |
| **Индекс (index)** | Показатель «средней» динамики корзины бумаг (IMOEX, S&P 500) | [[IMOEX_RTS]] | [MOEX](https://www.moex.com/a6231) |
| **Инфляция (inflation)** | Рост общего уровня цен; съедает покупательную способность cash | [[Finance_basics]] | — |
| **IPO (Initial Public Offering)** | Первое публичное размещение акций | [[What_is_trading]] | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |
| **IOC (Immediate or Cancel)** | Исполнить немедленно доступный объём, остаток отменить | [[Order_types]] | — |
| **Капитализация (market cap)** | Цена акции × число акций в обращении | [[Finance_basics]] | — |
| **Ключевая ставка** | Ставка ЦБ РФ; влияет на доходность облигаций и кредиты | [[Bonds_basics]] | [cbr.ru](https://www.cbr.ru/) |
| **Корреляция (correlation)** | Насколько синхронно движутся два актива (−1…+1) | [[Portfolio_diversification]] | — |
| **Котировка (quote)** | Текущие цены bid/ask/last по инструменту | [[Order_types]] | — |
| **Купон (coupon)** | Процентная выплата по облигации по графику | [[Bonds_basics]] | [Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |
| **CVaR (Conditional VaR)** | Ожидаемый убыток в худших сценариях за порогом VaR | [[Portfolio_diversification]] | — |
| **Leverage (плечо, margin)** | Торговля с заёмными средствами; усиливает прибыль и убыток | [[Position_sizing]] | [FINRA: Margin](https://www.finra.org/investors/investing/investment-products/stocks/margin-accounts) |
| **Limit order (лимитная заявка)** | Купить/продать только по указанной цене или лучше | [[Order_types]] | [SEC: Limit](https://www.sec.gov/answers/limit.htm) |
| **Liquidity (ликвидность)** | Лёгкость купить или продать без сильного сдвига цены | [[Finance_basics]] | — |
| **Long (лонг)** | Позиция на рост: купил — ждёшь роста | [[What_is_trading]] | — |
| **Lot (лот)** | Минимальный объём сделки на бирже (для SBER часто 1 акция) | [[MOEX_stocks]] | [MOEX](https://www.moex.com/) |

---

## Л–О

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **Last (последняя цена)** | Цена последней сделки; не гарантирует исполнение вашей заявки | [[Order_types]] | [SEC Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| **Limit price** | Цена в лимитной или stop-limit заявке | [[Order_types]] | [SEC](https://www.sec.gov/answers/limit.htm) |
| **MACD** | Индикатор: разница EMA(12) и EMA(26), сигнальная линия и гистограмма | [[Key_indicators_RSI_MACD]] | [Binance Academy](https://academy.binance.com/en/articles/what-is-the-macd-indicator) |
| **Margin call** | Требование брокера внести деньги при нехватке обеспечения по марже | [[Position_sizing]] | [FINRA: Margin](https://www.finra.org/investors/investing/investment-products/stocks/margin-accounts) |
| **Market cap weighted** | Вес бумаги в индексе пропорционален капитализации | [[IMOEX_RTS]] | [MOEX](https://www.moex.com/a6231) |
| **Market order (рыночная заявка)** | Исполнение по лучшей доступной цене сейчас | [[Order_types]] | [SEC Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| **Медвежий рынок (bear market)** | Длительное падение цен (часто ≥20% от пика) | [[What_is_trading]] | — |
| **MOEX (Московская биржа)** | Главная площадка России для акций, облигаций, деривативов | [[MOEX_stocks]] | [moex.com](https://www.moex.com/) |
| **Mutual fund (ПИФ)** | Паевой фонд; покупка/погашение через УК, не на бирже (кроме БПИФ) | [[ETFs_and_funds]] | [ЦБ: ПИФы](https://www.cbr.ru/finmarkets/supervision/supervision_pif/) |
| **NAV (стоимость чистых активов, СЧА)** | Стоимость активов фонда минус обязательства; цена пая ПИФа | [[ETFs_and_funds]] | [Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-2) |
| **НКД (ACI)** | Накопленный купонный доход по облигации на дату сделки | [[Bonds_basics]] | [MOEX ISS](https://iss.moex.com/iss/reference/) |
| **Номинал** | См. face value | [[Bonds_basics]] | — |
| **OCO (One-Cancels-Other)** | Связка заявок: исполнение одной отменяет другую | [[Stop_loss_take_profit]] | [Binance API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api) |
| **Облигация (bond)** | Долговая бумага: вы одолжили деньги эмитенту под проценты | [[Bonds_basics]] | [Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |
| **ОФЗ** | Облигация федерального займа; долг государства РФ | [[Bonds_basics]] | [MOEX](https://www.moex.com/) |
| **Order book (стакан)** | Список заявок bid/ask по уровням цен | [[Order_types]] | — |

---

## П–Р

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **P/E (Price/Earnings)** | Цена акции / прибыль на акцию; оценка «дороговизны» | [[Finance_basics]] | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |
| **Paper trading** | Торговля на демо/testnet без реальных денег | [[n8n_architecture_overview]] | — |
| **Portfolio (портфель)** | Все ваши активы вместе | [[Portfolio_diversification]] | — |
| **Position (позиция)** | Открытое владение активом (long) или обязательство (short) | [[What_is_trading]] | — |
| **Position sizing** | Выбор размера позиции с учётом риска на сделку | [[Position_sizing]] | — |
| **Preferred stock (привилегированная акция)** | Приоритет дивидендов; обычно без голоса | [[Finance_basics]] | [Investor.gov: Stocks](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) |
| **Premium / discount to NAV** | ETF торгуется выше/ниже расчётной стоимости активов | [[Index_ETF]] | [SEC Bulletin: ETFs](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/characteristics-mutual-funds-exchange-traded-funds) |
| **Primary market (первичный рынок)** | IPO, SPO — первое размещение бумаг | [[What_is_trading]] | — |
| **Просадка** | См. drawdown | [[Position_sizing]] | — |
| **RAG** | Retrieval-Augmented Generation: LLM + поиск по wiki | [[LLM_prompts_trading]] | — |
| **Rebalancing (ребалансировка)** | Возврат портфеля к целевым долям активов | [[Portfolio_diversification]] | [Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |
| **Resistance (сопротивление)** | Уровень, где продавцы historically сильнее | [[Technical_analysis_basics]] | — |
| **Risk/Reward (R:R)** | Соотношение потенциальной прибыли к риску на сделку | [[Stop_loss_take_profit]] | — |
| **ROI** | Return on Investment — доходность вложений в % | — | — |
| **RSI** | Relative Strength Index; осциллятор 0–100, перекупленность/перепроданность | [[Key_indicators_RSI_MACD]] | [Binance Academy](https://academy.binance.com/en/articles/what-is-the-rsi-indicator) |
| **RTSI (RTS Index)** | Индекс MOEX в долларах США | [[IMOEX_RTS]] | [MOEX](https://www.moex.com/a6231) |

---

## С–Т

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **SECID / Ticker (тикер)** | Биржевой код: SBER, GAZP, BTCUSDT | [[MOEX_stocks]] | — |
| **Secondary market (вторичный рынок)** | Торговля уже выпущенными бумагами между инвесторами | [[What_is_trading]] | — |
| **SEC (Секомиссия США)** | Регулятор рынка ценных бумаг США; сайт Investor.gov | [[Finance_basics]] | [investor.gov](https://www.investor.gov/) |
| **Settlement (расчёты)** | Переход прав и денег после сделки; на MOEX акции T+1 | [[MOEX_stocks]] | [MOEX](https://www.moex.com/) |
| **Sharpe ratio** | Доходность с поправкой на риск (volatility) | [[Portfolio_diversification]] | — |
| **Short (шорт)** | Позиция на падение: продал заёмное, купишь дешевле | [[What_is_trading]] | — |
| **Slippage (проскальзывание)** | Исполнение хуже ожидаемой цены | [[Order_types]] | [Investor.gov: Stop](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| **Smart contract** | Код на блокчейне, исполняющий условия сделки (DeFi) | [[Crypto_basics]] | [BIS Paper 156](https://www.bis.org/publ/bppdf/bispap156.pdf) |
| **Spread** | См. bid-ask spread | [[What_is_trading]] | — |
| **Stablecoin (стейблкоин)** | Криптоактив с заявленной привязкой к фиату (USDT, USDC) | [[Crypto_basics]] | [BIS WP 1146](https://www.bis.org/publ/work1146.pdf) |
| **Stop-loss (стоп-лосс)** | Заявка на выход при неблагоприятной цене | [[Stop_loss_take_profit]] | [Investor.gov: Stop](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| **Stop-limit** | При stop price выставляется limit, не market | [[Stop_loss_take_profit]] | [SEC Bulletin 14](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-14) |
| **Stop price** | Цена активации stop order | [[Order_types]] | [Investor.gov: Stop](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| **Support (поддержка)** | Уровень, где покупатели historically сильнее | [[Technical_analysis_basics]] | — |
| **Swing trading** | Удержание позиции от дней до недель | [[What_is_trading]] | — |

---

## У–Я

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **VaR (Value at Risk)** | Оценка максимального убытка за период с заданной вероятностью | [[Portfolio_diversification]] | — |
| **Volatility** | См. волатильность | [[Finance_basics]] | — |
| **Volume (объём)** | Сколько бумаг/контрактов сменило владельца за период | [[Technical_analysis_basics]] | — |
| **VWAP** | Средневзвешенная по объёму цена за период | [[Technical_analysis_basics]] | — |
| **Wash sale** | Продажа в убыток и быстрая повторная покупка (налоговое правило США) | — | [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) |
| **Yield to maturity (YTM)** | Полная доходность облигации при удержании до погашения | [[Bonds_basics]] | [Investor.gov: Bonds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |
| **ЦФА** | Цифровые финансовые активы; права на блокчейне по закону РФ | [[Crypto_regulation_RU]] | [259-ФЗ](https://www.consultant.ru/document/cons_doc_LAW_487488/) |
| **ЦБ РФ** | Банк России; регулятор финрынка и эмитент ключевой ставки | [[Crypto_regulation_RU]] | [cbr.ru](https://www.cbr.ru/) |

---

## Криптовалюта

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **51% attack** | Контроль большинства мощности сети для переписывания истории | [[Bitcoin_overview]] | [bitcoin.org](https://bitcoin.org/bitcoin.pdf) |
| **Address (адрес)** | Строка для получения криптовалюты в сети | [[Crypto_basics]] | — |
| **Altcoin** | Любая криптовалюта кроме Bitcoin | [[Crypto_basics]] | — |
| **Bitcoin (BTC)** | Первая децентрализованная криптовалюта; лимит ~21 млн | [[Bitcoin_overview]] | [Whitepaper](https://bitcoin.org/bitcoin.pdf) |
| **Block reward** | Награда майнеру за добавление блока | [[Bitcoin_overview]] | — |
| **CEX** | Централизованная биржа (Binance, Bybit); custody у биржи | [[Crypto_exchanges]] | [Investor.gov: Crypto](https://www.investor.gov/introduction-investing/crypto-assets) |
| **Circulating supply** | Монеты в обращении; для расчёта market cap | [[Crypto_basics]] | — |
| **Cold wallet** | Кошелёк offline; ключи не в сети | [[Crypto_basics]] | — |
| **DEX** | Децентрализованная биржа через смарт-контракты | [[Crypto_exchanges]] | [BIS Paper 156](https://www.bis.org/publ/bppdf/bispap156.pdf) |
| **FUD** | Fear, Uncertainty, Doubt — намеренный негатив для давления на цену | [[Crypto_exchanges]] | — |
| **Gas fee** | Комиссия сети за транзакцию (Ethereum и др.) | [[Crypto_basics]] | — |
| **Halving** | Уменьшение награды майнерам Bitcoin ~раз в 4 года | [[Bitcoin_overview]] | — |
| **Hot wallet** | Кошелёк online; удобнее, но выше риск взлома | [[Crypto_basics]] | — |
| **KYC** | Know Your Customer — верификация личности на бирже | [[Crypto_exchanges]] | — |
| **Mining (майнинг)** | Подтверждение транзакций и выпуск новых монет (PoW) | [[Bitcoin_overview]] | — |
| **Private key** | Секрет для подписи; потеря = потеря доступа к средствам | [[Crypto_basics]] | [Investor.gov: Crypto](https://www.investor.gov/introduction-investing/crypto-assets) |
| **Proof of Work (PoW)** | Консенсус через вычисления (Bitcoin) | [[Bitcoin_overview]] | [Whitepaper](https://bitcoin.org/bitcoin.pdf) |
| **Proof of Stake (PoS)** | Консенсус через залог монет (Ethereum после Merge) | [[Crypto_basics]] | — |
| **Token** | Актив на базе смарт-контракта (ERC-20 и др.) | [[Crypto_basics]] | — |
| **Wallet** | Программа/устройство для хранения ключей, не «монет» | [[Crypto_basics]] | — |
| **Web3** | Экосистема dApps на блокчейне | [[Crypto_basics]] | — |

---

## Технический анализ

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **Candlestick (свеча)** | График OHLC за период; тело = open–close | [[Technical_analysis_basics]] | — |
| **Close** | Цена последней сделки периода | [[Technical_analysis_basics]] | — |
| **Death cross** | EMA(50) пересекает EMA(200) сверху вниз | [[Key_indicators_RSI_MACD]] | — |
| **Downtrend** | Серия lower highs и lower lows | [[Technical_analysis_basics]] | — |
| **EMA** | Exponential Moving Average — сглаженная цена с весом последних баров | [[Key_indicators_RSI_MACD]] | — |
| **Golden cross** | EMA(50) пересекает EMA(200) снизу вверх | [[Key_indicators_RSI_MACD]] | — |
| **High / Low** | Максимум / минимум периода | [[Technical_analysis_basics]] | — |
| **OHLCV** | Open, High, Low, Close, Volume — формат свечи | [[Technical_analysis_basics]] | — |
| **Open** | Цена первой сделки периода | [[Technical_analysis_basics]] | — |
| **Overbought / oversold** | Зоны RSI: традиционно >70 / <30 | [[Key_indicators_RSI_MACD]] | [Binance Academy](https://academy.binance.com/en/articles/what-is-the-rsi-indicator) |
| **Range (боковик)** | Цена между support и resistance | [[Technical_analysis_basics]] | — |
| **SMA** | Simple Moving Average — простое среднее цен | [[Key_indicators_RSI_MACD]] | — |
| **Technical analysis (ТА)** | Анализ графиков и объёмов; не гарантирует будущее | [[Technical_analysis_basics]] | [Investopedia](https://www.investopedia.com/terms/t/technicalanalysis.asp) |
| **Timeframe (ТФ)** | Интервал свечи: 1m, 1h, 4h, 1D | [[Technical_analysis_basics]] | — |
| **Uptrend** | Серия higher highs и higher lows | [[Technical_analysis_basics]] | — |

---

## Российский рынок

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **БПИФ** | См. выше | [[ETFs_and_funds]] | [ЦБ](https://www.cbr.ru/finmarkets/supervision/supervision_pif/) |
| **Голубые фишки MOEX** | Крупнейшие ликвидные эмитенты (MOEXBC — 15 бумаг) | [[IMOEX_RTS]] | [MOEX](https://www.moex.com/a6231) |
| **IMOEX** | Главный индекс акций MOEX в рублях | [[IMOEX_RTS]] | [MOEX](https://www.moex.com/a6231) |
| **ISS (MOEX)** | Бесплатный HTTP API котировок и истории | [[MOEX_ISS_API]] | [iss.moex.com](https://iss.moex.com/iss/reference/) |
| **ISIN** | Международный код ценной бумаги (RU000A0JP7K5 — IMOEX) | [[IMOEX_RTS]] | — |
| **Мосбиржа** | См. MOEX | [[MOEX_stocks]] | — |
| **НДФЛ** | Налог на доходы физлиц; с дивидендов и продажи бумаг в РФ | [[Russia_tax_basics]] | [ФНС](https://www.nalog.gov.ru/rn77/fl/interest/taxation/investment/) |
| **НРД** | Национальный расчётный депозитарий | [[What_is_trading]] | — |
| **ОФЗ** | См. выше | [[Bonds_basics]] | — |
| **ОФЗ-ИН** | ОФЗ с защитой от инфляции | [[Bonds_basics]] | — |
| **ПИФ** | Паевой инвестиционный фонд | [[ETFs_and_funds]] | [ЦБ](https://www.cbr.ru/finmarkets/supervision/supervision_pif/) |
| **СЧА** | См. NAV | [[ETFs_and_funds]] | — |
| **T+1** | Расчёты на следующий рабочий день после сделки | [[MOEX_stocks]] | [MOEX](https://www.moex.com/) |
| **TQBR** | Режим торгов акциями MOEX в ISS API | [[MOEX_ISS_API]] | [ISS](https://iss.moex.com/iss/reference/) |
| **T-Invest API** | API брокера T-Bank для торговли на MOEX | [[Tinkoff_Invest_API]] | [tinkoff.github.io/investAPI](https://tinkoff.github.io/investAPI/) |

---

## Психология и риск

| Термин | Определение | Подробнее | Источник |
|--------|-------------|-----------|----------|
| **Anchoring (якорение)** | Решение привязано к «старой» цене покупки | [[Cognitive_biases]] | [Investopedia](https://www.investopedia.com/terms/a/anchoring-and-adjusting.asp) |
| **Circuit breaker** | Автоматическая остановка торгов при дневном лимите убытка | [[LLM_rules_and_guardrails]] | — |
| **Confirmation bias** | Ищем только аргументы «за» свою позицию | [[Cognitive_biases]] | [CFA: Behavioral](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/behavioral-finance) |
| **Disposition effect** | Рано фиксируем прибыль, долго держим убыток | [[Cognitive_biases]] | — |
| **FOMO** | Fear Of Missing Out — страх упустить рост | [[Trader_psychology]] | [SEC: FOMO](https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/say-no-go-fomo) |
| **Kelly criterion** | Формула оптимальной доли капитала в ставке (продвинутый) | [[Position_sizing]] | — |
| **Loss aversion** | Боль от убытка сильнее радости от равной прибыли | [[Cognitive_biases]] | [Kahneman & Tversky, 1979](https://www.jstor.org/stable/1914185) |
| **Overtrading** | Слишком много сделок без edge | [[Trader_psychology]] | — |
| **Prospect theory** | Теория перспектив Канемана и Тверски | [[Cognitive_biases]] | — |
| **Revenge trading** | Увеличение риска после убытка «отыграться» | [[Trader_psychology]] | — |
| **Risk tolerance** | Сколько просадки вы готовы пережить психологически | [[Finance_basics]] | [Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) |

---

## Индексы (справочник)

| Код | Название | Валюта | Подробнее |
|-----|----------|--------|-----------|
| **IMOEX** | Индекс МосБиржи | RUB | [[IMOEX_RTS]] |
| **RTSI** | RTS Index | USD | [[IMOEX_RTS]] |
| **MOEXBC** | Blue Chip Index | RUB | [[IMOEX_RTS]] |
| **RUBMI** | Broad Market (top-100) | RUB | [MOEX](https://www.moex.com/a6231) |
| **SPX / S&P 500** | 500 крупнейших компаний США | USD | [[Global_indices]] |
| **NDX** | NASDAQ-100 | USD | [[Global_indices]] |
| **DJIA** | Dow Jones 30 | USD | [[Global_indices]] |
| **MSCI World** | Developed markets | Multi | [[Global_indices]] |
| **MSCI EM** | Emerging markets | Multi | [[Global_indices]] |

---

## Типы заявок (сводка)

| Тип | Суть | Риск |
|-----|------|------|
| **Market** | По лучшей цене сейчас | Проскальзывание |
| **Limit** | Только по цене X или лучше | Может не исполниться |
| **Stop-market** | При stop → market | Проскальзывание после stop |
| **Stop-limit** | При stop → limit | Может не исполниться при gap |
| **Trailing stop** | Stop следует за ценой | — |
| **GTC** | Действует до отмены | — |
| **IOC / FOK** | Немедленное частичное/полное исполнение | — |

Подробнее: [[Order_types]], [[Stop_loss_take_profit]].

---

## Английский индекс (A–Z)

Быстрый поиск латиницей → раздел в глоссарии.

| | | | |
|---|---|---|---|
| A: [API](#а–в), [Ask](#а–в), [ATR](#а–в), [Asset allocation](#а–в) | B: [Beta](#а–в), [Bid](#а–в), [Bond](#л–о), [Bull](#а–в) | C: [CEX](#криптовалюта), [Close](#технический-анализ), [CVaR](#и–к) | D: [DCA](#г–д), [DeFi](#г–д), [DEX](#криптовалюта), [Drawdown](#г–д) |
| E: [EMA](#технический-анализ), [EMH](#е–з), [Equity](#е–з), [ETF](#е–з), [Execution](#е–з) | F: [FIGI](#е–з), [FOK](#и–к), [FOMO](#психология-и-риск), [FUD](#криптовалюта), [Futures](#е–з) | G: [Gap](#г–д), [Gas](#криптовалюта), [GTC](#типы-заявок-сводка) | H: [Halving](#криптовалюта) |
| I: [IOC](#и–к), [IPO](#и–к), [IMOEX](#российский-рынок), [ISIN](#российский-рынок) | K: [KYC](#криптовалюта) | L: [Leverage](#и–к), [Limit](#и–к), [Liquidity](#и–к), [Long](#и–к), [Lot](#и–к) | M: [MACD](#л–о), [Margin](#л–о), [Market cap](#л–о), [MOEX](#л–о) |
| N: [NAV](#л–о), [NDX](#индексы-справочник) | O: [OCO](#л–о), [OHLCV](#технический-анализ), [Open](#технический-анализ) | P: [P/E](#п–р), [PoS](#криптовалюта), [PoW](#криптовалюта) | R: [RAG](#п–р), [ROI](#п–р), [RSI](#п–р), [RTSI](#п–р) |
| S: [SEC](#с–т), [Settlement](#с–т), [Short](#с–т), [Slippage](#с–т), [Spread](#с–т), [Stop-loss](#с–т) | T: [Take-profit](#с–т), [Ticker](#с–т), [Token](#криптовалюта), [Trailing stop](#типы-заявок-сводка) | U: [Uptrend](#технический-анализ) | V: [VaR](#у–я), [Volatility](#а–в), [Volume](#у–я), [VWAP](#у–я) |
| Y: [YTM](#у–я), [Yield](#г–д) | | | |

---

## Проверенные источники

1. [Glossary — Investor.gov (SEC)](https://www.investor.gov/additional-resources/general-resources/glossary) — эталонный справочник сотен терминов.
2. [Investing Basics — FINRA](https://www.finra.org/investors/investing/investing-basics) — equity, debt, ордера, маржа.
3. [Moscow Exchange Indices — MOEX](https://www.moex.com/a6231) — IMOEX, RTS, free-float.
4. [ISS Reference — MOEX](https://iss.moex.com/iss/reference/) — поля API и биржевые коды.
5. [Цифровые финансовые активы — ЦБ РФ](https://www.cbr.ru/finmarkets/digital/) — крипто и ЦФА в РФ.

---

## В автоматической системе

- **RAG:** при вопросе «что такое X» — приоритетный поиск по `Financial_glossary.md`.
- **Теги Obsidian:** `#term/RSI`, `#term/limit-order` в статьях; Dataview по тегам.
- **tickers.yaml:** канонические тикеры и алиасы (SBER = Сбер).

```yaml
# n8n: glossary lookup
glossary_file: Financial_glossary.md
fallback: investor.gov/glossary
```

---

## Связанные темы

- [[Glossary]] — краткая версия в разделе «Основы»
- [[Finance_basics]]
- [[Wiki_structure]]
- [[Writing_style_guide]]

---

## Что изучить дальше

1. [[Finance_basics]] — если вы с нуля.
2. [Investor.gov Glossary](https://www.investor.gov/additional-resources/general-resources/glossary) — расширение за пределами wiki.
3. [Школа MOEX](https://school.moex.com/) — термины российского рынка в курсах.
