---
title: Академические источники
tags: [moc, академия, исследования, HSE, MIT, Stanford]
sources:
  - https://www.hse.ru/ma/invest/
  - https://ocw.mit.edu/courses/15-481x-adaptive-markets-financial-market-dynamics-and-human-behavior-fall-2022/
  - https://wp.hse.ru/en/prepfr_FE
updated: 2026-07-06
level: reference
style: informational
---

# Академические источники

> Университетские курсы и публикации **2021–2026** для углубления тем Wiki. Используйте вместе с регуляторами (SEC, FINRA, MOEX, ЦБ).

## Главное

- Приоритет источникам **не старше 5 лет** (с 2021). Классика (Shiller, Lo 2005) — только как фон.
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
| [[Crypto_basics]], [[Bitcoin_overview]] | BIS, ECB, ESRB, ВШЭ | BIS Papers 156, 159; Dobrynskaya & Dubrovskiy (2022) |
| [[IMOEX_RTS]], [[MOEX_stocks]] | ВШЭ | Manushkin (2024) Fama-French на российском рынке |
| [[n8n_architecture_overview]], [[LLM_prompts_trading]] | MIT, Stanford GSB, IEEE | Lo (AI advising); Stanford FINANCE 341; sentiment+DRL (2025) |
| [[Technical_analysis_basics]] | Stanford GSB | FINANCE 562 Trading Strategies; FINANCE 361 Behavioral Finance |

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

| Год | Организация | Документ | Ссылка |
|-----|------------|----------|--------|
| 2024 | BIS | CBDC survey (91% ЦБ) | [BIS Paper 159](https://www.bis.org/publ/bppdf/bispap159.htm) |
| 2024 | BIS | Crypto, DeFi, stability | [BIS Paper 156](https://www.bis.org/publ/bppdf/bispap156.pdf) |
| 2025 | ESRB | Macroprudential crypto risks | [ESRB Report 2025](https://www.esrb.europa.eu/pub/pdf/reports/esrb.report202510_cryptoassets.en.pdf) |
| 2022 | ВШЭ | Крипто и акции: risk factors | [WP BRP 86/FE/2022](https://wp.hse.ru/fe/BRP/86/2022) |

**Связь:** [[Crypto_basics]], [[Crypto_regulation_RU]].

### Российский рынок

| Год | Автор | Тема | Ссылка |
|-----|-------|------|--------|
| 2024 | Manushkin (ВШЭ) | Fama-French 5-factor, Россия | [WP BRP 95/FE/2024](https://wp.hse.ru/en/fe/BRP/95/2024) |

**Связь:** [[IMOEX_RTS]], [[MOEX_stocks]].

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
