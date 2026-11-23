from typing import List
from .base import BrokerProvider
from .tinvest import TInvestProvider
from .bcs import BcsProvider
from .finam import FinamProvider
from .alor import AlorProvider
from .report_import import ManualAndReportProvider
from .native_parsers import ALL_NON_REST_PLATFORMS
from ..models import ProviderHealth


def get_all_providers() -> List[BrokerProvider]:
    providers: List[BrokerProvider] = [
        TInvestProvider(),
        BcsProvider(),
        FinamProvider(),
        AlorProvider(),
    ]
    for broker_id, title in ALL_NON_REST_PLATFORMS.items():
        providers.append(ManualAndReportProvider(broker_id=broker_id, title=title))
    return providers


def check_all_providers_health() -> List[ProviderHealth]:
    return [p.check_connection() for p in get_all_providers()]
