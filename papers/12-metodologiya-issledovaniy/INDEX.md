# 12 — Методология исследований и бэктестинга

Критически важные работы о **достоверности** торговых стратегий: overfitting, multiple testing, репликация.

| ID | Название | Год | Тип | Ссылка |
|----|----------|-----|-----|--------|
| `meth-001` | Type I and Type II Errors of the Sharpe Ratio under Multiple Testing | 2022 | Peer-reviewed (J. Portfolio Management) | [DOI](https://doi.org/10.3905/jpm.2022.1.403) |
| `meth-002` | Time-variation, multiple testing, and the factor zoo | 2022 | Peer-reviewed (IRFA) | [DOI](https://doi.org/10.1016/j.irfa.2022.102394) |
| `meth-003` | Is There a Replication Crisis in Finance? | 2023 | Peer-reviewed (Journal of Finance) | [DOI](https://doi.org/10.1111/jofi.13249) |
| `meth-004` | Can LLM-based Strategies Outperform the Market? (FINSABER) | 2025 | arXiv | [arXiv](https://arxiv.org/abs/2505.07078) |
| `meth-005` | DeepFund: Live Real-Time LLM Fund Benchmarking | 2025 | arXiv | [arXiv](https://arxiv.org/abs/2505.11065) |

## Карточки

- [lopez-de-prado-type-errors.md](./lopez-de-prado-type-errors.md)
- [jensen-replication-crisis.md](./jensen-replication-crisis.md)
- [finsaber-methodology.md](./finsaber-methodology.md)

## Применение в системе

Обязательны для `n8n` backtest-flow и [[LLM_rules_and_guardrails]]: Deflated Sharpe, walk-forward, live-paper перед live.
