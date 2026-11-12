import pytest
from fastapi import HTTPException, status

from app.services import stock_service, watchlist_service

USER_ID = 1
OTHER_USER_ID = 2


@pytest.fixture(autouse=True)
def known_tickers(monkeypatch):
    """Only AAPL and MSFT exist, so the tests never call a market data provider."""

    async def fake_ensure_ticker_exists(ticker: str) -> str:
        normalized_ticker = stock_service.normalize_ticker(ticker)
        if normalized_ticker not in {"AAPL", "MSFT"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

        return normalized_ticker

    monkeypatch.setattr(stock_service, "ensure_ticker_exists", fake_ensure_ticker_exists)


async def test_duplicate_watchlist_names_are_rejected_ignoring_case(db_session) -> None:
    await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")

    with pytest.raises(HTTPException) as caught:
        await watchlist_service.create_watchlist(db_session, USER_ID, "  growth ")

    assert caught.value.status_code == 409


async def test_different_users_can_use_the_same_watchlist_name(db_session) -> None:
    await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")
    other = await watchlist_service.create_watchlist(db_session, OTHER_USER_ID, "Growth")

    assert other.name == "Growth"


async def test_blank_watchlist_name_is_rejected(db_session) -> None:
    with pytest.raises(HTTPException) as caught:
        await watchlist_service.create_watchlist(db_session, USER_ID, "   ")

    assert caught.value.status_code == 422


async def test_rename_watchlist(db_session) -> None:
    watchlist = await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")

    renamed = await watchlist_service.rename_watchlist(db_session, USER_ID, watchlist.id, " Tech ")

    assert renamed.name == "Tech"


async def test_rename_to_the_same_name_with_different_case_is_allowed(db_session) -> None:
    watchlist = await watchlist_service.create_watchlist(db_session, USER_ID, "growth")

    renamed = await watchlist_service.rename_watchlist(db_session, USER_ID, watchlist.id, "Growth")

    assert renamed.name == "Growth"


async def test_rename_to_another_lists_name_is_rejected(db_session) -> None:
    await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")
    second = await watchlist_service.create_watchlist(db_session, USER_ID, "Income")

    with pytest.raises(HTTPException) as caught:
        await watchlist_service.rename_watchlist(db_session, USER_ID, second.id, "GROWTH")

    assert caught.value.status_code == 409


async def test_delete_watchlist_removes_it_and_its_stocks(db_session) -> None:
    watchlist = await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")
    await watchlist_service.add_stock_to_watchlist(db_session, USER_ID, watchlist.id, "AAPL")

    await watchlist_service.delete_watchlist(db_session, USER_ID, watchlist.id)

    assert await watchlist_service.list_watchlists(db_session, USER_ID) == []


async def test_a_user_cannot_rename_or_delete_someone_elses_watchlist(db_session) -> None:
    watchlist = await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")

    with pytest.raises(HTTPException) as renamed:
        await watchlist_service.rename_watchlist(db_session, OTHER_USER_ID, watchlist.id, "Mine")
    with pytest.raises(HTTPException) as deleted:
        await watchlist_service.delete_watchlist(db_session, OTHER_USER_ID, watchlist.id)

    assert renamed.value.status_code == 404
    assert deleted.value.status_code == 404
    assert len(await watchlist_service.list_watchlists(db_session, USER_ID)) == 1


async def test_adding_an_unknown_ticker_is_rejected_and_nothing_is_saved(db_session) -> None:
    watchlist = await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")

    with pytest.raises(HTTPException) as caught:
        await watchlist_service.add_stock_to_watchlist(db_session, USER_ID, watchlist.id, "ZZZZQ")

    assert caught.value.status_code == 404
    saved = await watchlist_service.get_watchlist(db_session, USER_ID, watchlist.id)
    assert saved.stocks == []


async def test_adding_a_known_ticker_normalizes_it(db_session) -> None:
    watchlist = await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")

    updated = await watchlist_service.add_stock_to_watchlist(
        db_session, USER_ID, watchlist.id, " aapl "
    )

    assert [stock.ticker for stock in updated.stocks] == ["AAPL"]


async def test_adding_the_same_ticker_twice_is_rejected(db_session) -> None:
    watchlist = await watchlist_service.create_watchlist(db_session, USER_ID, "Growth")
    await watchlist_service.add_stock_to_watchlist(db_session, USER_ID, watchlist.id, "AAPL")

    with pytest.raises(HTTPException) as caught:
        await watchlist_service.add_stock_to_watchlist(db_session, USER_ID, watchlist.id, "aapl")

    assert caught.value.status_code == 409
