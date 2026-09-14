# GoFile ABDM Helper 開発・保守ガイド

この文書は、`README.md` より内部実装寄りの情報をまとめた、開発継続・保守・AI への引き継ぎ用ドキュメントです。

開発を始める前に、少なくとも次を確認してください。

1. `README.md`
2. この `DEVELOPMENT.md`
3. `CHANGELOG.md`
4. `docs/ARCHITECTURE.md`
5. 最新の `main` のコード

仕様変更を行った場合は、コードだけでなく該当ドキュメントも同じ変更で更新してください。

---

## 1. 現在の状態

調査基準日: **2026-09-14**

- リポジトリ: `Hoyomaru/gofile-abdm-helper`
- デフォルトブランチ: `main`
- 調査時 `main` HEAD: `8359b5fb2d09d0919aedcdc72418994441126c3a`
- `VERSION`: `1.0.3`
- Userscript `@version`: `1.0.3`
- 安定版として文書化されている版: `v1.0.3`
- `main` には `v1.0.3` より後の **Unreleased** 変更として、子フォルダを含むパスワード保護ツリー対応が入っている
- Git tag は調査時点で `v1.0.0` と `v1.0.3` を確認
- GitHub Release は調査時点で未作成
- `.github/` / GitHub Actions workflow は調査時点で存在しない
- CI による自動テストは未導入

つまり、**`VERSION=1.0.3` だから `main` が v1.0.3 と完全一致するわけではありません。** 開発時は `CHANGELOG.md` の `[Unreleased]` と `main` のコードも必ず確認してください。

### 実機・テスト状況の区分

#### 確認済みとして履歴に残っているもの

`v1.0.3` の PR には次の検証結果が記録されています。

- `python -m unittest discover -s tests -v`: 41 tests passed
- `node --check gofile-abdm.user.js`: passed

これは **v1.0.3 リリース時点の記録**です。

#### 現在の `main` でコード上確認できるもの

- Python 単体テスト: `tests/test_core.py`
- Userscript の Node テスト: `tests/test_userscript.cjs`
- 子フォルダ別パスワード、資格情報継承、アクセス拒否 envelope、キャッシュ分離、SPA 遷移時の stale resolve 排除、パスワードモーダル終了経路などの回帰テストが存在する

#### 未確認 / 要検証

調査時点では CI がないため、**現在の `main` HEAD に対してこの調査中にテストが実行された事実は確認できません**。

また、次はコードや履歴だけでは実機確認済みと断定できません。

- 現在の GoFile 実サービス上でのパスワード付きルート / 子フォルダの E2E
- Violentmonkey と Tampermonkey の両方での同一挙動
- GoFile の `sessionStorage` 補助経路が各 Userscript manager で利用できること
- 現在の ABDM バージョンでの実ファイル取得完了までの E2E
- Linux 上での手動 Helper 運用

これらは **未確認** として扱ってください。

---

## 2. プロジェクトの責務

このプロジェクトは、GoFile のページ上で選択したファイルを AB Download Manager（ABDM）へ登録するための橋渡しです。

```text
GoFile page
  ↓
Userscript
  ↓ GM_xmlhttpRequest
Flask Helper (127.0.0.1:8765)
  ├─ GoFile API からツリー / direct URL / 必要ヘッダーを解決
  └─ ABDM REST API へタスク登録
       ↓
AB Download Manager (127.0.0.1:15151)
```

Python Helper 自身はファイル本体を保存しません。実ダウンロード、速度、ETA、pause/resume/cancel、履歴は ABDM の責務です。

---

## 3. 主要ファイルと責務

| ファイル | 主な責務 | 主な副作用 |
|---|---|---|
| `gofile-abdm.user.js` | GoFile UI 統合、選択、設定、resolve/send 呼び出し、パスワード入力 | GM ストレージ、DOM、localhost Helper への通信 |
| `app.py` | localhost Flask API、入力検証、resolve キャッシュ、GoFile resolve の直列化、ABDM 送信仲介 | メモリキャッシュ、GoFile/ABDM クライアント呼び出し |
| `gofile.py` | GoFile guest session、Website Token、フォルダ取得、再帰 resolve、パス安全化 | GoFile API 通信、guest token のプロセスメモリ保持 |
| `abdm.py` | ABDM queues 取得、接続確認、download task 登録 | ABDM REST API への GET/POST |
| `tray.py` | Windows tray、Helper プロセス監視、自動起動、ログ | Windows Registry、helper process、`helper.log` |
| `start-tray.cmd` | Windows で `pythonw.exe tray.py` を非表示起動 | tray process 起動 |
| `tests/test_core.py` | Python 側の主要回帰テスト | mock 中心。通常は外部通信なし |
| `tests/test_userscript.cjs` | Userscript resolve/password 状態機械の Node テスト | VM / fake DOM 上で実行 |
| `VERSION` | リリース版番号 | なし |

