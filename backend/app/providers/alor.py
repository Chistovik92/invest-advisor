import time
import httpx
from typing import List, Tuple, Optional
from .base import BrokerProvider
from ..models import PositionModel, ProviderHealth
from ..config import settings


class AlorProvider(BrokerProvider):
    provider_id = "alor"
    title = "Алор Брокер (Alor OpenAPI)"
    mode = "api"
    OAUTH_URL = "https://oauth.alor.ru/refresh"
    API_URL = "https://api.alor.ru/md/v2"

    def __init__(self, refresh_token: Optional[str] = None, portfolio: Optional[str] = None):
        self.refresh_token = refresh_token if refresh_token is not None else settings.alor_refresh_token
        self.portfolio = portfolio if portfolio is not None else settings.alor_portfolio

    def is_configured(self) -> bool:
        return bool(self.refresh_token and self.portfolio)

    def _get_jwt(self, client: httpx.Client) -> str:
        r = client.post(self.OAUTH_URL, params={"token": self.refresh_token})
        r.raise_for_status()
        return r.json()["AccessToken"]

    def check_connection(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                provider_id=self.provider_id,
                title=self.title,
                mode=self.mode,
                configured=False,
                connected=False,
                message="ALOR_REFRESH_TOKEN / ALOR_PORTFOLIO не заданы"
            )
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=8.0) as client:
                jwt = self._get_jwt(client)
                r = client.get(
                    f"{self.API_URL}/Clients/MOEX/{self.portfolio}/positions",
                    headers={"Authorization": f"Bearer {jwt}"}
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
                message="Подключено к Alor OpenAPI"
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
                message=f"Ошибка Alor API: {exc}"
            )

    def fetch_positions(self) -> Tuple[List[PositionModel], float, float]:
        if not self.is_configured():
            return [], 0.0, 0.0
        with httpx.Client(timeout=10.0) as client:
            jwt = self._get_jwt(client)
            r = client.get(
                f"{self.API_URL}/Clients/MOEX/{self.portfolio}/positions",
                headers={"Authorization": f"Bearer {jwt}"}
            )
            r.raise_for_status()
            items = r.json()

        positions: List[PositionModel] = []
        rub_balance = 0.0
        for item in items:
            sym = item.get("symbol", "")
            qty = float(item.get("qty", 0))
            if sym == "RUB":
                rub_balance = qty
                continue
            avg_price = float(item.get("avgPrice", 0))
            cur_val = float(item.get("volume", 0))
            cur_price = round(cur_val / qty, 2) if qty else avg_price
            pnl = round(((cur_price - avg_price) / avg_price * 100.0), 2) if avg_price > 0 else 0.0
            positions.append(
                PositionModel(
                    broker=self.provider_id,
                    ticker=sym,
                    name=sym,
                    type="share",
                    quantity=qty,
                    lot=1,
                    current_price=cur_price,
                    lot_price=cur_price,
                    total_value=round(cur_val, 2),
                    pnl_pct=pnl,
                )
            )
        return positions, round(rub_balance, 2), 0.0
