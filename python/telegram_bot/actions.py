"""Shared bot actions for all menus."""

from __future__ import annotations

from aiogram.types import Message

from telegram_bot.api_client import get_json, post_json
from telegram_bot.formatters import (
    format_automation_overview,
    format_automat_doc,
    format_checklist,
    format_crypto_balances,
    format_crypto_funnel,
    format_crypto_testnet,
    format_events,
    format_host_status,
    format_live_status,
    format_news_alert_settings,
    format_news_latest,
    format_news_sources,
    format_restart_plan,
    format_system_summary,
    format_tinvest_account,
    format_tinvest_automation,
    format_tinvest_overview,
    format_tinvest_performance,
    format_tinvest_trades,
    format_wiki_toc,
)
from telegram_bot.keyboards import (
    confirmation_buttons,
    dca_sandbox_confirm,
    inline_automat_docs,
    inline_kill_menu,
    inline_news_alert_settings,
    reply_automat_menu,
    reply_crypto_test_menu,
    reply_knowledge_menu,
    reply_live_menu,
    reply_main_menu,
    reply_moex_sandbox_menu,
    reply_news_menu,
    reply_system_menu,
    restart_confirm,
)


async def send_welcome(message: Message) -> None:
    await message.answer(
        "📱 Trading Pult\n\n"
        "🤖 Автомат — торговые flow\n"
        "📚 База знаний — wiki и конфиг\n"
        "📰 Новости — RSS для LLM\n"
        "🖥 Управление — инфраструктура\n"
        "🛑 Kill Switch — аварийная остановка",
        reply_markup=reply_main_menu(),
    )


# --- Main sections ---


async def send_automat_menu(message: Message) -> None:
    data = await get_json("/api/automation/overview?days=7")
    await message.answer(format_automation_overview(data), reply_markup=reply_automat_menu())


async def send_knowledge_menu(message: Message) -> None:
    await message.answer("📚 База знаний", reply_markup=reply_knowledge_menu())


async def send_news_menu(message: Message) -> None:
    await message.answer("📰 Новости для LLM-контекста", reply_markup=reply_news_menu())


async def send_system_menu(message: Message) -> None:
    await message.answer("🖥 Управление системой", reply_markup=reply_system_menu())


async def send_kill_switch_menu(message: Message) -> None:
    status = await get_json("/api/system/status")
    kill = "🔴 ВКЛЮЧЁН" if status.get("kill_switch") else "🟢 ВЫКЛЮЧЕН"
    await message.answer(
        f"🛑 Kill Switch\n\nТекущее состояние: {kill}\n\nВыберите действие:",
        reply_markup=inline_kill_menu(),
    )


# --- Automat ---


async def send_crypto_test_menu(message: Message) -> None:
    await message.answer("₿ Крипто (testnet)", reply_markup=reply_crypto_test_menu())


async def send_moex_sandbox_menu(message: Message) -> None:
    data = await get_json("/api/testing/tinvest-sandbox?days=7")
    conn = data.get("connection", {})
    icon = "✅" if conn.get("status") == "ok" else "❌"
    await message.answer(
        f"📈 MOEX (sandbox) {icon}",
        reply_markup=reply_moex_sandbox_menu(),
    )


async def send_crypto_live_menu(message: Message) -> None:
    checklist = await get_json("/api/live/checklist")
    await message.answer(
        format_live_status("crypto", checklist),
        reply_markup=reply_live_menu(),
    )


async def send_moex_live_menu(message: Message) -> None:
    checklist = await get_json("/api/live/checklist")
    await message.answer(
        format_live_status("securities", checklist),
        reply_markup=reply_live_menu(),
    )


async def send_confirmations(message: Message) -> None:
    pending = await get_json("/api/admin/confirmations/pending")
    if not pending:
        await message.answer("Нет ожидающих подтверждений.", reply_markup=reply_automat_menu())
        return
    await message.answer(f"Ожидают: {len(pending)}", reply_markup=reply_automat_menu())
    for item in pending[:5]:
        await message.answer(
            f"⚠️ {item.get('title')}\nТип: {item.get('action_type')}",
            reply_markup=confirmation_buttons(item["id"]),
        )


async def send_automat_events(message: Message) -> None:
    crypto = await get_json("/api/events?market=crypto&limit=6")
    sec = await get_json("/api/events?market=securities&limit=6")
    combined = sorted(
        (crypto or []) + (sec or []),
        key=lambda e: e.get("event_at", ""),
        reverse=True,
    )
    await message.answer(
        format_events(combined, title="🧾 События автомата"),
        reply_markup=reply_automat_menu(),
    )


async def send_automat_docs(message: Message, *, section: str = "overview") -> None:
    data = await get_json(f"/api/automation/docs?section={section}")
    sections = data.get("sections") or []
    await message.answer(
        format_automat_doc(data),
        reply_markup=inline_automat_docs(section, sections),
    )


# --- Knowledge ---


async def send_wiki(message: Message) -> None:
    data = await get_json("/api/wiki/toc")
    await message.answer(format_wiki_toc(data), reply_markup=reply_knowledge_menu())


async def send_system_summary(message: Message) -> None:
    data = await get_json("/api/system/summary")
    await message.answer(format_system_summary(data), reply_markup=reply_knowledge_menu())


# --- News ---


async def send_news_latest(message: Message) -> None:
    items = await get_json("/api/news/latest?limit=8&include_trades=true")
    await message.answer(format_news_latest(items), reply_markup=reply_news_menu())


