# GoFile ABDM Helper

**Stable release:** `v1.0.1`

Repository: `https://github.com/Hoyomaru/gofile-abdm-helper`

A small personal-use tool that extends the **existing GoFile page** with a Userscript UI and sends selected GoFile files/folders to **AB Download Manager (ABDM)** through a localhost-only Python/Flask helper.

There is **no standalone Flask web UI**. The normal workflow is:

```text
GoFile page
    ↓
Userscript (checkboxes / toolbar / settings / progress)
    ↓ GM_xmlhttpRequest
localhost Flask Helper (127.0.0.1:8765)
    ↓
AB Download Manager (127.0.0.1:15151)
```

Python never downloads the file body. It only resolves GoFile metadata/direct URLs and registers tasks in ABDM.

## What this implementation is based on

The implementation was written from scratch after reviewing the current default branches on 2026-09-05:

- `ewigl/gofile-enhanced` — default branch `main`
  - Current Userscript imports GoFile's `/js/services/contents.js` and `/js/ui/{menu,popup,toast}.js` and integrates around `#fm-toolbar` / `#fm-root`.
  - This project borrows the **integration idea**, GM storage/request approach, and compact toolbar philosophy.
  - This project does **not** copy its downloader-choice UI or its `unsafeWindow` / `Object.prototype` FileManager interception. The helper resolves GoFile content instead, and DOM matching has a small fallback selection popup.
- `martadams89/gofile-dl` — default branch `main`
  - Guest account creation via `POST https://api.gofile.io/accounts`.
  - Dynamic `X-Website-Token` derivation, matching `User-Agent` / `X-BL`, SHA-256 password handling, recursion, UUID content IDs, and rate-limit handling.
  - This project does **not** reuse its Flask UI, downloader, Docker/CLI/task/history features, or file transfer logic.
- `amir1376/ab-download-manager` — default branch `master`
  - The current `REST-API.yml` documents `GET /queues` and `POST /start-headless-download`.
  - This project only sends documented fields: `downloadSource.link`, optional `downloadSource.headers`, optional `downloadSource.downloadPage`, optional `folder`, optional `name`, and optional `queueId`.
  - Queue choices are read from the documented `GET /queues` endpoint; selecting **Default (ABDM)** omits `queueId`.

## Files

```text
project/
├── gofile-abdm.user.js
├── app.py
├── tray.py
├── start-tray.cmd
├── gofile.py
├── abdm.py
├── requirements.txt
├── README.md
├── LICENSE
├── LICENSES/
│   └── optional-license-notices.txt
└── tests/
    └── test_core.py
```

No `templates/` or `static/` directory is used.

## Requirements

- Python 3.10+
- Violentmonkey (primary target) or Tampermonkey
- AB Download Manager with its local REST API/browser integration available on the default port `15151`
- A normal network connection that can reach GoFile

## Install

### 1. Install AB Download Manager

Install and start AB Download Manager. This helper intentionally fixes the API target to:

```text
http://127.0.0.1:15151
```

There is no option to point it at another machine.

### 2. Install Python dependencies

Windows / Linux:

```bash
python -m pip install -r requirements.txt
```

### 3. Start the localhost helper

#### Windows: recommended system-tray mode

Double-click:

```text
start-tray.cmd
```

This starts `tray.py` with `pythonw.exe`, so no terminal window remains open. The tray icon starts and monitors `app.py` in the background. Right-click the tray icon to use:

- **Helper: Running / Stopped** — current localhost-helper status
- **Restart Helper** — restart the tray-owned Flask helper
- **Open Folder** — open this project directory
- **View Log** — open `helper.log`
- **Start with Windows** — register/unregister the tray launcher for the current Windows user
- **Exit** — stop the tray-owned helper and close the tray application

