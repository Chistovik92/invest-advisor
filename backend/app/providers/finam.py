import time
import httpx
from typing import List, Tuple, Optional
from .base import BrokerProvider
from ..models import PositionModel, ProviderHealth
from ..config import settings


class FinamProvider(BrokerProvider):
    provider_id = "finam"
    title = "Финам (Finam Trade API)"
    mode = "api"
    BASE_URL = "https://trade-api.finam.ru/public/api/v1"

    def __init__(self, token: Optional[str] = None, client_id: Optional[str] = None):
        self.token = token if token is not None else settings.finam_token
        self.client_id = client_id if client_id is not None else settings.finam_client_id

    def is_configured(self) -> bool:
        return bool(self.token and self.client_id)

    def check_connection(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                provider_id=self.provider_id,
                title=self.title,
                mode=self.mode,
                configured=False,
                connected=False,
                message="FINAM_TOKEN / FINAM_CLIENT_ID не заданы"
            )
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=8.0) as client:
                r = client.get(
                    f"{self.BASE_URL}/portfolio",
                    params={"ClientId": self.client_id, "Content.IncludePositions": "true"},
                    headers={"X-Api-Key": self.token}
                )
                r.raise_for_status()
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return ProviderHealth(
                provider_id=self.provider_id,
                title=self.title,
                mode=self.mode,
                configured=True,
                connected=True,
                latency_ms=elapsed,
                message="Подключено к Finam Trade API"
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
                message=f"Ошибка Finam API: {exc}"
            )

    def fetch_positions(self) -> Tuple[List[PositionModel], float, float]:
        if not self.is_configured():
            return [], 0.0, 0.0
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"{self.BASE_URL}/portfolio",
                params={"ClientId": self.client_id, "Content.IncludePositions": "true"},
                headers={"X-Api-Key": self.token}
            )
            r.raise_for_status()
            data = r.json().get("data", {})

        positions: List[PositionModel] = []
        for pos in data.get("positions", []):
            qty = float(pos.get("balance", 0))
            price = float(pos.get("currentPrice", 0))
            val = round(qty * price, 2)
            positions.append(
                PositionModel(
                    broker=self.provider_id,
                    ticker=pos.get("securityCode", ""),
                    name=pos.get("securityCode", ""),
                    type="share",
                    quantity=qty,
                    lot=1,
                    current_price=price,
                    lot_price=price,
                    total_value=val,
                    pnl_pct=float(pos.get("unrealizedProfitPct", 0)),
                )
            )
        cash = float(data.get("equity", 0)) - sum(p.total_value for p in positions)
        return positions, round(max(0.0, cash), 2), 0.0
