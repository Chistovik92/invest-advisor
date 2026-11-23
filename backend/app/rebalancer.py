from typing import Dict, Any
from .config import load_yaml_config


def build_rebalance_recommendations(
    tinvest_service: Any,
    snapshot: Dict[str, Any],
    deposit_amount: float
) -> Dict[str, Any]:
    cfg = load_yaml_config()
    targets = cfg.get("portfolio_targets", {})

    class_weights = targets.get("asset_classes", {})
    stocks_cfg = targets.get("stocks", {})
    bonds_to_buy_cfg = targets.get("bonds_to_buy", [])

    rub_balance = snapshot.get("rub_balance", 0.0)
    margin_debt = snapshot.get("margin_debt", 0.0)
    available_cash = deposit_amount + (rub_balance if rub_balance > 0 else 0.0) - margin_debt

    if available_cash <= 0:
        return {
            "snapshot": snapshot,
            "deposit_amount": deposit_amount,
            "margin_debt_covered": round(deposit_amount, 2),
            "remaining_margin_debt": round(margin_debt - deposit_amount, 2),
            "orders": [],
            "unspent_cash": 0.0,
            "summary": "Вся сумма пойдёт на закрытие маржинального долга на ИИС."
        }

    pos_by_ticker = {}
    for p in snapshot.get("positions", []):
        t = p["ticker"]
        if t not in pos_by_ticker:
            pos_by_ticker[t] = dict(p)
        else:
            pos_by_ticker[t]["total_value"] += p["total_value"]

    total_iis_after = snapshot.get("total_iis_value", 0.0) + deposit_amount
    candidates = []

    stocks_share = class_weights.get("stocks", 0.55)
    for ticker, meta in stocks_cfg.items():
        target_share = stocks_share * meta["target_weight"]
        freeze = meta.get("freeze_buy", False)
        existing = pos_by_ticker.get(ticker)

        if existing and existing.get("lot_price", 0) > 0:
            cur_val = existing["total_value"]
            lot_price = existing["lot_price"]
            lot_size = existing.get("lot", 1)
            name = existing.get("name", ticker)
        else:
            info = tinvest_service.find_by_ticker(ticker)
            if not info:
                continue
            cur_val = existing["total_value"] if existing else 0.0
            lot_price = info["lot_price"]
            lot_size = info["lot"]
            name = meta.get("name", info["name"])

        candidates.append({
            "ticker": ticker,
            "name": name,
            "asset_class": "Акции ядра",
            "current_value": cur_val,
            "lot_price": lot_price,
            "lot_size": lot_size,
            "target_share": target_share,
            "freeze_buy": freeze,
        })

    for bond in bonds_to_buy_cfg:
        ticker = bond["ticker"]
        grp = bond["group"]
        target_share = class_weights.get(grp, 0.10) * bond["weight"]
        existing = pos_by_ticker.get(ticker)

        if existing and existing.get("lot_price", 0) > 0:
            cur_val = existing["total_value"]
            lot_price = existing["lot_price"]
            lot_size = existing.get("lot", 1)
            name = existing.get("name", ticker)
        else:
            info = tinvest_service.find_by_ticker(ticker)
            if not info:
                continue
            cur_val = existing["total_value"] if existing else 0.0
            lot_price = info["lot_price"]
            lot_size = info["lot"]
            name = bond.get("name", info["name"])

        candidates.append({
            "ticker": ticker,
            "name": name,
            "asset_class": "Облигации баланса",
            "current_value": cur_val,
            "lot_price": lot_price,
            "lot_size": lot_size,
            "target_share": target_share,
            "freeze_buy": False,
        })

    orders_map: Dict[str, Dict[str, Any]] = {}
    simulated_values = {c["ticker"]: c["current_value"] for c in candidates}

    while True:
        best = None
        max_deficit = 0.0

        for item in candidates:
            if item["freeze_buy"] or item["lot_price"] <= 0 or item["lot_price"] > available_cash:
                continue
            target_val = total_iis_after * item["target_share"]
            deficit = target_val - simulated_values[item["ticker"]]
            if deficit > max_deficit and deficit >= item["lot_price"] * 0.4:
                max_deficit = deficit
                best = item

        if not best:
            break

        t = best["ticker"]
        available_cash -= best["lot_price"]
        simulated_values[t] += best["lot_price"]

        if t not in orders_map:
            orders_map[t] = {
                "ticker": t,
                "name": best["name"],
                "asset_class": best["asset_class"],
                "lots_to_buy": 0,
                "shares_count": 0,
                "lot_price": best["lot_price"],
                "total_cost": 0.0,
                "current_share_pct": round((best["current_value"] / total_iis_after) * 100, 2) if total_iis_after > 0 else 0.0,
                "target_share_pct": round(best["target_share"] * 100, 2),
            }

        orders_map[t]["lots_to_buy"] += 1
        orders_map[t]["shares_count"] += best["lot_size"]
        orders_map[t]["total_cost"] = round(orders_map[t]["total_cost"] + best["lot_price"], 2)

    orders_list = sorted(orders_map.values(), key=lambda x: x["total_cost"], reverse=True)

    return {
        "snapshot": snapshot,
        "deposit_amount": deposit_amount,
        "margin_debt_covered": margin_debt,
        "remaining_margin_debt": 0.0,
        "orders": orders_list,
        "unspent_cash": round(available_cash, 2),
        "summary": f"Подобрано {len(orders_list)} позиций. Остаток кэша: {round(available_cash, 2)} ₽."
    }
