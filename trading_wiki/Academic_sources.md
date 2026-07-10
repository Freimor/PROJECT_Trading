---
title: Академические источники
tags: [moc, академия, исследования, HSE, MIT, Stanford]
sources:
  - https://www.hse.ru/ma/invest/
  - https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/
  - https://wp.hse.ru/en/prepfr_FE
updated: 2026-07-10
level: reference
style: informational
---

# Академические источники

> Университетские курсы и публикации **2021–2026** для углубления тем Wiki. Используйте вместе с регуляторами (SEC, FINRA, MOEX, ЦБ).

## Главное

- Приоритет источникам **не старше 5 лет** (с 2021). Классика (Shiller, Lo 2005) — только как фон.
- **Библиотека papers/** — 74 проверенных работ с анализом: [`../papers/README.md`](../papers/README.md), [`../papers/papers_analysis.yaml`](../papers/papers_analysis.yaml), [`../docs/papers-research-report-2026-07.md`](../docs/papers-research-report-2026-07.md).
- Карта ниже связывает тему Wiki с курсом или статьёй.
- В статьях — таблица «Академические источники»; сводка здесь.
- Для LLM/RAG: тег `#academic`, поле `academic_sources` в YAML.
- Не цитируйте академию как «гарантию дохода» — только контекст и методология.

---

## Карта: тема Wiki → академия

| Тема Wiki | Университет / институт | Ресурс |
|-----------|------------------------|--------|
| [[Finance_basics]], [[What_is_trading]] | Yale, MIT, ВШЭ | Shiller *Financial Markets*; MIT 15.481x; HSE Investment Analysis |
| [[Order_types]], [[Stop_loss_take_profit]] | Cornell/MIT (NBER) | Li, Ye, Zheng (2021) — типы ордеров |
| [[Portfolio_diversification]], [[Position_sizing]] | SSRN, Nature, IEEE | Jaeger & Marinelli (2022); Torrente & Uberti (2024); Agal et al. (2025) |
| [[Cognitive_biases]], [[Trader_psychology]] | MIT Sloan | Lo — Adaptive Markets (курс 2022) |
| [[Crypto_basics]], [[Bitcoin_overview]] | BIS, ECB, ESRB, ВШЭ | BIS WP 1049/1087/1227; ESRB 2025; Dobrynskaya (2022) |
| [[Crypto_indicators]] | BIS, Chaos Solitons, EJF | On-chain ribbons; whale typology |
| [[IMOEX_RTS]], [[MOEX_stocks]] | ВШЭ, Economy of Region | Abramov factor models 2025; volatility spillovers 2025 |
| [[n8n_architecture_overview]], [[LLM_prompts_trading]] | FINSABER, DeepFund, TradingAgents | LLM benchmarks 2025; Lopez-Lira 2024 |
| [[Technical_analysis_basics]] | Lopez-Lira, Digital Finance | ChatGPT sentiment; StockTwits events |
| [[Bonds_basics]] | Financial Analysts Journal | Ivashchenko bond capacity 2024 |
| [[Portfolio_diversification]] | JF, NBER, GFJ | Jensen replication 2023; DRL portfolio 2024 |

---

## Россия: ВШЭ (HSE University)

### Магистерские программы

| Программа | Содержание | Ссылка |
|-----------|------------|--------|
| **Инвестиции на финансовых рынках** | Оценка активов, портфели, риск/доходность, ЦФА | [hse.ru/ma/invest](https://www.hse.ru/ma/invest/) |
| **Financial Economics (ICEF)** | Asset Pricing, Corporate Finance, Microstructure | [hse.ru/en/ma/financial/courses](https://www.hse.ru/en/ma/financial/courses) |

### Учебные курсы

| Курс | Уровень | Ссылка |
|------|---------|--------|
| **Инвестиционный анализ** | Магистратура, DCF, мультипликаторы | [hse.ru/edu/courses/987071016](https://www.hse.ru/edu/courses/987071016) |
| **Investment Portfolio Management** | Управление портфелем (англ.) | [Профиль преподавателя](https://www.hse.ru/en/org/persons/228551063) |
| **Financial Market Microstructure** | Магистратура ICEF | [hse.ru/en/ma/financial/courses](https://www.hse.ru/en/ma/financial/courses) |

### Рабочие статьи HSE (2021–2025)

Полный список: [wp.hse.ru/en/prepfr_FE](https://wp.hse.ru/en/prepfr_FE)

| Год | Авторы | Тема | WP |
|-----|--------|------|-----|
| 2025 | Sokolov, Gorodilov | Банки, валютная переоценка, ликвидность | BRP 99/FE/2025 |
| 2024 | **Manushkin** | **Fama-French 5-factor на российском рынке** | [BRP 95/FE/2024](https://wp.hse.ru/en/fe/BRP/95/2024) |
| 2024 | Loginova, Semenova | Гендерное разнообразие советов директоров | BRP 94/FE/2024 |
| 2023 | Popova, Semenova, Sokolov | COVID-19 и стратегии вкладчиков | BRP 92/FE/2023 |
| 2022 | **Dobrynskaya, Dubrovskiy** | **Крипто и акции: факторы риска** | [BRP 86/FE/2022](https://wp.hse.ru/fe/BRP/86/2022) |
| 2022 | Lapshin | Иммунизация облигационного портфеля | BRP 88–89/FE/2022 |

### ВКР студентов ВШЭ

| Год | Тема | Ссылка |
|-----|------|--------|
| 2024 | Хеджирование деривативов с deep learning | [hse.ru/en/edu/vkr/929592108](https://www.hse.ru/en/edu/vkr/929592108) |
| 2023 | Публичная информация и цены акций MOEX | [hse.ru/en/edu/vkr/839142151](https://www.hse.ru/en/edu/vkr/839142151) |

---

## MIT

### Курс: Adaptive Markets (Fall 2022)

| Параметр | Значение |
|----------|----------|
| Код | **15.481X** |
| Преподаватель | Andrew W. Lo |
| Темы | EMH vs behavioral, AMH, нейронаука, AI, кризисы |
| Материалы | [MIT OCW Fall 2022](https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/) |

**Тезисы AMH:** рынки адаптивны; политика риска должна меняться с режимом.

**Связь:** [[Trader_psychology]], [[Cognitive_biases]], [[LLM_rules_and_guardrails]].

---

## Yale

### Financial Markets (Robert J. Shiller)

| Параметр | Значение |
|----------|----------|
| Платформа | [Coursera](https://www.coursera.org/learn/financial-markets-global) |
| Модули | CAPM, behavioral finance, акции/облигации, риск |

> Видео 2016–2017; для свежих данных дополняйте MIT Lo (2022) и BIS/ВШЭ.

**Связь:** [[Finance_basics]], [[Portfolio_diversification]].

---

## Stanford GSB

| Курс | Тема | Ссылка |
|------|------|--------|
| **FINANCE 201** | Оценка активов, портфель | [bulletin.stanford.edu](https://bulletin.stanford.edu/courses/2090781) |
| **FINANCE 341** | Modeling for Investment Management | [explorecourses.stanford.edu](https://explorecourses.stanford.edu/search?q=FINANCE+341) |
| **FINANCE 361** | Behavioral Finance | [gsb.stanford.edu RAIL](https://www.gsb.stanford.edu/experience/learning/experiential-learning/rail/curricular-integration) |
| **FINANCE 562** | Trading Strategies | Там же |

**Связь:** [[Technical_analysis_basics]], [[Crypto_flow_design]], [[Trader_psychology]].

---

## Публикации по темам (2021–2026)

### Типы заявок

| Год | Авторы | Вывод | Ссылка |
|-----|--------|-------|--------|
| 2021 | Li, Ye, Zheng | Market/limit/stop; ~57% объёма — non-routable | [NBER w28515](https://www.nber.org/papers/w28515) |

**Связь:** [[Order_types]], [[Stop_loss_take_profit]].

### Диверсификация и портфели

| Год | Авторы | Ссылка |
|-----|--------|--------|
| 2022 | Jaeger, Marinelli | [SSRN 4068889](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4068889) |
| 2024 | Torrente, Uberti | [SSRN 4840399](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4840399) |
| 2025 | Agal et al. | [Nature Sci Rep](https://doi.org/10.1038/s41598-025-26337-x) |
| 2025 | IEEE Access (CVaR+DRL+LLM) | [doi:10.1109/access.2025.3624652](https://doi.org/10.1109/access.2025.3624652) |
| 2025 | Kim et al. (Deep Ensembles) | [arXiv:2503.13544](https://arxiv.org/html/2503.13544) |

**Связь:** [[Portfolio_diversification]], [[LLM_prompts_trading]].

### Криптовалюты

| Год | Организация / авторы | Документ | Ссылка |
|-----|---------------------|----------|--------|
| 2025 | ESRB | Macroprudential crypto risks | [ESRB Report 2025](https://www.esrb.europa.eu/pub/pdf/reports/esrb.report202510_cryptoassets.en.pdf) |
| 2025 | FSB | Thematic Peer Review crypto framework | [FSB P161025](https://www.fsb.org/uploads/P161025-1.pdf) |
| 2024 | BIS | DEX liquidity (Uniswap V3) | [BIS WP 1227](https://www.bis.org/publ/work1227.htm) |
| 2024 | BIS | Crypto carry / futures basis | [BIS WP 1087](https://www.bis.org/publ/work1087.htm) |
| 2024 | Ketenci et al. | Blockchain metrics (Hash Ribbon) | [doi.org/10.1016/j.chaos.2023.114305](https://doi.org/10.1016/j.chaos.2023.114305) |
| 2023 | Liu et al. | Bitcoin trading patterns (whales) | [doi.org/10.1080/1351847X.2023.2241883](https://doi.org/10.1080/1351847X.2023.2241883) |
| 2022 | BIS | Retail crypto adoption | [BIS WP 1049](https://www.bis.org/publ/work1049.htm) |
| 2022 | ВШЭ | Крипто и акции: risk factors | [WP BRP 86/FE/2022](https://wp.hse.ru/fe/BRP/86/2022) |

**Связь:** [[Crypto_basics]], [[Crypto_regulation_RU]], [[Crypto_indicators]].

### LLM и автоматизация

| Год | Авторы | Вывод | Ссылка |
|-----|--------|-------|--------|
| 2025 | FINSABER | LLM alpha исчезает при bias-free 20y backtest | [arXiv:2505.07078](https://arxiv.org/abs/2505.07078) |
| 2025 | DeepFund | Live-тест: топ LLM теряют на реальном рынке | [arXiv:2505.11065](https://arxiv.org/abs/2505.11065) |
| 2025 | StockBench | Большинство LLM < buy-and-hold | [arXiv:2510.02209](https://arxiv.org/abs/2510.02209) |
| 2025 | TradingAgents | Multi-agent LLM framework (Ollama-ready) | [arXiv:2412.20138](https://arxiv.org/abs/2412.20138) |
| 2024 | Lopez-Lira & Tang | ChatGPT sentiment предсказывает акции OOS | [Anderson PDF](https://www.anderson.ucla.edu/sites/default/files/document/2024-04/4.19.24%20Alejandro%20Lopez%20Lira%20ChatGPT_V3.pdf) |

**Связь:** [[LLM_rules_and_guardrails]], [[n8n_architecture_overview]].

### Методология бэктеста

| Год | Авторы | Ссылка |
|-----|--------|--------|
| 2022 | López de Prado | Type I/II errors Sharpe | [doi.org/10.3905/jpm.2022.1.403](https://doi.org/10.3905/jpm.2022.1.403) |
| 2023 | Jensen, Kelly, Pedersen | Replication crisis in finance | [doi.org/10.1111/jofi.13249](https://doi.org/10.1111/jofi.13249) |
| 2023 | Arnott et al. | Factor momentum (RFS) | [doi.org/10.1093/rfs/hhad006](https://doi.org/10.1093/rfs/hhad006) |

**Связь:** [[LLM_rules_and_guardrails]], [[Portfolio_diversification]].

### Российский рынок

| Год | Автор | Тема | Ссылка |
|-----|-------|------|--------|
| 2025 | Abramov et al. (ВШЭ) | Factor models MOEX 2007–2024 | [doi.org/10.17323/j.jcfr.2073-0438.19.2.2025.67-81](https://doi.org/10.17323/j.jcfr.2073-0438.19.2.2025.67-81) |
| 2025 | Volatility spillovers MOEX sectors | 2020–2024 | [doi.org/10.31737/22212264_2025_2_65-84](https://doi.org/10.31737/22212264_2025_2_65-84) |
| 2024 | Manushkin (ВШЭ) | Fama-French 5-factor, Россия | [WP BRP 95/FE/2024](https://wp.hse.ru/en/fe/BRP/95/2024) |
| 2024 | Aizenman et al. | Geopolitical shocks → commodities | [doi.org/10.1016/j.ejpoleco.2024.102574](https://doi.org/10.1016/j.ejpoleco.2024.102574) |
| 2023 | Nazarova (ВШЭ) | Momentum на MOEX | [doi.org/10.31107/2075-1990-2023-1-58-73](https://doi.org/10.31107/2075-1990-2023-1-58-73) |
| 2023 | MOEX herding | Russia–Ukraine war | [doi.org/10.1108/rbf-01-2023-0014](https://doi.org/10.1108/rbf-01-2023-0014) |

**Связь:** [[IMOEX_RTS]], [[MOEX_stocks]].

### Облигации

| Год | Авторы | Ссылка |
|-----|--------|--------|
| 2024 | Ivashchenko & Kosowski | Bond strategy capacity | [doi.org/10.1080/0015198X.2024.2360390](https://doi.org/10.1080/0015198X.2024.2360390) |

**Связь:** [[Bonds_basics]].

---

## Как цитировать в Wiki и для LLM

```markdown
### Академическое дополнение
По данным BIS (2024), 91% ЦБ изучают CBDC
([BIS Paper 159](https://www.bis.org/publ/bppdf/bispap159.htm)).
```

YAML для RAG:

```yaml
academic_sources:
  - author: "Lo, A. W."
    year: 2022
    type: course
    url: "https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/"
```

---

## В автоматической системе

| Компонент | Применение |
|-----------|------------|
| **Obsidian** | MOC для RAG; приоритет: регулятор + академия 2021+ |
| **n8n** | `weekly-research-digest`: RSS/arXiv/HSE WP → summary |
| **Ollama** | System prompt: «поведение рынка — AMH (Lo 2022), не только EMH» |

```yaml
# academic_config.yaml
freshness_years: 5
priority_institutions: [HSE, MIT, Stanford, BIS, NBER]
fallback_classic: true
```

---

## Связанные темы

- [[Wiki_structure]] · [[Writing_style_guide]]
- [[Finance_basics]] · [[Cognitive_biases]] · [[Crypto_basics]]

## Что изучить дальше

1. Один курс: MIT 15.481x или HSE Investment Analysis — параллельно с wiki.
2. Перед [[LLM_prompts_trading]] — IEEE 2025 (LLM + portfolio).
3. Для MOEX — Manushkin (2024) vs ваш watchlist.
