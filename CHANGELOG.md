# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2026-09-05

Rate-limit safety update.

### Fixed

- Reuse one GoFile guest session/token for the lifetime of the Python Helper.
- Cache resolved GoFile content for 20 minutes by content ID and password digest, so repeated page resolves can use zero GoFile API requests.
- Stop immediately on GoFile HTTP/API rate-limit responses instead of retrying them.
- Serialize recursive GoFile resolves to prevent overlapping resolve bursts.

## [1.0.0] - 2026-09-05

Initial stable release.

### Features

- GoFile page integration through a Violentmonkey/Tampermonkey Userscript.
- File and folder selection with recursive folder resolution.
- GoFile guest access, dynamic Website Token handling, password-protected content, UUID content IDs, and rate-limit retry.
- AB Download Manager task registration through the documented localhost REST API.
- Hierarchy-preserving and Flat send modes.
- Save-folder presets and ABDM queue selection.
- Per-file send results and Retry Failed.
- Windows system-tray launcher with per-user startup at login.
- Localhost-only helper, path sanitization, SSRF restrictions, and secret-safe logging behavior.
