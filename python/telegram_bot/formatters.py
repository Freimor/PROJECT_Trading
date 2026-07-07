"""Format API responses for Telegram."""

from __future__ import annotations

import json
from typing import Any


def _truncate(text: str, limit: int = 3900) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _money_line(pos: dict[str, Any]) -> str:
    qty = pos.get("quantity", 0)
    ticker = pos.get("ticker") or pos.get("figi", "?")
    avg = pos.get("avg_price", 0)
    if ticker == "RUB000UTSTOM":
        return f"  💵 RUB: {qty:,.0f} ₽"
    return f"  • {ticker}: {qty:g} шт. (ср. {avg:.2f} ₽)"


def _funnel_lines(funnel: dict[str, Any], title: str) -> list[str]:
    lines = [title]
    for stage, vals in (funnel or {}).items():
        if isinstance(vals, dict):
            lines.append(f"  {stage}: {vals.get('passed', 0)}/{vals.get('total', 0)}")
    return lines


def format_automation_overview(data: dict[str, Any]) -> str:
    kill = "🔴 ON" if data.get("kill_switch") else "🟢 OFF"
    ollama = data.get("ollama", {})
    crypto = data.get("crypto", {})
    sec = data.get("securities", {})
    last = data.get("last_event")
    last_line = "—"
    if last:
        last_line = f"{last.get('workflow_name')} / {last.get('stage')}"
    cs = crypto.get("funnel_signal") or {}
    ss = sec.get("funnel_signal") or {}
    return _truncate(
        f"🤖 Автомат — сводка\n\n"
        f"Kill switch: {kill}\n"
        f"Режим: {data.get('trading_mode')} | Live flag: {data.get('live_flag')}\n"
        f"Ollama: {ollama.get('status', '?')} ({ollama.get('latency_ms', '?')} ms)\n"
        f"Сигналов dry-run (7d): {data.get('dry_run_signals_7d', 0)}\n"
        f"Последнее событие: {last_line}\n\n"
        f"₿ Крипто: {crypto.get('env')} / {crypto.get('mode')}\n"
        f"  пары: {', '.join(crypto.get('pairs', []))}\n"
        f"  воронка signal: {cs.get('passed', 0)}/{cs.get('total', 0)}\n\n"
        f"📈 MOEX: {sec.get('env')} / {sec.get('mode')} ({sec.get('active_mode')})\n"
        f"  T-Invest API: {sec.get('tinvest_api', '?')}\n"
        f"  воронка signal: {ss.get('passed', 0)}/{ss.get('total', 0)}"
    )


def format_checklist(data: dict[str, Any]) -> str:
    lines = ["📋 Live Checklist"]
    checks = data.get("checks", {})
    ok = sum(1 for v in checks.values() if v)
    for key, passed in checks.items():
        lines.append(f"{'✅' if passed else '❌'} {key}")
    ready = "✅ READY" if data.get("ready_for_live") else "❌ NOT READY"
    lines.append(f"\n{ready} ({ok}/{len(checks)})")
    return "\n".join(lines)


def format_events(events: list[dict[str, Any]], *, title: str = "🧾 События") -> str:
    if not events:
        return f"{title}\nНет данных."
    lines = [title]
    for e in events[:10]:
        sym = e.get("symbol") or ""
        lines.append(
            f"• {e.get('event_at', '')[:16]} [{e.get('market', '')}] "
            f"{e.get('env')} {e.get('stage')} {e.get('decision')} {sym}"
        )
    return _truncate("\n".join(lines))


def format_system_summary(data: dict[str, Any]) -> str:
    crypto = data.get("crypto", {})
    sec = data.get("securities", {})
    ollama = data.get("ollama", {})
    last = data.get("last_event")
    return _truncate(
        f"📋 Сводка системы\n\n"
        f"Режим guardrails: {data.get('trading_mode')}\n"
        f"Kill switch: {'ON' if data.get('kill_switch') else 'OFF'}\n"
        f"Live enabled: {data.get('live_enabled')}\n"
        f"Allowed envs: {', '.join(data.get('allowed_envs', []))}\n\n"
        f"₿ Crypto: {crypto.get('env')} / {crypto.get('mode')}\n"
        f"  пары: {', '.join(crypto.get('pairs', []))}\n"
        f"  LLM: {crypto.get('llm_model')}\n"
        f"  cron: {crypto.get('schedule') or '—'}\n\n"
        f"📈 Securities: {sec.get('env')} / {sec.get('mode')}\n"
        f"  режим: {sec.get('active_mode')}\n"
        f"  DCA: {sec.get('dca_ticker')}\n"
        f"  swing LLM: {sec.get('swing_model')}\n\n"
        f"Ollama: {ollama.get('status', '?')}\n"
        f"Last event: {last.get('workflow_name') if last else '—'}"
    )


