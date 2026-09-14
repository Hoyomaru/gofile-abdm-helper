# GoFile ABDM Helper

**安定版:** `v1.0.3`  
**開発状態:** `main` には `v1.0.3` より後の `[Unreleased]` 変更が含まれています。

GoFile の既存ページに Userscript の UI を追加し、選択したファイル / フォルダを localhost 専用の Python Helper 経由で **AB Download Manager (ABDM)** へ登録する個人利用向けツールです。

> **非公式ツールです。** GoFile および AB Download Manager の公式プロジェクトとは無関係です。

Python 側がファイル本体をダウンロードするわけではありません。GoFile のメタデータと download 情報を解決し、ABDM に download task を登録します。

```text
GoFile page
    ↓
Userscript
    ↓ GM_xmlhttpRequest
Flask Helper (127.0.0.1:8765)
    ↓
AB Download Manager (127.0.0.1:15151)
```

独立した Flask Web UI はありません。

---

## 主な機能

- GoFile ページへ選択 checkbox / toolbar を追加
- file / folder 選択
- folder の recursive resolve
- resolve 前や rate limit 中でも可能な provisional selection
- DOM row を対応付けられない場合の **Items** fallback selector
- **Send to ABDM**: GoFile folder structure を保持して登録
- **Send Flat**: GoFile folder structure を無視して登録
- ABDM queue 選択
- Save folder と preset
- file 単位の送信結果
- **Retry Failed**
- GoFile guest session / dynamic Website Token
- password protected root / child folder の resolve（現在の `main` の `[Unreleased]` を含む）
- GoFile rate-limit 対策
- Windows tray / Helper 自動監視
- Windows user login 時の自動起動

### このツールが解決する問題

GoFile の Web UI で見えている file / folder を、browser から直接保存する代わりに ABDM の task としてまとめて登録できるようにします。recursive folder、保存先 root、queue、Flat / structure の選択を GoFile page 上で行えます。

### 想定ユーザー

- GoFile の共有 URL を通常の browser で利用している
- AB Download Manager を local PC で使用している
- Userscript manager を利用できる
- localhost の Python Helper を自分で起動できる

---

## Stable と `main` の違い

`VERSION` と Userscript `@version` は現在どちらも `1.0.3` です。

一方、現在の `main` には `CHANGELOG.md` の `[Unreleased]` として、`v1.0.3` の後に実装された password-protected child folder 対応が含まれています。

したがって:

- **stable release の仕様確認** → tag `v1.0.3`
- **現在開発中の最新仕様確認** → `main` + `[Unreleased]`

として区別してください。

---

## 動作環境

### 必須

- Python **3.10+**
- `requirements.txt` の Python packages
- Violentmonkey（主な対象）または Tampermonkey
- AB Download Manager
- GoFile へ HTTPS 接続できるネットワーク

Python dependencies:

```text
Flask>=3.0,<4
requests>=2.31,<3
pystray>=0.19,<1
Pillow>=10,<13
```

### OS

- **Windows:** tray launcher / Start with Windows を含む主要対象
- **その他 OS:** `python app.py` で Helper 自体を直接起動するコード構成。tray は Windows 専用

Linux/macOS を含む各 OS での最新 `main` の実機確認状況は、このリポジトリだけからは確認できないため **未確認** とします。

### Browser

Userscript metadata は `https://gofile.io/*` を対象にしています。

Violentmonkey を主な対象としており、Tampermonkey も想定していますが、各 browser / manager / version の網羅的な動作確認表はありません。

### AB Download Manager

接続先は意図的に固定です。

```text
http://127.0.0.1:15151
```

現在使用する公開 REST endpoint:

```text
GET  /queues
POST /start-headless-download
```

別 PC の ABDM を接続先にする設定はありません。

---

## ファイル構成

