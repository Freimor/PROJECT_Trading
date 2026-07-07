"""Shared bot actions for all menus."""

from __future__ import annotations

from aiogram.types import Message

from telegram_bot.api_client import get_json, post_json
from telegram_bot.formatters import (
    format_automation_overview,
    format_automat_doc,
    format_benchmark_report,
    format_calibration_report,
    format_checklist,
    format_crypto_balances,
    format_crypto_funnel,
    format_crypto_testnet,
    format_events,
    format_host_status,
    format_live_status,
    format_paper_effectiveness,
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
    inline_workflows,
    reply_automat_menu,
    reply_benchmark_menu,
    reply_crypto_test_menu,
    reply_knowledge_menu,
    reply_live_menu,
    reply_main_menu,
    reply_moex_sandbox_menu,
    reply_news_menu,
    reply_paper_menu,
    reply_system_menu,
    restart_confirm,
)
from telegram_bot.screen import ScreenKey, show_screen, show_screen_chat


async def send_welcome(message: Message) -> None:
    await show_screen(
        message,
        "📱 Trading Pult\n\n"
        "🤖 Автомат — торговые flow\n"
        "📚 База знаний — wiki и конфиг\n"
        "📰 Новости — RSS для LLM\n"
        "🖥 Управление — инфраструктура\n"
        "🛑 Kill Switch — аварийная остановка",
        reply_markup=reply_main_menu(),
        screen_key=ScreenKey.MAIN,
    )


# --- Main sections ---


async def send_automat_menu(message: Message) -> None:
    data = await get_json("/api/automation/overview?days=7")
    await show_screen(
        message,
        format_automation_overview(data),
        reply_markup=reply_automat_menu(),
        screen_key=ScreenKey.AUTOMAT,
    )


async def send_knowledge_menu(message: Message) -> None:
    await show_screen(
        message,
        "📚 База знаний",
        reply_markup=reply_knowledge_menu(),
        screen_key=ScreenKey.KNOWLEDGE,
    )


async def send_news_menu(message: Message) -> None:
    await show_screen(
        message,
        "📰 Новости для LLM-контекста",
        reply_markup=reply_news_menu(),
        screen_key=ScreenKey.NEWS,
    )


async def send_system_menu(message: Message) -> None:
    await show_screen(
        message,
        "🖥 Управление системой",
        reply_markup=reply_system_menu(),
        screen_key=ScreenKey.SYSTEM,
    )


async def send_workflows_menu(message: Message) -> None:
    data = await get_json("/api/n8n/workflows")
    if data.get("status") != "ok":
        msg = data.get("message", "n8n API error")
        await show_screen(
            message,
            "🧩 Workflows\n\n"
            "Не удалось подключиться к n8n Public API.\n"
            f"Причина: {msg}\n\n"
            "Нужно: создать API key в n8n (Settings → API keys) "
            "и прописать `N8N_API_KEY` в `.env`, затем перезапустить `db-api`.",
            reply_markup=reply_system_menu(),
            screen_key=ScreenKey.SYSTEM,
        )
        return
    workflows = data.get("workflows") or []
    await show_screen(
        message,
        "🧩 Workflows\n\n"
        "Нажмите на workflow чтобы включить/выключить.\n"
        "Кнопки 15m/1h/4h — меняют cron для Schedule Trigger (если он есть).",
        reply_markup=inline_workflows(workflows),
        screen_key="workflows_inline",
        inline=True,
    )


async def send_kill_switch_menu(message: Message) -> None:
    status = await get_json("/api/system/status")
    kill = "🔴 ВКЛЮЧЁН" if status.get("kill_switch") else "🟢 ВЫКЛЮЧЕН"
    await show_screen(
        message,
        f"🛑 Kill Switch\n\nТекущее состояние: {kill}\n\nВыберите действие:",
        reply_markup=inline_kill_menu(),
        screen_key="kill_inline",
        inline=True,
    )


# --- Automat ---


