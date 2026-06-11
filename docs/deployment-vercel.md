# Vercel Deployment Guide

This guide is for a future deployment. Do not deploy until you are ready to publish the project.

## Recommended Vercel Role

Use Vercel for the Next.js frontend only.

The FastAPI backend, PostgreSQL database, and ML dependencies are better deployed on Railway or another backend-friendly platform. The frontend can call the backend through `NEXT_PUBLIC_API_BASE_URL`.

Official docs:

- Vercel Git deployments: https://vercel.com/docs/git
- Vercel environment variables: https://vercel.com/docs/environment-variables

## Project Settings

When importing the GitHub repository into Vercel:

- Framework preset: `Next.js`
- Root directory: `frontend`
- Build command: `npm run build`
- Install command: `npm install`
- Output: handled by Next.js

## Required Environment Variables

Set these in the Vercel project settings.

```text
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api/v1
API_INTERNAL_BASE_URL=https://your-backend-domain.com/api/v1
```

For production, both values should point to the public backend URL unless the frontend and backend are deployed inside a private network that Vercel can access.

## Deployment Flow

1. Push the repository to GitHub.
2. Create a new Vercel project from the repository.
3. Set root directory to `frontend`.
4. Add the required environment variables.
5. Deploy a preview first.
6. Test login, dashboard, stocks, news, assistant, and portfolio pages.
7. Promote to production only after backend CORS and cookies are configured.

## Backend Requirements Before Vercel Production

Before making the frontend public:

- Backend must be deployed.
- `BACKEND_CORS_ORIGINS` must include the Vercel production domain.
- `AUTH_COOKIE_SECURE=true` must be enabled in production.
- `NEXT_PUBLIC_API_BASE_URL` must use HTTPS.

## Notes

Vercel environment variables apply by environment. Production variables are used for production deployments, and preview variables are used for branch preview deployments.
