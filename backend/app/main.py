import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import Dict, Any

from .config import settings, load_yaml_config, save_yaml_config
from .providers.tinvest import TInvestProvider
from .providers.registry import get_all_providers, check_all_providers_health
from .providers.native_parsers import parse_any_broker_file
from .rebalancer import build_rebalance_recommendations
from .telegram_bot import bot, dp, run_scheduled_check


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_scheduled_check, "interval", minutes=30)
    scheduler.start()
    bot_task = asyncio.create_task(dp.start_polling(bot)) if bot else None
    yield
    scheduler.shutdown()
    if bot_task:
        bot_task.cancel()


app = FastAPI(title="InvestAdvisor Multi-Broker API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "providers": [p.model_dump() for p in check_all_providers_health()]
    }


@app.get("/api/portfolio")
def get_aggregated_portfolio():
    tinvest = TInvestProvider()
    iis_positions, rub_balance, tmon_cash = tinvest.fetch_positions()
    total_iis = round(sum(p.total_value for p in iis_positions) + rub_balance, 2)

    external_positions = []
    for prov in get_all_providers():
        if prov.provider_id == "tinvest" or not prov.is_configured():
            continue
        pos_list, _, _ = prov.fetch_positions()
        external_positions.extend(pos_list)

    ext_total = round(sum(p.total_value for p in external_positions), 2)
    return {
        "iis_account_id": settings.iis_account_id or "IIS-MAIN",
        "total_iis_value": total_iis,
        "external_brokers_value": ext_total,
        "rub_balance": rub_balance,
        "margin_debt": round(abs(rub_balance), 2) if rub_balance < 0 else 0.0,
        "tmon_available": tmon_cash,
        "positions": [p.model_dump() for p in (iis_positions + external_positions)],
        "providers_health": [h.model_dump() for h in check_all_providers_health()],
    }


@app.get("/api/recommend")
def get_recommendations(deposit: float = Query(15000.0, ge=0)):
    snapshot = get_aggregated_portfolio()
    return build_rebalance_recommendations(TInvestProvider(), snapshot, deposit_amount=deposit)


@app.post("/api/import-report/{broker_id}")
async def import_broker_report(broker_id: str, file: UploadFile = File(...)):
    raw_bytes = await file.read()
    parsed = parse_any_broker_file(broker_id, file.filename or "report.csv", raw_bytes)
    cfg = load_yaml_config()
    existing = [h for h in cfg.get("external_holdings", []) if h.get("broker") != broker_id]
    for p in parsed:
        existing.append({
            "broker": broker_id,
            "ticker": p.ticker,
            "name": p.name,
            "type": p.type,
            "quantity": p.quantity,
            "current_price": p.current_price,
            "pnl_pct": p.pnl_pct,
        })
    cfg["external_holdings"] = existing
    save_yaml_config(cfg)
    return {"status": "imported", "broker": broker_id, "count": len(parsed)}


@app.post("/api/quik-bridge/{broker_id}")
def receive_quik_positions(broker_id: str, items: list[dict] = Body(...)):
    cfg = load_yaml_config()
    existing = [h for h in cfg.get("external_holdings", []) if h.get("broker") != broker_id]
    for item in items:
        ticker = str(item.get("ticker", "")).upper()
        qty = float(item.get("quantity", 0))
        price = float(item.get("price", 0))
        if ticker and qty > 0:
            existing.append({
                "broker": broker_id,
                "ticker": ticker,
                "name": ticker,
                "type": "bond" if ticker.startswith(("SU", "RU000")) else "share",
                "quantity": qty,
                "current_price": price,
                "pnl_pct": 0.0,
            })
    cfg["external_holdings"] = existing
    save_yaml_config(cfg)
    return {"status": "synced", "broker": broker_id, "count": len(items)}


@app.get("/api/config")
def get_config():
    return load_yaml_config()


@app.post("/api/config")
def update_config(new_cfg: Dict[str, Any] = Body(...)):
    save_yaml_config(new_cfg)
    return {"status": "saved"}
