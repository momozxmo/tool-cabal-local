# Deploy All for Cabal Web to Render (free tier)

The web app runs anywhere Docker runs. This guide uses [Render](https://render.com)
with a free external PostgreSQL database (Supabase or Neon). No secret value is
ever committed — every secret is entered in the Render dashboard.

## 1. Create a PostgreSQL database (Supabase or Neon)

1. Create a free Postgres database on [Supabase](https://supabase.com) or
   [Neon](https://neon.tech).
2. Copy its connection string and convert it to the SQLAlchemy + psycopg form:

   ```text
   postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
   ```

   (Change a leading `postgres://` or `postgresql://` to `postgresql+psycopg://`.)

## 2. Generate secrets locally

Run these locally and copy the output — they print to your terminal only and are
never written into a tracked file:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"        # APP_SECRET_KEY
python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"  # AZTEK_SESSION_ENCRYPTION_KEY
```

Keep `AZTEK_SESSION_ENCRYPTION_KEY` safe: rotating it makes every stored Aztek
session undecryptable, and users must reconnect.

## 3. Create the Render service

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, point it at the repo. Render reads
   `render.yaml` and creates one Docker web service.
3. Open the service's **Environment** tab and set the `sync:false` values:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | your `postgresql+psycopg://…?sslmode=require` string |
   | `APP_SECRET_KEY` | generated above |
   | `AZTEK_SESSION_ENCRYPTION_KEY` | generated above (url-safe base64, 32 bytes) |
   | `BOOTSTRAP_ADMIN_USERNAME` | e.g. `admin` |
   | `BOOTSTRAP_ADMIN_PASSWORD` | a strong password |

   `APP_ENV=production`, `SESSION_COOKIE_SECURE=true`, and `BROWSER_CONCURRENCY=1`
   are already set by `render.yaml`.

4. Deploy. The container runs `alembic upgrade head` and then starts uvicorn.
   The bootstrap admin is created on first start from the two `BOOTSTRAP_*` vars.

## 4. First login and admin

1. Open the Render URL — `/` redirects to `/login`.
2. Log in as the bootstrap admin.
3. Change the bootstrap password from `/account` (it revokes all sessions;
   log in again with the new password).

> Admin user-management screens are not built yet. For now, create additional
> member accounts by running `AuthService.create_user` against the database, or
> add them once the admin panel ships.

## 5. Connect an Aztek session (bookmarklet — no extension)

Each member connects their own Aztek session with a bookmarklet — nothing to
install:

1. Open `/account` on the deployed site and drag the **“เชื่อม Aztek”** button to
   the browser bookmarks bar (one time).
2. Log in to the Aztek web app (the v2 host) in a normal tab.
3. On `/account`, click **สร้างรหัสจับคู่** and copy the pairing token.
4. On the Aztek tab, click the **“เชื่อม Aztek”** bookmark. It reads the page's
   session cookies and opens `/pair-bridge` on your site; paste the token there
   and connect. The token is single-use and expires in 5 minutes.

## Free-tier notes

- Render free web services sleep after inactivity; the first request after idle
  is slow to wake, and a headless search adds Chromium start-up time.
- `BROWSER_CONCURRENCY=1` keeps memory within the free tier — one search runs at
  a time; others queue.
- Supabase/Neon free databases may pause when idle; the first query reconnects.
