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
    kill_confirm,
    reply_automat_menu,
    reply_main_menu,
    reply_moex_sandbox_menu,
    reply_news_menu,
    reply_system_menu,
)

router = Router()


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
        await cb.message.edit_text("Отменено.")
        await cb.message.answer("Главное меню:", reply_markup=reply_main_menu())
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
    await cb.message.edit_text(f"{icon} Kill switch обновлён")
    await cb.message.answer("Главное меню:", reply_markup=reply_main_menu())
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
        await cb.message.edit_text("Отменено.")
        await cb.message.answer("Управление:", reply_markup=reply_system_menu())
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
    await cb.message.edit_text("Команды перезапуска:")
    await cb.message.answer(format_restart_plan(plan), reply_markup=reply_system_menu())
    await cb.answer()


@router.callback_query(F.data == "tinvest:dca:cancel")
async def tinvest_dca_cancel(cb: CallbackQuery) -> None:
    if cb.message:
        await cb.message.edit_text("DCA тест отменён.")
        await cb.message.answer("MOEX sandbox:", reply_markup=reply_moex_sandbox_menu())
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
    await cb.message.answer(text, reply_markup=reply_moex_sandbox_menu())
    dashboard = await get_json("/api/testing/tinvest-sandbox?days=7")
    await cb.message.answer(format_tinvest_account(dashboard), reply_markup=reply_moex_sandbox_menu())
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
        await cb.message.answer("⏳ Проверяю новости и LLM…")
        result = await post_json("/api/news/alerts/process?limit=3", {})
        await cb.message.answer(
            f"Готово: отправлено {result.get('sent', 0)}, "
            f"проанализировано {result.get('analyzed', 0)}",
            reply_markup=reply_news_menu(),
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