async def send_news_alert_settings(message: Message) -> None:
    data = await get_json("/api/news/alerts/settings")
    news_on = data.get("news_digest", {}).get("enabled", True)
    trades_on = data.get("trade_alerts", {}).get("enabled", True)
    await message.answer(
        format_news_alert_settings(data),
        reply_markup=inline_news_alert_settings(news_on, trades_on),
    )


async def send_news_trades_toggle_info(message: Message) -> None:
    data = await get_json("/api/news/alerts/settings")
    enabled = data.get("trade_alerts", {}).get("enabled", True)
    new_state = not enabled
    updated = await post_json(
        "/api/news/alerts/settings",
        {"trade_enabled": new_state, "operator": f"telegram:{message.chat.id}"},
    )
    state = "включены" if updated.get("trade_alerts", {}).get("enabled") else "выключены"
    await message.answer(
        f"💼 Сделки в ленте {state}.",
        reply_markup=reply_news_menu(),
    )


async def send_news_sources(message: Message) -> None:
    sources = await get_json("/api/news/sources")
    await message.answer(format_news_sources(sources), reply_markup=reply_news_menu())


async def send_news_ingest(message: Message) -> None:
    await message.answer("🔄 Загружаю RSS…", reply_markup=reply_news_menu())
    result = await post_json("/api/news/ingest")
    await message.answer(
        f"Готово: +{result.get('inserted', 0)} новых, "
        f"дубликатов {result.get('skipped_dup', 0)}",
        reply_markup=reply_news_menu(),
    )


# --- System ---


async def send_host_status(message: Message) -> None:
    data = await get_json("/api/system/host-status")
    await message.answer(format_host_status(data), reply_markup=reply_system_menu())


async def send_smoke_test(message: Message) -> None:
    await message.answer("Запускаю smoke test…", reply_markup=reply_system_menu())
    result = await post_json("/api/admin/smoke-test")
    text = (result.get("output") or "")[:3500] or str(result)
    await message.answer(f"Smoke: {result.get('status')}\n\n{text}", reply_markup=reply_system_menu())


async def send_restart_prompt(message: Message) -> None:
    await message.answer(
        "🔁 Перезапуск сервисов Docker\n\nПоказать команды для хоста?",
        reply_markup=restart_confirm(),
    )


# --- Crypto testnet ---


async def _crypto_dashboard() -> dict:
    return await get_json("/api/crypto/testnet-dashboard?days=7")


async def send_crypto_overview(message: Message) -> None:
    data = await _crypto_dashboard()
    await message.answer(format_crypto_testnet(data), reply_markup=reply_crypto_test_menu())


async def send_crypto_funnel(message: Message) -> None:
    data = await _crypto_dashboard()
    await message.answer(format_crypto_funnel(data), reply_markup=reply_crypto_test_menu())


async def send_crypto_events(message: Message) -> None:
    events = await get_json("/api/events?market=crypto&limit=10")
    await message.answer(
        format_events(events or [], title="🧾 Crypto события"),
        reply_markup=reply_crypto_test_menu(),
    )


async def send_crypto_balance(message: Message) -> None:
    balances = await get_json("/api/binance/balances?testnet=true")
    await message.answer(format_crypto_balances(balances or []), reply_markup=reply_crypto_test_menu())


# --- MOEX sandbox ---


async def _moex_dashboard() -> dict:
    return await get_json("/api/testing/tinvest-sandbox?days=7")


async def send_moex_overview(message: Message) -> None:
    await message.answer(format_tinvest_overview(await _moex_dashboard()), reply_markup=reply_moex_sandbox_menu())


async def send_moex_account(message: Message) -> None:
    await message.answer(format_tinvest_account(await _moex_dashboard()), reply_markup=reply_moex_sandbox_menu())


async def send_moex_automation(message: Message) -> None:
    await message.answer(format_tinvest_automation(await _moex_dashboard()), reply_markup=reply_moex_sandbox_menu())


async def send_moex_trades(message: Message) -> None:
    await message.answer(format_tinvest_trades(await _moex_dashboard()), reply_markup=reply_moex_sandbox_menu())


async def send_moex_performance(message: Message) -> None:
    await message.answer(format_tinvest_performance(await _moex_dashboard()), reply_markup=reply_moex_sandbox_menu())


async def send_moex_dca_prompt(message: Message) -> None:
    dca = (await _moex_dashboard()).get("automation", {}).get("index_dca", {})
    await message.answer(
        f"▶️ Тест DCA sandbox\n\n"
        f"Купить {dca.get('ticker', 'TMOS')} на ~{dca.get('amount_rub', 10000)} ₽?",
        reply_markup=dca_sandbox_confirm(),
    )


# --- Live submenus ---


async def send_live_checklist(message: Message) -> None:
    data = await get_json("/api/live/checklist")
    await message.answer(format_checklist(data), reply_markup=reply_live_menu())


async def send_live_status_detail(message: Message) -> None:
    status = await get_json("/api/system/status")
    summary = await get_json("/api/system/summary")
    await message.answer(
        f"📊 Статус live-окружения\n\n"
        f"Mode: {summary.get('trading_mode')}\n"
        f"Live flag: {summary.get('live_enabled')}\n"
        f"Kill: {'ON' if status.get('kill_switch') else 'OFF'}\n"
        f"Ollama: {status.get('ollama', {}).get('status', '?')}",
        reply_markup=reply_live_menu(),
    )
