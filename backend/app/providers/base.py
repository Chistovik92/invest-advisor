from abc import ABC, abstractmethod
from typing import List, Tuple
from ..models import PositionModel, ProviderHealth


class BrokerProvider(ABC):
    provider_id: str = "base"
    title: str = "Base Broker"
    mode: str = "api"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def check_connection(self) -> ProviderHealth:
        ...

    @abstractmethod
    def fetch_positions(self) -> Tuple[List[PositionModel], float, float]:
        ...
