# Отчёт по библиотеке papers/ (волны 1–4)

**Дата:** 2026-07-10  
**Итого источников:** 74 (проверяемые ссылки, 2021–2026)  
**Статус сбора:** завершён — новые peer-reviewed работы по MOEX post-2024 и репликации LLM на Ollama **не найдены** в достаточном количестве

---

## 1. Executive summary

За четыре волны собрана библиотека из **74 работ** (академия, центробанки, NBER/BIS/FSB, отраслевые журналы). Главный вывод для автоматической системы:

> **LLM — аналитический слой, не исполнитель сделок.** Достоверные бенчмарки 2025 (FINSABER, DeepFund, StockBench) показывают, что «успех» LLM-стратегий исчезает при честном бэктесте и live-тесте. Крипторынок структурно неблагоприятен для розницы (BIS). Российский рынок факторно предсказуем на истории, но микроструктура после санкций MOEX 2024 требует новых данных.

---

## 2. Что добавлено по волнам

| Волна | Фокус | +работ | Ключевые источники |
|-------|-------|--------|-------------------|
| 1 | Базовая коллекция | 57 | JFE, BIS, NBER, MOEX herding |
| 2 | Регуляторика, микроструктура, LLM-бенчмарки | 19 | ESRB 2025, NBER w34054, FINSABER |
| 3 | On-chain, DRL, факторы, геополитика | 12 | Chaos Solitons, Arnott RFS, Aizenman EJPE |
| 4 | Методология, облигации, FSB | 6 | Lopez de Prado JPM, Ivashchenko FAJ |

Полный каталог: [`papers/README.md`](../papers/README.md)  
Анализ достоверности: [`papers/papers_analysis.yaml`](../papers/papers_analysis.yaml)  
Тренды: [`papers/TRENDS.md`](../papers/TRENDS.md)

---

## 3. Топ-10 по достоверности (tier 1)

