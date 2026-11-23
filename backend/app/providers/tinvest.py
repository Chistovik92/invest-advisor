import time
import logging
from typing import Dict, List, Tuple, Any, Optional
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tinkoff.invest import Client, InstrumentIdType
from tinkoff.invest.exceptions import RequestError
from tinkoff.invest.utils import quotation_to_decimal

from .base import BrokerProvider
from ..models import PositionModel, ProviderHealth
from ..config import settings, load_yaml_config

logger = logging.getLogger(__name__)
_INSTRUMENT_CACHE: TTLCache = TTLCache(maxsize=1024, ttl=21600)


def _money_to_float(money_val) -> float:
    if not money_val:
        return 0.0
    return float(money_val.units) + float(money_val.nano) / 1e9


class TInvestProvider(BrokerProvider):
    provider_id = "tinvest"
    title = "Т-Инвестиции (T-Invest API)"
    mode = "api"

    def __init__(self, token: Optional[str] = None):
        self.token = token if token is not None else settings.tinvest_token

    def is_configured(self) -> bool:
        return bool(self.token and len(self.token.strip()) > 10)

    def check_connection(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                provider_id=self.provider_id,
                title=self.title,
                mode=self.mode,
                configured=False,
                connected=False,
                message="Токен TINVEST_TOKEN не задан в .env"
            )
        start = time.perf_counter()
        try:
            with Client(self.token) as client:
                accs = client.users.get_accounts().accounts
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return ProviderHealth(
                provider_id=self.provider_id,
                title=self.title,
                mode=self.mode,
                configured=True,
                connected=True,
                latency_ms=elapsed,
                message=f"Подключено (найдено счетов: {len(accs)})"
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return ProviderHealth(
                provider_id=self.provider_id,
                title=self.title,
                mode=self.mode,
                configured=True,
                connected=False,
                latency_ms=elapsed,
                message=f"Ошибка API: {exc}"
            )

    def _resolve_instrument(self, client: Client, figi: str) -> Dict[str, Any]:
        if figi in _INSTRUMENT_CACHE:
            return _INSTRUMENT_CACHE[figi]
        try:
            inst = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=figi
            ).instrument
            info = {
                "figi": inst.figi,
                "ticker": inst.ticker,
                "name": inst.name,
                "lot": max(1, int(inst.lot)),
                "instrument_type": inst.instrument_type,
            }
            _INSTRUMENT_CACHE[figi] = info
            return info
        except Exception:
            return {"figi": figi, "ticker": figi, "name": figi, "lot": 1, "instrument_type": "unknown"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(RequestError),
        reraise=True,
    )
    def find_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        if not self.is_configured():
            return None
        with Client(self.token) as client:
            found = client.instruments.find_instrument(query=ticker).instruments
            for item in found:
                if item.ticker.upper() == ticker.upper() and item.class_code in ("TQBR", "TQOB", "TQCB", "TQTF"):
                    prices = client.market_data.get_last_prices(figi=[item.figi]).last_prices
                    last_price = float(quotation_to_decimal(prices[0].price)) if prices else 0.0
                    if item.instrument_type == "bond":
                        bond_info = client.instruments.bond_by(
                            id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=item.figi
                        ).instrument
                        nominal = _money_to_float(bond_info.nominal)
                        last_price = (last_price / 100.0) * nominal
                    lot = max(1, int(item.lot))
                    return {
                        "figi": item.figi,
                        "ticker": item.ticker,
                        "name": item.name,
                        "lot": lot,
                        "price": round(last_price, 2),
                        "lot_price": round(last_price * lot, 2),
                        "instrument_type": item.instrument_type,
                    }
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(RequestError),
        reraise=True,
    )
    def fetch_positions(self) -> Tuple[List[PositionModel], float, float]:
        if not self.is_configured():
            return [], 0.0, 0.0

        cfg = load_yaml_config()
        exit_map = {
            item["ticker"]: item["target_pnl_pct"]
            for item in cfg.get("portfolio_targets", {}).get("exit_candidates", [])
        }

        with Client(self.token) as client:
            accounts = client.users.get_accounts().accounts
            iis_id = settings.iis_account_id
            if not iis_id:
                for a in accounts:
                    if "IIS" in a.type.name:
                        iis_id = a.id
                        break
            if not iis_id and accounts:
                iis_id = accounts[0].id

            iis_portfolio = client.operations.get_portfolio(account_id=iis_id)
            rub_balance = 0.0
            positions: List[PositionModel] = []

            for pos in iis_portfolio.positions:
                inst = self._resolve_instrument(client, pos.figi)
                qty = float(quotation_to_decimal(pos.quantity))
                cur_price = _money_to_float(pos.current_price)
                avg_price = _money_to_float(pos.average_position_price)
                total_val = round(qty * cur_price, 2)

                if inst["instrument_type"] == "currency" and inst["ticker"].startswith("RUB"):
                    rub_balance = total_val
                    continue

                pnl_pct = round(((cur_price - avg_price) / avg_price * 100.0), 2) if avg_price > 0 else 0.0
                positions.append(
                    PositionModel(
                        broker=self.provider_id,
                        figi=pos.figi,
                        ticker=inst["ticker"],
                        name=inst["name"],
                        type=inst["instrument_type"],
                        quantity=qty,
                        lot=inst["lot"],
                        current_price=round(cur_price, 2),
                        lot_price=round(cur_price * inst["lot"], 2),
                        total_value=total_val,
                        pnl_pct=pnl_pct,
                        is_exit_candidate=inst["ticker"] in exit_map,
                        exit_target_pnl=exit_map.get(inst["ticker"]),
                    )
                )

            tmon_cash = 0.0
            for acc in accounts:
                if acc.id == iis_id:
                    continue
                if settings.tmon_account_id and acc.id != settings.tmon_account_id:
                    continue
                try:
                    p = client.operations.get_portfolio(account_id=acc.id)
                    for pos in p.positions:
                        inst = self._resolve_instrument(client, pos.figi)
                        if inst["ticker"] in ("TMON", "RUB000UTSTOM"):
                            qty = float(quotation_to_decimal(pos.quantity))
                            cur_price = _money_to_float(pos.current_price)
                            tmon_cash += qty * cur_price
                except Exception:
                    continue

            return positions, round(rub_balance, 2), round(tmon_cash, 2)
