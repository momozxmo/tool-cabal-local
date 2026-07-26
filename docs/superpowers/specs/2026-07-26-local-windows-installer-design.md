# All for Cabal Web Local Windows Installer Design

**Date:** 2026-07-26
**Target:** Windows 10/11 64-bit
**Distribution repository:** `https://github.com/momozxmo/tool-cabal-local.git`

## 1. Goal

Provide a full offline `All for Cabal Web Setup.exe` that a team member can
download, install, and open without installing Python, Docker, Playwright, or
Chromium and without typing terminal commands.

After installation, opening the All for Cabal Web shortcut starts the local
server and opens the Item Finder in the user's default browser. The Local build
has no visible application login, username, password, logout, password-change,
or user-management flow.

## 2. Scope

The installer includes:

- the FastAPI web application and all static assets;
- a private Python runtime and all required Python packages;
- Playwright and a compatible bundled Chromium;
- Alembic and the current database migrations;
- a Windows launcher/controller;
- shortcuts and an uninstaller.

The Local build retains Item Finder, Create Bundle, Item Code, Event, Aztek
Bookmarklet pairing, previews, job history, and audit data. It does not expose
the server to the LAN and does not share data between team members.

Deployment to Railway and Neon is separate deferred work. The Local installer
must not weaken or remove production authentication behavior.

## 3. Runtime Architecture

The installed application is split into two locations:

1. Read-only program files under the installer-selected application directory.
2. Per-user runtime data under `%LOCALAPPDATA%\AllForCabalWeb`.

The runtime data directory contains:

- the SQLite database;
- generated application and session-encryption keys;
- local launcher settings;
- sanitized application logs;
- non-secret release metadata.

It must never contain an Aztek password. Aztek browser sessions remain
encrypted at rest. Reinstalling or upgrading the application preserves this
directory.

The server binds only to `127.0.0.1:8000`. If the port is occupied by a process
that is not this application, the launcher displays a clear Thai error and does
not choose a different port silently.

## 4. Passwordless Local Access

Production authentication remains unchanged. Passwordless behavior is enabled
only when all of these conditions hold:

- the packaged launcher sets the explicit Local desktop mode;
- the server is bound to a loopback address;
- the request originates from loopback;
- the local installation has a valid generated launcher secret.

On first start, the launcher:

1. creates the runtime directory;
2. generates application and encryption secrets with the operating-system
   cryptographic random source;
3. applies database migrations;
4. creates one internal local owner record without a username/password login;
5. starts the local server;
6. requests a short-lived, single-use local launch token;
7. opens the default browser at a loopback bootstrap URL.

The bootstrap endpoint validates the token with constant-time comparison, sets
an HttpOnly SameSite=Strict local session cookie, consumes the token, and
redirects to Item Finder. The user never sees a login form or secret.

Opening the shortcut again reuses the running server and opens a newly
authenticated browser tab. Requests without a valid local session cannot run
search, preview, or create actions. This prevents an unrelated website from
using the localhost service as the user.

The Local navigation hides login, logout, password-change, and user-management
controls. The Account page continues to provide Aztek pairing and connection
status.

## 5. Windows Launcher

The launcher is a single-instance Windows GUI application. It starts with a
small Thai controller window and automatically opens the web application.

The controller shows:

- server state and local URL;
- `เปิดหน้าเว็บ`;
- `เริ่มใหม่`;
- `ปิดโปรแกรม`.

Closing the controller asks once whether to stop the local server. A second
launcher invocation signals the existing instance to open the web page instead
of starting another server.

Server output is captured to rotating sanitized logs in the runtime directory.
Logs must not contain passwords, cookies, browser storage, pairing tokens,
encryption keys, raw request authorization values, or uploaded workbook
contents.

## 6. Packaging and Installer

The application is packaged as a PyInstaller one-directory build. One-directory
is preferred over one-file because Chromium, web assets, and migrations are
large and need predictable paths; it also avoids extracting the full browser
runtime on every launch.

An Inno Setup script creates `All for Cabal Web Setup.exe` and:

- installs the packaged application;
- creates Start Menu and optional Desktop shortcuts;
- starts the launcher after installation when the user leaves the default
  checkbox enabled;
- supports in-place upgrades;
- removes program files on uninstall;
- preserves `%LOCALAPPDATA%\AllForCabalWeb` by default.

The installer is fully offline. It does not download Python packages or a
browser during installation or first start.

Local `.env` files, SQLite databases, browser profiles, cookies, uploaded
workbooks, logs, `dist/`, build caches, and developer credentials must be
excluded from both the PyInstaller input and Git repository.

## 7. Repository and Release Flow

Local-installer work is developed on a dedicated branch and published to the
separate repository:

`https://github.com/momozxmo/tool-cabal-local.git`

The original `momozxmo/all-for-cabal` remote is not used as the push target for
Local-installer commits.

The separate repository contains source, tests, build scripts, installer
definition, and documentation. Generated installer files are not committed.
Each approved installer is attached to a GitHub Release together with its
SHA-256 checksum and version notes so team members download one verified Setup
file.

The initial push targets `main` in the separate repository only after the
installer implementation and clean-machine smoke tests pass.

## 8. Upgrade and Data Compatibility

Every release carries an application version. Startup runs forward-only Alembic
migrations before serving the page. If migration fails, the launcher keeps the
old database, records a sanitized error, and does not start the application.

Before migration, the launcher creates a recoverable database backup in the
runtime directory. A successful upgrade keeps local workspaces, job history,
audit records, and encrypted Aztek session data.

Downgrades are not automatic. The installer warns when installing a version
older than the recorded local data version.

## 9. Error Handling

The controller reports actionable Thai messages for:

- port 8000 already in use;
- missing or damaged packaged Chromium;
- database migration failure;
- server startup timeout;
- local browser launch failure;
- an incompatible or incomplete installation.

Failure must not fall back to a developer Python installation, a shared Chrome
profile, a LAN listener, or an unencrypted session store.

## 10. Verification

Automated tests cover:

- Local mode cannot activate on a non-loopback bind or request;
- production mode still requires normal login;
- local launch tokens are short-lived and single-use;
- local cookies are HttpOnly and SameSite=Strict;
- a second launch reuses the running instance;
- runtime paths always resolve under `%LOCALAPPDATA%\AllForCabalWeb`;
- generated secrets and database files are not stored in Program Files;
- migrations and upgrades preserve existing data;
- packaging manifests exclude forbidden private files.

A clean Windows 10/11 64-bit virtual-machine test must verify:

1. installation works with Python, Docker, and Playwright absent;
2. the installer works without network access;
3. the shortcut starts the server and opens Item Finder without a login page;
4. Bookmarklet pairing connects an already logged-in Aztek browser without
   requesting an Aztek password;
5. Item Finder, Bundle, Item Code, and Event preview work;
6. closing the controller stops the server cleanly;
7. installing a newer Setup preserves local data;
8. uninstalling preserves local data by default.

No real Aztek create action is part of packaging verification without the
user's separate explicit approval.