| # | Работа | Score | Ссылка |
|---|--------|-------|--------|
| 1 | BIS WP 1049 — retail crypto adoption | 10 | [bis.org/publ/work1049.htm](https://www.bis.org/publ/work1049.htm) |
| 2 | Jensen et al. — Replication Crisis in Finance (JF 2023) | 10 | [doi.org/10.1111/jofi.13249](https://doi.org/10.1111/jofi.13249) |
| 3 | Liu et al. — Taming the bias zoo (JFE 2022) | 10 | [doi.org/10.1016/j.jfineco.2021.06.001](https://doi.org/10.1016/j.jfineco.2021.06.001) |
| 4 | BIS WP 1227 — DEX liquidity | 10 | [bis.org/publ/work1227.htm](https://www.bis.org/publ/work1227.htm) |
| 5 | BIS WP 1087 — crypto carry | 10 | [bis.org/publ/work1087.htm](https://www.bis.org/publ/work1087.htm) |
| 6 | ESRB Report — crypto systemic risks (2025) | 9 | [esrb.europa.eu/.../esrb.report202510_cryptoassets.en.pdf](https://www.esrb.europa.eu/pub/pdf/reports/esrb.report202510_cryptoassets.en.pdf) |
| 7 | Lopez-Lira & Tang — ChatGPT forecasts (2024) | 9 | [Anderson PDF](https://www.anderson.ucla.edu/sites/default/files/document/2024-04/4.19.24%20Alejandro%20Lopez%20Lira%20ChatGPT_V3.pdf) |
| 8 | NBER w34054 — AI collusion | 9 | [doi.org/10.3386/w34054](https://doi.org/10.3386/w34054) |
| 9 | Arnott et al. — Factor Momentum (RFS 2023) | 9 | [doi.org/10.1093/rfs/hhad006](https://doi.org/10.1093/rfs/hhad006) |
| 10 | MOEX herding during war (RBF 2023) | 8 | [doi.org/10.1108/rbf-01-2023-0014](https://doi.org/10.1108/rbf-01-2023-0014) |

---

## 4. Тренды (синтез)

### LLM в трейдинге
- **2023–24:** сентимент ChatGPT предсказывает акции ([Lopez-Lira 2024](https://www.anderson.ucla.edu/sites/default/files/document/2024-04/4.19.24%20Alejandro%20Lopez%20Lira%20ChatGPT_V3.pdf))
- **2025:** FINSABER, DeepFund, StockBench — LLM **не бьют** buy-and-hold при честной оценке ([arXiv:2505.07078](https://arxiv.org/abs/2505.07078), [arXiv:2505.11065](https://arxiv.org/abs/2505.11065))
- **Практика:** RAG + guardrails; live-paper обязателен

### Крипто
- Розница системно проигрывает ([BIS Bulletin 69](https://www.bis.org/publ/bisbull69.pdf))
- On-chain метрики (hash rate, CPTRA) дают edge в peer-reviewed работах ([doi.org/10.1016/j.chaos.2023.114305](https://doi.org/10.1016/j.chaos.2023.114305))
- <1% пользователей = >95% объёма BTC ([doi.org/10.1080/1351847X.2023.2241883](https://doi.org/10.1080/1351847X.2023.2241883))

### MOEX / Россия
- Factor strategies бьют MOEX-TR ([doi.org/10.17323/j.jcfr.2073-0438.19.2.2025.67-81](https://doi.org/10.17323/j.jcfr.2073-0438.19.2.2025.67-81))
- Momentum работает с комиссиями ([doi.org/10.31107/2075-1990-2023-1-58-73](https://doi.org/10.31107/2075-1990-2023-1-58-73))
- **Пробел:** нет peer-reviewed MOEX post-санкций 06.2024

### Риск и методология
- End-to-end ML > predict-then-optimize ([doi.org/10.3386/w34861](https://doi.org/10.3386/w34861))
- Deflated Sharpe обязателен при multiple testing ([doi.org/10.3905/jpm.2022.1.403](https://doi.org/10.3905/jpm.2022.1.403))
- Factor zoo: 13 тем реплицируются ([doi.org/10.1111/jofi.13249](https://doi.org/10.1111/jofi.13249))

---

## 5. Рекомендации для системы (n8n + Ollama + Obsidian)

### Критичные (P0)

1. **FINSABER-style backtest module** — walk-forward, survivorship-free universe, Deflated Sharpe ([meth-004](https://arxiv.org/abs/2505.07078))
2. **DeepFund live-paper** — отдельный flow с данными post-training-cutoff Ollama ([meth-005](https://arxiv.org/abs/2505.11065))
3. **LLM = validate only** — ордера только из Code/YAML rules ([LLM_rules_and_guardrails](../trading_wiki/09-LLM%20промпты%20и%20инструменты/LLM_rules_and_guardrails.md))
4. **Crypto retail guard** — не входить против whale flow; учитывать BIS retail loss data

### Важные (P1)

5. **On-chain pipeline** — hash rate, CPTRA ribbons как фильтр, не как единственный сигнал ([krypto-008](https://doi.org/10.1016/j.chaos.2023.114305))
6. **MOEX factor sleeve** — отдельный flow для factor portfolios vs intraday ([cb-005](https://doi.org/10.17323/j.jcfr.2073-0438.19.2.2025.67-81))
7. **Regulatory monitor** — RSS ESRB/FSB/CBR → macro-context для kill_switch
8. **NeuraTradeBench-style** Ollama paper-trading harness (GitHub: sakshyambanjade/neuratrade)

### Улучшения (P2)

9. TradingAgents multi-agent pattern для Ollama ([arXiv:2412.20138](https://arxiv.org/abs/2412.20138))
10. Bond ladder flow с duration shock alerts ([doi.org/10.1080/0015198X.2024.2360390](https://doi.org/10.1080/0015198X.2024.2360390))
11. Geopolitical risk overlay для commodity-linked MOEX names ([doi.org/10.1016/j.ejpoleco.2024.102574](https://doi.org/10.1016/j.ejpoleco.2024.102574))

---

## 6. Почему сбор остановлен

| Пробел | Статус поиска |
|--------|---------------|
| MOEX post-санкции 2024 peer-reviewed | Не найдено |
| Ollama LLM trading peer-reviewed | Только GitHub tools, не журналы |
| Tinkoff API academic case studies | Не найдено |
| Finam/Smart-Lab как наука | Только блоги — tier 5 |

Дальнейший сбор имеет смысл при появлении новых публикаций (arXiv alerts, HSE WP, BIS quarterly).

---

## Связанные файлы

- Wiki: [[Academic_sources]](../trading_wiki/Academic_sources.md)
- Roadmap: [docs/roadmap-razvitiya.md](../docs/roadmap-razvitiya.md)
