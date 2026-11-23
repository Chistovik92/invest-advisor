from typing import List, Tuple
from .base import BrokerProvider
from ..models import PositionModel, ProviderHealth
from ..config import load_yaml_config


class ManualAndReportProvider(BrokerProvider):
    def __init__(self, broker_id: str, title: str):
        self.provider_id = broker_id
        self.title = title
        self.mode = "manual" if broker_id == "finuslugi" else "report_import"

    def is_configured(self) -> bool:
        cfg = load_yaml_config()
        holdings = cfg.get("external_holdings", [])
        return any(h.get("broker") == self.provider_id for h in holdings)

    def check_connection(self) -> ProviderHealth:
        configured = self.is_configured()
        return ProviderHealth(
            provider_id=self.provider_id,
            title=self.title,
            mode=self.mode,
            configured=configured,
            connected=configured,
            latency_ms=0.1,
            message="Активны импортированные позиции" if configured else "Нет открытого REST API; доступен импорт отчёта / QUIK"
        )

    def fetch_positions(self) -> Tuple[List[PositionModel], float, float]:
        cfg = load_yaml_config()
        positions: List[PositionModel] = []
        for item in cfg.get("external_holdings", []):
            if item.get("broker") != self.provider_id:
                continue
            qty = float(item.get("quantity", 0))
            price = float(item.get("current_price", 0))
            positions.append(
                PositionModel(
                    broker=self.provider_id,
                    ticker=item["ticker"],
                    name=item.get("name", item["ticker"]),
                    type=item.get("type", "bond"),
                    quantity=qty,
                    lot=1,
                    current_price=price,
                    lot_price=price,
                    total_value=round(qty * price, 2),
                    pnl_pct=float(item.get("pnl_pct", 0.0)),
                )
            )
        return positions, 0.0, 0.0
