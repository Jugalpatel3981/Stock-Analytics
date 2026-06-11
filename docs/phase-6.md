# Phase 6: Watchlist Functionality

## Implemented

- User-owned watchlists
- Add stock ticker to watchlist
- Remove stock ticker from watchlist
- Protected backend APIs
- Frontend watchlist management page
- Sidebar navigation entry for Watchlists

## Database

### `watchlists`

- `id`
- `user_id`
- `name`
- `created_at`

### `watchlist_stocks`

- `id`
- `watchlist_id`
- `ticker`
- `added_at`

Each ticker is unique per watchlist.

## Backend API

- `GET /api/v1/watchlists`
- `POST /api/v1/watchlists`
- `GET /api/v1/watchlists/{watchlist_id}`
- `POST /api/v1/watchlists/{watchlist_id}/stocks`
- `DELETE /api/v1/watchlists/{watchlist_id}/stocks/{ticker}`

All endpoints require authentication.

## Frontend

- `/watchlists`

Users can create a watchlist, add tickers, remove tickers, and open stock detail pages from ticker links.

## Testing

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
npm run build
```
