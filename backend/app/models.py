from pydantic import BaseModel, Field
from typing import List, Optional


class PositionModel(BaseModel):
    broker: str = "tinvest"
    figi: str = ""
    ticker: str
    name: str
    type: str
    quantity: float
    lot: int = 1
    current_price: float
    lot_price: float
    total_value: float
    pnl_pct: float = 0.0
    is_exit_candidate: bool = False
    exit_target_pnl: Optional[float] = None


class ProviderHealth(BaseModel):
    provider_id: str
    title: str
    mode: str
    configured: bool
    connected: bool
    latency_ms: Optional[float] = None
    message: str


class PortfolioSnapshot(BaseModel):
    iis_account_id: str = ""
    total_iis_value: float = 0.0
    external_brokers_value: float = 0.0
    rub_balance: float = 0.0
    margin_debt: float = 0.0
    tmon_available: float = 0.0
    positions: List[PositionModel] = Field(default_factory=list)
    providers_health: List[ProviderHealth] = Field(default_factory=list)