async def send_crypto_test_menu(message: Message) -> None:
    await show_screen(
        message,
        "₿ Крипто (testnet)",
        reply_markup=reply_crypto_test_menu(),
        screen_key=ScreenKey.CRYPTO_TEST,
    )


async def send_moex_sandbox_menu(message: Message) -> None:
    data = await get_json("/api/testing/tinvest-sandbox?days=7")
    conn = data.get("connection", {})
    icon = "✅" if conn.get("status") == "ok" else "❌"
    await show_screen(
        message,
        f"📈 MOEX (sandbox) {icon}",
        reply_markup=reply_moex_sandbox_menu(),
        screen_key=ScreenKey.MOEX_SANDBOX,
    )


async def send_crypto_live_menu(message: Message) -> None:
    checklist = await get_json("/api/live/checklist")
    await show_screen(
        message,
        format_live_status("crypto", checklist),
        reply_markup=reply_live_menu(),
        screen_key=ScreenKey.LIVE,
    )


async def send_moex_live_menu(message: Message) -> None:
    checklist = await get_json("/api/live/checklist")
    await show_screen(
        message,
        format_live_status("securities", checklist),
        reply_markup=reply_live_menu(),
        screen_key=ScreenKey.LIVE,
    )


async def send_confirmations(message: Message) -> None:
    pending = await get_json("/api/admin/confirmations/pending")
    if not pending:
        await show_screen(
            message,
            "Нет ожидающих подтверждений.",
            reply_markup=reply_automat_menu(),
            screen_key=ScreenKey.AUTOMAT,
        )
        return
    await show_screen(
        message,
        f"⚠️ Ожидают подтверждения: {len(pending)}\n\nВыберите действие в сообщениях ниже.",
        reply_markup=reply_automat_menu(),
        screen_key=ScreenKey.AUTOMAT,
    )
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
    await show_screen(
        message,
        format_events(combined, title="🧾 События автомата"),
        reply_markup=reply_automat_menu(),
        screen_key=ScreenKey.AUTOMAT,
    )


async def send_automat_docs(message: Message, *, section: str = "overview") -> None:
    data = await get_json(f"/api/automation/docs?section={section}")
    sections = data.get("sections") or []
    await show_screen(
        message,
        format_automat_doc(data),
        reply_markup=inline_automat_docs(section, sections),
        screen_key="automat_docs_inline",
        inline=True,
    )


# --- Knowledge ---


async def send_wiki(message: Message) -> None:
    data = await get_json("/api/wiki/toc")
    await show_screen(
        message,
        format_wiki_toc(data),
        reply_markup=reply_knowledge_menu(),
        screen_key=ScreenKey.KNOWLEDGE,
    )


async def send_system_summary(message: Message) -> None:
    data = await get_json("/api/system/summary")
    await show_screen(
        message,
        format_system_summary(data),
        reply_markup=reply_knowledge_menu(),
        screen_key=ScreenKey.KNOWLEDGE,
    )


# --- News ---


async def send_news_latest(message: Message) -> None:
    items = await get_json("/api/news/latest?limit=8&include_trades=true")
    await show_screen(
        message,
        format_news_latest(items),
        reply_markup=reply_news_menu(),
        screen_key=ScreenKey.NEWS,
    )