def format_automat_doc(data: dict[str, Any]) -> str:
    title = data.get("title", "Документация")
    body = data.get("body", "")
    return _truncate(f"📖 {title}\n\n{body}")


def format_wiki_toc(data: dict[str, Any]) -> str:
    lines = ["📖 Trading Wiki", data.get("intro", ""), "", "Разделы:"]
    for sec in data.get("sections", [])[:12]:
        lines.append(f"• {sec.get('folder')} ({sec.get('files')} файлов)")
    if data.get("glossary"):
        lines.append("• Financial_glossary.md")
    lines.append(f"\nПуть: {data.get('wiki_path', '')}")
    lines.append("Полная wiki — в Obsidian / GitHub.")
    return _truncate("\n".join(lines))


def format_paper_effectiveness(data: dict[str, Any]) -> str:
    cfg = data.get("config", {})
    pnl = data.get("pnl_vs_baseline") or {}
    llm_c = data.get("llm_eval", {}).get("crypto", {})
    llm_s = data.get("llm_eval", {}).get("securities", {})
    session = data.get("session") or {}
    lines = [
        "📊 Paper — эффективность LLM",
        f"Режим: {cfg.get('global_mode', '?')}",
        f"Сессия: {session.get('label') or '—'}",
        "",
        f"Paper-ордера: {data.get('paper_orders_executed', 0)}/{data.get('paper_orders_total', 0)}",
        f"LLM approve → ордер: {data.get('llm_approved_then_executed', 0)}",
        "",
        "LLM crypto:",
        f"  вызовов: {llm_c.get('count', 0)}, approve: {llm_c.get('approve_rate', '—')}",
        f"  confidence: {llm_c.get('avg_confidence', '—')}",
        "",
        "LLM MOEX:",
        f"  вызовов: {llm_s.get('count', 0)}, approve: {llm_s.get('approve_rate', '—')}",
        "",
        "PnL vs baseline сессии:",
        f"  USDT: {pnl.get('usdt_delta', '—')}",
        f"  BTC: {pnl.get('btc_delta', '—')}",
        f"  RUB: {pnl.get('rub_delta', '—')}",
        "",
        "⚠️ Не инвестрекомендация. Binance PnL — от baseline, не от нуля.",
    ]
    return _truncate("\n".join(lines))


