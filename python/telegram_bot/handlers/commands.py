"""Backward-compatible command aliases."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.actions import (
    send_automat_menu,
    send_kill_switch_menu,
    send_smoke_test,
    send_welcome,
)
from telegram_bot.config import is_allowed
from telegram_bot.api_client import post_json

router = Router()


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if is_allowed(message.chat.id):
        await send_automat_menu(message)


@router.message(Command("kill"))
async def cmd_kill(message: Message) -> None:
    if is_allowed(message.chat.id):
        await send_kill_switch_menu(message)


@router.message(Command("smoke"))
async def cmd_smoke(message: Message) -> None:
    if is_allowed(message.chat.id):
        await send_smoke_test(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    if is_allowed(message.chat.id):
        await send_welcome(message)


@router.message(Command("cron"))
async def cmd_cron(message: Message) -> None:
    """Set cron for an n8n workflow with a Schedule Trigger.

    Usage:
      /cron <workflow_id> <cronExpression>
    Example:
      /cron wfSecSwingDryRun 15 18 * * 1-5
    """
    if not is_allowed(message.chat.id) or not message.text:
        return
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Формат:\n"
            "`/cron <workflow_id> <cronExpression>`\n\n"
            "Пример:\n"
            "`/cron wfSecSwingDryRun 15 18 * * 1-5`"
        )
        return
    wid = parts[1].strip()
    expr = parts[2].strip()
    result = await post_json(f"/api/n8n/workflows/{wid}/cron", {"cron_expression": expr})
    if result.get("status") == "ok":
        await message.answer("✅ Cron обновлён")
    else:
        await message.answer(f"❌ {result.get('message', 'n8n error')}")
