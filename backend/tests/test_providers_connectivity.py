import os
import pytest
import respx
import httpx
from app.providers.tinvest import TInvestProvider
from app.providers.finam import FinamProvider
from app.providers.alor import AlorProvider


@respx.mock
def test_finam_api_connectivity_mock():
    respx.get("https://trade-api.finam.ru/public/api/v1/portfolio").mock(
        return_value=httpx.Response(200, json={"data": {"positions": [], "equity": 10000}})
    )
    provider = FinamProvider(token="test_finam_token", client_id="12345")
    status = provider.check_connection()
    assert status.connected is True


@respx.mock
def test_alor_api_connectivity_mock():
    respx.post("https://oauth.alor.ru/refresh").mock(
        return_value=httpx.Response(200, json={"AccessToken": "jwt_token"})
    )
    respx.get("https://api.alor.ru/md/v2/Clients/MOEX/D12345/positions").mock(
        return_value=httpx.Response(200, json=[{"symbol": "RUB", "qty": 5000}])
    )
    provider = AlorProvider(refresh_token="ref_tok", portfolio="D12345")
    status = provider.check_connection()
    assert status.connected is True


@pytest.mark.skipif(not os.getenv("TINVEST_TOKEN"), reason="Нет реального TINVEST_TOKEN в окружении")
def test_live_tinvest_connectivity():
    status = TInvestProvider().check_connection()
    assert status.connected is True
