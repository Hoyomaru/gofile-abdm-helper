# GoFile ABDM Helper

**現在のリリース:** `v1.2.1`  
**リリース日:** 2026-09-27

GoFile の既存ページに Userscript の UI を追加し、選択したファイル / フォルダを localhost 専用の Python Helper 経由で **AB Download Manager (ABDM)** へ登録する個人利用向けツールです。

> **非公式ツールです。** GoFile および AB Download Manager の公式プロジェクトとは無関係です。

Python Helper 自身がファイル本体を保存するわけではありません。GoFile のメタデータと download 情報を解決し、ABDM に download task を登録します。

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
- root / child folder の password challenge 対応
- parent から child への password credential 継承
- resolve 前や rate limit 中でも使える provisional selection
- DOM row を対応付けられない場合の **Items** fallback selector
- **ABDMへ送信**: 1つのprimary actionから送信
- **フォルダ構造を維持**: ONでstructure保持、OFFでflat送信
- ABDM queue 選択
- Save folder と preset
- file 単位の送信結果と error detail
- **Retry Failed** / **Cancel Send**
- ABDM POST の結果不明時を `Uncertain` として分離し、blind retry を防止
- `resolve_id` expiry 時の content ID ベース再 resolve / 残り送信再開
- GoFile guest session / dynamic Website Token
- 20分の resolve cache
- recursive resolve の直列化と request pacing
- Windows tray / Helper 自動監視・hung process recovery
- Windows user login 時の自動起動
- Windows向け1ステップ setup（ローカル .venv 作成・依存導入・tray起動）
- Settings の自己診断で Helper / ABDM / Queue 接続を一括確認
- GitHub Actions による Python / Userscript regression test

### このツールが解決する問題

GoFile の Web UI で表示している file / folder を、AB Download Manager の task としてまとめて登録できます。recursive folder、保存先 root、ABDM queue、Flat / structure の選択を GoFile page 上で行えます。

---

## v1.2.1 について

`v1.2.1` は、新機能を追加せず既存機能の信頼性・安全性・保守性を改善したbug-fix releaseです。2026-09-27の正式リリースとして扱います。

- Release: https://github.com/Hoyomaru/gofile-abdm-helper/releases/tag/v1.2.1
- Tag: `v1.2.1`
- Release title: `GoFile ABDM Helper v1.2.1`

主な更新点:

- ABDM接続確認中の連続送信で同じ選択が二重登録され得る競合を修正
- send preflight中もnavigation / cancelのgeneration guardを適用
- GoFile resolveにfolder depth 128 / node 100,000の安全上限を追加し、超過時は `422 tree_limit_exceeded`
- tree serializationとsize / file count集計を反復処理化
- 大規模・長時間resolveのaggregate-only診断logを追加
- 二重送信、preflight invalidation、tree limitの回帰テストを追加
- 正式Releaseに解決済みPython依存スナップショットを添付
- 2026-09-27 実環境確認完了

## v1.2.0 について

`v1.2.0` は、日常の送信UIとWindows導入・診断を簡潔にしたbackward-compatible feature releaseです。2026-09-27の正式リリースとして扱います。

- Release: https://github.com/Hoyomaru/gofile-abdm-helper/releases/tag/v1.2.0
- Tag: `v1.2.0`
- Release title: `GoFile ABDM Helper v1.2.0`

主な更新点:

- **ABDMへ送信** 1操作 + **フォルダ構造を維持** checkboxへ整理
- `setup-windows.cmd` によるlocal `.venv` one-step setup
- Settingsの **自己診断** でPython Helper / ABDM / Queue状態を切り分け
- `start-tray.cmd` のlocal venv優先
- Windows setupをGitHub Actions上でも実行し、idempotent reuseまで検証

## v1.1.0 について

`v1.1.0` は、送信処理の信頼性・復旧性を強化した backward-compatible feature release です。2026-09-15 の正式リリースとして扱います。

- Release: https://github.com/Hoyomaru/gofile-abdm-helper/releases/tag/v1.1.0
- Tag: `v1.1.0`
- Release title: `GoFile ABDM Helper v1.1.0`

主な更新点:

- **Cancel Send** と persistent **Retry Failed**
- SPA navigation / manual Load 時の stale send 無効化
- `resolve_id` expiry 後の content ID ベース再 resolve / remap / resume
- ABDM POST の結果不明を `Uncertain` として分離し、blind retry を防止
- Website Token retry、Windows drive root、sanitize collision / long filename の修正
- tray の helper identity check と hung process recovery
- GitHub Actions regression CI