For automatic startup, launch the tray once and turn on **Start with Windows**. This writes a per-user `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry pointing to `pythonw.exe tray.py`; administrator rights are not required.

If an old `python app.py` is already running manually, the tray shows **Running (external)** and will not kill it. Close the old terminal once; the tray detects the stopped helper and starts its own hidden copy automatically.

#### Manual / Linux mode

You can still run the helper directly:

```bash
python app.py
```

It binds only to:

```text
127.0.0.1:8765
```

Optional health check:

```text
http://127.0.0.1:8765/health
```

### 4. Install the Userscript

Install Violentmonkey, create a new script, and paste the complete contents of:

```text
gofile-abdm.user.js
```

The script only grants cross-origin Userscript access to `localhost` / `127.0.0.1`; it does not use `@connect *` and does not use `unsafeWindow`.

### 5. Open GoFile normally

Open a shared URL such as:

```text
https://gofile.io/d/xxxxxxxx
```

The Userscript adds a small ABDM toolbar to the GoFile page. It does not redirect you to a Flask page.

## Usage

1. Start ABDM.
2. On Windows, keep the tray launcher running (recommended); otherwise run `python app.py`.
3. Open the GoFile share URL normally.
4. Wait for the toolbar to show the resolved file count.
5. Check files or folders in the GoFile list.
6. Use **Select All** / **Clear** as needed.
7. Optionally open **⚙** and choose an ABDM download queue, Save folder, or preset.
   - **Default (ABDM)** — omit `queueId` and let ABDM use its default behavior.
   - Any named queue — send that queue's integer ID as `queueId`.
8. Choose a send mode:
   - **Send to ABDM** — preserve the GoFile folder hierarchy.
   - **Send Flat** — ignore the GoFile folder hierarchy and place files directly in the selected Save folder (or ABDM default folder when Save folder is empty).
9. The toolbar shows registration progress, for example `12 / 30`.
10. If individual tasks fail, use **Retry Failed**. Retry keeps the send mode used by the failed batch.

The displayed progress is **ABDM task-registration progress**, not actual download progress. Speed, ETA, pause/resume, cancel, and history remain ABDM's responsibility.

## Windows tray and automatic startup

The tray launcher is intentionally separate from `app.py`: `app.py` remains a small localhost-only Flask API, while `tray.py` only manages its process and Windows startup behavior. No Flask HTML UI is added.

### First-time setup

After updating the project, install the added tray dependencies once:

```bash
python -m pip install -r requirements.txt
```

Then double-click `start-tray.cmd`. A small blue download icon appears in the Windows notification area. If Windows hides it, open the `^` hidden-icons menu.

Right-click the icon and enable **Start with Windows**. From the next login onward, the tray application and Flask helper start automatically without a terminal window.

### Logs

Because the background helper has no terminal, Flask output is written to:

```text
helper.log
```

When it grows beyond roughly 2 MB, the previous log is rotated to `helper.log.1`. Request bodies, passwords, cookies, tokens, and temporary direct URLs are not intentionally logged by the helper.

### Stopping automatic startup

Right-click the tray icon and uncheck **Start with Windows**. This removes only this application's per-user Run entry. It does not uninstall Python, ABDM, or the Userscript.

## File and folder selection

The Userscript resolves the current GoFile tree through the Python helper and then tries to attach checkboxes to the existing GoFile rows.

The DOM integration intentionally does not hard-code one fragile GoFile row class. It prefers known identifiers/links and then uses a conservative filename match. If some rows cannot be matched after a GoFile frontend change, an **Items** button appears and opens a small fallback tree selector. It is not a separate application and is only a fallback for DOM mismatch.

Selecting a folder selects all descendant files recursively. Folder selection counts and total size are computed from the helper-resolved tree.

### Preserve structure vs flat download

The toolbar has two ABDM send actions:

- **Send to ABDM** preserves each file's GoFile-relative folder path.
- **Send Flat** discards the GoFile-relative folder path. This is useful when you select one file inside a deeply nested GoFile folder and want only that file in your destination, without creating the GoFile folders.

Example with Save folder `D:/Downloads` and GoFile path `Anime/Subs/Episode01.ass`:

```text
Send to ABDM -> D:/Downloads/Anime/Subs/Episode01.ass
Send Flat    -> D:/Downloads/Episode01.ass
```

Flat mode also works for multiple selected files. If different source folders contain files with the same filename, ABDM's own duplicate-name behavior applies.

## SPA navigation

The script handles:

- `history.pushState`
- `history.replaceState`
- `popstate`
- replacement of the file-manager DOM

A debounced observer is attached to the file-manager/main area instead of running a high-frequency page-wide polling loop. Toolbar and checkbox insertion are idempotent to avoid duplicates.

## Save folder and presets

The settings popup stores only browser-side UI preferences with GM storage:

- selected ABDM queue ID
- last save folder
- save-folder presets

Presets can be added, edited, deleted, and selected.

### ABDM queue selection

Open **⚙ → Download queue** to select the queue used for new tasks. The list is refreshed from ABDM each time Settings opens using:

```text
GET http://127.0.0.1:15151/queues
```

- **Default (ABDM)**: the helper omits the optional `queueId` field.
- **Named queue**: the helper sends that queue's integer ID as `queueId` in every `/start-headless-download` request.
- **Retry Failed** keeps the same queue that was used for the original failed batch, just like it keeps Flat vs hierarchy-preserving mode.

If a previously saved queue no longer exists, Settings shows it as unavailable so you can select another queue or return to Default.

Passwords are **never persisted**.

### ABDM default save folder

If Save folder is empty, the helper omits ABDM's optional `folder` field so ABDM uses its configured default behavior.

Important limitation: the current official ABDM REST specification does not document an operation meaning “ABDM default directory + this relative subfolder”. Therefore, when Save folder is blank, **Send Flat** cleanly uses ABDM's default directory, while hierarchy-preserving behavior cannot reliably append a relative subfolder to that unknown default. To guarantee preservation of the GoFile folder hierarchy, set an explicit root such as:

```text
D:/Downloads
```

Then a GoFile path such as:

```text
Anime/Subs/Episode01.ass
```

is registered with an ABDM folder similar to:

```text
D:/Downloads/Anime/Subs
```

## Password-protected content

If GoFile reports that the content requires a password, the Userscript opens a password popup. The password is sent only to the localhost helper for that resolve request and is kept only in page memory for the current session.

The helper sends the SHA-256 password value to GoFile's content API, matching the behavior used by the current GoFile tooling.

## Guest access and Website Token

No Premium/account token input is implemented.

The helper creates a GoFile guest account and derives `X-Website-Token` dynamically from:

```text
sha256(User-Agent :: language :: guest-account-token :: 4-hour-window :: salt)
```

The token itself is therefore not a copied static Website Token.

GoFile can rotate the salt embedded in its website JavaScript. This project ships the value current in the reviewed `gofile-dl` implementation on 2026-09-05. If GoFile later rejects it, set the current salt before starting the helper:

Windows PowerShell:

```powershell
$env:GOFILE_WT_SALT="current-value"
python app.py
```

Linux/macOS shell:

```bash
GOFILE_WT_SALT="current-value" python app.py
```

You can also override `GOFILE_USER_AGENT` and `GOFILE_LANGUAGE` if GoFile changes what it validates. These values must match the values hashed into the Website Token.

## ABDM connection status

The helper checks ABDM using the documented:

```text
GET http://127.0.0.1:15151/queues
```

The Userscript checks connection status:

- once on initial load
- when Settings opens
- immediately before sending

It does not continuously poll ABDM.

## GoFile request / rate-limit behavior

The Helper deliberately minimizes repeated GoFile API traffic:

- one guest GoFile session/token is reused while the Helper process is running;
- successful resolves are cached for 20 minutes by content ID and a SHA-256 password digest;
- a repeated resolve of the same content within that window is served from local memory;
- recursive resolves are serialized so two resolves do not run against GoFile at the same time;
- HTTP/API rate-limit responses stop the resolve immediately and are not retried.

Restarting the Helper clears these in-memory caches and creates a new guest session on the next resolve.

## Security

The helper intentionally applies the following restrictions:

- Flask binds to `127.0.0.1` only.
- ABDM is fixed to `127.0.0.1:15151`.
- The helper accepts only a validated GoFile `/d/<content-id>` URL or content ID.
- There is no generic URL-fetch endpoint, preventing the helper from becoming an SSRF proxy.
- API requests require the custom `X-GoFile-ABDM: 1` marker and JSON for POST requests; no permissive CORS headers are added.
- GoFile-derived filenames/folder segments are sanitized before they are appended to a user-specified root.
- `../`, `..\`, slashes, backslashes, NUL/control characters, Windows drive injection, trailing dots/spaces, and reserved Windows names are neutralized in GoFile-derived path segments.
- The user-selected save root itself is not rewritten beyond normalizing path separators for the ABDM API.
- Guest tokens, Website Tokens, cookies, passwords, Authorization headers, and temporary direct URLs are not intentionally logged.
- One task failure does not stop the remaining tasks.
- Resolved direct URLs/headers are stored only in an in-memory helper cache (20-minute TTL); the Userscript receives opaque file keys rather than direct URLs/cookies.

Because localhost HTTP services can be targeted by browser pages, keep the helper bound to loopback and do not add CORS or LAN binding.

## Features intentionally not implemented

- Premium / Account Token input
- URL history / favorites
- search / extension filters / sorting / previews
- direct browser download
- Aria2 / IDM / JDownloader
- Python file downloader or Flask streaming
- transfer speed / ETA
- pause / resume / cancel
- download history database
- dashboard
- React / Vue
- Docker
- CLI
- database / Celery / Redis

## Tests

Run the local tests:

```bash
python -m unittest discover -s tests -v
```

Static syntax checks used during development:

```bash
python -m py_compile app.py gofile.py abdm.py
node --check gofile-abdm.user.js
```

The unit tests use mocks and do not contact GoFile or ABDM.

## Troubleshooting

### Python Helper Offline

Make sure:

```bash
python app.py
```

is still running and the Userscript has permission to access `127.0.0.1`.

### ABDM Offline

Start AB Download Manager and confirm its local REST/browser integration is enabled on port `15151`.

### `website_token_rejected`

GoFile likely changed the Website Token salt or browser-validation inputs. Update `GOFILE_WT_SALT` first. Do not replace the implementation with an old static `config.js` Website Token.

### Rate limit

The helper does **not** retry GoFile rate-limit responses. A 429/API rate-limit response stops the current recursive resolve immediately. Wait before trying again; repeated identical resolves within the 20-minute cache window are served from local memory without another GoFile API request.

### Some checkboxes do not appear

GoFile's frontend DOM may have changed. Use the **Items** fallback selector. The helper-side resolve/send logic is independent of GoFile row classes.

## License

This project is provided under the MIT License. See `LICENSE`.

The implementation is original and uses the three upstream projects as behavioral/API references rather than copying their code. See `LICENSES/optional-license-notices.txt` for reference-project notices.