def format_benchmark_report(data: dict[str, Any]) -> str:
    report = data.get("report") or data
    if report.get("status") != "ok":
        return f"📊 LLM Benchmark\nОшибка: {report.get('message', '?')}"

    snapshot = report.get("last_snapshot") or data.get("last_snapshot") or {}
    golden = data.get("golden") or snapshot.get("golden")

    lines = [
        "📊 LLM Benchmark",
        f"Период: {report.get('days', 30)} дн.",
        "",
        "── Outcome (live/paper) ──",
        f"Кейсов: {report.get('total_cases', 0)} | размечено: {report.get('labeled_cases', 0)}",
    ]
    if report.get("labeled_cases", 0) == 0:
        lines.append(
            "  ⏳ Размеченных кейсов пока нет (нужно ≥30ч после сделки)."
        )

    for mkt, block in (report.get("by_market") or {}).items():
        out = block.get("outcome") or {}
        op = block.get("operational") or {}
        lines.append(f"\n{'₿' if mkt == 'crypto' else '📈'} {mkt.upper()}:")
        lines.append(f"  precision approve: {out.get('precision_approve', '—')}")
        lines.append(f"  recall: {out.get('recall', '—')}")
        lines.append(
            f"  good/bad approve: {out.get('good_approves', 0)}/{out.get('bad_approves', 0)}"
        )
        lines.append(f"  missed opportunities: {out.get('missed_opportunities', 0)}")
        lines.append(f"  sim PnL (approve): {out.get('simulated_pnl_approve_pct', '—')}%")
        lines.append(f"  LLM approve rate: {op.get('approve_rate', '—')}")
        lines.append(f"  avg latency: {op.get('avg_latency_ms', '—')} ms")

    if golden and golden.get("status") == "ok":
        lines.append("")
        tier = golden.get("tier", "synthetic")
        lines.append(f"── {'Синтетика' if tier == 'synthetic' else 'Golden'} (известные данные) ──")
        saved = snapshot.get("saved_at", "")
        if saved:
            lines.append(f"  обновлено: {saved[:16]}")
        lines.append(
            f"  🏅 {golden.get('passed', 0)}/{golden.get('total', 0)} "
            f"({golden.get('pass_rate', 0)})"
        )
        failed = [d for d in golden.get("details", []) if not d.get("pass")]
        for d in failed[:5]:
            summary = (d.get("summary") or "").strip()
            lines.append(f"  ❌ {d.get('id')}: expected {d.get('expected')}, got {d.get('actual')}")
            if summary:
                lines.append(f"     {summary}")
        if not failed:
            lines.append("  ✅ Все golden-кейсы прошли")

    hist_snap = report.get("last_historical_snapshot") or data.get("last_historical_snapshot") or {}
    historical = data.get("historical") or hist_snap
    if historical and historical.get("status") == "ok":
        lines.append("")
        lines.append("── История (реальные котировки) ──")
        saved_h = hist_snap.get("saved_at", "")
        if saved_h:
            lines.append(f"  обновлено: {saved_h[:16]}")
        lines.append(
            f"  🏅 {historical.get('passed', 0)}/{historical.get('total', 0)} "
            f"({historical.get('pass_rate', 0)})"
        )
        failed_h = [d for d in historical.get("details", []) if not d.get("pass")]
        for d in failed_h[:5]:
            summary = (d.get("summary") or "").strip()
            as_of = (d.get("as_of") or "")[:10]
            lines.append(f"  ❌ {d.get('id')} ({as_of}): {d.get('actual')} ≠ {d.get('expected')}")
            if summary:
                lines.append(f"     {summary}")

    if not (report.get("by_market") or {}) and not golden and not historical:
        lines.append("\nНет данных. Запустите paper/dry-run или Golden set.")

    cal_snap = report.get("last_calibration_snapshot") or data.get("last_calibration_snapshot") or {}
    if cal_snap and cal_snap.get("status") == "ok":
        lines.append("")
        lines.append("── Offline-калибровка (последняя) ──")
        saved_c = cal_snap.get("saved_at", "")
        if saved_c:
            lines.append(f"  обновлено: {saved_c[:16]}")
        rec = cal_snap.get("recommended") or {}
        if rec:
            lines.append(
                f"  рекомендация: temp={rec.get('temperature')}, "
                f"min_conf={rec.get('min_confidence')}, score={rec.get('composite_score')}"
            )
        cur = cal_snap.get("current_guardrails") or {}
        lines.append(
            f"  текущие guardrails: temp={cur.get('temperature')}, min_conf={cur.get('min_confidence')}"
        )
        lines.append("  (применение вручную в guardrails.yaml)")

    lines.append("\n⚠️ Outcome metrics — образовательный бэктест, не инвестрекомендация.")
    return _truncate("\n".join(lines))


