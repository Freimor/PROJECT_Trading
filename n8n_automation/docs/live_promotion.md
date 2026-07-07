# Live promotion checklist

Переход на **live** только после выполнения всех пунктов. Проверка: `GET http://localhost:8000/api/live/checklist`

## Автоматические проверки (API)

| Check | Условие |
|-------|---------|
| `kill_switch_off` | `guardrails.yaml` → `trading.kill_switch: false` |
| `compliance_geo_reviewed` | `crypto_config.yaml` → `compliance.geo_restrictions_reviewed: true` |
| `compliance_legal_counsel` | `compliance.legal_counsel_consulted: true` |
| `compliance_kyc` | `compliance.kyc_completed: true` |
| `fiat_offramp_disabled` | `compliance.fiat_offramp_automation: false` |
| `live_env_flag` | `.env` → `LIVE_TRADING_ENABLED=true` |
| `binance_credentials` | `BINANCE_API_KEY` задан (не testnet) |
| `tinkoff_credentials` | `TINKOFF_TOKEN` задан |

## Ручные проверки (оператор)

- [ ] ≥ 4 недели paper trading без critical errors
- [ ] Win rate и max drawdown задокументированы в `trading_wiki/logs/`
- [ ] Binance API: **Disable Withdrawals**
- [ ] Отдельные API keys для live (не testnet)
- [ ] Workflow tags `#env/live` на live workflows
- [ ] Kill switch проверен вручную
- [ ] Telegram alerts протестированы (`shared-telegram-alert`)
- [ ] Юридический контекст: [[Crypto_regulation_RU]], [[Russia_tax_basics]]

## Включение live

1. Выполнить все пункты checklist
2. `.env`: `LIVE_TRADING_ENABLED=true`
3. `crypto_config.yaml`: `env: live`, `mode: live`
4. `guardrails.yaml`: добавить `live` в `allowed_envs`
5. Импортировать и активировать workflows с тегом `env/live`
6. **Не** активировать до финальной проверки оператором

## Откат

```yaml
# guardrails.yaml
trading:
  kill_switch: true  # немедленная остановка
```

Или: `LIVE_TRADING_ENABLED=false` + деактивировать live workflows в n8n.
