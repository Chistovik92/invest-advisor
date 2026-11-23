import csv
import io
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import openpyxl
from ..models import PositionModel


ALL_NON_REST_PLATFORMS: Dict[str, str] = {
    "sber": "СберИнвестиции (HTML/XLSX отчёт / QUIK)",
    "vtb": "ВТБ Мои Инвестиции (XLSX отчёт / QUIK)",
    "alfa": "Альфа-Инвестиции (HTML/XLSX отчёт / Альфа-Директ)",
    "gazprom": "Газпромбанк Инвестиции (XLSX/XML отчёт)",
    "psb": "ПСБ Инвестиции (Отчёт / QUIK)",
    "rshb": "РСХБ Брокер (Отчёт / QUIK)",
    "raiffeisen": "Райффайзен Инвестиции (Отчёт)",
    "sovcom": "Совкомбанк Инвестиции (Отчёт / QUIK)",
    "rencredit": "Ренессанс Брокер (Отчёт / QUIK)",
    "uralsib": "Уралсиб Брокер (Отчёт / QUIK)",
    "aton": "АТОН (Отчёт / QUIK)",
    "cifra": "Цифра Брокер (Отчёт / QUIK)",
    "mkb": "МКБ Инвестиции (Отчёт / QUIK)",
    "finuslugi": "Финуслуги МосБиржи (Реестр облигаций и ПИФов)",
}


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = re.sub(r"[^\d,.\-]", "", str(val)).replace(",", ".")
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def parse_sber_html_report(broker_id: str, html_bytes: bytes) -> List[PositionModel]:
    text = html_bytes.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(text, "lxml")
    positions: List[PositionModel] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [th.get_text(" ", strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        joined = " ".join(headers)
        if not (("код" in joined or "тикер" in joined or "isin" in joined) and ("количество" in joined or "кол-во" in joined)):
            continue

        idx_ticker = next((i for i, h in enumerate(headers) if "код" in h or "тикер" in h or "isin" in h), 0)
        idx_name = next((i for i, h in enumerate(headers) if "наименование" in h or "актив" in h), idx_ticker)
        idx_qty = next((i for i, h in enumerate(headers) if "количество" in h or "кол-во" in h), -1)
        idx_price = next((i for i, h in enumerate(headers) if "рыночная цена" in h or "цена" in h), -1)
        idx_val = next((i for i, h in enumerate(headers) if "стоимость" in h or "оценка" in h), -1)

        if idx_qty == -1:
            continue

        for tr in rows[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) <= idx_qty:
                continue
            ticker = cells[idx_ticker].strip().upper()
            if not ticker or "итого" in ticker.lower():
                continue
            qty = _to_float(cells[idx_qty])
            if qty <= 0:
                continue
            total_val = _to_float(cells[idx_val]) if idx_val != -1 and len(cells) > idx_val else 0.0
            price = _to_float(cells[idx_price]) if idx_price != -1 and len(cells) > idx_price else (total_val / qty if qty else 0.0)
            if total_val == 0.0 and price > 0:
                total_val = round(qty * price, 2)

            asset_type = "bond" if ticker.startswith(("SU", "RU000")) else "share"
            positions.append(
                PositionModel(
                    broker=broker_id,
                    ticker=ticker,
                    name=cells[idx_name] if len(cells) > idx_name else ticker,
                    type=asset_type,
                    quantity=qty,
                    lot=1,
                    current_price=round(price, 2),
                    lot_price=round(price, 2),
                    total_value=round(total_val, 2),
                    pnl_pct=0.0,
                )
            )
    return positions


def parse_xlsx_broker_report(broker_id: str, xlsx_bytes: bytes) -> List[PositionModel]:
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    positions: List[PositionModel] = []

    for sheet in wb.worksheets:
        header_row_idx = None
        col_map: Dict[str, int] = {}

        for r_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            row_strs = [str(c).strip().lower() if c is not None else "" for c in row]
            line = " ".join(row_strs)
            if ("тикер" in line or "код" in line or "isin" in line) and ("количество" in line or "кол-во" in line or "остаток" in line):
                header_row_idx = r_idx
                for c_idx, cell_text in enumerate(row_strs):
                    if "тикер" in cell_text or "код" in cell_text or "isin" in cell_text:
                        col_map.setdefault("ticker", c_idx)
                    elif "наименование" in cell_text or "инструмент" in cell_text:
                        col_map.setdefault("name", c_idx)
                    elif "количество" in cell_text or "кол-во" in cell_text or "остаток" in cell_text:
                        col_map.setdefault("qty", c_idx)
                    elif "цена" in cell_text:
                        col_map.setdefault("price", c_idx)
                    elif "стоимость" in cell_text or "оценка" in cell_text:
                        col_map.setdefault("value", c_idx)
                break

        if header_row_idx is None or "ticker" not in col_map or "qty" not in col_map:
            continue

        for row in sheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
            raw_ticker = row[col_map["ticker"]] if len(row) > col_map["ticker"] else None
            if not raw_ticker:
                continue
            ticker = str(raw_ticker).strip().upper()
            if "итого" in ticker.lower() or "всего" in ticker.lower():
                break
            qty = _to_float(row[col_map["qty"]] if len(row) > col_map["qty"] else 0)
            if qty <= 0:
                continue
            val = _to_float(row[col_map["value"]]) if "value" in col_map and len(row) > col_map["value"] else 0.0
            price = _to_float(row[col_map["price"]]) if "price" in col_map and len(row) > col_map["price"] else (val / qty if qty else 0.0)
            if val == 0.0 and price > 0:
                val = round(qty * price, 2)
            name = str(row[col_map["name"]]).strip() if "name" in col_map and len(row) > col_map["name"] and row[col_map["name"]] else ticker

            positions.append(
                PositionModel(
                    broker=broker_id,
                    ticker=ticker,
                    name=name,
                    type="bond" if ticker.startswith(("SU", "RU000")) else "share",
                    quantity=qty,
                    lot=1,
                    current_price=round(price, 2),
                    lot_price=round(price, 2),
                    total_value=round(val, 2),
                    pnl_pct=0.0,
                )
            )
    return positions


def parse_any_broker_file(broker_id: str, filename: str, content: bytes) -> List[PositionModel]:
    fname = filename.lower()
    if fname.endswith((".html", ".htm")):
        return parse_sber_html_report(broker_id, content)
    if fname.endswith(".xlsx"):
        return parse_xlsx_broker_report(broker_id, content)
    text = content.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text.strip()), delimiter=";")
    items: List[PositionModel] = []
    for row in reader:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        qty = _to_float(row.get("quantity"))
        price = _to_float(row.get("price"))
        avg = _to_float(row.get("avg_price") or price)
        pnl = round(((price - avg) / avg * 100.0), 2) if avg > 0 else 0.0
        items.append(
            PositionModel(
                broker=broker_id,
                ticker=ticker,
                name=(row.get("name") or ticker).strip(),
                type=(row.get("type") or "share").strip(),
                quantity=qty,
                lot=1,
                current_price=round(price, 2),
                lot_price=round(price, 2),
                total_value=round(qty * price, 2),
                pnl_pct=pnl,
            )
        )
    return items