def format_calibration_report(data: dict[str, Any]) -> str:
    if data.get("status") != "ok":
        return f"🎛 Калибровка\nОшибка: {data.get('message', data.get('status', '?'))}"

    lines = ["🎛 Offline-калибровка LLM", ""]

    fixtures = data.get("fixtures") or {}
    lines.append(
        f"Фикстуры: синт. {fixtures.get('synthetic_total', '?')} "
        f"(train {fixtures.get('synthetic_train', '?')}, "
        f"holdout {fixtures.get('synthetic_holdout', '?')}), "
        f"история {fixtures.get('historical', '?')}"
    )

    grid_size = data.get("grid_size") or {}
    lines.append(
        f"Сетка: {grid_size.get('temperatures', '?')} temp × "
        f"{grid_size.get('min_confidence', '?')} conf = {grid_size.get('cells', '?')} ячеек"
    )

    cur = data.get("current_guardrails") or {}
    lines.append(
        f"\nТекущие guardrails: temp={cur.get('temperature')}, min_conf={cur.get('min_confidence')}"
    )

    rec = data.get("recommended")
    if rec:
        lines.append(
            f"\n✅ Рекомендация: temp={rec.get('temperature')}, "
            f"min_conf={rec.get('min_confidence')}"
        )
        lines.append(f"   composite={rec.get('composite_score')}")
        lines.append(
            f"   hist={rec.get('historical_pass')}, train={rec.get('synthetic_train_pass')}, "
            f"holdout={rec.get('synthetic_holdout_pass')}"
        )
        lines.append(f"   outcome precision={rec.get('outcome_precision')}")

    note = data.get("recommendation_note")
    if note:
        lines.append(f"\n{note}")

    heatmap = data.get("heatmap") or {}
    temps = heatmap.get("temperatures") or []
    confs = heatmap.get("min_confidence") or []
    scores = heatmap.get("composite_scores") or []
    if temps and confs and scores:
        lines.append("\n── Heatmap (composite score) ──")
        header = "      " + " ".join(f"{c:.2f}" for c in confs)
        lines.append(header)
        for i, temp in enumerate(temps):
            row = scores[i] if i < len(scores) else []
            cells: list[str] = []
            for j in range(len(confs)):
                val = row[j] if j < len(row) else None
                cells.append(f"{val:.2f}" if val is not None else " — ")
            lines.append(f"T={temp:g} " + " ".join(cells))

    saved = data.get("saved_at", "")
    if saved:
        lines.append(f"\nСохранено: {saved[:16]}")

    unload = data.get("ollama_unload")
    if unload:
        lines.append(f"Ollama unload: {unload.get('status', unload)}")

    lines.append("\n⚠️ min_confidence — порог guardrails после LLM, не параметр Ollama.")
    lines.append("⚠️ Не инвестрекомендация.")
    return _truncate("\n".join(lines))


def format_news_latest(items: list[dict[str, Any]]) -> str:
    if not items:
        return "🗞 Новости\nПусто. Нажмите «Обновить»."
    lines = ["🗞 Лента (новости + сделки)"]
    for item in items[:8]:
        if item.get("type") == "trade":
            lines.append(f"💼 {item.get('title', '?')}")
            summary = (item.get("summary") or "")[:60]
            if summary:
                lines.append(f"   {summary}")
            continue
        title = (item.get("title") or "")[:72]
        src = item.get("source_name", "?")
        v = item.get("verification_status", "?")
        icon = "✅" if v == "verified" else ("❌" if v == "rejected" else "⏳")
        tickers = item.get("matched_symbols")
        if isinstance(tickers, str):
            try:
                import json
                tickers = ", ".join(json.loads(tickers)[:3])
            except Exception:
                tickers = ""
        elif isinstance(tickers, list):
            tickers = ", ".join(tickers[:3])
        else:
            tickers = ""
        suffix = f" [{tickers}]" if tickers else ""
        lines.append(f"{icon} [{src}] {title}{suffix}")
    return _truncate("\n".join(lines))


def format_news_alert_settings(data: dict[str, Any]) -> str:
    news = data.get("news_digest", {})
    trades = data.get("trade_alerts", {})
    watch = data.get("watch_symbols_resolved") or data.get("watch_symbols") or []
    if not watch:
        watch_note = "авто: whitelist + config"
    else:
        watch_note = ", ".join(watch[:8])
    return (
        "🔔 Настройки новостных алертов\n\n"
        f"LLM-дайджесты: {'✅ ВКЛ' if news.get('enabled', True) else '❌ ВЫКЛ'}\n"
        f"  модель: {news.get('ollama_model', '—')}\n"
        f"  min confidence: {news.get('min_confidence', 0.55)}\n\n"
        f"Сделки в ленте: {'✅ ВКЛ' if trades.get('enabled', True) else '❌ ВЫКЛ'}\n"
        f"Push сделок в Telegram: {'✅' if trades.get('push_telegram', True) else '❌'}\n\n"
        f"Мониторинг: {watch_note}\n\n"
        "Значимые новости (Smart-Lab, MOEX, …) → LLM-анализ → push."
    )


