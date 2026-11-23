import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from .config import settings
from .providers.tinvest import TInvestProvider
from .rebalancer import build_rebalance_recommendations

logger = logging.getLogger(__name__)
bot = Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None
dp = Dispatcher()


def _quick_snapshot() -> dict:
    tinvest = TInvestProvider()
    pos_list, rub_balance, tmon_cash = tinvest.fetch_positions()
    total_iis = round(sum(p.total_value for p in pos_list) + rub_balance, 2)
    return {
        "total_iis_value": total_iis,
        "rub_balance": rub_balance,
        "margin_debt": round(abs(rub_balance), 2) if rub_balance < 0 else 0.0,
        "tmon_available": tmon_cash,
        "positions": [p.model_dump() for p in pos_list],
    }


@dp.message(Command("start", "help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📊 <b>InvestAdvisor — помощник ребалансировки ИИС</b>\n\n"
        "• /status — сводка по ИИС, марже и TMON\n"
        "• /buy 15000 — расчёт точных лотов к покупке\n"
        "• /tails — проверка «хвостов» на выход",
        parse_mode="HTML",
    )


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    snap = _quick_snapshot()
    margin_line = (
        f"⚠️ <b>Маржинальный долг:</b> −{snap['margin_debt']} ₽"
        if snap["margin_debt"] > 0
        else "✅ Маржинального долга нет"
    )
    await message.answer(
        f"💼 <b>ИИС:</b> {snap['total_iis_value']:,.2f} ₽\n"
        f"💵 <b>Подушка TMON:</b> {snap['tmon_available']:,.2f} ₽\n"
        f"{margin_line}",
        parse_mode="HTML",
    )


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    parts = message.text.split()
    amount = float(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 15000.0
    snap = _quick_snapshot()
    plan = build_rebalance_recommendations(TInvestProvider(), snap, deposit_amount=amount)

    lines = [f"🛒 <b>План покупок на {amount:,.0f} ₽:</b>\n"]
    if plan["margin_debt_covered"] > 0:
        lines.append(f"1️⃣ Погашение маржи: <b>{plan['margin_debt_covered']:,.2f} ₽</b>\n")
    for idx, order in enumerate(plan["orders"], start=1):
        lines.append(
            f"{idx}. <b>{order['name']}</b> (<code>{order['ticker']}</code>): "
            f"<b>{order['lots_to_buy']} лот.</b> ({order['shares_count']} шт.) ≈ {order['total_cost']:,.2f} ₽"
        )
    lines.append(f"\n💰 Остаток: <b>{plan['unspent_cash']:,.2f} ₽</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("tails"))
async def cmd_tails(message: types.Message):
    snap = _quick_snapshot()
    tails = [p for p in snap["positions"] if p["is_exit_candidate"]]
    if not tails:
        await message.answer("Хвостов на выход не найдено.")
        return
    lines = ["🧹 <b>Статус «хвостов»:</b>\n"]
    for t in tails:
        ready = "✅ ГОТОВО" if t["pnl_pct"] >= (t["exit_target_pnl"] or 0.0) else "⏳ ждём"
        lines.append(f"• <b>{t['ticker']}</b>: PnL <b>{t['pnl_pct']:+.2f}%</b> — {ready}")
    await message.answer("\n".join(lines), parse_mode="HTML")


async def run_scheduled_check():
    if not bot or not settings.telegram_chat_id:
        return
    try:
        snap = _quick_snapshot()
        ready = [p for p in snap["positions"] if p["is_exit_candidate"] and p["pnl_pct"] >= (p["exit_target_pnl"] or 0.0)]
        if ready:
            tickers = ", ".join(f"{t['ticker']} ({t['pnl_pct']:+.1f}%)" for t in ready)
            await bot.send_message(settings.telegram_chat_id, f"🔔 <b>Сигнал на выход из хвостов:</b> {tickers}", parse_mode="HTML")
    except Exception as exc:
        logger.error("Ошибка проверки: %s", exc)