```text
project/
├─ gofile-abdm.user.js           # Browser UI / selection / send
├─ app.py                        # localhost Flask Helper
├─ gofile.py                     # GoFile API / recursive resolve
├─ abdm.py                       # ABDM REST API client
├─ tray.py                       # Windows tray / process monitor
├─ start-tray.cmd                # Windows tray launcher
├─ requirements.txt
├─ VERSION
├─ README.md
├─ DEVELOPMENT.md
├─ CHANGELOG.md
├─ LICENSE
├─ LICENSES/
│  └─ optional-license-notices.txt
├─ docs/
│  ├─ ARCHITECTURE.md
│  ├─ RELEASE.md
│  ├─ TROUBLESHOOTING.md
│  └─ Password-Protected-Folders-Luna-Implementation-Plan.md
└─ tests/
   ├─ test_core.py
   └─ test_userscript.cjs
```

`templates/` / `static/` は使用しません。

`docs/Password-Protected-Folders-Luna-Implementation-Plan.md` は password feature **実装前の調査・計画資料**を含みます。現行仕様の正本としては使用せず、現在のコード、`CHANGELOG.md`、`DEVELOPMENT.md` を優先してください。

---

# インストール

## 1. AB Download Manager を用意

ABDM をインストールして起動します。

Helper は次へ接続します。

```text
127.0.0.1:15151
```

## 2. Python dependencies

```bash
python -m pip install -r requirements.txt
```

## 3. Helper を起動

### Windows: tray mode（推奨）

```text
start-tray.cmd
```

`tray.py` が `pythonw.exe` で起動し、terminal を常時表示せず Helper を監視します。

tray menu:

- **Helper: Running / Stopped**
- **Restart Helper**
- **Open Folder**
- **View Log**
- **Start with Windows**
- **Exit**

### Start with Windows

