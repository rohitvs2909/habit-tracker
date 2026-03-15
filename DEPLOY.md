# Habit Tracker Deployment Guide

This app supports MySQL and PostgreSQL backends.

## 1) Render Deploy With PostgreSQL (recommended)

1. Create a PostgreSQL instance in Render.
2. Create a Web Service from this repository.
3. Set Build Command to: pip install -r requirements.txt
4. Set Start Command to: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
5. Set environment variables:
- DB_ENGINE=postgresql
- DATABASE_URL=<Render PostgreSQL Internal Database URL>
- FLASK_SECRET_KEY=<long random secret>
6. Deploy.

Notes:
- When DATABASE_URL is present, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME are not required.
- The app auto-creates schema/tables on startup.

## 2) Prepare Your Database (MySQL path)

Use one of these options:

- Managed MySQL (recommended): Railway MySQL, Aiven MySQL, PlanetScale-compatible MySQL endpoint
- Your own MySQL server: must allow remote connections from your app host

Create credentials and note:

- `DB_HOST`
- `DB_PORT` (usually `3306`)
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME` (example: `habit_tracker`)

## 3) Required Environment Variables (MySQL path)

Set these on your hosting platform:

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `FLASK_SECRET_KEY` (use a long random value)

Optional seed users for first boot:

- `APP_USER_1`
- `APP_PASS_1`
- `APP_USER_2`
- `APP_PASS_2`

## 4) Deploy on Render (MySQL quick path)

1. Push this project to GitHub.
2. In Render, create a **Web Service** from your repo.
3. Set:
- Runtime: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
4. Add the environment variables above.
5. Deploy.

## 5) Deploy on Railway

1. Create a new project and connect this repo.
2. Add environment variables listed above.
3. Start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

## 6) Verify After Deploy

Check these URLs:

- `/login`
- `/register`

Then test:

- Create account
- Login
- Add/edit/delete habits
- Toggle checkboxes
- Change password

## Netlify

Netlify does not run a long-lived Python Flask server like this app out of the box.

For this project, use one of these:

- Recommended: Deploy full app on Render or Railway (single deployment)
- Split setup: Deploy frontend on Netlify and backend Flask API on Render or Railway

If you choose split setup:

1. Deploy Flask backend on Render or Railway with DB variables for your selected engine.
2. Point frontend requests to your backend domain (instead of same-origin paths).
3. Configure CORS on backend for your Netlify domain.
4. Set Netlify build/publish only for static assets.

If you want, the next step is to convert your frontend fetch URLs to use a configurable backend base URL so Netlify + Render works cleanly.

## Notes

- Data persists in your configured database backend.
- The app auto-creates schema/tables on startup (`init_db()`).
- Do not use Flask dev server in production.
