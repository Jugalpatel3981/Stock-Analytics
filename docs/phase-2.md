# Phase 2: Authentication

## Implemented

- JWT authentication in the FastAPI backend
- HttpOnly cookie token storage
- User registration
- User login
- User logout
- Protected current-user route
- Protected dashboard route in the frontend
- Login and register pages
- SQLAlchemy `users` table model
- Development database initialization script

## Backend API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/protected`

## Users Table

- `id`
- `name`
- `email`
- `password_hash`
- `created_at`

## Security Notes

Access tokens are set as HttpOnly cookies. This avoids storing JWTs in `localStorage` and keeps tokens unavailable to browser JavaScript.

For production, set:

- `JWT_SECRET_KEY` to a long random secret
- `AUTH_COOKIE_SECURE=true`
- HTTPS on both frontend and backend

## Local Database Setup

With Docker Compose, the backend creates tables automatically in development.

Without Docker, start PostgreSQL and run:

```bash
cd backend
python -m app.scripts.init_db
```

## Testing

```bash
cd backend
pytest
```
