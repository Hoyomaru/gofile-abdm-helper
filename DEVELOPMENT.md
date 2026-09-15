# GoFile ABDM Helper 開発・保守ガイド

この文書は、`README.md` より内部実装寄りの情報をまとめた、開発継続・保守・AI への引き継ぎ用ドキュメントです。

開発開始時は最低限、次を確認してください。

1. `README.md`
2. `DEVELOPMENT.md`
3. `CHANGELOG.md`
4. `docs/ARCHITECTURE.md`
5. 最新の `main` のコード

仕様変更時はコードだけでなく関連ドキュメントも同じ変更で更新してください。

---

## 1. 現在の状態

基準日: **2026-09-15**

- repository: `Hoyomaru/gofile-abdm-helper`
- default branch: `main`
- 正式リリース体系: **`v1.0.0` から開始**
- `VERSION`: `1.0.0`
- `v1.0.0`: **2026-09-14 に公開済み**の初回正式リリース
- `v1.0.0` tag target: `e4fcf3a2ce0cee18f9320a9ff5df683acf78912a`
- GitHub Release title: `GoFile ABDM Helper v1.0.0`
- GitHub Actions / CI: `.github/workflows/tests.yml` を導入済み
- 専用 build / binary artifact: なし
- custom Release asset: なし。GitHub-generated `Source code (zip)` / `Source code (tar.gz)` を利用可能

`v1.0.0` 公開後の `main` には次回 Release 向けの code / test / documentation change が入り、`CHANGELOG.md` の `[Unreleased]` で管理します。公開済み `v1.0.0` tag は移動しません。

### 過去の version 名について

開発途中の commit / PR には `v1.0.1`～`v1.0.3` という名称が残っています。

これらは **正式公開リリース履歴としては扱いません**。公開履歴は整理済みで、現在の完成状態を `v1.0.0` として最初の正式 Release にしました。

履歴調査では commit / PR の内容を参照して構いませんが、利用者向け Version 判定は `VERSION` / `CHANGELOG.md` / release tag を正としてください。

### テスト状況

現行 repository には次があります。

- Python core tests: `tests/test_core.py`
- review regression tests: `tests/test_review_regressions.py`
- send / uncertain Helper tests: `tests/test_send_regressions.py`
- tray source guards: `tests/test_tray_source.py`
- Userscript password/state tests: `tests/test_userscript.cjs`
- Userscript send-session tests: `tests/test_send_userscript.cjs`
- GitHub Actions: `.github/workflows/tests.yml`

CI は push / pull request で次を実行します。

```bash
python -m unittest discover -s tests -v
node --test tests/*.cjs
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

**v1.0.0 公開時に実機 E2E を新たに実行したとは記録しません。** CI も実サービス / browser / ABDM 実機 E2E の代替ではありません。

未確認として扱うもの:

- 現在の GoFile 実サービスでの root / child password E2E
- Violentmonkey / Tampermonkey 双方での網羅確認
- 各 Userscript manager での GoFile `sessionStorage` 補助経路
- 現在の ABDM で実 download 完了までの E2E
- Windows tray の hung-process recovery を含む実機長時間確認
- Linux/macOS の網羅実機確認

---

## 2. プロジェクトの責務

この project は GoFile page と AB Download Manager の間の localhost bridge です。

```text
GoFile page
  ↓
Userscript
  ↓ GM_xmlhttpRequest
Flask Helper (127.0.0.1:8765)
  ├─ GoFile API から tree / direct URL / headers を resolve
  └─ ABDM REST API へ download task 登録
       ↓
