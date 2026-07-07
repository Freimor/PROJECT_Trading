"""Telegram keyboards — hierarchical reply menus + inline confirmations."""

from __future__ import annotations

from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# --- Main ---
BTN_AUTOMAT = "🤖 Автомат"
BTN_KNOWLEDGE = "📚 База знаний"
BTN_NEWS = "📰 Новости"
BTN_SYSTEM = "🖥 Управление"
BTN_KILL = "🛑 Kill Switch"

MAIN_BUTTONS = {BTN_AUTOMAT, BTN_KNOWLEDGE, BTN_NEWS, BTN_SYSTEM, BTN_KILL}

# --- Automat ---
BTN_CRYPTO_TEST = "₿ Крипто (testnet)"
BTN_MOEX_SANDBOX = "📈 MOEX (sandbox)"
BTN_CRYPTO_LIVE = "₿ Крипто LIVE ⚠️"
BTN_MOEX_LIVE = "📈 MOEX LIVE ⚠️"
BTN_CONFIRM = "✅ Подтверждения"
BTN_EVENTS = "🧾 События"
BTN_AUTOMAT_DOCS = "📖 Как работает"
BTN_PAPER_TEST = "🧪 Paper тест"
BTN_BENCHMARK = "📊 LLM Benchmark"
BTN_BACK_MAIN = "⬅️ Назад"

AUTOMAT_BUTTONS = {
    BTN_CRYPTO_TEST,
    BTN_MOEX_SANDBOX,
    BTN_CRYPTO_LIVE,
    BTN_MOEX_LIVE,
    BTN_CONFIRM,
    BTN_EVENTS,
    BTN_AUTOMAT_DOCS,
    BTN_PAPER_TEST,
    BTN_BENCHMARK,
    BTN_BACK_MAIN,
}

# --- Paper test ---
BTN_PAPER_EFF = "📊 Эффективность"
BTN_PAPER_RESET = "🔄 Сброс sandbox"
BTN_PAPER_RUN_CR = "▶️ Crypto paper"
BTN_PAPER_RUN_MX = "▶️ MOEX swing"
BTN_BACK_AUTOMAT = "⬅️ Автомат"

PAPER_BUTTONS = {
    BTN_PAPER_EFF,
    BTN_PAPER_RESET,
    BTN_PAPER_RUN_CR,
    BTN_PAPER_RUN_MX,
    BTN_BACK_AUTOMAT,
}

# --- LLM Benchmark ---
BTN_BM_REPORT = "📊 Отчёт"
BTN_BM_SYNTHETIC = "🧪 Синтетика"
BTN_BM_HISTORICAL = "📜 История"
BTN_BM_GOLDEN = BTN_BM_SYNTHETIC  # alias
BTN_BM_FULL = "▶️ Полный прогон"
BTN_BM_CALIBRATE = "🎛 Калибровка"

BENCHMARK_BUTTONS = {
    BTN_BM_REPORT,
    BTN_BM_SYNTHETIC,
    BTN_BM_HISTORICAL,
    BTN_BM_FULL,
    BTN_BM_CALIBRATE,
    BTN_BACK_AUTOMAT,
}

# --- Knowledge ---
BTN_WIKI = "📖 Wiki"
BTN_SYS_SUMMARY = "📋 Сводка системы"

KNOWLEDGE_BUTTONS = {BTN_WIKI, BTN_SYS_SUMMARY, BTN_BACK_MAIN}

# --- News ---
BTN_NEWS_LATEST = "🗞 Последние"
BTN_NEWS_SOURCES = "⚙️ Источники"
BTN_NEWS_INGEST = "🔄 Обновить"
BTN_NEWS_ALERTS = "🔔 Алерты LLM"
BTN_NEWS_TRADES = "💼 Сделки в ленте"

NEWS_BUTTONS = {
    BTN_NEWS_LATEST,
    BTN_NEWS_SOURCES,
    BTN_NEWS_INGEST,
    BTN_NEWS_ALERTS,
    BTN_NEWS_TRADES,
    BTN_BACK_MAIN,
}