より大きな構造は [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) を参照してください。

---

## 4. Userscript の状態

`gofile-abdm.user.js` の `state` がブラウザ側の中心状態です。主要項目は次のとおりです。

- `sourceUrl`: 現在 resolve 対象として扱う URL
- `resolveId`: Helper が発行した不透明な resolve session ID
- `root`, `topLevel`, `currentLevel`, `nodeByKey`: 解決済みツリー
- `selectedKeys`: 解決済みノードの選択
- `provisionalSelectedIds`: resolve 前 / 失敗中に DOM 上で暫定選択した GoFile content ID
- `failedFileKeys`:直前の送信で失敗した file key
- `lastSendPreserveStructure`: Retry Failed 用の送信モード
- `lastSendQueueId`: Retry Failed 用の queue ID
- `passwordHashes`: content ID → SHA-256 digest
- `resolveGeneration`, `activeResolve`: stale resolve を無効化する世代管理
- `resolving`, `sending`: UI 操作抑止用フラグ

### resolve 状態遷移

```text
IDLE
  ↓ Load / navigation
RESOLVING
  ├─ password_required / wrong_password
  │      ↓
  │  PASSWORD_PROMPT
  │      ├─ Unlock → digest 更新 → RESOLVING
  │      └─ Cancel / Escape / 背景 / modal replacement → CANCELED
  ├─ success → READY
  └─ error   → ERROR（暫定選択は復元）
```

新しい navigation / Load が始まると世代を進め、以前の非同期 response は `isCurrentResolve()` で捨てます。

### send 状態遷移

```text
READY
  ↓ Send to ABDM / Send Flat
CHECK_ABDM
  ↓ connected
SENDING (1 file = 1 Helper request)
  ↓
RESULT
  ├─ all success
  └─ failedFileKeys → Retry Failed
```

送信進捗は **ABDM への登録進捗**であり、実ダウンロード進捗ではありません。

---

## 5. 永続化と一時状態

### Userscript GM ストレージ

永続化される UI 設定は次の3種類です。

| キー | 用途 |
|---|---|
| `gofile_abdm_last_save_folder` | 最後に使用した Save folder |
| `gofile_abdm_presets` | Save folder プリセット |
| `gofile_abdm_queue_id` | 選択中 ABDM queue ID |

パスワードや GoFile guest token はここへ保存しません。

### GoFile `sessionStorage` 補助

Userscript は password challenge 時に、対象 ID について `password|<content-id>` を一度だけ候補として読むことがあります。

- 全 storage を走査しない
- 値は 64 桁 SHA-256 hex の場合のみ候補にする
- Userscript 自身はこのキーへ保存しない
- 拒否された候補は繰り返し盲目的に使わない

### Helper メモリ

`app.py` には2種類の TTL 20分キャッシュがあります。

- `_source_cache`: 同じ GoFile source + credential map の再 resolve を抑える
- `_cache`: Userscript へ返す `resolve_id` から `ResolveResult` を引く

Helper 再起動で両方消えます。

`GoFileClient` の guest token も Helper プロセスのメモリ内だけです。

### Windows Registry / ログ

