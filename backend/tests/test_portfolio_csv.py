from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import HTTPException, status

from app.schemas.portfolio import PortfolioHoldingRead
from app.services import portfolio_csv, portfolio_service, stock_service

USER_ID = 1


@pytest.fixture(autouse=True)
def fake_market(monkeypatch):
    """AAPL and MSFT are the only real tickers."""

    async def fake_ensure_ticker_exists(ticker: str) -> str:
        normalized_ticker = stock_service.normalize_ticker(ticker)
        if normalized_ticker not in {"AAPL", "MSFT"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

        return normalized_ticker

    async def fake_get_current_price(_symbol: str) -> float:
        return 200.0

    monkeypatch.setattr(stock_service, "ensure_ticker_exists", fake_ensure_ticker_exists)
    monkeypatch.setattr(portfolio_service, "get_current_price", fake_get_current_price)


def test_parse_reads_rows_and_normalizes_values() -> None:
    parsed = portfolio_csv.parse_holdings_csv(
        "symbol,quantity,buy_price,buy_date\n"
        " aapl ,10,150.5,2025-01-31\n"
        'MSFT,2.5,"$1,410.00",03/15/2025\n'
    )

    assert parsed.errors == []
    assert [row for row, _holding in parsed.holdings] == [2, 3]
    first, second = (holding for _row, holding in parsed.holdings)
    assert (first.symbol, first.quantity, first.buy_price) == ("AAPL", 10, 150.5)
    assert first.buy_date == date(2025, 1, 31)
    assert second.buy_price == 1410.0
    assert second.buy_date == date(2025, 3, 15)


def test_parse_accepts_common_column_names_in_any_order_and_ignores_extras() -> None:
    parsed = portfolio_csv.parse_holdings_csv(
        "Purchase Date,Ticker,Shares,Price,Notes\n2025-02-01,AAPL,3,100,long term\n"
    )

    assert parsed.errors == []
    assert parsed.holdings[0][1].symbol == "AAPL"
    assert parsed.holdings[0][1].quantity == 3


def test_parse_reports_each_bad_row_with_its_spreadsheet_row_number() -> None:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    parsed = portfolio_csv.parse_holdings_csv(
        "symbol,quantity,buy_price,buy_date\n"
        "AAPL,10,150,2025-01-31\n"
        "MSFT,abc,100,2025-01-31\n"
        "MSFT,0,100,2025-01-31\n"
        "MSFT,1,100,31 Jan 2025\n"
        f"MSFT,1,100,{tomorrow}\n"
        "MSFT,,100,2025-01-31\n"
    )

    assert len(parsed.holdings) == 1
    messages = {error.row: error.message for error in parsed.errors}
    assert messages[3] == "quantity must be a number"
    assert messages[4] == "quantity: input should be greater than 0"
    assert messages[5] == "buy_date must look like 2025-01-31"
    assert messages[6] == "Buy date cannot be in the future"
    assert messages[7] == "quantity is empty"


def test_parse_rejects_a_file_without_the_needed_columns() -> None:
    parsed = portfolio_csv.parse_holdings_csv("symbol,quantity\nAAPL,1\n")

    assert parsed.holdings == []
    assert parsed.errors[0].row == 1
    assert "buy_price, buy_date" in parsed.errors[0].message


def test_parse_rejects_empty_and_oversized_files() -> None:
    assert portfolio_csv.parse_holdings_csv("  \n").errors[0].message == "The file is empty."

    rows = "\n".join("AAPL,1,100,2025-01-31" for _ in range(portfolio_csv.MAX_IMPORT_ROWS + 1))
    too_big = portfolio_csv.parse_holdings_csv(f"symbol,quantity,buy_price,buy_date\n{rows}\n")
    assert too_big.holdings == []
    assert "more than 200" in too_big.errors[0].message


def test_export_writes_a_header_and_one_row_per_holding() -> None:
    holding = PortfolioHoldingRead(
        id=1,
        symbol="AAPL",
        quantity=2,
        buy_price=100.0,
        buy_date=date(2025, 1, 2),
        current_price=150.0,
        current_value=300.0,
        cost_basis=200.0,
        gain_loss=100.0,
        percentage_return=50.0,
        created_at=datetime.now(UTC),
    )
    unpriced = holding.model_copy(
        update={"symbol": "MSFT", "current_price": None, "current_value": None, "gain_loss": None}
    )

    lines = portfolio_csv.export_holdings_csv([holding, unpriced]).splitlines()

    assert lines[0] == (
        "symbol,quantity,buy_price,buy_date,current_price,current_value,gain_loss,return_percent"
    )
    assert lines[1] == "AAPL,2.0,100.0,2025-01-02,150.0,300.0,100.0,50.0"
    assert lines[2] == "MSFT,2.0,100.0,2025-01-02,,,,50.0"


async def test_import_saves_good_rows_and_reports_the_rest(db_session) -> None:
    result = await portfolio_service.import_holdings_csv(
        db_session,
        USER_ID,
        "symbol,quantity,buy_price,buy_date\n"
        "AAPL,10,150,2025-01-31\n"
        "ZZZZQ,1,10,2025-01-31\n"
        "msft,oops,100,2025-01-31\n"
        "MSFT,2,400,2025-02-03\n",
    )

    assert result.imported == 2
    assert result.skipped == 2
    assert [(error.row, error.message) for error in result.errors] == [
        (3, "Stock ticker 'ZZZZQ' was not found"),
        (4, "quantity must be a number"),
    ]
    saved = await portfolio_service.list_raw_holdings(db_session, USER_ID)
    assert sorted(holding.symbol for holding in saved) == ["AAPL", "MSFT"]


async def test_exported_file_can_be_imported_again(db_session) -> None:
    await portfolio_service.import_holdings_csv(
        db_session, USER_ID, "symbol,quantity,buy_price,buy_date\nAAPL,10,150,2025-01-31\n"
    )

    exported = await portfolio_service.export_holdings_csv(db_session, USER_ID)
    result = await portfolio_service.import_holdings_csv(db_session, 2, exported)

    assert result.imported == 1
    assert result.errors == []
    copied = await portfolio_service.list_raw_holdings(db_session, 2)
    assert (copied[0].symbol, copied[0].quantity, copied[0].buy_price) == ("AAPL", 10, 150)
    assert copied[0].buy_date == date(2025, 1, 31)