# --- System ---
BTN_HOST_STATUS = "📊 Состояние"
BTN_WORKFLOWS = "🧩 Workflows"
BTN_RESTART = "🔁 Перезапуск"
BTN_SMOKE = "💨 Smoke test"

SYSTEM_BUTTONS = {BTN_HOST_STATUS, BTN_WORKFLOWS, BTN_RESTART, BTN_SMOKE, BTN_BACK_MAIN}

# --- Crypto testnet ---
BTN_CR_OVERVIEW = "📋 Сводка"
BTN_CR_FUNNEL = "🔄 Воронка"
BTN_CR_EVENTS = "🧾 События"
BTN_CR_BALANCE = "💰 Баланс"
BTN_BACK_AUTOMAT = "⬅️ Автомат"

CRYPTO_TEST_BUTTONS = {
    BTN_CR_OVERVIEW,
    BTN_CR_FUNNEL,
    BTN_CR_EVENTS,
    BTN_CR_BALANCE,
    BTN_BACK_AUTOMAT,
}

# --- MOEX sandbox ---
BTN_MX_OVERVIEW = "📋 Сводка"
BTN_MX_ACCOUNT = "👤 Демо-счёт"
BTN_MX_AUTO = "⚙️ Автомат"
BTN_MX_TRADES = "💼 Сделки"
BTN_MX_PERF = "📉 Эффективность"
BTN_MX_DCA = "▶️ Тест DCA"

MOEX_SANDBOX_BUTTONS = {
    BTN_MX_OVERVIEW,
    BTN_MX_ACCOUNT,
    BTN_MX_AUTO,
    BTN_MX_TRADES,
    BTN_MX_PERF,
    BTN_MX_DCA,
    BTN_BACK_AUTOMAT,
}

# --- Live submenus ---
BTN_LIVE_CHECKLIST = "📋 Checklist"
BTN_LIVE_STATUS = "📊 Статус"

LIVE_BUTTONS = {BTN_LIVE_CHECKLIST, BTN_LIVE_STATUS, BTN_BACK_AUTOMAT}

MENU_BUTTONS = MAIN_BUTTONS


