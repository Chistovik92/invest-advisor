import time
import httpx
from typing import List, Tuple, Optional
from .base import BrokerProvider
from ..models import PositionModel, ProviderHealth
from ..config import settings


class BcsProvider(BrokerProvider):
    provider_id = "bcs"
    title = "БКС Мир Инвестиций (BCS Trade API)"
    mode = "api"
    AUTH_URL = "https://be.broker.ru/trade-api-keycloak/realms/tradeapi/protocol/openid-connect/token"
    PORTFOLIO_URL = "https://be.broker.ru/trade-api-portfolio/api/v1/portfolio"

    def __init__(self, refresh_token: Optional[str] = None):
        self.refresh_token = refresh_token if refresh_token is not None else settings.bcs_refresh_token

    def is_configured(self) -> bool:
        return bool(self.refresh_token and len(self.refresh_token.strip()) > 10)

    def _get_access_token(self, client: httpx.Client) -> str:
        r = client.post(
            self.AUTH_URL,
            data={
                "client_id": "trade-api-read",
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        r.raise_for_status()
        return r.json()["access_token"]

    def check_connection(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                provider_id=self.provider_id,
                title=self.title,
                mode=self.mode,
                configured=False,
                connected=False,
                message="BCS_REFRESH_TOKEN не задан в .env",
            )
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=8.0) as client:
                token = self._get_access_token(client)
                r = client.get(
                    self.PORTFOLIO_URL,
                    headers={"Authorization": f"Bearer {token}"},
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
                message="Подключено к БКС Trade API",
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
                message=f"Ошибка БКС API: {exc}",
            )

    def fetch_positions(self) -> Tuple[List[PositionModel], float, float]:
        if not self.is_configured():
            return [], 0.0, 0.0
        with httpx.Client(timeout=10.0) as client:
            token = self._get_access_token(client)
            r = client.get(
                self.PORTFOLIO_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            items = r.json()

        positions: List[PositionModel] = []
        rub_balance = 0.0
        for item in items:
            ticker = item.get("ticker", "")
            qty = float(item.get("quantity", 0))
            if ticker == "RUB":
                rub_balance += qty
                continue
            cur_price = float(item.get("currentPrice", 0))
            bal_price = float(item.get("balancePrice", cur_price))
            pnl = round(((cur_price - bal_price) / bal_price * 100.0), 2) if bal_price > 0 else 0.0
            positions.append(
                PositionModel(
                    broker=self.provider_id,
                    ticker=ticker,
                    name=item.get("displayName", ticker),
                    type=item.get("instrumentType", "share").lower(),
                    quantity=qty,
                    lot=1,
                    current_price=round(cur_price, 2),
                    lot_price=round(cur_price, 2),
                    total_value=round(qty * cur_price, 2),
                    pnl_pct=pnl,
                )
            )
        return positions, round(rub_balance, 2), 0.0