AB Download Manager (127.0.0.1:15151)
```

Helper 自身は file body を download /保存しません。

---

## 3. 主要ファイル

| ファイル | 責務 |
|---|---|
| `gofile-abdm.user.js` | GoFile UI 統合、selection、settings、resolve/send、password prompt |
| `app.py` | localhost Flask API、validation、cache、resolve serialization、ABDM 仲介 |
| `gofile.py` | GoFile guest session、Website Token、recursive resolve、path sanitize / collision disambiguation |
| `abdm.py` | ABDM `/queues` / `/start-headless-download` client、uncertain POST 分類 |
| `tray.py` | Windows tray、Helper monitor、自動起動、hung-process recovery、log |
| `start-tray.cmd` | Windows tray launcher |
| `.github/workflows/tests.yml` | Python / Userscript CI |
| `tests/test_core.py` | Python core regression tests |
| `tests/test_review_regressions.py` | Website Token / Windows root / sanitize collision regression |
| `tests/test_send_regressions.py` | Helper send / uncertain outcome regression |
| `tests/test_tray_source.py` | Windows tray recovery source guard |
| `tests/test_userscript.cjs` | Userscript resolve / password state regression |
| `tests/test_send_userscript.cjs` | Userscript send generation / resume regression |
| `VERSION` | repository release version |

全体構造は [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) を参照してください。

---

## 4. Userscript state

`gofile-abdm.user.js` の `state` が browser 側の主要 state です。

重要項目:

- `sourceUrl`
- `resolveId`
- `root`, `topLevel`, `currentLevel`, `nodeByKey`
- `selectedKeys`
- `provisionalSelectedIds`
- `failedFileKeys`, `failedResults`, `uncertainResults`
- `lastSendPreserveStructure`
- `lastSendQueueId`
- `passwordHashes`
- `resolveGeneration`, `activeResolve`
- `sendGeneration`, `activeSend`
- `resolving`, `sending`

### resolve state

```text
IDLE
  ↓ Load / navigation
RESOLVING
  ├─ password_required / wrong_password
  │      ↓
  │  PASSWORD_PROMPT
  │      ├─ Unlock → digest update → RESOLVING
  │      └─ Cancel / Escape / background / replacement → CANCELED
  ├─ success → READY
  └─ error   → ERROR
```

新しい navigation / Load は generation を進め、古い async response を `isCurrentResolve()` で破棄します。

### send state

```text
READY
 ↓
CHECK_ABDM
 ↓
SENDING (normally one file per Helper request)
 ├─ resolve_expired → remaining content IDs を保持 → RESOLVING → key remap → SENDING
 ├─ navigation / Load / Cancel Send → send generation invalidate → CANCELED
 ↓
RESULT
 ├─ success
 ├─ definite failure → failedResults → Retry Failed
 └─ uncertain → uncertainResults → automatic retry 対象外
```

`isCurrentSend()` は active operation / generation / source URL / cancelled flag を確認します。古い operation response は新しい page state を更新しません。

send progress は ABDM への task registration progress です。

### send batching 方針

Helper API 自体は複数 `file_keys` を受けられますが、現行 Userscript は通常 **1 file / Helper request** を維持します。

理由:

- navigation / Cancel Send 後も、既に Helper が処理中の request 自体を browser から確実に取り消せない
- 大きな batch にすると一度の in-flight request 内で複数 ABDM task が旧 page から継続し得る
- ABDM POST は idempotency key を持たないため、結果不明時の retry blast radius を広げたくない

batch 化は Helper-side cancellation / idempotency を設計してから再検討してください。

---

## 5. 永続化

### Userscript GM storage

```text
gofile_abdm_last_save_folder
gofile_abdm_presets
gofile_abdm_queue_id
```

password / GoFile token は保存しません。

### GoFile sessionStorage 補助

password challenge 時、対象 ID の `password|<content-id>` を一度だけ候補として読む場合があります。

- 64桁 SHA-256 hex のみ
- 全 storage を scan しない
- Userscript 自身は保存しない
- reject 値を同じ operation で blind retry しない

### Helper memory

TTL 20分:

- `_source_cache`: source + credential map の resolve 結果
- `_cache`: opaque `resolve_id` → `ResolveResult`

Helper restart で消えます。

GoFile guest token も process memory のみです。

### Windows Registry / log

startup:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
value: GoFileABDMHelper
```