def reply_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_AUTOMAT), KeyboardButton(text=BTN_KNOWLEDGE)],
            [KeyboardButton(text=BTN_NEWS), KeyboardButton(text=BTN_SYSTEM)],
            [KeyboardButton(text=BTN_KILL)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_automat_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CRYPTO_TEST), KeyboardButton(text=BTN_MOEX_SANDBOX)],
            [KeyboardButton(text=BTN_CRYPTO_LIVE), KeyboardButton(text=BTN_MOEX_LIVE)],
            [KeyboardButton(text=BTN_CONFIRM), KeyboardButton(text=BTN_EVENTS)],
            [KeyboardButton(text=BTN_AUTOMAT_DOCS)],
            [KeyboardButton(text=BTN_PAPER_TEST), KeyboardButton(text=BTN_BENCHMARK)],
            [KeyboardButton(text=BTN_BACK_MAIN)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_benchmark_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BM_REPORT)],
            [KeyboardButton(text=BTN_BM_SYNTHETIC), KeyboardButton(text=BTN_BM_HISTORICAL)],
            [KeyboardButton(text=BTN_BM_FULL), KeyboardButton(text=BTN_BM_CALIBRATE)],
            [KeyboardButton(text=BTN_BACK_AUTOMAT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_paper_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PAPER_EFF), KeyboardButton(text=BTN_PAPER_RESET)],
            [KeyboardButton(text=BTN_PAPER_RUN_CR), KeyboardButton(text=BTN_PAPER_RUN_MX)],
            [KeyboardButton(text=BTN_BACK_AUTOMAT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_knowledge_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_WIKI), KeyboardButton(text=BTN_SYS_SUMMARY)],
            [KeyboardButton(text=BTN_BACK_MAIN)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_news_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEWS_LATEST), KeyboardButton(text=BTN_NEWS_SOURCES)],
            [KeyboardButton(text=BTN_NEWS_INGEST)],
            [KeyboardButton(text=BTN_NEWS_ALERTS), KeyboardButton(text=BTN_NEWS_TRADES)],
            [KeyboardButton(text=BTN_BACK_MAIN)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_system_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_HOST_STATUS), KeyboardButton(text=BTN_SMOKE)],
            [KeyboardButton(text=BTN_WORKFLOWS)],
            [KeyboardButton(text=BTN_RESTART)],
            [KeyboardButton(text=BTN_BACK_MAIN)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def inline_workflows(workflows: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Inline toggle + schedule presets for n8n workflows."""
    rows: list[list[InlineKeyboardButton]] = []
    for w in workflows[:12]:
        wid = str(w.get("id", ""))
        name = str(w.get("name", "workflow"))[:26]
        active = bool(w.get("active"))
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{'✅' if active else '⏸'} {name}",
                    callback_data=f"wf:toggle:{wid}:{'off' if active else 'on'}",
                ),
            ]
        )
        # schedule presets (best-effort; if no schedule trigger, API will return error)
        rows.append(
            [
                InlineKeyboardButton(text="⏱ 15m", callback_data=f"wf:cron:{wid}:*/15 * * * *"),
                InlineKeyboardButton(text="🕐 1h", callback_data=f"wf:cron:{wid}:0 * * * *"),
                InlineKeyboardButton(text="🕓 4h", callback_data=f"wf:cron:{wid}:0 */4 * * *"),
            ]
        )
    rows.append([InlineKeyboardButton(text="✍️ Custom cron (/cron)", callback_data="wf:help:cron")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reply_crypto_test_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CR_OVERVIEW), KeyboardButton(text=BTN_CR_FUNNEL)],
            [KeyboardButton(text=BTN_CR_EVENTS), KeyboardButton(text=BTN_CR_BALANCE)],
            [KeyboardButton(text=BTN_BACK_AUTOMAT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_moex_sandbox_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MX_OVERVIEW), KeyboardButton(text=BTN_MX_ACCOUNT)],
            [KeyboardButton(text=BTN_MX_AUTO), KeyboardButton(text=BTN_MX_TRADES)],
            [KeyboardButton(text=BTN_MX_PERF), KeyboardButton(text=BTN_MX_DCA)],
            [KeyboardButton(text=BTN_BACK_AUTOMAT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def reply_live_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LIVE_CHECKLIST), KeyboardButton(text=BTN_LIVE_STATUS)],
            [KeyboardButton(text=BTN_BACK_AUTOMAT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def inline_kill_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Включить", callback_data="kill:ask:on"),
                InlineKeyboardButton(text="🟢 Выключить", callback_data="kill:ask:off"),
            ],
        ]
    )


def kill_confirm(enabled: bool) -> InlineKeyboardMarkup:
    state = "on" if enabled else "off"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"kill:confirm:{state}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="kill:cancel"),
            ]
        ]
    )


def restart_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Показать команды", callback_data="restart:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="restart:cancel"),
            ]
        ]
    )


def dca_sandbox_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Купить TMOS", callback_data="tinvest:dca:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="tinvest:dca:cancel"),
            ]
        ]
    )


def inline_news_alert_settings(news_on: bool, trades_on: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if news_on else '❌'} Алерты LLM",
                    callback_data="newsalert:toggle:news",
                ),
                InlineKeyboardButton(
                    text=f"{'✅' if trades_on else '❌'} Сделки",
                    callback_data="newsalert:toggle:trades",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="▶️ Проверить сейчас",
                    callback_data="newsalert:process",
                ),
            ],
        ]
    )


def inline_automat_docs(section_id: str, sections: list[dict[str, str]]) -> InlineKeyboardMarkup:
    """Navigation between Automat documentation sections."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for sec in sections:
        label = sec.get("title", sec.get("id", "?"))
        sid = sec.get("id", "")
        prefix = "• " if sid == section_id else ""
        row.append(
            InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"autodoc:{sid}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirmation_buttons(conf_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"conf:{conf_id}:approved"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"conf:{conf_id}:rejected"),
            ]
        ]
    )