def format_news_sources(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "⚙️ Источники\nНе настроены."
    lines = [
        "⚙️ Источники RSS",
        "official > media; проверка домена ссылки",
        "",
    ]
    for s in sources:
        flag = "✅" if s.get("enabled") else "⏸"
        err = s.get("last_error")
        err_s = f" ⚠️" if err else ""
        lines.append(
            f"{flag} {s.get('name')} ({s.get('source_tier')}){err_s}\n"
            f"   fetch: каждые {s.get('fetch_interval_min', '?')} мин"
        )
    lines.append("\nКонфиг: trading_wiki/config/news_sources.yaml")
    return _truncate("\n".join(lines))


def format_host_status(data: dict[str, Any]) -> str:
    host = data.get("host", {})
    ollama = data.get("ollama", {})
    lines = [
        "📊 Состояние системы",
        f"UTC: {data.get('utc_time', '—')}",
        f"Москва: {data.get('moscow_time', '—')}",
        f"MOEX сессия: {data.get('moex_session', '—')}",
        f"Сейчас торги: {'да' if data.get('in_moex_session') else 'нет'}",
        "",
        f"Ollama: {ollama.get('status', '?')} ({ollama.get('latency_ms', '?')} ms)",
        f"Models: {', '.join(ollama.get('models', [])[:3]) or '—'}",
    ]
    if host.get("available"):
        lines.extend([
            "",
            f"CPU: {host.get('cpu_pct')}%",
            f"RAM: {host.get('ram_used_gb')}/{host.get('ram_total_gb')} GB ({host.get('ram_pct')}%)",
        ])
    else:
        lines.append(f"\n{host.get('note', 'Метрики хоста недоступны')}")
    health = data.get("services_health") or []
    if health:
        lines.append("\nHealth checks:")
        for h in health[:5]:
            lines.append(f"  {h.get('service_name')}: {h.get('status')}")
    return _truncate("\n".join(lines))


def format_restart_plan(data: dict[str, Any]) -> str:
    lines = ["🔁 Перезапуск сервисов", data.get("message", ""), ""]
    for cmd in data.get("commands", []):
        lines.append(cmd)
    return "\n".join(lines)


def format_crypto_testnet(data: dict[str, Any]) -> str:
    cfg = data.get("config", {})
    llm = data.get("llm_eval", {})
    return _truncate(
        f"₿ Крипто (testnet)\n\n"
        f"env: {cfg.get('env')} | mode: {cfg.get('mode')}\n"
        f"пары: {', '.join(cfg.get('pairs', []))}\n"
        f"LLM: {cfg.get('llm_model')} ({cfg.get('prompt_version')})\n"
        f"cron: {cfg.get('schedule') or '—'}\n\n"
        f"LLM eval ({data.get('days')}d): {llm.get('count', 0)} calls\n"
        f"approve rate: {llm.get('approve_rate', '—')}"
    )


def format_crypto_funnel(data: dict[str, Any]) -> str:
    funnel = data.get("funnel", {}).get("funnel", {})
    return _truncate("\n".join(_funnel_lines(funnel, f"🔄 Воронка crypto ({data.get('days')}d)")))


def format_crypto_balances(balances: list[dict[str, Any]] | dict[str, Any]) -> str:
    rows: list[dict[str, Any]]
    if isinstance(balances, dict):
        if balances.get("status") == "empty":
            return f"💰 Binance testnet\n{balances.get('message', 'Нет данных или ключи не заданы.')}"
        rows = balances.get("balances") or []
    else:
        rows = balances or []
    if not rows:
        return "💰 Binance testnet\nНет данных или ключи не заданы."
    lines = ["💰 Binance testnet"]
    for b in rows[:10]:
        lines.append(f"  {b.get('asset')}: {b.get('free', b.get('balance', '?'))}")
    return "\n".join(lines)


def format_live_status(market: str, data: dict[str, Any]) -> str:
    cfg_key = "crypto" if market == "crypto" else "securities"
    overview = data if "checks" not in data else {}
    if "checks" in data:
        checklist = data
    else:
        checklist = overview.get("checklist", {})
    return _truncate(
        f"{'₿' if market == 'crypto' else '📈'} {market.upper()} LIVE\n\n"
        f"⚠️ Реальные деньги. Kill switch должен быть OFF только осознанно.\n\n"
        + format_checklist(checklist if checklist else {"checks": {}, "ready_for_live": False})
    )


# --- MOEX sandbox (from tinvest dashboard) ---


def format_tinvest_overview(data: dict[str, Any]) -> str:
    conn = data.get("connection", {})
    auto = data.get("automation", {})
    dca = auto.get("index_dca", {})
    swing = auto.get("swing_signals", {})
    conn_icon = "✅" if conn.get("status") == "ok" else "❌"
    lines = [
        "📋 MOEX sandbox — сводка",
        f"API: {conn_icon} accounts={conn.get('accounts', '?')}",
        f"Config: {auto.get('env')} / {auto.get('mode')}",
        f"Active: {auto.get('active_mode')}",
        "",
        f"DCA: {dca.get('ticker')} {dca.get('amount_rub')} ₽",
        f"Swing LLM: {swing.get('llm_model')}",
    ]
    funnel = data.get("funnel", {}).get("funnel", {})
    if funnel:
        lines.append("")
        lines.extend(_funnel_lines(funnel, "Funnel 7d:")[1:])
    return _truncate("\n".join(lines))


def format_tinvest_account(data: dict[str, Any]) -> str:
    port = data.get("portfolio", {})
    if port.get("status") != "ok":
        return f"👤 Демо-счёт\n❌ {port.get('message') or port.get('reject_reason', 'error')}"
    lines = ["👤 T-Invest демо-счёт", f"Account: …{str(port.get('account_id', ''))[-8:]}", "Позиции:"]
    for p in port.get("positions") or []:
        lines.append(_money_line(p))
    if len(lines) == 3:
        lines.append("  (пусто)")
    return "\n".join(lines)


def format_tinvest_automation(data: dict[str, Any]) -> str:
    auto = data.get("automation", {})
    dca = auto.get("index_dca", {})
    swing = auto.get("swing_signals", {})
    return _truncate(
        f"⚙️ Автомат MOEX\n"
        f"env: {auto.get('env')} | mode: {auto.get('mode')}\n"
        f"режим: {auto.get('active_mode')}\n\n"
        f"DCA: {dca.get('ticker')} {dca.get('amount_rub')} ₽\n"
        f"cron: {dca.get('schedule_cron')}\n\n"
        f"Swing LLM: {swing.get('llm_model')}\n"
        f"prompt: {swing.get('prompt_version')}\n"
        f"universe: {', '.join(swing.get('universe', [])[:5])}\n"
        f"cron: {swing.get('schedule_cron')}"
    )


def format_tinvest_trades(data: dict[str, Any]) -> str:
    orders = data.get("orders") or []
    if not orders:
        return "💼 Сделки\nПока нет ордеров."
    lines = ["💼 Сделки MOEX"]
    for o in orders[:8]:
        extra = ""
        payload = o.get("payload_json")
        if payload:
            try:
                p = json.loads(payload) if isinstance(payload, str) else payload
                if p.get("order_id"):
                    extra = f" id={str(p.get('order_id'))[:8]}"
            except (json.JSONDecodeError, TypeError):
                pass
        notional = o.get("notional")
        amount = f" {notional:.0f}₽" if notional else ""
        lines.append(
            f"• {o.get('event_at', '')[:16]} {o.get('symbol')}{amount} {o.get('decision')}{extra}"
        )
    return _truncate("\n".join(lines))


def format_tinvest_performance(data: dict[str, Any]) -> str:
    funnel = data.get("funnel", {}).get("funnel", {})
    llm = data.get("llm_eval", {})
    lines = [f"📉 Эффективность MOEX ({data.get('days')}d)", ""]
    lines.extend(_funnel_lines(funnel, "Воронка:")[1:])
    lines.extend([
        "",
        f"LLM: {llm.get('count', 0)} calls",
        f"approve: {llm.get('approve_rate', '—')}",
        f"latency: {llm.get('avg_latency_ms', '—')} ms",
    ])
    return _truncate("\n".join(lines))
