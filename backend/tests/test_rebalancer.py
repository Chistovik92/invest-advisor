from app.rebalancer import build_rebalance_recommendations


class FakeTInvest:
    def find_by_ticker(self, ticker: str):
        catalog = {
            "SBER": {"figi": "1", "ticker": "SBER", "name": "Сбербанк", "lot": 10, "price": 290.0, "lot_price": 2900.0, "instrument_type": "share"},
            "MDMG": {"figi": "2", "ticker": "MDMG", "name": "Мать и дитя", "lot": 1, "price": 1250.0, "lot_price": 1250.0, "instrument_type": "share"},
            "X5":   {"figi": "3", "ticker": "X5", "name": "ИКС 5", "lot": 1, "price": 2270.0, "lot_price": 2270.0, "instrument_type": "share"},
            "YDEX": {"figi": "4", "ticker": "YDEX", "name": "Яндекс", "lot": 1, "price": 3260.0, "lot_price": 3260.0, "instrument_type": "share"},
            "T":    {"figi": "5", "ticker": "T", "name": "Т-Технологии", "lot": 1, "price": 276.0, "lot_price": 276.0, "instrument_type": "share"},
            "TATN": {"figi": "6", "ticker": "TATN", "name": "Татнефть", "lot": 1, "price": 557.0, "lot_price": 557.0, "instrument_type": "share"},
            "PRMD": {"figi": "7", "ticker": "PRMD", "name": "Промомед", "lot": 1, "price": 433.0, "lot_price": 433.0, "instrument_type": "share"},
            "OZPH": {"figi": "8", "ticker": "OZPH", "name": "Озон Фарма", "lot": 10, "price": 47.0, "lot_price": 470.0, "instrument_type": "share"},
            "MOEX": {"figi": "9", "ticker": "MOEX", "name": "МосБиржа", "lot": 10, "price": 165.0, "lot_price": 1650.0, "instrument_type": "share"},
            "SU26236RMFS8": {"figi": "10", "ticker": "SU26236RMFS8", "name": "ОФЗ 26236", "lot": 1, "price": 750.0, "lot_price": 750.0, "instrument_type": "bond"},
            "SU29025RMFS2": {"figi": "11", "ticker": "SU29025RMFS2", "name": "ОФЗ 29025", "lot": 1, "price": 980.0, "lot_price": 980.0, "instrument_type": "bond"},
            "RU000A105A04": {"figi": "12", "ticker": "RU000A105A04", "name": "Валютная обл.", "lot": 1, "price": 1000.0, "lot_price": 1000.0, "instrument_type": "bond"},
        }
        return catalog.get(ticker)


def test_margin_debt_covered_first():
    snapshot = {
        "total_iis_value": 259000.0,
        "rub_balance": -2848.31,
        "margin_debt": 2848.31,
        "tmon_available": 150000.0,
        "positions": [
            {"ticker": "T", "name": "Т-Технологии", "total_value": 37260.0, "lot_price": 276.0, "lot": 1}
        ]
    }
    res = build_rebalance_recommendations(FakeTInvest(), snapshot, deposit_amount=15000.0)
    assert res["margin_debt_covered"] == 2848.31
    assert res["remaining_margin_debt"] == 0.0
    tickers = [o["ticker"] for o in res["orders"]]
    # T заморожена от покупок из-за перевеса
    assert "T" not in tickers
    total_spent = sum(o["total_cost"] for o in res["orders"])
    assert round(total_spent + res["margin_debt_covered"] + res["unspent_cash"], 2) == 15000.0


def test_deposit_less_than_margin_debt():
    snapshot = {
        "total_iis_value": 259000.0,
        "rub_balance": -2848.31,
        "margin_debt": 2848.31,
        "tmon_available": 150000.0,
        "positions": []
    }
    res = build_rebalance_recommendations(FakeTInvest(), snapshot, deposit_amount=2000.0)
    assert res["orders"] == []
    assert res["remaining_margin_debt"] == 848.31
