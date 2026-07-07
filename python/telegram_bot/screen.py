"""Single editable panel per chat — less clutter in Telegram history."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

logger = logging.getLogger(__name__)

_panels: dict[int, int] = {}
_screen_keys: dict[int, str] = {}


async def show_screen(
    message: Message,
    text: str,
    reply_markup: ReplyKeyboardMarkup | InlineKeyboardMarkup | None = None,
    *,
    screen_key: str,
    inline: bool = False,
) -> int | None:
    """Show or update the bot panel; replace message when menu level changes."""
    try:
        await message.delete()
    except Exception:
        pass
    return await show_screen_chat(
        message.bot,
        message.chat.id,
        text,
        reply_markup,
        screen_key=screen_key,
        inline=inline,
    )


async def show_screen_chat(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: ReplyKeyboardMarkup | InlineKeyboardMarkup | None = None,
    *,
    screen_key: str,
    inline: bool = False,
) -> int | None:
    """Show or update the bot panel for a chat (callbacks / progress updates)."""
    prev_key = _screen_keys.get(chat_id)
    panel_id = _panels.get(chat_id)
    key_changed = prev_key != screen_key
    _screen_keys[chat_id] = screen_key

    if panel_id and not key_changed:
        try:
            await bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=panel_id,
                reply_markup=reply_markup if inline else None,
            )
            return panel_id
        except Exception as exc:
            logger.debug("edit_message_text failed: %s", exc)

    if panel_id:
        try:
            await bot.delete_message(chat_id, panel_id)
        except Exception:
            pass

    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    _panels[chat_id] = sent.message_id
    return sent.message_id


async def update_panel(bot: Bot, chat_id: int, text: str) -> None:
    """Update panel text in place (progress / long operations)."""
    panel_id = _panels.get(chat_id)
    if not panel_id:
        return
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=panel_id)
    except Exception as exc:
        logger.debug("update_panel failed: %s", exc)


def reset_panel(chat_id: int) -> None:
    _panels.pop(chat_id, None)
    _screen_keys.pop(chat_id, None)


class ScreenKey:
    MAIN = "main"
    AUTOMAT = "automat"
    KNOWLEDGE = "knowledge"
    NEWS = "news"
    SYSTEM = "system"
    CRYPTO_TEST = "crypto_test"
    MOEX_SANDBOX = "moex_sandbox"
    LIVE = "live"
    PAPER = "paper"
    BENCHMARK = "benchmark"
    BENCHMARK_RUN = "benchmark_run"