log:

```text
helper.log
helper.log.1
```

2 MiB 超の rotation 判定は Helper 起動時です。

---

## 6. Helper API

すべての `/api/*` は loopback request + 次の marker を要求します。

```http
X-GoFile-ABDM: 1
```

POST / PUT / PATCH は JSON 必須です。`POST /api/gofile/resolve` と `POST /api/abdm/send` は JSON **object** であることも検証します。

### `GET /health`

tray health check。marker 不要。

正常 payload:

```json
{"ok": true, "service": "gofile-abdm-helper"}
```

tray は HTTP 200 だけでなく `service` identity も確認し、別 process の `/health` を Helper と誤認しないようにします。

### `GET /api/abdm/status`

ABDM `GET /queues` を使って connection を確認。

### `GET /api/abdm/queues`

ABDM queue list。

### `POST /api/gofile/resolve`

代表入力:

```json
{
  "url": "https://gofile.io/d/<id>",
  "password_hashes": {
    "<content-id>": "<sha256-hex>"
  }
}
```

legacy compatibility として root 用 `password` plaintext も受け付けます。

`password_hashes`:

- max 1000 entries
- key: valid content ID
- value: 64-digit SHA-256 hex

主な error:

| HTTP | code |
|---:|---|
| 400 | `invalid_body`, `invalid_content`, `invalid_password_hashes` 等 |
| 401 | `password_required`, `wrong_password` |
| 403 | `content_access_denied` |
| 404 | `not_found` |
| 429 | `rate_limited` |
| 502 | `website_token_rejected`, `gofile_error` |
| 500 | `internal_error` |

成功時に Userscript へ返す tree には direct URL / Cookie を含めません。

### `POST /api/abdm/send`

```json
{
  "resolve_id": "...",
  "file_keys": ["..."],
  "save_root": "D:/Downloads",
  "preserve_structure": true,
  "queue_id": 7
}
```

validation:

- request body: JSON object
- `file_keys`: max 1000
- `save_root`: max 1000 chars, NUL forbidden
- `queue_id`: integer / null
- expired `resolve_id`: 410 `resolve_expired`

各 result は `ok` と `uncertain` を分けます。

- `ok: true`: ABDM が success response
- `ok: false, uncertain: false`: definite failure
- `ok: false, uncertain: true`: POST transport failure のため ABDM が task を受け付けたか断定不可

現行 Userscript は通常1 fileずつ送ります。

---

## 7. GoFile API

主な endpoint:

| Method | Endpoint | 用途 |
|---|---|---|
| POST | `https://api.gofile.io/accounts` | guest token |
| GET | `https://api.gofile.io/contents/<content-id>` | folder/file metadata |

### Website Token

概念上:

```text
sha256(User-Agent :: language :: guest-token :: 4-hour-window :: salt)
```

環境変数:

- `GOFILE_WT_SALT`
- `GOFILE_USER_AGENT`
- `GOFILE_LANGUAGE`
- `GOFILE_REQUEST_INTERVAL`

retry policy:

- ordinary timeout: current 4-hour window の token のまま limited retry
- `WebsiteTokenRejected`: previous 4-hour window を一度だけ fallback
- previous window も reject: stop

一般的な network timeout と time-window fallback を同じ retry counter に結び付けないでください。

### Rate limit

- default pacing: 0.75 sec
- HTTP 429 / API rate limit: immediate stop
- blind automatic retry: しない
- recursive resolves: process 内 serialize

この安全条件を速度目的で弱めないでください。

---

## 8. ABDM API

base URL:

```text
http://127.0.0.1:15151
```

使用 endpoint:

```text
GET  /queues
POST /start-headless-download
```

送信 field:

- `downloadSource.link`
- `downloadSource.headers`
- `downloadSource.downloadPage`
- optional `folder`
- optional `name`
- optional `queueId`

