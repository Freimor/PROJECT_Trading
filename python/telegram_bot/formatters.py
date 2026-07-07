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


def format_crypto_balances(balances: list[dict[str, Any]]) -> str:
    if not balances:
        return "💰 Binance testnet\nНет данных или ключи не заданы."
    lines = ["💰 Binance testnet"]
    for b in balances[:10]:
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