async def send_news_alert_settings(message: Message) -> None:
    data = await get_json("/api/news/alerts/settings")
    news_on = data.get("news_digest", {}).get("enabled", True)
    trades_on = data.get("trade_alerts", {}).get("enabled", True)
    await show_screen(
        message,
        format_news_alert_settings(data),
        reply_markup=inline_news_alert_settings(news_on, trades_on),
        screen_key="news_alerts_inline",
        inline=True,
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
    await show_screen(
        message,
        f"💼 Сделки в ленте {state}.",
        reply_markup=reply_news_menu(),
        screen_key=ScreenKey.NEWS,
    )


async def send_news_sources(message: Message) -> None:
    sources = await get_json("/api/news/sources")
    await show_screen(
        message,
        format_news_sources(sources),
        reply_markup=reply_news_menu(),
        screen_key=ScreenKey.NEWS,
    )


async def send_news_ingest(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "🔄 Загружаю RSS…",
        reply_markup=reply_news_menu(),
        screen_key=ScreenKey.NEWS,
    )
    result = await post_json("/api/news/ingest")
    await show_screen_chat(
        bot,
        chat_id,
        f"🗞 RSS обновлён\n\n"
        f"+{result.get('inserted', 0)} новых, дубликатов {result.get('skipped_dup', 0)}",
        reply_markup=reply_news_menu(),
        screen_key=ScreenKey.NEWS,
    )


# --- Paper test ---


async def send_paper_menu(message: Message) -> None:
    status = await get_json("/api/paper/status")
    mode = status.get("global_mode", "?")
    await show_screen(
        message,
        f"🧪 Paper тест\n\nРежим: {mode}\n"
        "Виртуальные сделки на testnet/sandbox.\n"
        "Сброс MOEX → новый демо-счёт ~1M ₽.",
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )


async def send_paper_effectiveness(message: Message) -> None:
    data = await get_json("/api/paper/effectiveness?days=7")
    await show_screen(
        message,
        format_paper_effectiveness(data),
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )


async def send_paper_reset(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "⏳ Сброс MOEX sandbox + новая сессия…",
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )
    result = await post_json(
        "/api/paper/session/reset",
        {"reset_moex": True, "operator": f"telegram:{message.chat.id}"},
    )
    moex = result.get("moex", {})
    session = result.get("session", {})
    await show_screen_chat(
        bot,
        chat_id,
        f"✅ Paper сессия сброшена\n\n"
        f"Сессия: {session.get('session_id', '—')[:8]}…\n"
        f"MOEX: {moex.get('status', '—')}\n"
        f"{result.get('binance_note', '')[:200]}",
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )


async def send_paper_run_crypto(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "⏳ Crypto paper: signal + LLM + order…",
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )
    result = await post_json("/api/paper/crypto/run?symbol=BTCUSDT", {}, timeout=600.0)
    status = result.get("status", "?")
    detail = result.get("message") or result.get("reject_reason") or ""
    await show_screen_chat(
        bot,
        chat_id,
        f"₿ Crypto paper\n\nРезультат: {status}\n{detail}"[:3500],
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )


async def send_paper_run_moex(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "⏳ MOEX swing paper: signal + LLM + order…",
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )
    result = await post_json("/api/paper/securities/swing?ticker=SBER", {}, timeout=600.0)
    status = result.get("status", "?")
    detail = result.get("message") or result.get("reject_reason") or ""
    await show_screen_chat(
        bot,
        chat_id,
        f"📈 MOEX paper\n\nРезультат: {status}\n{detail}"[:3500],
        reply_markup=reply_paper_menu(),
        screen_key=ScreenKey.PAPER,
    )


# --- LLM Benchmark ---


async def _benchmark_run_progress(
    bot,
    chat_id: int,
    text: str,
    *,
    screen_key: str = ScreenKey.BENCHMARK_RUN,
) -> None:
    """Refresh benchmark progress panel (reliable vs edit-only update_panel)."""
    await show_screen_chat(
        bot,
        chat_id,
        text,
        reply_markup=reply_benchmark_menu(),
        screen_key=screen_key,
    )


def _golden_pair_label(case: dict) -> str:
    """Short human label: BTCUSDT → BTC/USD, SBER → SBER."""
    market = case.get("market", "")
    symbol = (case.get("symbol") or "?").upper()
    if market == "crypto":
        for quote in ("USDT", "USDC", "BUSD"):
            if symbol.endswith(quote) and len(symbol) > len(quote):
                return f"{symbol[: -len(quote)]}/{quote[:3]}"
        return symbol
    return symbol


def _golden_running_status(step: int, total: int, case: dict | None) -> str:
    if not case or step > total:
        return ""
    label = _golden_pair_label(case)
    if case.get("market") == "crypto":
        return f"⏳ Выполняется {step} из {total} шагов, тест пары {label}"
    return f"⏳ Выполняется {step} из {total} шагов, тест акции {label}"


def _golden_progress_text(
    completed: int,
    total: int,
    *,
    current: dict | None = None,
    details: list[dict] | None = None,
    title_prefix: str = "",
) -> str:
    details = details or []
    passed = sum(1 for d in details if d.get("pass"))
    failed = completed - passed

    lines = [title_prefix or "📊 Golden set", ""]

    if current and completed < total:
        step = completed + 1
        lines.append(_golden_running_status(step, total, current))
        summary = (current.get("summary") or "").strip()
        if summary:
            lines.append(f"   📝 {summary}")
        as_of = (current.get("as_of") or "")[:10]
        if as_of:
            lines.append(f"   📅 Дата среза: {as_of}")
        news_src = current.get("news_source")
        if news_src:
            lines.append(f"   📰 Новости: {news_src}")
        lines.append("   Вызов LLM… (~1–3 мин)")
        lines.append("")
    elif completed < total:
        lines.append(f"⏳ Подготовка шага {completed + 1} из {total}…")
        lines.append("")

    if total:
        lines.append(f"✅ Пройдено: {passed}/{total} тестов")
        lines.append(f"📋 Выполнено: {completed}/{total}")
        if failed:
            lines.append(f"❌ Провалено: {failed}/{completed}")

    recent = details[-4:]
    if recent:
        lines.append("")
        lines.append("Последние:")
        for d in recent:
            icon = "✅" if d.get("pass") else "❌"
            pair = _golden_pair_label(d)
            exp = d.get("expected", "?")
            act = d.get("actual", "?")
            lines.append(f"  {icon} {pair}: {act} (ожид. {exp})")

    latencies = [d.get("latency_ms") for d in details if d.get("latency_ms")]
    if latencies and completed < total:
        avg_s = int(sum(latencies) / len(latencies) / 1000)
        remaining = total - completed
        eta_min = max(1, (avg_s * remaining) // 60)
        lines.append("")
        lines.append(f"⏱ Осталось ~{eta_min} мин (по среднему времени кейса)")

    return "\n".join(lines)


async def _run_fixture_cases(
    message: Message,
    *,
    cases_path: str,
    one_path: str,
    title_prefix: str = "",
    snapshot_kind: str | None = None,
) -> dict:
    """Run benchmark fixtures one-by-one (synthetic or historical)."""
    chat_id = message.chat.id
    bot = message.bot
    cases = await get_json(cases_path)
    total = len(cases)
    if not total:
        return {"status": "error", "message": "no_cases", "total": 0, "passed": 0, "details": []}

    await _benchmark_run_progress(
        bot,
        chat_id,
        _golden_progress_text(0, total, title_prefix=title_prefix),
    )

    details: list[dict] = []
    for i, case in enumerate(cases, 1):
        await _benchmark_run_progress(
            bot,
            chat_id,
            _golden_progress_text(i - 1, total, current=case, details=details, title_prefix=title_prefix),
        )
        result = await post_json(
            one_path,
            {"case_id": case.get("id"), "market": case.get("market")},
            timeout=600.0,
        )
        if result.get("status") == "ok":
            details.append(result)
        else:
            details.append(
                {
                    "id": case.get("id"),
                    "market": case.get("market"),
                    "symbol": case.get("symbol"),
                    "summary": case.get("summary") or "",
                    "as_of": case.get("as_of"),
                    "expected": case.get("expected_action"),
                    "actual": "?",
                    "pass": False,
                    "error": result.get("message"),
                }
            )
        await _benchmark_run_progress(
            bot,
            chat_id,
            _golden_progress_text(i, total, details=details, title_prefix=title_prefix),
        )

    passed = sum(1 for d in details if d.get("pass"))
    tier = "synthetic" if snapshot_kind == "golden" else (snapshot_kind or "fixture")
    payload = {
        "status": "ok",
        "tier": tier,
        "total": len(details),
        "passed": passed,
        "pass_rate": round(passed / len(details), 4) if details else 0,
        "details": details,
    }
    if snapshot_kind == "golden":
        await post_json("/api/benchmark/snapshot", {"golden": payload, "kind": "golden"})
    elif snapshot_kind == "historical":
        await post_json("/api/benchmark/historical/snapshot", payload)
    try:
        await post_json("/api/benchmark/ollama/reset", {})
    except Exception:
        pass
    return payload


async def _run_golden_cases(message: Message, *, title_prefix: str = "") -> dict:
    return await _run_fixture_cases(
        message,
        cases_path="/api/benchmark/synthetic/cases",
        one_path="/api/benchmark/golden/one",
        title_prefix=title_prefix or "📊 Синтетика",
        snapshot_kind="golden",
    )


async def _run_historical_cases(message: Message, *, title_prefix: str = "") -> dict:
    return await _run_fixture_cases(
        message,
        cases_path="/api/benchmark/historical/cases",
        one_path="/api/benchmark/historical/one",
        title_prefix=title_prefix or "📜 История (реальные данные)",
        snapshot_kind="historical",
    )


async def send_benchmark_menu(message: Message) -> None:
    synth = await get_json("/api/benchmark/synthetic/cases")
    hist = await get_json("/api/benchmark/historical/cases")
    await show_screen(
        message,
        "📊 LLM Benchmark\n\n"
        "Два уровня оценки свежей модели:\n"
        f"• 🧪 Синтетика ({len(synth)}) — известные индикаторы/новости\n"
        f"• 📜 История ({len(hist)}) — реальные котировки на дату + новости\n"
        "• 📊 Отчёт — outcome + последние прогоны\n"
        "• ▶️ Полный прогон — outcome + синтетика\n"
        "• 🎛 Калибровка — сетка temp × min_confidence (долго)",
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK,
    )


async def send_benchmark_report(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "📊 Отчёт\n\n⏳ Считаю benchmark…",
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK,
    )
    data = await get_json("/api/benchmark/report?days=30")
    await show_screen_chat(
        bot,
        chat_id,
        format_benchmark_report(data),
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK,
    )


async def send_benchmark_golden(message: Message) -> None:
    """Synthetic benchmark (alias: golden)."""
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "🧪 Синтетика\n\n⏳ Загружаю кейсы…",
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK_RUN,
    )
    try:
        golden = await _run_golden_cases(message)
        if golden.get("status") != "ok":
            text = f"🧪 Синтетика\n\nОшибка: {golden.get('message', '?')}"
        else:
            report = await get_json("/api/benchmark/report?days=30")
            text = format_benchmark_report({"status": "ok", "report": report, "golden": golden})
    except Exception as exc:
        text = f"🧪 Синтетика\n\n❌ Ошибка: {exc}"
    await show_screen_chat(
        bot,
        chat_id,
        text,
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK,
    )


async def send_benchmark_historical(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "📜 История\n\n⏳ Загружаю кейсы (котировки с биржи)…",
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK_RUN,
    )
    try:
        historical = await _run_historical_cases(message)
        if historical.get("status") != "ok":
            text = f"📜 История\n\nОшибка: {historical.get('message', '?')}"
        else:
            report = await get_json("/api/benchmark/report?days=30")
            text = format_benchmark_report(
                {"status": "ok", "report": report, "historical": historical}
            )
    except Exception as exc:
        text = f"📜 История\n\n❌ Ошибка: {exc}"
    await show_screen_chat(
        bot,
        chat_id,
        text,
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK,
    )


async def send_benchmark_full(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    days = 30

    async def step(n: int, title: str) -> None:
        await _benchmark_run_progress(
            bot,
            chat_id,
            f"📊 Полный прогон benchmark\n\n[{n}/4] {title}…",
        )

    await show_screen(
        message,
        "📊 Полный прогон benchmark\n\n[1/4] Сэмплирование кейсов…",
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK_RUN,
    )
    try:
        sample = await post_json(f"/api/benchmark/sample?days={days}", {})
        await step(2, f"Разметка outcomes (новых: {sample.get('inserted', 0)})")
        label = await post_json("/api/benchmark/label", {})
        await step(3, f"Отчёт outcome (размечено: {label.get('labeled', 0)})")
        report = await get_json(f"/api/benchmark/report?days={days}")
        golden = await _run_golden_cases(
            message,
            title_prefix="📊 Полный прогон [4/4] · Golden set",
        )
        await post_json(
            "/api/benchmark/snapshot",
            {"kind": "full", "report": report, "golden": golden},
        )
        text = format_benchmark_report({"status": "ok", "report": report, "golden": golden})
    except Exception as exc:
        text = f"📊 Полный прогон\n\n❌ Ошибка: {exc}"
    await show_screen_chat(
        bot,
        chat_id,
        text,
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK,
    )


async def send_benchmark_calibrate(message: Message) -> None:
    """Offline grid search: LLM per temperature, score min_confidence without extra calls."""
    chat_id = message.chat.id
    bot = message.bot
    plan = await get_json("/api/benchmark/calibrate/plan")
    temps = plan.get("temperatures") or []
    fixtures = plan.get("fixtures") or {}
    case_count = int(fixtures.get("synthetic", 0)) + int(fixtures.get("historical", 0))
    total_t = len(temps)

    await show_screen(
        message,
        "🎛 Калибровка\n\n"
        f"Сетка: {plan.get('grid_cells', '?')} ячеек, "
        f"~{plan.get('llm_calls', '?')} вызовов LLM\n"
        f"Кейсов на температуру: {case_count}",
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK_RUN,
    )
    try:
        for ti, temp in enumerate(temps, 1):
            await _benchmark_run_progress(
                bot,
                chat_id,
                f"🎛 Калибровка [{ti}/{total_t}]\n\n"
                f"⏳ temperature={temp}\n"
                f"Прогон {case_count} кейсов (синтетика + история)…",
            )
            await post_json(
                "/api/benchmark/calibrate/temperature",
                {"temperature": temp},
                timeout=3600.0,
            )
        await _benchmark_run_progress(
            bot,
            chat_id,
            "🎛 Калибровка\n\n⏳ Считаю сетку и рекомендацию…",
        )
        result = await post_json("/api/benchmark/calibrate/finalize", {}, timeout=120.0)
        text = format_calibration_report(result)
    except Exception as exc:
        text = f"🎛 Калибровка\n\n❌ Ошибка: {exc}"
    await show_screen_chat(
        bot,
        chat_id,
        text,
        reply_markup=reply_benchmark_menu(),
        screen_key=ScreenKey.BENCHMARK,
    )


# --- System ---


async def send_host_status(message: Message) -> None:
    data = await get_json("/api/system/host-status")
    await show_screen(
        message,
        format_host_status(data),
        reply_markup=reply_system_menu(),
        screen_key=ScreenKey.SYSTEM,
    )


async def send_smoke_test(message: Message) -> None:
    chat_id = message.chat.id
    bot = message.bot
    await show_screen(
        message,
        "🧪 Smoke test\n\n⏳ Запускаю…",
        reply_markup=reply_system_menu(),
        screen_key=ScreenKey.SYSTEM,
    )
    result = await post_json("/api/admin/smoke-test", timeout=600.0)
    text = (result.get("output") or "")[:3500] or str(result)
    await show_screen_chat(
        bot,
        chat_id,
        f"🧪 Smoke: {result.get('status')}\n\n{text}",
        reply_markup=reply_system_menu(),
        screen_key=ScreenKey.SYSTEM,
    )


async def send_restart_prompt(message: Message) -> None:
    await show_screen(
        message,
        "🔁 Перезапуск сервисов Docker\n\nПоказать команды для хоста?",
        reply_markup=restart_confirm(),
        screen_key="restart_inline",
        inline=True,
    )


# --- Crypto testnet ---


async def _crypto_dashboard() -> dict:
    return await get_json("/api/crypto/testnet-dashboard?days=7")


async def send_crypto_overview(message: Message) -> None:
    data = await _crypto_dashboard()
    await show_screen(
        message,
        format_crypto_testnet(data),
        reply_markup=reply_crypto_test_menu(),
        screen_key=ScreenKey.CRYPTO_TEST,
    )


async def send_crypto_funnel(message: Message) -> None:
    data = await _crypto_dashboard()
    await show_screen(
        message,
        format_crypto_funnel(data),
        reply_markup=reply_crypto_test_menu(),
        screen_key=ScreenKey.CRYPTO_TEST,
    )


async def send_crypto_events(message: Message) -> None:
    events = await get_json("/api/events?market=crypto&limit=10")
    await show_screen(
        message,
        format_events(events or [], title="🧾 Crypto события"),
        reply_markup=reply_crypto_test_menu(),
        screen_key=ScreenKey.CRYPTO_TEST,
    )


async def send_crypto_balance(message: Message) -> None:
    balances = await get_json("/api/binance/balances?testnet=true")
    await show_screen(
        message,
        format_crypto_balances(balances if isinstance(balances, dict) else balances or []),
        reply_markup=reply_crypto_test_menu(),
        screen_key=ScreenKey.CRYPTO_TEST,
    )


# --- MOEX sandbox ---


async def _moex_dashboard() -> dict:
    return await get_json("/api/testing/tinvest-sandbox?days=7")


async def send_moex_overview(message: Message) -> None:
    await show_screen(
        message,
        format_tinvest_overview(await _moex_dashboard()),
        reply_markup=reply_moex_sandbox_menu(),
        screen_key=ScreenKey.MOEX_SANDBOX,
    )


async def send_moex_account(message: Message) -> None:
    await show_screen(
        message,
        format_tinvest_account(await _moex_dashboard()),
        reply_markup=reply_moex_sandbox_menu(),
        screen_key=ScreenKey.MOEX_SANDBOX,
    )


async def send_moex_automation(message: Message) -> None:
    await show_screen(
        message,
        format_tinvest_automation(await _moex_dashboard()),
        reply_markup=reply_moex_sandbox_menu(),
        screen_key=ScreenKey.MOEX_SANDBOX,
    )


async def send_moex_trades(message: Message) -> None:
    await show_screen(
        message,
        format_tinvest_trades(await _moex_dashboard()),
        reply_markup=reply_moex_sandbox_menu(),
        screen_key=ScreenKey.MOEX_SANDBOX,
    )


async def send_moex_performance(message: Message) -> None:
    await show_screen(
        message,
        format_tinvest_performance(await _moex_dashboard()),
        reply_markup=reply_moex_sandbox_menu(),
        screen_key=ScreenKey.MOEX_SANDBOX,
    )


async def send_moex_dca_prompt(message: Message) -> None:
    dca = (await _moex_dashboard()).get("automation", {}).get("index_dca", {})
    await show_screen(
        message,
        f"▶️ Тест DCA sandbox\n\n"
        f"Купить {dca.get('ticker', 'TMOS')} на ~{dca.get('amount_rub', 10000)} ₽?",
        reply_markup=dca_sandbox_confirm(),
        screen_key="moex_dca_inline",
        inline=True,
    )


# --- Live submenus ---


async def send_live_checklist(message: Message) -> None:
    data = await get_json("/api/live/checklist")
    await show_screen(
        message,
        format_checklist(data),
        reply_markup=reply_live_menu(),
        screen_key=ScreenKey.LIVE,
    )


async def send_live_status_detail(message: Message) -> None:
    status = await get_json("/api/system/status")
    summary = await get_json("/api/system/summary")
    await show_screen(
        message,
        f"📊 Статус live-окружения\n\n"
        f"Mode: {summary.get('trading_mode')}\n"
        f"Live flag: {summary.get('live_enabled')}\n"
        f"Kill: {'ON' if status.get('kill_switch') else 'OFF'}\n"
        f"Ollama: {status.get('ollama', {}).get('status', '?')}",
        reply_markup=reply_live_menu(),
        screen_key=ScreenKey.LIVE,
    )