Default queue の場合は `queueId` を省略します。

Save folder empty の場合は `folder` を省略します。

POST の `requests.RequestException` は definite failure ではありません。ABDM が受理後に response が失われた可能性があるため `ABDMUncertainError` として扱います。

---

## 9. Path safety

GoFile-derived segment は `sanitize_segment()` / `sanitize_relative_path()` を通します。

対象:

- slash / backslash
- `:*?"<>|`
- NUL / control chars
- `.` / `..`
- Windows reserved names
- trailing dot / space
- long filename の extension preservation

さらに、同一 folder 内で sanitize 後の target 名が case-insensitive に衝突する場合は content ID 由来の stable suffix で deterministic に disambiguate します。folder segment collision も同様に処理します。

user-selected `save_root` 自体は separator normalization 以上に勝手に変更しません。Windows drive root `C:\` / `C:/` は `C:/` として root semantics を維持します。

---

## 10. Retry policy

| 条件 | 現在の処理 |
|---|---|
| GoFile guest token temporary error | limited retry |
| GoFile content timeout | current Website Token window のまま limited retry |
| Website Token rejection | previous time window を一度だけ fallback |
| HTTP/API 429 | **retry せず stop** |
| password required/wrong | user challenge → same root re-resolve |
| access denied | stop |
| `resolve_expired` during send | remaining content IDs を保持 → re-resolve → key remap → resume |
| ABDM definite individual failure | remaining files continue / Retry Failed candidate |
| ABDM ambiguous POST result | `uncertain` として分離 / automatic blind retry しない |
| send 中 navigation / manual Load | active send を invalidate / old loop stop |

`Retry Failed` は definite failure に対する user action です。`uncertain` は含めません。

---

# 絶対に壊してはいけない不変条件

1. Helper を LAN へ bind しない。
2. ABDM の接続先を user-controlled arbitrary host にしない。
3. generic URL fetch / proxy endpoint を追加しない。
4. `X-GoFile-ABDM` marker guard を弱めない。
5. mutation request の JSON guard を弱めない。
6. GoFile URL / direct link host validation を弱めない。
7. direct URL / Cookie / token / password を UI / log / error へ不用意に露出しない。
8. GoFile-derived path sanitization と collision disambiguation を削除しない。
9. 429 を blind retry して request を増幅させない。
10. access-denied / password challenge の途中 tree を完成済み成功結果として cache / send しない。
11. stale resolve / send response で新しい navigation state を上書きしない。
12. ABDM POST の結果不明時に automatic resend を追加しない。idempotency を設計してから行う。
13. cancellation safety を犠牲にする大きな send batch を、Helper-side cancel / idempotency なしで追加しない。

「便利だから」という理由だけでこれらを弱めないでください。

---

## 11. 過去に修正した重要な問題

正式リリース前の開発履歴で次を修正しています。

### Rate-limit amplification

- guest session 再利用
- resolve cache
- resolve serialization
- request pacing
- 429 immediate stop

### Provisional checkbox regression

resolve failure 後、DOM mutation がなくても provisional checkbox を復元するよう修正。

### Fixed 180-second Userscript deadline

recursive resolve に Userscript-side fixed deadline を置かない設計へ変更。

### Password access envelope

HTTP 200 / `status: ok` でも `canAccess: false` を success としないよう修正。

### Password modal unresolved Promise

Cancel / Escape / background / replacement / navigation の全 close route で operation が終了するよう修正。

### Stale resolve response

resolve generation guard で navigation 後の stale response を無視。

### Website Token timeout fallback coupling

content request の timeout retry が previous 4-hour window を使ってしまう問題を分離し、Website Token rejection 時だけ previous window を試すよう修正。

### Windows drive root

`C:\` / `C:/` が `C:` へ縮退しないよう修正。

### Sanitized path collisions

異なる GoFile name が同じ sanitized target へ衝突する場合に stable suffix で分離。

### Send operation recovery

- send generation guard
- navigation / manual Load / Cancel Send invalidation
- `resolve_expired` の remaining content ID resume
- uncertain POST の通常 Retry Failed からの分離
- file-level failure detail / persistent Retry Failed

### Tray hung Helper

health 200 だけでなく service identity を確認し、owned process が alive のまま連続 health failure した場合に threshold 後 restart。

---

## 12. 現在の既知問題 / 要検証

### In-flight ABDM POST

Cancel Send / SPA navigation で send loop は止めますが、その時点で既に送信中だった1件の ABDM POST が受理済みかどうかは browser 側から確定できない場合があります。

そのため:

- cancel 後の blind retry はしない
- transport failure は `uncertain` に分離
- 現行 Userscript は通常1 file / request を維持

### Log rotation

2 MiB 判定は Helper 起動時です。

### Default folder + structure

Save root が空の場合、ABDM の unknown default folder に relative subfolder だけを確実に追加する API contract は確認できません。

### External E2E

GoFile / ABDM は外部仕様なので、CI success だけで current service compatibility を保証しません。release 前に実機 smoke test が必要です。

---

## 13. Crash / restart recovery

### Helper restart

失うもの:

- resolve cache
- `resolve_id`
- GoFile guest token

active send 中に `resolve_expired` を受けた場合、Userscript は同一 page の remaining content ID を保持して再 resolve / key remap / resume を試みます。

残るもの:

- Userscript GM settings
- Windows startup setting
- log file

### Browser reload

失うもの:

- selection
- resolved tree
- hand-entered password state

残るもの:

- Save folder / preset / queue

### Tray

tray が ownership を持つ Helper が終了した場合は health monitor が restart を試みます。

process が alive のまま health check が失敗する場合も、連続4回（default interval 3秒、約12秒）の失敗後に owned process を restart します。短い startup / busy interval で即 restart しないため threshold を設けています。

health response は `service: gofile-abdm-helper` を要求します。

外部 Helper は kill しません。

---

## 14. Debug

### Helper health

```text
http://127.0.0.1:8765/health
```

期待値:

```json
{"ok": true, "service": "gofile-abdm-helper"}
```

### Logs

```text
helper.log
helper.log.1
```

### Browser

- DevTools Console
- Network
- Userscript manager permission
- toolbar status / progress
- send result の Failed / Uncertain detail

問題報告時に共有してよいもの:

- error code
- HTTP status
- operation step
- OS / Python / browser / Userscript manager / ABDM version

共有してはいけないもの:

- password
- Cookie
- Authorization
- guest token
- Website Token
- signed/direct URL
- private share URL

---

## 15. Release 前チェック

詳細は [`docs/RELEASE.md`](docs/RELEASE.md)。

最低限:

- [ ] `VERSION` と Userscript `@version` が一致
- [ ] CHANGELOG に release entry
- [ ] GitHub Actions `Tests` workflow が green
- [ ] Python tests
- [ ] Userscript Node tests (`node --test tests/*.cjs`)
- [ ] Python syntax check
- [ ] Userscript syntax check
- [ ] GoFile / ABDM / Windows tray の必要な実機 smoke test
- [ ] README / DEVELOPMENT / docs sync
- [ ] secrets が混入していない
- [ ] security invariants を維持
- [ ] tag が release commit を指す
- [ ] GitHub Release title / note / tag が一致

公開後に documentation fix を `main` へ追加した場合は `[Unreleased]` に記録し、既存の公開 tag を移動しないでください。

---

## 16. 今後の開発ルール

開発開始時:

1. README
2. DEVELOPMENT
3. CHANGELOG
4. latest code

開発終了時:

1. code
2. tests
3. README
4. DEVELOPMENT
5. CHANGELOG
6. 必要な docs

を同期します。

新しい API / state / credential / destructive behavior / persistence を追加する場合は、実装だけでなく trust boundary と failure recovery も更新してください。
