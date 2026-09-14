# トラブルシューティング

GoFile ABDM Helper `v1.0.0` の問題切り分け手順です。

基本は **症状 → 原因候補 → 確認 → 対処** の順で確認します。

password、Cookie、Authorization header、guest token、Website Token、一時 direct download URL、private share URL は公開 Issue やログへ貼らないでください。

---

## 1. `Python Helper is offline.`

### 原因候補

- `app.py` が起動していない
- tray が起動していない / Helper start に失敗
- dependency 不足
- port 8765 conflict

### 確認

```text
http://127.0.0.1:8765/health
```

期待値は `ok: true`。

Windows tray 使用時は tray status と `helper.log` も確認します。

### 対処

```bash
python -m pip install -r requirements.txt
python app.py
```

Windows:

```text
start-tray.cmd
```

`Running (external)` は、tray 外で起動した Helper がすでに port 8765 を使用している状態です。

---

## 2. `pythonw.exe was not found in PATH.`

確認:

```bat
where python
where pythonw
python --version
```

Python install / PATH を修正後、`start-tray.cmd` を再実行します。

---

## 3. Windows 起動時に tray が出ない

startup registration:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
value: GoFileABDMHelper
```

project directory / Python path を移動した場合、一度 **Start with Windows** を off → on にして再登録します。

---

## 4. `ABDM Offline`

Helper が確認に使う endpoint:

```text
GET http://127.0.0.1:15151/queues
```

AB Download Manager が起動し、この endpoint が default port 15151 で応答することを確認してください。

この project は ABDM host / port を任意変更する UI を持ちません。

---

## 5. queue が Settings に出ない

Settings open ごとに `/queues` を refresh します。

以前保存した queue が消えている場合、`Unavailable queue (#...)` になる場合があります。

対処:

- ABDM 側で queue を確認
- Settings を開き直す
- 別 queue または `Default (ABDM)` を選択

`Default (ABDM)` は `queueId` field を省略します。

---

## 6. `website_token_rejected`

GoFile が Website Token の salt / User-Agent / language 等の検証条件を変更した可能性があります。

環境変数:

- `GOFILE_WT_SALT`
- `GOFILE_USER_AGENT`
- `GOFILE_LANGUAGE`

例:

```powershell
$env:GOFILE_WT_SALT="current-value"
python app.py
```

古い固定 Website Token をコードへ貼り付ける方式へ戻さず、GoFile の現行実装を確認してから変更してください。

---

## 7. `rate_limited` / HTTP 429

現在の behavior:

- recursive content request は default 0.75 sec pacing
- HTTP 429 / API rate limit で current resolve を即停止
- rate limit の automatic retry はしない
- successful resolve は20分 cache

対処:

- 時間を置く
- Load を連打しない
- 必要なら `GOFILE_REQUEST_INTERVAL` を安全側へ調整

速度だけを理由に pacing を無効化することは推奨しません。

---

## 8. resolve が長い

large tree では folder / pagination request 数に応じて時間がかかります。

現在の regression test には 242 request を 0.75 sec pacing した場合、pacing だけで約180.75 sec になるケースがあります。

Userscript の recursive resolve に fixed 180 sec deadline はありません。Helper の個別 HTTP timeout は別に存在します。

対処:

- progress / error を待つ
- rate limit でなければ Load を連打しない
- `helper.log` を確認

---

## 9. password prompt が出る

`v1.0.0` は root / child folder の password challenge に対応します。

- plaintext は browser 内で SHA-256
- Helper へ content ID → digest map を送る
- parent と child で異なる password を扱える
- wrong password は対象 folder の digest を更新して same root を re-resolve
- Cancel / Escape / background click で cancel
- empty password は送信しない

GoFile page が解除済みの場合、`sessionStorage` の `password|<content-id>` digest を一度だけ候補として利用する場合があります。

---

## 10. `wrong_password` が続く

原因候補:

- password が違う
- parent / child の password が違う
- GoFile access state が変わった
- `sessionStorage` candidate が古い

表示される Target path を確認し、その folder に対応する password を入力します。

---

## 11. `content_access_denied`

GoFile response が access 不可を示しているものの、password challenge として分類できない状態です。

確認:

- share が有効か
- browser の通常 GoFile UI で access 可能か
- private / expired / その他制限ではないか

理由が不明な場合、Helper は推測で password prompt を出しません。

---

## 12. checkbox が一部表示されない

row matching priority:

- `data-content-id`
- `data-id`
- `data-item-id`
- `data-uuid`
- link
- filename text fallback

GoFile DOM change により mapping できない場合は toolbar の **Items** を使用します。

Helper resolve / send logic 自体は GoFile row class に依存しません。

---

## 13. Helper resolve 前に選択したい

visible row に content ID があれば provisional checkbox が使えます。

ただし ABDM 送信には direct URL / headers の resolve が必要なので、最終的には resolve success が必要です。

---

## 14. `Resolved GoFile session expired.`

Helper resolve cache TTL は20分です。Helper restart でも cache は消えます。

現行実装は 410 `resolve_expired` を受けると re-resolve しますが、元 `selectedKeys` の自動保持と batch 自動再送を保証していません。

対処:

1. re-resolve 完了を待つ
2. selection を再確認
3. 必要なら再選択
4. Send を実行

これは既知の要検証事項です。

---

## 15. `Send to ABDM` で folder structure が期待と違う

Save folder empty の場合、Helper は ABDM の optional `folder` を省略します。

そのため「ABDM default directory + GoFile relative subfolder」を Helper 側から確実に指定できません。

structure を確実に保持する場合は明示 root を設定します。

```text
D:/Downloads
```

GoFile:

```text
Anime/Subs/Episode01.ass
```

ABDM folder:

```text
D:/Downloads/Anime/Subs
```

Flat にする場合は **Send Flat**。

---

## 16. ABDM に duplicate task ができた

`POST /start-headless-download` が ABDM 側では成功したが Helper が response を受け取れなかった場合、client からは failed に見える可能性があります。

その状態で `Retry Failed` を実行すると duplicate task になる可能性があります。

現在:

- automatic blind retry はしない
- idempotency key / reconciliation API は使用していない
- Retry Failed は user action

network timeout / reset 直後は、先に ABDM task list を確認してください。

---

## 17. Send 中に別 GoFile page へ移動した

resolve には stale response generation guard がありますが、send loop には同等の navigation cancellation guard がありません。

old page の remaining task registration が続く可能性があります。

送信完了後に別 share へ移動する運用を推奨します。

---

## 18. `helper.log` が 2 MiB を超えた

rotation は Helper startup 時に size を確認します。

```text
helper.log -> helper.log.1
```

running 中に 2 MiB 到達時点で即 rotate する方式ではありません。

---

## 19. direct download link が reject される

Helper が許可する resolved link:

- scheme: `https`
- host: `gofile.io` or `*.gofile.io`

GoFile が別 host model に変更した場合は、現行仕様を確認してから validation を変更してください。任意 host allow にしないでください。

---

## 20. Save folder の文字が置換される

GoFile-derived path segment は path traversal / invalid filename 対策で sanitize します。

例:

- `../`
- slash / backslash
- NUL / control chars
- Windows reserved names
- trailing dot / space

user-selected save root 自体は separator normalization 以上に勝手に sanitize しません。

---

## 21. Tray の Restart Helper が external Helper を止めない

`Running (external)` の process は tray ownership 外です。

tray は他 process を勝手に terminate しません。

external Helper を自分で終了すると、tray monitor が Helper を起動できる状態になります。

---

## 22. 診断時に集める情報

共有してよいもの:

- OS
- Python version
- browser / Userscript manager
- ABDM version
- error code / HTTP status
- problem step
- sanitized log excerpt

共有しないもの:

- password
- Cookie
- Authorization header
- guest token
- Website Token
- direct/signed download URL
- private share URL

---

## 23. Developer checks

```bash
python -m unittest discover -s tests -v
node --test tests/test_userscript.cjs
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

CI はありません。release 前に実行結果と未実施項目を区別してください。

詳細な internal design は [`../DEVELOPMENT.md`](../DEVELOPMENT.md) と [`ARCHITECTURE.md`](ARCHITECTURE.md) を参照してください。
