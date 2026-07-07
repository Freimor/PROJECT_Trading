"""Inline callback handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from telegram_bot.api_client import get_json, post_json
from telegram_bot.config import is_allowed
from telegram_bot.formatters import (
    format_automat_doc,
    format_news_alert_settings,
    format_restart_plan,
    format_tinvest_account,
)
from telegram_bot.keyboards import (
    inline_automat_docs,
    inline_news_alert_settings,
    inline_workflows,
    kill_confirm,
    reply_automat_menu,
    reply_main_menu,
    reply_moex_sandbox_menu,
    reply_news_menu,
    reply_system_menu,
)
from telegram_bot.screen import ScreenKey, show_screen_chat

router = Router()

@router.callback_query(F.data.startswith("wf:"))
async def workflow_callbacks(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return

    parts = (cb.data or "").split(":", 3)
    action = parts[1] if len(parts) > 1 else ""

    if action == "help":
        await cb.answer()
        await cb.message.answer(
            "✍️ Custom cron\n\n"
            "Используйте команду:\n"
            "`/cron <workflow_id> <cronExpression>`\n\n"
            "Пример:\n"
            "`/cron wfSecSwingDryRun 15 18 * * 1-5`",
            reply_markup=reply_system_menu(),
        )
        return

    if action == "toggle":
        # wf:toggle:<id>:on|off
        _, _, wid, state = (cb.data or "").split(":", 3)
        endpoint = f"/api/n8n/workflows/{wid}/activate" if state == "on" else f"/api/n8n/workflows/{wid}/deactivate"
        result = await post_json(endpoint, {})
        if result.get("status") != "ok":
            await cb.answer(result.get("message", "n8n error"), show_alert=True)
            return
        data = await get_json("/api/n8n/workflows")
        workflows = (data.get("workflows") if data.get("status") == "ok" else []) or []
        await cb.message.edit_text("🧩 Workflows", reply_markup=inline_workflows(workflows))
        await cb.answer("Обновлено")
        return

    if action == "cron":
        # wf:cron:<id>:<expr>
        _, _, wid, expr = (cb.data or "").split(":", 3)
        result = await post_json(f"/api/n8n/workflows/{wid}/cron", {"cron_expression": expr})
        if result.get("status") != "ok":
            await cb.answer(result.get("message", "cron error"), show_alert=True)
            return
        await cb.answer("Cron обновлён")
        return

    await cb.answer()


@router.callback_query(F.data.startswith("kill:ask:"))
async def kill_ask(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return
    state = cb.data.split(":")[-1]
    enabled = state == "on"
    label = "включить 🔴" if enabled else "выключить 🟢"
    await cb.message.edit_text(
        f"Подтвердите: {label} kill switch?",
        reply_markup=kill_confirm(enabled),
    )
    await cb.answer()


@router.callback_query(F.data == "kill:cancel")
async def kill_cancel(cb: CallbackQuery) -> None:
    if cb.message:
        await show_screen_chat(
            cb.message.bot,
            cb.message.chat.id,
            "Отменено.",
            reply_markup=reply_main_menu(),
            screen_key=ScreenKey.MAIN,
        )
    await cb.answer()


@router.callback_query(F.data.startswith("kill:confirm:"))
async def kill_confirm_cb(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return
    state = cb.data.split(":")[-1]
    enabled = state == "on"
    operator = f"telegram:{cb.from_user.id}"
    result = await post_json(
        "/api/admin/kill-switch",
        {"enabled": enabled, "operator": operator, "source": "telegram"},
    )
    icon = "🔴" if result.get("kill_switch") else "🟢"
    await show_screen_chat(
        cb.message.bot,
        cb.message.chat.id,
        f"{icon} Kill switch обновлён",
        reply_markup=reply_main_menu(),
        screen_key=ScreenKey.MAIN,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("conf:"))
async def confirmation_resolve(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return
    _, conf_id, decision = cb.data.split(":", 2)
    operator = f"telegram:{cb.from_user.id}"
    result = await post_json(
        f"/api/admin/confirmations/{conf_id}/resolve",
        {"decision": decision, "operator": operator},
    )
    await cb.message.edit_text(f"Результат: {result.get('status')} / {decision}")
    await cb.answer()


@router.callback_query(F.data == "restart:cancel")
async def restart_cancel(cb: CallbackQuery) -> None:
    if cb.message:
        await show_screen_chat(
            cb.message.bot,
            cb.message.chat.id,
            "Отменено.",
            reply_markup=reply_system_menu(),
            screen_key=ScreenKey.SYSTEM,
        )
    await cb.answer()


@router.callback_query(F.data == "restart:confirm")
async def restart_confirm_cb(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return
    plan = await post_json(
        "/api/admin/services/restart-plan",
        {"services": ["db-api", "telegram-bot", "n8n"]},
    )
    await show_screen_chat(
        cb.message.bot,
        cb.message.chat.id,
        format_restart_plan(plan),
        reply_markup=reply_system_menu(),
        screen_key=ScreenKey.SYSTEM,
    )
    await cb.answer()


@router.callback_query(F.data == "tinvest:dca:cancel")
async def tinvest_dca_cancel(cb: CallbackQuery) -> None:
    if cb.message:
        await show_screen_chat(
            cb.message.bot,
            cb.message.chat.id,
            "DCA тест отменён.",
            reply_markup=reply_moex_sandbox_menu(),
            screen_key=ScreenKey.MOEX_SANDBOX,
        )
    await cb.answer()


@router.callback_query(F.data == "tinvest:dca:confirm")
async def tinvest_dca_confirm(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return
    await cb.message.edit_text("⏳ Отправляю sandbox DCA…")
    result = await post_json("/api/securities/dca?dry_run=false&env=paper")
    order = result.get("order", {})
    if order.get("status") == "submitted":
        text = (
            f"✅ Ордер отправлен\n"
            f"Ticker: {order.get('ticker')}\n"
            f"Lots: {order.get('lots')}\n"
            f"Order ID: {order.get('order_id', '—')}"
        )
    elif order.get("status") == "error":
        text = f"❌ {order.get('reject_reason')}: {order.get('message', '')}"
    else:
        text = f"Результат: {result}"
    dashboard = await get_json("/api/testing/tinvest-sandbox?days=7")
    account = format_tinvest_account(dashboard)
    await show_screen_chat(
        cb.message.bot,
        cb.message.chat.id,
        f"{text}\n\n{account}",
        reply_markup=reply_moex_sandbox_menu(),
        screen_key=ScreenKey.MOEX_SANDBOX,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("autodoc:"))
async def automat_docs_nav(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return
    section = cb.data.split(":", 1)[1]
    data = await get_json(f"/api/automation/docs?section={section}")
    sections = data.get("sections") or []
    await cb.message.edit_text(
        format_automat_doc(data),
        reply_markup=inline_automat_docs(section, sections),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("newsalert:"))
async def news_alert_callbacks(cb: CallbackQuery) -> None:
    if not cb.message or not is_allowed(cb.message.chat.id):
        await cb.answer("Access denied", show_alert=True)
        return
    parts = cb.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    target = parts[2] if len(parts) > 2 else ""
    operator = f"telegram:{cb.from_user.id}"

    if action == "process":
        chat_id = cb.message.chat.id
        bot = cb.message.bot
        await show_screen_chat(
            bot,
            chat_id,
            "⏳ Проверяю новости и LLM…",
            reply_markup=reply_news_menu(),
            screen_key=ScreenKey.NEWS,
        )
        result = await post_json("/api/news/alerts/process?limit=3", {})
        await show_screen_chat(
            bot,
            chat_id,
            f"🔔 Алерты\n\n"
            f"Отправлено: {result.get('sent', 0)}, "
            f"проанализировано: {result.get('analyzed', 0)}",
            reply_markup=reply_news_menu(),
            screen_key=ScreenKey.NEWS,
        )
        await cb.answer()
        return

    if action == "toggle" and target in ("news", "trades"):
        data = await get_json("/api/news/alerts/settings")
        if target == "news":
            cur = data.get("news_digest", {}).get("enabled", True)
            body = {"news_enabled": not cur, "operator": operator}
        else:
            cur = data.get("trade_alerts", {}).get("enabled", True)
            body = {"trade_enabled": not cur, "operator": operator}
        updated = await post_json("/api/news/alerts/settings", body)
        news_on = updated.get("news_digest", {}).get("enabled", True)
        trades_on = updated.get("trade_alerts", {}).get("enabled", True)
        await cb.message.edit_text(
            format_news_alert_settings(updated),
            reply_markup=inline_news_alert_settings(news_on, trades_on),
        )
        await cb.answer("Обновлено")
        return

    await cb.answer()
