"""Telegram bot entrypoint with proxy failover."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand

from telegram_bot.config import bot_token
from telegram_bot.handlers import callbacks, commands, menu
from telegram_bot.api_client import get_json, post_json
from telegram_proxy import load_proxy_candidates, mark_proxy_failed, select_working_proxy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_RETRY_SEC = 15


def _build_session(proxy: str | None) -> AiohttpSession:
    if proxy:
        return AiohttpSession(proxy=proxy)
    return AiohttpSession()


async def main() -> None:
    token = bot_token()
    dp = Dispatcher()
    dp.include_router(menu.router)
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)

    async def _alert_poll_loop() -> None:
        while True:
            try:
                settings = await get_json("/api/news/alerts/settings")
                interval = int(settings.get("news_digest", {}).get("poll_interval_sec", 300))
                if settings.get("news_digest", {}).get("enabled", True):
                    await post_json("/api/news/alerts/process?limit=3", {})
            except Exception as exc:
                logger.warning("News alert poll failed: %s", exc)
            try:
                settings = await get_json("/api/news/alerts/settings")
                interval = int(settings.get("news_digest", {}).get("poll_interval_sec", 300))
            except Exception:
                interval = 300
            await asyncio.sleep(max(60, interval))

    poll_task = asyncio.create_task(_alert_poll_loop())

    current_proxy: str | None = None
    while True:
        try:
            proxy = await asyncio.to_thread(select_working_proxy, force=current_proxy is not None, bot_token=token)
            if load_proxy_candidates() and proxy is None:
                logger.error("No working Telegram proxy among candidates, retry in %ss", _RETRY_SEC)
                await asyncio.sleep(_RETRY_SEC)
                continue
            if proxy != current_proxy:
                current_proxy = proxy
                logger.info("Bot session proxy: %s", proxy or "direct")

            session = _build_session(proxy)
            bot = Bot(token=token, session=session)
            try:
                await bot.set_my_commands([BotCommand(command="start", description="Открыть меню")])
                await dp.start_polling(bot, handle_signals=False)
            finally:
                await bot.session.close()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Polling failed: %s", exc)
            mark_proxy_failed(current_proxy)
            current_proxy = None
            await asyncio.sleep(_RETRY_SEC)


if __name__ == "__main__":
    asyncio.run(main())