`v1.0.0` は、このリポジトリの最初の正式な公開リリースで、2026-09-14 に公開されました。

開発途中では `v1.0.1`～`v1.0.3` という version 名を使った commit / PR が存在しますが、これらは正式な公開 Release ではありません。利用者向けの正式リリース履歴は `v1.0.0` から開始します。

`v1.2.1` 公開後の `main` には、次回 Release 向けの未リリース code / test / documentation change が入る場合があります。**公開版そのものを再現したい場合は `v1.2.1` tag / Release の source archive を使用してください。**

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
- **その他 OS:** `python app.py` で Helper を直接起動可能。tray は Windows 専用

Linux/macOS を含む各 OS での網羅的な実機確認表はありません。

### Browser / Userscript manager

Userscript metadata は `https://gofile.io/*` を対象にします。

Violentmonkey を主な対象としており、Tampermonkey も想定しています。

### AB Download Manager

接続先は意図的に固定です。

```text
http://127.0.0.1:15151
```

使用する REST endpoint:

```text
GET  /queues
POST /start-headless-download
```

別 PC の ABDM を接続先にする設定はありません。

---

## ファイル構成

```text
project/
├─ .github/
│  └─ workflows/
│     ├─ tests.yml              # GitHub Actions regression tests
│     └─ publish-release.yml     # Release gate / tag / GitHub Release
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
│  └─ TROUBLESHOOTING.md
└─ tests/
   ├─ test_core.py
   ├─ test_review_regressions.py
   ├─ test_send_regressions.py
   ├─ test_tray_source.py
   ├─ test_userscript.cjs
   └─ test_send_userscript.cjs
```

`templates/` / `static/` は使用しません。

---

# インストール

Windows で初めて導入する場合は、次の順番で進めるのが簡単です。

## 1. GoFile ABDM Helper をダウンロード

### Release ZIP（推奨）

