# トラブルシューティング

GoFile ABDM Helper の詳細な問題切り分け手順です。

基本方針は **症状 → 原因候補 → 確認 → 対処** の順です。

秘密情報を含むため、password、Cookie、Authorization header、guest token、direct download URL、private share URL を公開 Issue やログへ貼らないでください。

---

## 1. `Python Helper is offline.`

### 症状

- Userscript が Helper offline と表示する
- Load / Send が localhost 接続エラーになる

### 原因候補

- `app.py` が起動していない
- Windows tray が起動していない / Helper start に失敗した
- Python dependency が不足
- port 8765 を別 process が使用

### 確認

Browser で次を開きます。

```text
http://127.0.0.1:8765/health
```

期待値は JSON の `ok: true` です。

Windows tray 使用時は tray status と `helper.log` を確認します。

### 対処

手動:

```bash
python -m pip install -r requirements.txt
python app.py
```

Windows tray:

```text
start-tray.cmd
```

tray に `Running (external)` と出る場合、別に起動した Helper がすでに port 8765 を使用しています。tray は外部 process を勝手に終了しません。

---

## 2. `pythonw.exe was not found in PATH.`

### 症状

`start-tray.cmd` 実行時に上記メッセージが出る。

### 原因候補

- Python が未導入
- `pythonw.exe` を含む Python install directory が PATH から見えない

### 対処

まず通常の command line で確認します。

```bat
where python
where pythonw
python --version
```

Python install / PATH を修正後、`start-tray.cmd` を再実行します。

---

## 3. Windows 起動時に tray が立ち上がらない

### 症状

以前 **Start with Windows** を有効にしたが login 後に tray がない。