`tray.py` の **Start with Windows** は次を使用します。

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
value: GoFileABDMHelper
```

ログ:

```text
helper.log
helper.log.1
```

`helper.log` が 2 MiB を超えていた場合、**Helper 起動時**に `.1` へローテーションします。稼働中に連続監視して 2 MiB で即ローテーションする実装ではありません。

---

## 6. localhost Helper API

すべての `/api/*` リクエストは loopback からであることに加え、次の marker が必要です。

```http
X-GoFile-ABDM: 1
```

POST/PUT/PATCH は JSON 必須です。

### `GET /health`

tray の health check 用です。API marker は不要です。

### `GET /api/abdm/status`

ABDM の `GET /queues` を使って疎通確認します。

### `GET /api/abdm/queues`

ABDM queue 一覧を返します。ABDM エラー時は `502 abdm_offline`。

### `POST /api/gofile/resolve`

入力の中心:

```json
{
  "url": "https://gofile.io/d/<id>",
  "password_hashes": {
    "<content-id>": "<sha256-hex>"
  }
}
```

後方互換としてルート用の平文 `password` も受け付けます。この場合、64桁 hex に見えても **平文として SHA-256 を1回計算**します。

`password_hashes` は最大1000件で、キーは有効な content ID、値は64桁 hex に限定されます。

主なエラー分類:

| HTTP | code | 意味 |
|---:|---|---|
| 400 | `invalid_body`, `invalid_content`, `invalid_password_hashes` 等 | 入力不正 |
| 401 | `password_required`, `wrong_password` | password challenge |
| 403 | `content_access_denied` | password 以外を含むアクセス拒否 |
| 404 | `not_found` | GoFile content 不明 |
| 429 | `rate_limited` | GoFile rate limit |
| 502 | `website_token_rejected`, `gofile_error` | 上流 GoFile 側の失敗 |
| 500 | `internal_error` | 想定外。秘密値を応答へ含めない |

成功時、Userscript には tree metadata と不透明な file key を返します。direct URL / Cookie は返しません。

### `POST /api/abdm/send`

主な入力:

```json
{
  "resolve_id": "...",
  "file_keys": ["..."],
  "save_root": "D:/Downloads",
  "preserve_structure": true,
  "queue_id": 7
}
```

制限:

- `file_keys`: 1リクエスト最大1000件
- `save_root`: 最大1000文字、NUL 不可
- `queue_id`: integer または null
- expired `resolve_id`: HTTP 410 `resolve_expired`

現行 Userscript は通常1ファイルずつこの endpoint を呼びます。

---

## 7. 外部 API

### GoFile

コード上で直接使用している主な endpoint:

| Method | Endpoint | 用途 | 書き込み |
|---|---|---|---|
| POST | `https://api.gofile.io/accounts` | guest account/token 取得 | GoFile 側で guest session を作る |
| GET | `https://api.gofile.io/contents/<content-id>` | folder/file metadata 解決 | いいえ |

`/contents` は pageSize 1000 で pagination します。

認証関連 header:

- `Authorization: Bearer <guest-token>`
- `X-Website-Token`
- `X-BL`
- `User-Agent`
- `Origin`, `Referer`

`X-Website-Token` は固定 token ではなく、現在の実装では概ね次を SHA-256 します。

```text
User-Agent :: language :: guest-token :: 4-hour-window :: salt
```

`salt`、UA、language は環境変数で上書きできます。

### AB Download Manager

接続先は固定です。

```text
http://127.0.0.1:15151
```

使用 endpoint:

| Method | Endpoint | 用途 |
|---|---|---|
| GET | `/queues` | queue 一覧 / connection check |
| POST | `/start-headless-download` | download task 登録 |

送信するのは ABDM の公開 REST API に文書化された `downloadSource`、`folder`、`name`、`queueId` の範囲です。

---

## 8. 再試行・レート制限ポリシー

| 事象 | 現在の処理 |
|---|---|
| guest account 作成の通常通信失敗 | 最大3回、1.5秒刻みの待機 |
| guest account で 429 / API rate limit | 即停止、再試行しない |
| content request timeout | 最大4 attempt、2/4/6秒 backoff |
| content 429 / API rate limit | 即停止、再試行しない |
| Website Token reject | 現在 window 失敗後に前 window を試す経路あり |
| password required / wrong | 同じ resolve operation 内で資格情報を更新して同じ root を再 resolve |
| ABDM GET/POST 通信失敗 | 自動再試行しない |
| 個別 ABDM task 失敗 | 残りを継続し、`Retry Failed` 用に記録 |

GoFile recursive content request はデフォルト `0.75s` 間隔で pace します。`GOFILE_REQUEST_INTERVAL` で変更でき、0で無効化できます。

### resolve の排他

`app.py` の `_resolve_lock` により recursive resolve は直列化されます。待っている同一 resolve は lock 内でキャッシュを再確認します。

---

## 9. クラッシュ / 再起動時

### Helper 再起動

失われるもの:

- guest token
- `_source_cache`
- `resolve_id` キャッシュ
- Helper 側の in-flight 処理

残るもの:

- Userscript GM 設定
- tray の Windows startup 設定
- ログファイル

Userscript が持つ古い `resolve_id` は Helper 再起動後に無効になります。

### Browser reload / navigation

通常の selection、resolve tree、手入力した password digest はページメモリなので永続化されません。Save folder / preset / queue のみ GM storage から復元されます。

SPA navigation 中の古い resolve response は generation guard により無視されます。

### Tray

tray 自身が起動していれば 3秒間隔で Helper health を確認し、tray が所有する Helper が落ちた場合は再起動します。

---

## 10. 絶対に弱めない安全条件

次は、この実装で意図的に置かれている安全境界です。便利さのために安易に削除しないでください。

1. **Flask を LAN へ bind しない。** `127.0.0.1` のままにする。
2. **ABDM 接続先を任意ホスト入力にしない。** 現在は `127.0.0.1:15151` 固定。
3. **汎用 URL fetch endpoint を追加しない。** GoFile `/d/<id>` または bare content ID だけを受け付ける。
4. **Userscript の `@connect *` や `unsafeWindow` を安易に追加しない。**
5. **API marker と JSON guard を弱めない。** localhost もブラウザページから攻撃対象になり得る。
6. **GoFile の 429 を自動再試行しない。** rate limit 中の request 増幅を防ぐ。
7. **recursive resolve の直列化と request pacing を理由なく外さない。**
8. **`canAccess: false` を空フォルダ成功として扱わない。** 部分ツリーも成功としてキャッシュ / 送信しない。
9. **password 平文・guest token・Cookie・Authorization・direct URL をログへ出さない。**
10. **password 平文を cache key や永続 storage に保存しない。**
11. **Userscript へ direct URL / Cookie を返さない。** opaque file key を使う。
12. **GoFile 由来のファイル名 / 相対パスをサニタイズする。** 一方、ユーザーが明示した save root を勝手に別場所へ変換しない。
13. **GoFile direct link を任意 host として受け入れない。** HTTPS の `gofile.io` またはその subdomain に限定する。
14. **ABDM の非公開 / 推測 API を前提にしない。** 公開 REST 仕様と照合する。
15. **release 時に `VERSION` と Userscript `@version` を分離させない。** 意図的な例外なら CHANGELOG へ明記する。

---

## 11. 過去に確認された重要な問題と対策

### v1.0.1 — GoFile rate limit 耐性

症状 / リスク:
- resolve ごとに guest session を作ったり、recursive resolve が重なると request burst が起きやすい。

対策:
- Helper process 内で guest token を再利用。
- resolve を20分 cache。
- recursive resolve を直列化。
- 429 は即停止。

### v1.0.2 — 選択 UI の DOM 依存

症状:
- GoFile DOM の ID 属性差や resolve 前の状態により、選択できないケースがあった。

対策:
- `data-content-id`, `data-id`, `data-item-id`, `data-uuid` を扱う。
- provisional selection を導入。
- `Items` fallback selector を常時利用可能にする。

### v1.0.3 — resolve 失敗後の provisional checkbox 消失

症状:
- resolve 失敗後、DOM mutation がなければ provisional checkbox が復元されない。

原因:
- reset 時に自身の checkbox を消し、MutationObserver は自身の変更を除外するため、失敗後に再注入されない経路があった。

修正:
- `resolveContent()` の `finally` で未解決時に `injectCheckboxes()` を再実行。

### v1.0.3 — Userscript 側 180秒固定 timeout

症状:
- request pacing のある大きな recursive resolve が180秒を超え得る。

修正:
- resolve の `gmRequest(..., 0)` で Userscript 側 deadline を外した。
- Helper 内の個々の HTTP timeout は維持。

### Unreleased — password protected child folders

旧問題として実装計画に記録されていたもの:

- HTTP 200 `status: ok` でも `canAccess: false` を空成功として扱う可能性
- child folder が parent と別 password の場合の資格情報管理不足
- password modal を背景クリックで消すと Promise が未完了になる経路

現在の `main` では、それぞれ access envelope 判定、per-folder digest、modal completion guard が実装されています。

---

## 12. 現在の既知問題 / コードレビュー上の要注意点

以下は **今回のドキュメント調査でコードから確認したもの**です。今回コード修正は行っていません。実機での再現確認は別途必要です。

### [要検証] send 中に `resolve_expired` が起きた場合、選択が保持されない

`sendSelected()` は `resolve_expired` を受けると `resolveContent()` をデフォルト引数で呼びます。現在の `resetResolution(false)` は `selectedKeys` を消すため、再 resolve 後に元の batch を自動復元・再送しません。

影響:
- 長時間ページを開いた後の送信で 20分 TTL を跨いだ場合、ユーザーが選択し直す必要が生じる可能性。

### [要検証] send 中の SPA navigation は古い batch を停止しない

navigation 時の `invalidateResolve()` は resolve generation を無効化しますが、進行中 `sendSelected()` の for-loop には navigation generation / abort guard がありません。

影響:
- 送信途中に別 GoFile URL へ SPA 遷移した場合、旧ページの残りタスク登録が続く可能性。

### [要検証] ABDM POST の結果不明時に手動 Retry Failed すると重複し得る

ABDM への `POST /start-headless-download` は自動再試行しません。これは安全側です。ただし、ネットワーク timeout 等で「ABDM が登録したが Helper が成功 response を受け取れなかった」場合、Userscript は失敗として `Retry Failed` に含めます。

影響:
- ユーザーが手動 retry すると同じ task が重複登録される可能性。

現状、ABDM 側との idempotency key / 照合 API は利用していません。

### [仕様上の注意] log rotation は Helper 起動時のみ

`helper.log` が2 MiBを超えた瞬間に自動 rotate するのではなく、次の Helper start 時に判定します。

---

## 13. デバッグ

### Helper health

```text
http://127.0.0.1:8765/health
```

### Windows tray log

```text
helper.log
helper.log.1
```

ログへ request body / password / Cookie / token / direct URL を追加しないでください。

### Browser

- GoFile ページの Developer Tools Console
- Userscript manager の実行状態 / permission
- `127.0.0.1` への GM request permission

### ABDM

- ABDM 自体が起動しているか
- `127.0.0.1:15151` の REST API が利用可能か
- Settings で queue 一覧が取得できるか

### 問題報告時に欲しい情報

秘密情報を除外したうえで、次を集めると切り分けしやすくなります。

- OS / Python version
- Userscript manager と version
- ABDM version
- `VERSION` と Git commit SHA
- 問題発生操作（Load / Send / Send Flat / Retry Failed 等）
- Helper の error code / HTTP status
- `helper.log` の該当時刻付近（秘密情報を再確認してから共有）
- GoFile の content ID は必要性を確認してから共有し、private share URL や password は公開 Issue に貼らない

---

## 14. 開発環境とテスト

Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Python test:

```bash
python -m unittest discover -s tests -v
```

Userscript Node test:

```bash
node --test tests/test_userscript.cjs
```

Syntax check:

```bash
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

`tray.py` は Windows 固有 API を import するため、非 Windows での扱いには注意してください。

### 現在 CI はない

`.github/workflows/` は存在しません。したがって、PR / push 時にテストが自動実行される前提で作業しないでください。

---

## 15. リリース前チェックリスト

詳細は [`docs/RELEASE.md`](docs/RELEASE.md) を参照してください。

最低限:

- [ ] `VERSION` と Userscript `@version` を確認
- [ ] `CHANGELOG.md` を更新
- [ ] Python tests
- [ ] Node Userscript tests
- [ ] Python / JS syntax check
- [ ] README / DEVELOPMENT / docs を現行コードと再照合
- [ ] localhost bind / API marker / URL validation / path sanitization を弱めていない
- [ ] 429 の即停止を維持
- [ ] password / token / Cookie / direct URL をログ・docs・test fixture に混入させていない
- [ ] 実機 smoke test の実施範囲を記録
- [ ] Tag / Release の作成方針を確認

---

## 16. 今後の開発ルール

### 開始時

1. `README.md`
2. `DEVELOPMENT.md`
3. `CHANGELOG.md`
4. `docs/ARCHITECTURE.md`
5. 最新コード

を確認する。

### 終了時

1. コード
2. tests
3. README
4. DEVELOPMENT
5. CHANGELOG
6. 必要な `docs/*`

を同期する。

### 変更を避けるべきやり方

- ドキュメントへ合わせるために動いているコードを勝手に変える
- 実機未確認を「確認済み」と書く
- GoFile / ABDM の非公開仕様を推測で確定事項にする
- security boundary を「ローカルだから不要」と削除する
- rate limit 対策を速度だけを理由に解除する
- password / token / Cookie をデバッグ出力へ足す
- `main` の Unreleased と stable tag を混同する

---

## 17. 関連資料

- [`README.md`](README.md) — 利用者向けの主要文書
- [`CHANGELOG.md`](CHANGELOG.md) — バージョン履歴 / Unreleased
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — コンポーネント / trust boundary / data flow
- [`docs/RELEASE.md`](docs/RELEASE.md) — リリース手順と現状
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) — 詳細な問題切り分け
- `docs/Password-Protected-Folders-Luna-Implementation-Plan.md` — パスワード対応実装前の調査・計画資料。現在は実装済み内容を含むため、**現行仕様の正本としては使わない**
