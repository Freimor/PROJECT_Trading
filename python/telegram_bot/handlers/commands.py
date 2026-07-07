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
