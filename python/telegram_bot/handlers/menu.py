"""Menu handlers — hierarchical reply keyboard."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from telegram_bot.actions import (
    send_automat_docs,
    send_automat_events,
    send_automat_menu,
    send_confirmations,
    send_crypto_balance,
    send_crypto_events,
    send_crypto_funnel,
    send_crypto_live_menu,
    send_crypto_overview,
    send_crypto_test_menu,
    send_host_status,
    send_kill_switch_menu,
    send_knowledge_menu,
    send_live_checklist,
    send_live_status_detail,
    send_moex_account,
    send_moex_automation,
    send_moex_dca_prompt,
    send_moex_live_menu,
    send_moex_overview,
    send_moex_performance,
    send_moex_sandbox_menu,
    send_moex_trades,
    send_news_alert_settings,
    send_news_ingest,
    send_news_latest,
    send_news_menu,
    send_news_sources,
    send_news_trades_toggle_info,
    send_restart_prompt,
    send_smoke_test,
    send_system_menu,
    send_system_summary,
    send_welcome,
    send_wiki,
)
from telegram_bot.config import is_allowed
from telegram_bot.keyboards import (
    AUTOMAT_BUTTONS,
    BTN_AUTOMAT,
    BTN_AUTOMAT_DOCS,
    BTN_BACK_AUTOMAT,
    BTN_BACK_MAIN,
    BTN_CONFIRM,
    BTN_CR_BALANCE,
    BTN_CR_EVENTS,
    BTN_CR_FUNNEL,
    BTN_CR_OVERVIEW,
    BTN_CRYPTO_LIVE,
    BTN_CRYPTO_TEST,
    BTN_EVENTS,
    BTN_HOST_STATUS,
    BTN_KILL,
    BTN_KNOWLEDGE,
    BTN_LIVE_CHECKLIST,
    BTN_LIVE_STATUS,
    BTN_MOEX_LIVE,
    BTN_MOEX_SANDBOX,
    BTN_MX_ACCOUNT,
    BTN_MX_AUTO,
    BTN_MX_DCA,
    BTN_MX_OVERVIEW,
    BTN_MX_PERF,
    BTN_MX_TRADES,
    BTN_NEWS,
    BTN_NEWS_ALERTS,
    BTN_NEWS_INGEST,
    BTN_NEWS_LATEST,
    BTN_NEWS_SOURCES,
    BTN_NEWS_TRADES,
    BTN_RESTART,
    BTN_SMOKE,
    BTN_SYS_SUMMARY,
    BTN_SYSTEM,
    BTN_WIKI,
    CRYPTO_TEST_BUTTONS,
    KNOWLEDGE_BUTTONS,
    LIVE_BUTTONS,
    MAIN_BUTTONS,
    MOEX_SANDBOX_BUTTONS,
    NEWS_BUTTONS,
    SYSTEM_BUTTONS,
)

router = Router()


@router.message(CommandStart())
@router.message(Command("help"))
async def on_start(message: Message) -> None:
    if is_allowed(message.chat.id):
        await send_welcome(message)


@router.message(F.text.in_(MAIN_BUTTONS))
async def on_main(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    text = message.text
    if text == BTN_AUTOMAT:
        await send_automat_menu(message)
    elif text == BTN_KNOWLEDGE:
        await send_knowledge_menu(message)
    elif text == BTN_NEWS:
        await send_news_menu(message)
    elif text == BTN_SYSTEM:
        await send_system_menu(message)
    elif text == BTN_KILL:
        await send_kill_switch_menu(message)


@router.message(F.text.in_(AUTOMAT_BUTTONS))
async def on_automat(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    text = message.text
    if text == BTN_BACK_MAIN:
        await send_welcome(message)
    elif text == BTN_CRYPTO_TEST:
        await send_crypto_test_menu(message)
    elif text == BTN_MOEX_SANDBOX:
        await send_moex_sandbox_menu(message)
    elif text == BTN_CRYPTO_LIVE:
        await send_crypto_live_menu(message)
    elif text == BTN_MOEX_LIVE:
        await send_moex_live_menu(message)
    elif text == BTN_CONFIRM:
        await send_confirmations(message)
    elif text == BTN_EVENTS:
        await send_automat_events(message)
    elif text == BTN_AUTOMAT_DOCS:
        await send_automat_docs(message)


@router.message(F.text.in_(KNOWLEDGE_BUTTONS))
async def on_knowledge(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    if message.text == BTN_BACK_MAIN:
        await send_welcome(message)
    elif message.text == BTN_WIKI:
        await send_wiki(message)
    elif message.text == BTN_SYS_SUMMARY:
        await send_system_summary(message)


@router.message(F.text.in_(NEWS_BUTTONS))
async def on_news(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    if message.text == BTN_BACK_MAIN:
        await send_welcome(message)
    elif message.text == BTN_NEWS_LATEST:
        await send_news_latest(message)
    elif message.text == BTN_NEWS_SOURCES:
        await send_news_sources(message)
    elif message.text == BTN_NEWS_INGEST:
        await send_news_ingest(message)
    elif message.text == BTN_NEWS_ALERTS:
        await send_news_alert_settings(message)
    elif message.text == BTN_NEWS_TRADES:
        await send_news_trades_toggle_info(message)


@router.message(F.text.in_(SYSTEM_BUTTONS))
async def on_system(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    if message.text == BTN_BACK_MAIN:
        await send_welcome(message)
    elif message.text == BTN_HOST_STATUS:
        await send_host_status(message)
    elif message.text == BTN_SMOKE:
        await send_smoke_test(message)
    elif message.text == BTN_RESTART:
        await send_restart_prompt(message)


@router.message(F.text.in_(CRYPTO_TEST_BUTTONS))
async def on_crypto_test(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    if message.text == BTN_BACK_AUTOMAT:
        await send_automat_menu(message)
    elif message.text == BTN_CR_OVERVIEW:
        await send_crypto_overview(message)
    elif message.text == BTN_CR_FUNNEL:
        await send_crypto_funnel(message)
    elif message.text == BTN_CR_EVENTS:
        await send_crypto_events(message)
    elif message.text == BTN_CR_BALANCE:
        await send_crypto_balance(message)


@router.message(F.text.in_(MOEX_SANDBOX_BUTTONS))
async def on_moex_sandbox(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    if message.text == BTN_BACK_AUTOMAT:
        await send_automat_menu(message)
    elif message.text == BTN_MX_OVERVIEW:
        await send_moex_overview(message)
    elif message.text == BTN_MX_ACCOUNT:
        await send_moex_account(message)
    elif message.text == BTN_MX_AUTO:
        await send_moex_automation(message)
    elif message.text == BTN_MX_TRADES:
        await send_moex_trades(message)
    elif message.text == BTN_MX_PERF:
        await send_moex_performance(message)
    elif message.text == BTN_MX_DCA:
        await send_moex_dca_prompt(message)


@router.message(F.text.in_(LIVE_BUTTONS))
async def on_live(message: Message) -> None:
    if not message.text or not is_allowed(message.chat.id):
        return
    if message.text == BTN_BACK_AUTOMAT:
        await send_automat_menu(message)
    elif message.text == BTN_LIVE_CHECKLIST:
        await send_live_checklist(message)
    elif message.text == BTN_LIVE_STATUS:
        await send_live_status_detail(message)