### 実装上の保存場所

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
value: GoFileABDMHelper
```

### 確認

1. 一度 `start-tray.cmd` を手動起動
2. tray の **Start with Windows** が check 済みか確認
3. Python の配置場所を変更していないか確認

登録値は `pythonw.exe tray.py` の実パスと一致している必要があります。Python / project directory を移動した場合、一度 off → on にして再登録してください。

---

## 4. `ABDM Offline`

### 症状

- toolbar が `ABDM Offline`
- Settings の queue が取得できない
- Send 前に offline error

### 原因候補

- AB Download Manager が起動していない
- localhost REST API / browser integration が利用できない
- port `15151` で応答していない

### 実装が確認に使う endpoint

```text
GET http://127.0.0.1:15151/queues
```

### 対処

ABDM を起動し、REST API が default port 15151 で利用可能な状態にします。

この project は ABDM 接続先を任意 host / port へ変更する UI を持ちません。

---

## 5. queue が Settings に出ない

### 症状

ABDM は Connected だが期待する queue がない。

### 確認

Settings を閉じて再度開きます。Settings open ごとに `/queues` を取得します。

以前保存した queue ID が ABDM 側でなくなっている場合、`Unavailable queue (#...)` として表示される場合があります。

### 対処

- ABDM 側で queue を確認
- Settings で別 queue を選択
- または `Default (ABDM)` に戻す

`Default (ABDM)` は `queueId` field を省略します。

---

## 6. `website_token_rejected`

### 症状

GoFile resolve が `website_token_rejected` で失敗する。

### 原因候補

GoFile が Website Token の salt、User-Agent、language 等の検証条件を変更した可能性があります。

### 現在の設定項目

- `GOFILE_WT_SALT`
- `GOFILE_USER_AGENT`
- `GOFILE_LANGUAGE`

Windows PowerShell 例:

```powershell
$env:GOFILE_WT_SALT="current-value"
python app.py
```

### 注意

古い固定 Website Token をコードへ貼り付ける方式へ安易に戻さないでください。現在は guest token / time window 等から動的生成しています。

実際に新しい salt が必要かどうかは、GoFile 側の現行実装を再調査してから判断してください。

---

## 7. `rate_limited` / HTTP 429

### 症状

resolve が rate limit で停止する。

### 現在の挙動

- recursive content request はデフォルト 0.75秒間隔
- HTTP 429 / API rate limit を受けたら **その resolve は即停止**
- rate limit を自動 retry しない
- 同一の成功済み resolve は20分 cache される

### 対処

時間を置いてから再試行します。

rate limit 中に Load を連打しないでください。

`GOFILE_REQUEST_INTERVAL` で pacing を変更できますが、rate limit を避けるための安全策なので、速度だけを理由に 0 へすることは推奨しません。

---

## 8. resolve が長時間かかる

### 症状

大きな folder tree で Load が長い。

### 原因候補

recursive folder 数が多く、各 content request を pace している。

`v1.0.3` では 242 request を想定した regression test があり、0.75秒 pacing だけで約180.75秒になることを確認する test が追加されています。

### 現在の設計

Userscript 側の resolve に固定180秒 timeout は設定していません。

Helper 内の個々の HTTP request timeout は別に存在します。

### 対処

- progress / error を待つ
- rate limit でなければ無闇に Load を連打しない
- Helper log を確認

---

## 9. password prompt が出る

### 症状

GoFile folder の resolve 中に password prompt が表示される。

### 現在の動作

- root と child folder で別 password を扱える
- plaintext は Browser 側で SHA-256 化して Helper へ digest map として渡す
- wrong password の場合、その folder の digest を更新して同じ root を再 resolve
- Cancel / Escape / 背景 click で中止可能
- empty password は送信しない

GoFile page がすでに解除済みの場合、`sessionStorage` の `password|<content-id>` digest を一度だけ候補として使う場合があります。

### 対処

正しい password を入力するか Cancel します。

password を公開 Issue / `helper.log` へ記録しないでください。

---

## 10. `wrong_password` が繰り返される

### 原因候補

- 入力 password が違う
- parent と child で password が異なる
- GoFile 側の access state が変わった
- `sessionStorage` の補助 digest が古く、最初の1回が reject された

### 対処

表示される Target path を確認し、その folder の password を入力します。

補助 storage 値は一度 reject されたら同一 operation で無限再利用しない設計です。

---

## 11. `content_access_denied`

### 症状

password prompt ではなく 403 系 access denied になる。

### 意味

GoFile response が access 不可を示しているが、現在の Helper が password challenge として分類できない状態です。

### 対処

- share がまだ有効か確認
- browser の通常 GoFile UI で access 可能か確認
- private / expired / その他制限の可能性を確認

正確な理由が response から分からない場合、Helper は推測で password prompt を出しません。

---

## 12. チェックボックスが一部表示されない

### 原因候補

GoFile の DOM structure が変化し、row matching ができない。

### 現在対応している識別子

- `data-content-id`
- `data-id`
- `data-item-id`
- `data-uuid`

link / filename fallback もあります。

### 対処

toolbar の **Items** を開き、fallback tree selector を使用します。

DOM row matching が壊れても Helper の resolve/send 自体は row class に依存しません。

---

## 13. Helper resolve 前でも選択したい

表示中 row に content ID がある場合は provisional checkbox が使えます。

選択後、Send の直前または Load 成功時に解決済み tree と照合します。

ただし、ABDM へ送るには direct URL / headers が必要なので、最終的には resolve success が必要です。

---

## 14. `Resolved GoFile session expired.`

### 症状

送信時に resolve session expired と表示される。

### 原因

Helper の resolve cache TTL は20分です。Helper 再起動でも cache は消えます。

### 現在のコード上の注意

Userscript は `resolve_expired` を受けると再 resolve を開始しますが、現在の実装ではこの経路が元の `selectedKeys` を自動保持して batch を再送する保証はありません。

### 対処

1. resolve が完了するのを待つ
2. selection を再確認
3. 必要なら再選択
4. Send を実行

これは現在 **要検証の既知事項**です。詳細は `DEVELOPMENT.md` を参照してください。

---

## 15. `Send to ABDM` で folder structure が期待どおりにならない

### Save folder が空の場合

Helper は ABDM の optional `folder` field を省略します。

そのため「ABDM の default directory + GoFile relative subfolder」を Helper 側から確実に指定できません。

### 対処

folder structure を確実に保ちたい場合は明示的な root を指定します。

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

Flat にしたい場合は **Send Flat** を使います。

---

## 16. 同じ download task が ABDM に重複した

### 原因候補

`POST /start-headless-download` の response を Helper が受け取れない network failure が起きたが、ABDM 側では task 登録が完了していた可能性があります。

その file は client から見ると failed になり、`Retry Failed` で再送すると重複する可能性があります。

### 現在の設計

- Helper は ABDM POST を自動 blind retry しない
- ABDM task の idempotency key / 照合 API は現在使用していない
- `Retry Failed` はユーザー操作

### 対処

通信 timeout / connection reset 直後の Retry Failed は、まず ABDM task list に同じ item が入っていないか確認してください。

---

## 17. Send 中に別の GoFile page へ移動した

### 現在のコード上の注意

resolve には stale response guard がありますが、進行中の send loop には navigation generation guard がありません。

したがって send 中の SPA navigation では、旧 page の残り task 登録が続く可能性があります。

### 対処

送信 progress が完了してから別 share へ移動する運用を推奨します。

これは現在 **要検証の既知事項**です。

---

## 18. `helper.log` が 2 MiB を超えている

### 現在のローテーション方式

`tray.py` は Helper を起動する際に log size を確認します。

2 MiB を超えていれば:

```text
helper.log -> helper.log.1
```

既存 `.1` は置き換えます。

### 注意

稼働中に常時監視して 2 MiB 到達時点で即 rotate する方式ではありません。

---

## 19. GoFile download link が reject される

Helper は解決済み direct link を無条件で受け入れません。

必要条件:

- scheme: `https`
- hostname: `gofile.io` または `*.gofile.io`

GoFile API behavior が将来変化し、正規の download domain がこの条件外になった場合はコード調査が必要です。セキュリティ確認なしに任意 host 許可へ広げないでください。

---

## 20. Test が動かない

### Python dependency

```bash
python -m pip install -r requirements.txt
```

### Python tests

```bash
python -m unittest discover -s tests -v
```

### Node tests

```bash
node --test tests/test_userscript.cjs
```

### Syntax

```bash
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

`tests/test_core.py` は Flask が import できない環境では一部 Flask test を skip する設計ですが、`requests` など主要 dependency がない場合は import 自体が成立しないことがあります。release 判定では dependency を入れた環境で全 test を実行してください。

---

## 21. 問題報告前チェック

- [ ] `VERSION`
- [ ] commit SHA
- [ ] OS
- [ ] Python version
- [ ] Userscript manager / version
- [ ] ABDM version
- [ ] Helper `/health`
- [ ] ABDM Connected / Offline
- [ ] 操作モード（Send Flat / structure）
- [ ] error code / HTTP status
- [ ] `helper.log` の秘密情報確認済み抜粋
- [ ] 再現手順

private password、Cookie、token、Authorization、direct URL、署名付き URL は貼らないでください。