1. [`v1.2.1` Release](https://github.com/Hoyomaru/gofile-abdm-helper/releases/tag/v1.2.1) を開く
2. GitHub が表示する **Source code (zip)** をダウンロード
3. ZIP を任意の固定フォルダへ展開する

例:

```text
C:\Tools\gofile-abdm-helper
```

`v1.2.1` の主配布物は GitHub が release tag から自動生成する **Source code (zip)** / **Source code (tar.gz)** です。exe / installer はありません。再現・障害調査用として `python-dependencies-v1.2.1.txt` も Release asset に添付します。

> `v1.2.1` の source archive は公開時点の snapshot です。最新の README は `main` 上のこのページを参照してください。

### Git を使う場合

公開版 `v1.2.1` を取得する場合:

```bash
git clone --branch v1.2.1 --depth 1 https://github.com/Hoyomaru/gofile-abdm-helper.git
cd gofile-abdm-helper
```

開発中の最新 `main` を使う場合は branch 指定を外してください。

## 2. AB Download Manager を用意

AB Download Manager をインストールして起動します。

Helper は次へ接続します。

```text
127.0.0.1:15151
```

ABDM が起動していないと、Userscript 側では ABDM へ task を登録できません。

## 3. Windows setup を実行（推奨）

Python **3.10+** をインストールしたあと、展開したフォルダで **`setup-windows.cmd` をダブルクリック**します。

setup は次を自動で行います。

1. Python 3.10+ を確認
2. project直下へ `.venv` を作成
3. `requirements.txt` の依存packageをインストール/更新
4. Flask / requests / pystray / Pillow をimportできることを確認
5. `.venv\Scripts\pythonw.exe` からtrayを起動

管理者権限やsystem-wide Python package installは不要です。以後 `start-tray.cmd` も `.venv` があればそのPythonを優先します。

PowerShellからsetupだけ行い、trayを起動したくない場合:

```powershell
.\setup-windows.ps1 -NoLaunch
```

### 手動でdependenciesを用意する場合

setup scriptを使わない場合は、Python versionを確認してから従来どおり実行できます。

```bash
python --version
python -m pip install -r requirements.txt
```

## 4. Helper を起動

### Windows: tray mode（推奨）

通常は `setup-windows.cmd` 完了時にtrayが起動します。後から起動する場合は `start-tray.cmd` をダブルクリックします。

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

tray を使わない場合:

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

## 5. Userscript をインストール

先に Violentmonkey または Tampermonkey を browser へインストールしてください。

### release 版を直接開く方法

Userscript manager が有効な browser で次を開きます。

https://raw.githubusercontent.com/Hoyomaru/gofile-abdm-helper/v1.2.1/gofile-abdm.user.js

通常は Userscript manager のインストール画面が開くので、内容を確認してインストールします。

### 手動で入れる方法

直接インストール画面が開かない場合:

1. Userscript manager で新しい script を作成
2. `gofile-abdm.user.js` の内容をすべて貼り付け
3. 保存して有効化

許可する cross-origin connect は次だけです。

```text
127.0.0.1
localhost
```

`@connect *` / `unsafeWindow` は使用しません。

Userscript metadata に `@updateURL` / `@downloadURL` はないため、将来の新しい Release へ更新する場合は新しい `gofile-abdm.user.js` を手動で更新してください。

## 6. 正常に導入できたか確認

1. AB Download Manager を起動する
2. `setup-windows.cmd` または `start-tray.cmd` でtrayを起動する
3. GoFile の共有 URL を開く
4. GoFile page に ABDM toolbar が追加されることを確認する
5. toolbarの **設定 → 自己診断** を実行する
6. **Python Helper ✓** と **AB Download Manager ✓** が表示されることを確認する
7. 必要ならtray menuで **Start with Windows** を有効にする

自己診断はHelper自身のversionと、ABDMの `/queues` 接続・Queue件数を確認します。Helperへ接続できない場合は、setup/tray起動を案内します。

GoFile share の例:

```text
https://gofile.io/d/xxxxxxxx
```

ここまで確認できれば基本的な導入は完了です。

---

# 使用方法

1. ABDM を起動
2. Helper / tray を起動
3. GoFile share を開く
4. resolve 完了を待つ
5. file / folder を checkbox で選択
6. 必要なら **全選択** / **選択解除** を使用
7. ページ上の項目との対応付けに失敗した場合は **一覧から選択** を使用
8. 必要なら **設定** で Queue / 保存先フォルダ / preset を設定
9. **フォルダ構造を維持** を on/off して送信方式を選ぶ
   - on: GoFile の relative folder structure を保持
   - off: folder structure を無視して flat に送信
10. **ABDMへ送信** を押す
11. ABDM への登録進捗を確認
12. 一部失敗時は結果の file-level error を確認し、必要なら **失敗を再送**
13. 送信を止める必要がある場合は **送信を中止**

表示される progress は **ABDM への task 登録進捗**です。実際の download % / speed / ETA ではありません。

`Uncertain` と表示された item は、ABDM が task を受け付けたか通信上確認できなかったものです。**通常の Retry Failed には含めません。ABDM の task list を確認してから手動で判断してください。**

---

## 選択の仕組み

Userscript は GoFile の単一 class 名に固定せず、既知の content ID 属性を優先します。

- `data-content-id`
- `data-id`
- `data-item-id`
- `data-uuid`

その後 link、最後に保守的な filename text matching を使用します。

### Items fallback

GoFile DOM が変わって row と tree を対応付けられない場合は、toolbar に **一覧から選択** が表示され、解決済み tree から直接選択できます。通常時はこの fallback 操作を表示しません。

### Provisional selection

Helper resolve が一時的に失敗していても、visible row に content ID があれば provisional checkbox で選択できます。

最終送信には direct URL / headers の解決が必要なので、送信前には resolve success が必要です。

### Folder selection

folder を選択すると descendant file を recursive に選択対象にします。

---

# 設定

**設定** で管理するもの:

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

### 自己診断

Settings の **自己診断** は `GET /api/diagnostics` を利用し、次を確認します。

- Python Helperへ接続できるか
- Helper versionを取得できるか
- AB Download Managerの `GET /queues` が成功するか
- 利用可能なQueue件数

ABDMがofflineでもdiagnostics endpoint自体はHTTP 200で応答し、Helper正常 / ABDM異常を分けて表示します。credential、GoFile token、direct URL、保存先pathは診断レスポンスへ含めません。

### Queue

Settings を開くたび、Helper 経由で ABDM の `/queues` を取得します。

- **Default (ABDM)**: `queueId` を送らない
- named queue: integer ID を送る

以前保存した queue が消えている場合は unavailable として扱い、別 queue または Default を選び直せます。

---

# 保存先と送信モード

Toolbar の **フォルダ構造を維持** で送信方式を切り替えます。

- **on:** GoFile の relative folder structure を保持します。
- **off:** relative folder を無視して flat に送信します。

flat mode で Save folder が空なら ABDM の optional `folder` field を省略します。

structure mode で Save root がある場合:

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

現在のリリースでは root と child folder の password challenge を扱います。

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

Website Token rejection の場合のみ前の 4-hour window を fallback として試します。通常の timeout retry では current window の token を維持します。

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

---

# 再開・復旧

- **Helper crash:** tray mode なら health monitor が再起動を試みる
- **Helper hung:** tray が所有する process で health failure が連続した場合は再起動を試みる
- **Helper restart / resolve expiry:** memory cache / guest token / resolve ID は失われるが、同一 page の active send 中は remaining content ID を保持して再 resolve / remap / resume を試みる
- **Browser reload:** selection / resolve tree / hand-entered password state は失われる。GM settings は残る
- **GoFile rate limit:** 自動 retry せず user が後で再試行
- **ABDM definite send failure:** 残りを継続し `Retry Failed` 候補へ記録
- **ABDM uncertain POST:** `Uncertain` として分離し、通常の Retry Failed 対象にしない
- **SPA navigation / Load:** active send operation を無効化して旧 page の残り loop を止める

Cancel / navigation 時点で既に ABDM へ送信中だった **1件の in-flight request** は、通信を止めても ABDM が受け付け済みの可能性があります。そのため cancel 後の即時 blind retry は避けてください。

---

# セキュリティ

重要な境界:

- Flask bind は `127.0.0.1` のみ
- ABDM 接続先は `127.0.0.1:15151` 固定
- `/api/*` は `X-GoFile-ABDM: 1` marker を要求
- POST / PUT / PATCH は JSON を要求
- GoFile URL は `https://gofile.io/d/<id>` または bare content ID のみ
- direct download URL は `https` かつ `gofile.io` / subdomain のみ
- GoFile 由来 path segment を sanitize
- Userscript の `@connect` は localhost のみ
- direct URL / Cookie / guest token / Website Token / password を意図的に log しない
- Userscript には direct URL / Cookie を返さず opaque file key を返す

localhost service を LAN 公開したり、CORS を広げたり、generic URL proxy を追加しないでください。

---

# 既知の制限・要検証事項

- Cancel / SPA navigation で active send loop は停止しますが、既に送信中だった1件の ABDM POST が受理済みかどうかを browser 側から確定できない場合があります
- Userscript → Helper の送信は安全な cancellation boundary を維持するため通常1 file / request で、大きな batch send は行いません
- `helper.log` の 2 MiB rotation は Helper 起動時判定で、稼働中常時 rotation ではありません
- Save folder が空の structure mode では、ABDM の unknown default folder に relative subfolder だけを確実に追加できません
- GoFile / ABDM の外部仕様変更により互換性が壊れる可能性があります

詳細は [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) と [`DEVELOPMENT.md`](DEVELOPMENT.md) を参照してください。

---

# 診断・テスト

health check:

```text
http://127.0.0.1:8765/health
```

Windows tray log:

```text
helper.log
helper.log.1
```

Python tests:

```bash
python -m unittest discover -s tests -v
```

Userscript tests:

```bash
node --test tests/*.cjs
```

syntax checks:

```bash
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

GitHub Actions の `Tests` workflow でも、push / pull request 時に同じ Python / Userscript regression test と syntax check を実行します。実機 E2E は CI では代替できないため、release 前には別途確認してください。

---

# 更新

新しい正式 Release が公開された場合:

1. 新しい Release の source archive を取得して project files を更新
2. `python -m pip install -r requirements.txt` を再実行
3. tray / Helper を再起動
4. 新しい `gofile-abdm.user.js` を Userscript manager へ更新

Helper を更新した後は、古い memory cache を残さないため再起動してください。

`main` を直接追従する場合は未リリース変更を含む可能性があります。安定した公開版を使う場合は Release tag を使用してください。

---

# アンインストール

1. tray の **Start with Windows** を off
2. tray を **Exit**
3. Userscript manager から GoFile ABDM Helper を削除
4. project directory を削除
5. 不要なら Python packages / ABDM を別途削除

残り得るもの:

- Userscript manager の GM storage
- `helper.log` / `helper.log.1`
- Windows Run entry（Start with Windows を off にしていない場合）

---

# 開発者向け資料

- [`DEVELOPMENT.md`](DEVELOPMENT.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/RELEASE.md`](docs/RELEASE.md)
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

開発開始時は README / DEVELOPMENT / CHANGELOG / 最新コードを確認し、仕様変更時は同じ変更で関連ドキュメントを同期してください。

---

# License

MIT License。`LICENSE` を参照してください。

参照した外部プロジェクトに関する通知は `LICENSES/optional-license-notices.txt` を参照してください。
