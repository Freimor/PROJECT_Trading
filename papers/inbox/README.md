# Inbox — черновики из `papers-monitor`

Автоматически создаваемые карточки для **human review** перед добавлением в основную библиотеку `papers/`.

## Поток

1. Workflow `papers-monitor-weekly` или кнопка «Собрать» на странице **Research** в web-console
2. Источники: arXiv, CrossRef, OpenAlex, Semantic Scholar, RSS BIS/IMF
3. Кандидаты в SQLite → при **Approve** создаётся `.md` здесь
4. После проверки URL и tier — перенос в `papers/XX-тема/` и запись в `papers_analysis.yaml`

## Не удаляйте эту папку

Она используется `python/papers_monitor.py` → `create_obsidian_draft()`.