tray の **Start with Windows** を有効にすると、現在の Windows user の次へ登録します。

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
value: GoFileABDMHelper
```

管理者権限を必要とする system-wide startup ではありません。

### Manual Helper

```bash
python app.py
```

bind 先:

```text
127.0.0.1:8765
```

health check:

```text
http://127.0.0.1:8765/health
```

## 4. Userscript

Violentmonkey / Tampermonkey で新しい Userscript を作成し、`gofile-abdm.user.js` の内容を入れます。

許可する cross-origin connect は次だけです。

```text
127.0.0.1
localhost
```

`@connect *` / `unsafeWindow` は使用していません。

## 5. GoFile を開く

通常どおり共有 URL を開きます。

```text
https://gofile.io/d/xxxxxxxx
```

GoFile page に ABDM toolbar が追加されます。

---

# 使用方法

1. ABDM を起動
2. Helper / tray を起動
3. GoFile share を開く
4. resolve 完了を待つ
5. file / folder を checkbox で選択
6. 必要なら **Select All** / **Clear** / **Items** を使用
7. 必要なら **⚙** で queue / Save folder / preset を設定
8. 送信モードを選ぶ
   - **Send to ABDM**: structure 保持
   - **Send Flat**: structure を無視
9. ABDM への登録進捗を確認
10. 一部失敗時は結果を確認し、必要なら **Retry Failed**

表示される progress は **ABDM への task 登録進捗**です。実際の download % / speed / ETA ではありません。

---

## 選択の仕組み

Userscript は GoFile の単一 class 名に固定せず、既知の content ID 属性を優先します。

- `data-content-id`
- `data-id`
- `data-item-id`
- `data-uuid`

その後 link、最後に保守的な filename text matching を使用します。

### Items fallback

GoFile DOM が変わって row と tree を対応付けられない場合でも、**Items** から解決済み tree を直接選択できます。

### Provisional selection

Helper resolve が一時的に失敗していても、visible row に content ID があれば provisional checkbox で選択できます。

最終送信には direct URL / headers の解決が必要なので、送信前には resolve success が必要です。

### Folder selection

folder を選択すると descendant file を recursive に選択対象にします。

---

# 設定

Settings（**⚙**）で管理するもの:

| 設定 | 保存 | デフォルト / 動作 |
|---|---|---|
| Download queue | GM storage | `Default (ABDM)` = `queueId` を省略 |
| Save folder | GM storage | 空 = ABDM の `folder` を省略 |
| Save preset | GM storage | name + path の一覧 |

GM storage key:

```text
gofile_abdm_queue_id
gofile_abdm_last_save_folder
gofile_abdm_presets
```

password はこの GM storage へ永続保存しません。

### Queue

Settings を開くたび、Helper 経由で ABDM の `/queues` を取得します。

- **Default (ABDM)**: `queueId` を送らない
- named queue: integer ID を送る

以前保存した queue が消えている場合は unavailable として扱い、別 queue または Default を選び直せます。

---

# 保存先と送信モード

## Send Flat

GoFile の relative folder を無視します。

Save folder が空なら ABDM の optional `folder` field を省略します。

## Send to ABDM

Save root がある場合:

```text
D:/Downloads
```

GoFile:

```text
Anime/Subs/Episode01.ass
```

ABDM へ渡す folder:

```text
D:/Downloads/Anime/Subs
```

### 重要な制限

Save folder が空の場合、Helper は ABDM の `folder` field を省略します。

現在使用している ABDM REST 仕様には「ABDM の未知の default directory に relative subfolder だけを追加する」操作は確認できないため、**structure を確実に保持したい場合は明示的な Save root を指定してください。**

---

# パスワード保護コンテンツ

現在の `main` では root だけでなく child folder の password challenge も扱います。この変更は `CHANGELOG.md` 上 `[Unreleased]` です。

動作:

1. GoFile が password challenge を返す
2. Userscript が対象 folder path を表示
3. password を browser 内で SHA-256
4. content ID → digest map を Helper へ送る
5. 同じ root から再 resolve

parent と child で異なる password を指定できます。

wrong password の場合はその folder の digest を更新します。

Cancel / Escape / popup 背景 click で cancel できます。empty password は送信しません。

### GoFile `sessionStorage` 補助

GoFile page 側で解除済みの場合、Userscript は対象 ID の次の key を一度だけ候補として読むことがあります。

```text
password|<content-id>
```

- 64桁 SHA-256 hex のみ候補
- 全 storage を走査しない
- Userscript 自身はここへ password / digest を保存しない
- reject された値を同じ operation で無限 retry しない

---

# GoFile guest access / Website Token

Premium / account token 入力 UI はありません。

Helper は guest account token を取得し、現在の実装では概ね次を SHA-256 して `X-Website-Token` を生成します。

```text
User-Agent :: language :: guest-account-token :: 4-hour-window :: salt
```

環境変数:

- `GOFILE_WT_SALT`
- `GOFILE_USER_AGENT`
- `GOFILE_LANGUAGE`
- `GOFILE_REQUEST_INTERVAL`

GoFile の実装が変わった場合は、現在の GoFile behavior を再確認してから更新してください。

---

# Rate limit / cache

Helper は GoFile API request を増幅させないようにしています。

- Helper process 中は guest session / token を再利用
- 成功 resolve を20分 cache
- cache key は root content ID + credential map 由来 hash
- recursive resolve は process 内で直列化
- content request はデフォルト0.75秒 pace
- HTTP/API rate limit は **即停止し、自動 retry しない**

`GOFILE_REQUEST_INTERVAL` で interval を変更できます。

```bash
GOFILE_REQUEST_INTERVAL=1.0 python app.py
```

`0` で pacing を無効化できますが、rate-limit safety を弱める可能性があります。

Helper restart で guest token と memory cache は消えます。

---

# Windows tray / ログ

`tray.py` は Windows 専用です。

Helper health を3秒間隔で確認し、tray 自身が管理する Helper が停止した場合は再起動します。

すでに別 process の Helper が動いている場合は `Running (external)` とし、その process を終了しません。

log:

```text
helper.log
helper.log.1
```

`helper.log` が2 MiBを超えている場合、**Helper start 時**に `.1` へ rotate します。

request body、password、Cookie、guest token、Authorization header、direct URL を意図的に log へ出す実装にはしないでください。

---

# 更新

## Git clone で管理している場合

Helper / tray を停止し、local modification を確認してから更新します。

例:

```bash
git pull --ff-only
python -m pip install -r requirements.txt
```

その後:

1. Helper / tray を再起動
2. Userscript manager 内の script を repository の最新 `gofile-abdm.user.js` と同期
3. `VERSION` / `CHANGELOG.md` を確認

### 注意

Userscript metadata に自動 update URL は設定されていないため、repository 更新だけで browser 内 script が自動的に置き換わる前提にしないでください。

## 手動配置の場合

既存設定を確認したうえで project files を新しい版へ置き換え、`requirements.txt` を再適用し、Userscript 内容も更新します。

release ごとの互換性注意は `CHANGELOG.md` を確認してください。

---

# アンインストール

## Windows tray を使用している場合

1. tray の **Start with Windows** を off
2. tray の **Exit**
3. Userscript manager から GoFile ABDM Helper を削除
4. project directory を削除

Start with Windows を off にすると、この app の HKCU Run value を削除します。

## 手動 Helper の場合

1. `python app.py` を停止
2. Userscript を削除
3. project directory を削除

### 残る可能性があるもの

- Userscript manager 側の GM storage（削除方法は manager に依存）
- Python packages（他 project と共有している可能性があるため、この project は自動削除しない）
- project directory を残す場合 `helper.log` / `helper.log.1`

GoFile password / guest token / resolve cache は Helper / page memory のため、process / page 終了で失われます。

---

# 技術仕様

## 使用言語

- Python
- JavaScript Userscript
- Windows CMD launcher

## Python libraries

- Flask
- requests
- pystray
- Pillow

## Helper API

```text
GET  /health
GET  /api/abdm/status
GET  /api/abdm/queues
POST /api/gofile/resolve
POST /api/abdm/send
```

`/api/*` には次が必要です。

```http
X-GoFile-ABDM: 1
```

POST/PUT/PATCH は JSON を要求します。

## 内部処理

```text
GoFile URL / content ID
 ↓ validate
resolve cache
 ↓ miss
GoFile guest token / Website Token
 ↓
recursive folder resolve
 ↓
public tree + opaque file keys
 ↓ user selection
file key lookup in Helper memory
 ↓
path sanitize / folder build
 ↓
ABDM task registration
```

詳細: [`DEVELOPMENT.md`](DEVELOPMENT.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

# データと状態

## 永続

Userscript GM storage:

- queue ID
- last Save folder
- presets

Windows:

- optional HKCU startup entry
- `helper.log`, `helper.log.1`

## process / page memory

- GoFile guest token
- resolved content cache
- resolve ID cache
- selection
- password digest map
- failed file keys

DB / Redis / persistent server queue はありません。

---

# 再開・復旧

- **Helper crash:** tray mode なら health monitor が再起動を試みる
- **Helper restart:** memory cache / guest token / resolve ID は失われる
- **Browser reload:** selection / resolve tree / hand-entered password state は失われる。GM settings は残る
- **GoFile rate limit:** 自動 retry せず user が後で再試行
- **ABDM individual send failure:** 残りを継続し `Retry Failed` 候補へ記録

詳細な既知事項は `DEVELOPMENT.md` を参照してください。

---

# セキュリティ

現在の重要な制限:

- Flask は `127.0.0.1` のみ
- ABDM は `127.0.0.1:15151` 固定
- GoFile `/d/<id>` / bare content ID のみ受理
- generic URL fetch endpoint なし
- `/api/*` request marker 必須
- JSON guard
- permissive CORS を追加していない
- GoFile path segment を sanitize
- direct link は HTTPS + `gofile.io` / subdomain に限定
- password / token / Cookie / direct URL を log しない
- direct URL / Cookie を Userscript へ返さない
- 429 を blind retry しない
- password/access-denied folder を部分成功として cache しない

詳細と「絶対に弱めない条件」は [`DEVELOPMENT.md`](DEVELOPMENT.md) を参照してください。

---

# 既知の制限 / 要検証

### 現在の仕様上の制限

- Python 自身は file downloader ではない
- transfer speed / ETA / pause / resume / cancel は ABDM 側
- Save root 空のまま未知の ABDM default folder へ relative subfolder を確実に追加できない
- Windows tray は Windows 専用
- GitHub Actions / CI は未導入
- GitHub Releases は調査時点で未作成

### コード確認で見つかった要検証事項

次は今回勝手に修正していません。

- `resolve_expired` からの再 resolve で元 selection を自動保持・再送しない可能性
- send 中の SPA navigation で旧 batch の残り送信が継続する可能性
- ABDM POST の結果不明時、手動 **Retry Failed** で task が重複する可能性

詳細: [`DEVELOPMENT.md`](DEVELOPMENT.md)

---

# 意図的に実装していない機能

- Premium / Account Token 入力 UI
- browser 直接 download
- Aria2 / IDM / JDownloader 等の downloader selector
- Python file streaming / downloader
- download history database
- dashboard
- React / Vue
- Docker
- persistent server-side queue
- Redis / Celery
- multi-user / LAN service

---

# テスト

Python:

```bash
python -m unittest discover -s tests -v
```

Userscript Node tests:

```bash
node --test tests/test_userscript.cjs
```

Syntax:

```bash
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

テストは mock / VM を中心にしており、通常は GoFile / ABDM への実通信を目的としません。

`v1.0.3` の PR には当時 `41 tests passed` と `node --check` pass の記録がありますが、現在の `main` にはその後の変更があるため、release 前には改めて実行してください。

---

# トラブルシューティング

代表例のみここに記載します。詳細は [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) を参照してください。

## Helper Offline

```text
http://127.0.0.1:8765/health
```

を確認し、必要なら `python app.py` または `start-tray.cmd` を起動します。

## ABDM Offline

ABDM を起動し、`127.0.0.1:15151` の `/queues` が利用可能な状態か確認します。

## `website_token_rejected`

GoFile の Website Token 条件が変わった可能性があります。現行 GoFile behavior を再調査し、必要なら `GOFILE_WT_SALT` 等を更新します。

## `rate_limited`

Helper は自動 retry しません。時間を置いて再試行してください。

## checkbox が表示されない

**Items** fallback selector を使用してください。

---

# 診断

問題報告時は、秘密情報を除外して次を確認してください。

- OS
- Python version
- Userscript manager / version
- ABDM version
- `VERSION`
- Git commit SHA
- Helper `/health`
- error code / HTTP status
- 再現操作
- `helper.log` の安全な範囲

private share URL、password、Cookie、token、Authorization、direct URL は公開しないでください。

---

# 開発者向け資料

- [DEVELOPMENT.md](DEVELOPMENT.md) — 内部実装、状態、API、安全条件、既知問題、開発引き継ぎ
- [CHANGELOG.md](CHANGELOG.md) — release / Unreleased 履歴
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — component / data flow / trust boundary
- [docs/RELEASE.md](docs/RELEASE.md) — release 現状と手順
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — 詳細 troubleshooting

---

# 参考にしているプロジェクト

この project は source file をそのまま取り込むのではなく、挙動 / API / architecture の参考として次を確認して実装されたと repository 内で記録されています。

- `ewigl/gofile-enhanced`
- `martadams89/gofile-dl`
- `amir1376/ab-download-manager`

第三者通知は [`LICENSES/optional-license-notices.txt`](LICENSES/optional-license-notices.txt) を参照してください。

現在の ABDM integration は、公開 `REST-API.yml` の `GET /queues` と `POST /start-headless-download` を使用します。

---

# License

MIT License。[`LICENSE`](LICENSE) を参照してください。
