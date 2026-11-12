"""Read and write portfolio holdings as CSV."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from pydantic import ValidationError

from app.schemas.analytics import HoldingImportError
from app.schemas.portfolio import PortfolioHoldingCreate, PortfolioHoldingRead

MAX_IMPORT_ROWS = 200
EXPORT_COLUMNS = [
    "symbol",
    "quantity",
    "buy_price",
    "buy_date",
    "current_price",
    "current_value",
    "gain_loss",
    "return_percent",
]
# Other column names that spreadsheets and brokers commonly use.
COLUMN_ALIASES = {
    "ticker": "symbol",
    "shares": "quantity",
    "qty": "quantity",
    "price": "buy_price",
    "buy price": "buy_price",
    "cost": "buy_price",
    "date": "buy_date",
    "buy date": "buy_date",
    "purchase date": "buy_date",
}
REQUIRED_COLUMNS = ("symbol", "quantity", "buy_price", "buy_date")
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y")


@dataclass(frozen=True)
class ParsedHoldings:
    holdings: list[tuple[int, PortfolioHoldingCreate]]
    errors: list[HoldingImportError]


def export_holdings_csv(holdings: list[PortfolioHoldingRead]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_COLUMNS)

    for holding in holdings:
        writer.writerow(
            [
                holding.symbol,
                holding.quantity,
                holding.buy_price,
                holding.buy_date.isoformat(),
                _blank_if_none(holding.current_price),
                _blank_if_none(holding.current_value),
                _blank_if_none(holding.gain_loss),
                _blank_if_none(holding.percentage_return),
            ]
        )

    return buffer.getvalue()


def _blank_if_none(value: float | None) -> str | float:
    return "" if value is None else round(value, 2)


def _column_name(header: str) -> str:
    name = header.strip().lower().lstrip("﻿").replace("_", " ")
    return COLUMN_ALIASES.get(name, name.replace(" ", "_"))


def _parse_date(value: str) -> date:
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    raise ValueError("buy_date must look like 2025-01-31")


def _parse_number(value: str, column: str) -> float:
    try:
        return float(value.replace(",", "").replace("$", ""))
    except ValueError as exc:
        raise ValueError(f"{column} must be a number") from exc


def _first_error(error: ValidationError) -> str:
    first = error.errors()[0]
    message = str(first["msg"])
    if message.startswith("Value error, "):
        return message.removeprefix("Value error, ")

    field = first["loc"][-1] if first["loc"] else "value"
    return f"{field}: {message[0].lower()}{message[1:]}"


def parse_holdings_csv(content: str) -> ParsedHoldings:
    """Turn CSV text into holdings. Rows that cannot be read are reported, not dropped silently.

    Row numbers match a spreadsheet: the header is row 1 and the first holding is row 2.
    """
    reader = csv.reader(io.StringIO(content.strip()))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return ParsedHoldings([], [HoldingImportError(row=1, message="The file is empty.")])

    columns = [_column_name(header) for header in rows[0]]
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        return ParsedHoldings(
            [],
            [
                HoldingImportError(
                    row=1,
                    message=f"Missing column: {', '.join(missing)}. "
                    f"The file needs {', '.join(REQUIRED_COLUMNS)}.",
                )
            ],
        )

    data_rows = rows[1:]
    if len(data_rows) > MAX_IMPORT_ROWS:
        return ParsedHoldings(
            [],
            [
                HoldingImportError(
                    row=1, message=f"The file has more than {MAX_IMPORT_ROWS} holdings."
                )
            ],
        )

    holdings: list[tuple[int, PortfolioHoldingCreate]] = []
    errors: list[HoldingImportError] = []
    for row_number, row in enumerate(data_rows, start=2):
        cells = {column: cell.strip() for column, cell in zip(columns, row, strict=False)}
        try:
            blank = [column for column in REQUIRED_COLUMNS if not cells.get(column)]
            if blank:
                raise ValueError(f"{', '.join(blank)} is empty")

            holdings.append(
                (
                    row_number,
                    PortfolioHoldingCreate(
                        symbol=cells["symbol"].upper(),
                        quantity=_parse_number(cells["quantity"], "quantity"),
                        buy_price=_parse_number(cells["buy_price"], "buy_price"),
                        buy_date=_parse_date(cells["buy_date"]),
                    ),
                )
            )
        except ValidationError as exc:
            errors.append(HoldingImportError(row=row_number, message=_first_error(exc)))
        except ValueError as exc:
            errors.append(HoldingImportError(row=row_number, message=str(exc)))

    return ParsedHoldings(holdings, errors)
