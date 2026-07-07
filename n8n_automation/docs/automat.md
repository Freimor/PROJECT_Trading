# Автомат — документация

Полная версия с привязкой к Wiki:  
`trading_wiki/06-Стратегии автоматизированной LLM торговли/Automat_documentation.md`

В Telegram-боте: **🤖 Автомат → 📖 Как работает** (разделы с inline-навигацией).

## Кратко

| Тема | Где читать |
|------|------------|
| Архитектура n8n + Ollama + SQLite | [[system_overview.md]] |
| Crypto pipeline | Wiki: [[Crypto_flow_design]] |
| MOEX pipeline | Wiki: [[Securities_flow_design]] |
| Wiki → код | Раздел «Wiki→код» в Automat_documentation.md |
| Live checklist | [[live_promotion.md]] |
| Дорожная карта | [[roadmap.md]] |

## API

```
GET /api/automation/docs              — оглавление разделов
GET /api/automation/docs?section=overview
```

Разделы: `overview`, `pipeline`, `crypto`, `moex`, `wiki_map`, `bot_menu`.
