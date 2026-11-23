import io
import respx
import httpx
import openpyxl
from fastapi.testclient import TestClient

from app.main import app
from app.providers.bcs import BcsProvider
from app.providers.native_parsers import parse_any_broker_file
from app.providers.registry import check_all_providers_health

client = TestClient(app)


def test_all_18_platforms_registered():
    health = check_all_providers_health()
    ids = {h.provider_id for h in health}
    expected = {
        "tinvest", "bcs", "finam", "alor",
        "sber", "vtb", "alfa", "gazprom", "psb", "rshb",
        "raiffeisen", "sovcom", "rencredit", "uralsib",
        "aton", "cifra", "mkb", "finuslugi"
    }
    assert expected.issubset(ids)


@respx.mock
def test_bcs_trade_api_connectivity():
    respx.post("https://be.broker.ru/trade-api-keycloak/realms/tradeapi/protocol/openid-connect/token").mock(
        return_value=httpx.Response(200, json={"access_token": "bcs_jwt"})
    )
    respx.get("https://be.broker.ru/trade-api-portfolio/api/v1/portfolio").mock(
        return_value=httpx.Response(200, json=[
            {"ticker": "SBER", "displayName": "Сбербанк", "quantity": 10, "currentPrice": 295.0, "balancePrice": 280.0}
        ])
    )
    bcs = BcsProvider(refresh_token="valid_refresh_token_12345")
    status = bcs.check_connection()
    assert status.connected is True
    positions, _, _ = bcs.fetch_positions()
    assert len(positions) == 1
    assert positions[0].total_value == 2950.0


def test_parse_native_sber_html_report():
    sber_html = """
    <html><body>
      <table>
        <tr><th>Наименование</th><th>Код</th><th>Количество</th><th>Рыночная цена</th><th>Рыночная стоимость</th></tr>
        <tr><td>Сбербанк АО</td><td>SBER</td><td>20</td><td>290,50</td><td>5810,00</td></tr>
        <tr><td>ОФЗ 26238</td><td>SU26238RMFS4</td><td>5</td><td>560,00</td><td>2800,00</td></tr>
      </table>
    </body></html>
    """.encode("utf-8")

    items = parse_any_broker_file("sber", "sber_report.html", sber_html)
    assert len(items) == 2
    assert items[0].ticker == "SBER"
    assert items[0].total_value == 5810.0
    assert items[1].type == "bond"


def test_parse_native_vtb_and_finuslugi_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Отчет брокера ВТБ Мои Инвестиции"])
    ws.append(["Наименование инструмента", "Тикер", "Количество", "Цена", "Стоимость"])
    ws.append(["ЛУКОЙЛ", "LKOH", 2, 6800.0, 13600.0])
    ws.append(["Газпром Капитал", "RU000A105A04", 3, 1005.0, 3015.0])

    buf = io.BytesIO()
    wb.save(buf)
    items = parse_any_broker_file("vtb", "vtb_portfolio.xlsx", buf.getvalue())
    assert len(items) == 2
    assert items[0].ticker == "LKOH"
    assert items[0].total_value == 13600.0


def test_quik_bridge_endpoint():
    resp = client.post("/api/quik-bridge/sovcom", json=[
        {"ticker": "GAZP", "quantity": 10, "price": 135.5}
    ])
    assert resp.status_code == 200
    assert resp.json()["status"] == "synced"
