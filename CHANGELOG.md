# Changelog

All notable changes to this project will be documented in this file.

## [1.0.3] - 2026-09-08

Review regression fixes.

### Fixed

- Restore provisional row checkboxes when GoFile resolve fails, including cases where the page DOM does not change afterward.
- Remove the fixed 180-second Userscript deadline from recursive resolve requests while retaining the Helper's per-request GoFile API timeouts.
- Add regression coverage for 242 paced content requests (180.75 seconds), failed-resolve checkbox restoration, and recursive resolve without a Userscript deadline.

## [1.0.2] - 2026-09-06

Selection and rate-limit robustness update.

### Fixed

- Expand GoFile row matching to support `data-item-id` and `data-uuid` in addition to the existing ID attributes.
- Prefer visible content IDs when detecting the current folder before falling back to filename text matching.
- Keep the **Items** fallback selector visible at all times so selection remains available when GoFile DOM row matching changes.
- Make **Select All** fall back to the resolved root children instead of silently doing nothing when current-level detection is empty.
- Allow visible GoFile rows to be selected provisionally before Helper resolve succeeds; reconcile those content IDs after a later successful resolve.
- Pace recursive GoFile content requests at 0.75 seconds by default to reduce bursty API traffic while still stopping immediately on 429.

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
