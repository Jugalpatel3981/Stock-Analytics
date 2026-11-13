# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-11-12

The project is now **Stock Portfolio Analytics**: the AI features were removed and replaced
with portfolio analytics and stock comparison.

### Added
- **Analytics page:** portfolio return against the S&P 500, volatility, Sharpe ratio, beta,
  max drawdown, allocation by stock and sector, and concentration warnings.
- **Compare page:** up to five stocks on one indexed chart, with side-by-side risk figures and
  a correlation heatmap.
- Analyst ratings, 52-week range, next earnings date and key figures on each stock page.
- CSV import and export for portfolio holdings, with a row-by-row report of anything skipped.
- Rename and delete watchlists, and edit a holding's quantity, buy price and buy date.
- A "no stocks found" message for searches without results.

### Changed
- **Redesigned dashboard:** four key figures, a portfolio vs S&P 500 chart, top movers, and a
  watchlist table with one-month trend lines. It replaces the editable market cards and the
  duplicate watchlist.
- Each page shows its title once, in a consistent header. Gains and losses are green and red
  everywhere, with the day's change kept separate from pre-market and after-hours moves.
- Phones get a slide-in menu instead of a horizontal tab strip, and no page scrolls sideways.
- Pages show grey placeholders while data loads instead of "Loading..." text.
- If the server is not ready, pages show "Waiting for the server" and retry by themselves.
- Stock search and company news now use Finnhub. Search finds companies by name
  (for example "disney" or "coca cola") instead of only exact tickers.
- The open, high, low and close boxes above the price chart describe the whole selected
  period instead of its last bar.

### Fixed
- News was empty because the Yahoo Finance news feed stopped responding.
- Tickers that do not exist could be saved to watchlists and portfolios.
- Holdings could be saved with a buy date in the future.
- Two watchlists could share the same name.
- After-hours and pre-market changes were measured against the previous day's close, and
  pages disagreed about the price until a live trade arrived.
- Passwords made only of digits or only of letters were accepted.
- The frontend container always reported "unhealthy".
- The backend logged an "Event loop is closed" error on every start.
- Price history failed with a server error when Yahoo Finance returned a day with missing
  prices. Such days are now skipped.

### Removed
- The AI assistant, news sentiment and price prediction features, with their database
  tables (migration `0003`), settings and dependencies. The prediction model did not beat
  simple baselines in its own backtest, and the AI features depended on an LLM provider
  that was no longer available.
- The decorative bar chart on the dashboard and the "Momentum" / "Review" watchlist tags,
  which did not represent real data. The watchlist now shows today's percentage change.

## [1.0.0] - 2026-10-15

First public release.

### Added
- Landing page with one-click demo login and a seeded sample portfolio and watchlist.
- Walk-forward backtesting for the prediction model, compared with naive baselines and
  buy-and-hold, shown next to every prediction.
- News sentiment classified by an LLM (Groq), batched and cached.
- Alembic database migrations, applied automatically on start.
- Caching for Yahoo Finance calls and rate limits on login, registration, demo login and chat.
- Free-tier deployment on Vercel, Render and Neon (`render.yaml`, `docs/deployment.md`).
- Site icon, link-preview image, per-page titles, and friendly error and 404 pages.
- CI for linting, tests, migrations, type-checking, builds and Docker images.

### Changed
- The model predicts next-day returns from scale-free features instead of raw prices.
- Trained models are stored in PostgreSQL instead of the local disk.
- Browser API calls go through the frontend's own domain, so logins work when the frontend
  and backend are hosted separately.

### Fixed
- The AI assistant failed on every message.
- Portfolio and news pages crashed when Yahoo Finance was unavailable.
- Portfolio totals showed a total loss when prices were missing.

### Removed
- Hardcoded confidence scores, placeholder headlines and a static AI insight.
- The Hugging Face dependency and per-phase build logs.
