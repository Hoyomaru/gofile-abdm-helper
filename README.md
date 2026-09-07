# GoFile ABDM Helper

**安定版:** `v1.0.3`

リポジトリ: `https://github.com/Hoyomaru/gofile-abdm-helper`

**既存の GoFile ページ**に Userscript の UI を追加し、選択した GoFile のファイル／フォルダを localhost 専用の Python/Flask ヘルパー経由で **AB Download Manager (ABDM)** に送信する、個人利用向けの小さなツールです。

**独立した Flask Web UI はありません。** 通常の処理フローは次のとおりです。

```text
GoFile ページ
    ↓
Userscript（チェックボックス / ツールバー / 設定 / 進捗）
    ↓ GM_xmlhttpRequest
localhost Flask Helper (127.0.0.1:8765)
    ↓
AB Download Manager (127.0.0.1:15151)
```

Python 側がファイル本体をダウンロードすることはありません。GoFile のメタデータ／直接 URL を解決し、ABDM にダウンロードタスクを登録するだけです。

## この実装が参考にしているもの

この実装は、2026-09-05 時点の各リポジトリのデフォルトブランチを確認したうえで、ゼロから実装しています。

- `ewigl/gofile-enhanced` — デフォルトブランチ `main`
  - 現在の Userscript は GoFile の `/js/services/contents.js` と `/js/ui/{menu,popup,toast}.js` を import し、`#fm-toolbar` / `#fm-root` 周辺へ統合しています。
  - このプロジェクトでは、**統合の考え方**、GM ストレージ／リクエストの使い方、コンパクトなツールバーという方針を参考にしています。
  - downloader 選択 UI や、`unsafeWindow` / `Object.prototype` を使った FileManager のインターセプト処理はコピーしていません。代わりにヘルパー側で GoFile のコンテンツを解決し、DOM マッチングに失敗した場合は小さなフォールバック選択ポップアップを使用します。
- `martadams89/gofile-dl` — デフォルトブランチ `main`
  - `POST https://api.gofile.io/accounts` によるゲストアカウント作成。
  - 動的な `X-Website-Token` 生成、`User-Agent` / `X-BL` の整合、SHA-256 パスワード処理、再帰、UUID コンテンツ ID、レート制限処理。
  - このプロジェクトでは Flask UI、ダウンローダー、Docker/CLI/タスク/履歴機能、ファイル転送処理は再利用していません。
- `amir1376/ab-download-manager` — デフォルトブランチ `master`
  - 現在の `REST-API.yml` では `GET /queues` と `POST /start-headless-download` が文書化されています。
  - このプロジェクトが送信するのは文書化済みフィールドのみです。`downloadSource.link`、任意の `downloadSource.headers`、任意の `downloadSource.downloadPage`、任意の `folder`、任意の `name`、任意の `queueId` を使用します。
  - キュー一覧は文書化済みの `GET /queues` から取得します。**Default (ABDM)** を選択した場合は `queueId` を省略します。

## ファイル構成

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

`templates/` や `static/` ディレクトリは使用しません。

## 必要環境

- Python 3.10+
- Violentmonkey（主な対象）または Tampermonkey
- デフォルトポート `15151` でローカル REST API／ブラウザ連携が利用できる AB Download Manager
- GoFile に接続できる通常のネットワーク環境

## インストール

### 1. AB Download Manager をインストールする

AB Download Manager をインストールして起動します。このヘルパーは API 接続先を意図的に次へ固定しています。

```text
http://127.0.0.1:15151
```

別の PC を接続先に指定するオプションはありません。

### 2. Python の依存パッケージをインストールする

Windows / Linux:

```bash
python -m pip install -r requirements.txt
```

### 3. localhost ヘルパーを起動する

#### Windows: 推奨のシステムトレイモード

次をダブルクリックします。

```text
start-tray.cmd
```

`tray.py` が `pythonw.exe` で起動するため、ターミナルウィンドウは残りません。トレイアイコンがバックグラウンドで `app.py` を起動・監視します。トレイアイコンを右クリックすると、次の操作ができます。

- **Helper: Running / Stopped** — 現在の localhost ヘルパー状態
- **Restart Helper** — トレイが管理している Flask ヘルパーを再起動
- **Open Folder** — このプロジェクトのフォルダを開く
- **View Log** — `helper.log` を開く
- **Start with Windows** — 現在の Windows ユーザーについてトレイランチャーの自動起動を登録／解除
- **Exit** — トレイ管理下のヘルパーを停止し、トレイアプリも終了

自動起動を有効にするには、一度トレイを起動して **Start with Windows** をオンにします。これにより、ユーザー単位の `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` に `pythonw.exe tray.py` を指すエントリが作成されます。管理者権限は不要です。

古い `python app.py` が手動で起動済みの場合、トレイには **Running (external)** と表示され、そのプロセスを終了しません。古いターミナルを一度閉じると、トレイがヘルパー停止を検知し、自動的に自身の非表示プロセスを起動します。

#### 手動 / Linux モード

ヘルパーを直接起動することもできます。

```bash
python app.py
```

バインド先は次だけです。

```text
127.0.0.1:8765
```

任意のヘルスチェック:

```text
http://127.0.0.1:8765/health
```

### 4. Userscript をインストールする

Violentmonkey をインストールし、新しいスクリプトを作成して次のファイルの内容をすべて貼り付けます。

```text
gofile-abdm.user.js
```

このスクリプトがクロスオリジンで許可するのは `localhost` / `127.0.0.1` への Userscript アクセスだけです。`@connect *` や `unsafeWindow` は使用しません。

### 5. 通常どおり GoFile を開く

たとえば次のような共有 URL を開きます。

```text
https://gofile.io/d/xxxxxxxx
```

Userscript が GoFile ページに小さな ABDM ツールバーを追加します。Flask ページへリダイレクトされることはありません。

## 使い方

1. ABDM を起動します。
2. Windows ではトレイランチャーを起動したままにするのがおすすめです。それ以外では `python app.py` を実行します。
3. GoFile の共有 URL を通常どおり開きます。
4. ツールバーに解決済みファイル数が表示されるまで待ちます。
5. GoFile の一覧でファイルまたはフォルダにチェックを入れます。
6. 必要に応じて **Select All** / **Clear** を使います。
7. 必要なら **⚙** を開き、ABDM のダウンロードキュー、Save folder、またはプリセットを選択します。
   - **Default (ABDM)** — `queueId` を省略し、ABDM のデフォルト動作に任せます。
   - 任意の名前付きキュー — そのキューの整数 ID を `queueId` として送信します。
8. 送信モードを選びます。
   - **Send to ABDM** — GoFile のフォルダ階層を保持します。
   - **Send Flat** — GoFile のフォルダ階層を無視し、選択した Save folder（空の場合は ABDM のデフォルトフォルダ）へ直接ファイルを配置します。
9. ツールバーには、たとえば `12 / 30` のように登録進捗が表示されます。
10. 個別タスクが失敗した場合は **Retry Failed** を使用します。再試行時も、失敗したバッチで使用した送信モードが維持されます。

表示される進捗は**ABDM へのタスク登録進捗**であり、実際のダウンロード進捗ではありません。速度、ETA、一時停止／再開、キャンセル、履歴は ABDM 側の機能です。

## Windows トレイと自動起動

トレイランチャーは意図的に `app.py` から分離されています。`app.py` は localhost 専用の小さな Flask API のままで、`tray.py` はそのプロセス管理と Windows の自動起動のみを担当します。Flask の HTML UI は追加していません。

### 初回セットアップ

プロジェクト更新後、追加されたトレイ用依存パッケージを一度インストールします。

```bash
python -m pip install -r requirements.txt
```

その後 `start-tray.cmd` をダブルクリックします。Windows の通知領域に小さな青いダウンロードアイコンが表示されます。Windows によって隠されている場合は、`^` の隠しアイコンメニューを開いてください。

アイコンを右クリックし、**Start with Windows** を有効にします。次回ログイン以降は、ターミナルを表示せずにトレイアプリと Flask ヘルパーが自動起動します。

### ログ

バックグラウンドのヘルパーにはターミナルがないため、Flask の出力は次へ書き込まれます。

```text
helper.log
```

約 2 MB を超えると、以前のログは `helper.log.1` にローテーションされます。リクエスト本文、パスワード、Cookie、トークン、一時的な直接 URL をヘルパーが意図的にログへ記録することはありません。

### 自動起動を停止する

トレイアイコンを右クリックし、**Start with Windows** のチェックを外します。削除されるのは、このアプリケーションのユーザー単位 Run エントリだけです。Python、ABDM、Userscript はアンインストールされません。

## ファイル／フォルダの選択

Userscript は Python ヘルパーを通して現在の GoFile ツリーを解決し、既存の GoFile 行へチェックボックスを付けようとします。

DOM 統合では、壊れやすい単一の GoFile 行クラスを固定で使用しない設計にしています。既知のコンテンツ識別子（`data-content-id`、`data-id`、`data-item-id`、`data-uuid`）を優先し、その次にリンク、最後に保守的なファイル名一致を使用します。**Items** ボタンは常に利用でき、完全なフォールバック用ツリーセレクターを開けるため、選択機能は特定の GoFile 行レイアウトだけに依存しません。

Helper がすぐに解決できない場合（たとえば GoFile が一時的に HTTP 429 を返している場合）でも、表示中の GoFile 行は content ID を使って暫定的に選択できます。その後 **Load** が成功した時点、または送信直前に、選択済み ID を解決済みツリーと照合します。実際の送信には、ABDM 用の直接リンクとヘッダーが必要なため、最終的には resolve の成功が必要です。

フォルダを選択すると、その配下にあるすべてのファイルが再帰的に選択されます。フォルダの選択件数と合計サイズは、ヘルパーが解決したツリーから計算されます。

### 階層保持とフラットダウンロード

ツールバーには 2 種類の ABDM 送信操作があります。

- **Send to ABDM** は各ファイルの GoFile 上の相対フォルダパスを保持します。
- **Send Flat** は GoFile 上の相対フォルダパスを破棄します。深い階層内の 1 ファイルだけを選び、GoFile のフォルダを作らずに保存先へ直接置きたい場合に便利です。

Save folder が `D:/Downloads`、GoFile 上のパスが `Anime/Subs/Episode01.ass` の場合:

```text
Send to ABDM -> D:/Downloads/Anime/Subs/Episode01.ass
Send Flat    -> D:/Downloads/Episode01.ass
```

Flat モードは複数ファイルでも利用できます。異なる元フォルダに同名ファイルがある場合は、ABDM 自身の重複ファイル名処理が適用されます。

## SPA ナビゲーション

スクリプトは次を処理します。

- `history.pushState`
- `history.replaceState`
- `popstate`
- ファイルマネージャー DOM の置き換え

ページ全体を高頻度でポーリングするのではなく、デバウンスされた observer をファイルマネージャー／main 領域へ付けています。ツールバーとチェックボックスの挿入は、重複しないよう冪等に実装されています。

## 保存先フォルダとプリセット

設定ポップアップが GM ストレージへ保存するのは、ブラウザ側の UI 設定だけです。

- 選択中の ABDM キュー ID
- 最後に使用した Save folder
- Save folder プリセット

プリセットは追加、編集、削除、選択できます。

### ABDM キューの選択

**⚙ → Download queue** を開き、新しいタスクで使用するキューを選択します。Settings を開くたびに、次の API を使って ABDM から一覧を更新します。

```text
GET http://127.0.0.1:15151/queues
```

- **Default (ABDM)**: ヘルパーは任意フィールド `queueId` を省略します。
- **Named queue**: ヘルパーは `/start-headless-download` の各リクエストで、そのキューの整数 ID を `queueId` として送信します。
- **Retry Failed** は Flat／階層保持モードと同様に、元の失敗バッチで使用していたキューを維持します。

以前保存したキューが存在しなくなっている場合、Settings では利用不可として表示されるため、別のキューを選ぶか Default に戻せます。

パスワードは**永続保存されません**。

### ABDM のデフォルト保存先

Save folder が空の場合、ヘルパーは ABDM の任意フィールド `folder` を省略し、ABDM の設定済みデフォルト動作に任せます。

重要な制限: 現在の ABDM 公式 REST 仕様には「ABDM のデフォルトディレクトリ + この相対サブフォルダ」という意味の操作が文書化されていません。そのため Save folder が空の場合、**Send Flat** は問題なく ABDM のデフォルトディレクトリを使用できますが、階層保持モードでは未知のデフォルトディレクトリへ相対サブフォルダを確実に追加できません。GoFile のフォルダ階層を確実に保持したい場合は、次のように明示的なルートを指定してください。

```text
D:/Downloads
```

GoFile 上のパスが次の場合:

```text
Anime/Subs/Episode01.ass
```

ABDM には次のようなフォルダが登録されます。

```text
D:/Downloads/Anime/Subs
```

## パスワード保護コンテンツ

GoFile がパスワード必須コンテンツだと返した場合、Userscript がパスワード入力ポップアップを開きます。パスワードはその resolve リクエストのためだけに localhost ヘルパーへ送られ、現在のセッション中だけページメモリに保持されます。

ヘルパーは現在の GoFile ツールと同じ動作になるよう、SHA-256 化したパスワード値を GoFile の content API へ送信します。

## ゲストアクセスと Website Token

Premium／アカウントトークンの入力機能は実装していません。

ヘルパーは GoFile のゲストアカウントを作成し、次の式から `X-Website-Token` を動的に生成します。

```text
sha256(User-Agent :: language :: guest-account-token :: 4-hour-window :: salt)
```

したがって、このトークンはコピーされた固定 Website Token ではありません。

GoFile は Web サイトの JavaScript に埋め込まれた salt を変更する可能性があります。このプロジェクトには、2026-09-05 に確認した `gofile-dl` 実装で当時使用されていた値を同梱しています。将来 GoFile がその値を拒否するようになった場合は、ヘルパー起動前に現在の salt を設定してください。

Windows PowerShell:

```powershell
$env:GOFILE_WT_SALT="current-value"
python app.py
```

Linux/macOS shell:

```bash
GOFILE_WT_SALT="current-value" python app.py
```

GoFile 側の検証対象が変わった場合は、`GOFILE_USER_AGENT` と `GOFILE_LANGUAGE` も上書きできます。これらの値は Website Token のハッシュに使用する値と一致している必要があります。

## ABDM の接続状態

ヘルパーは文書化済みの次の API を使って ABDM を確認します。

```text
GET http://127.0.0.1:15151/queues
```

Userscript が接続状態を確認するタイミングは次のとおりです。

- 初回読み込み時に 1 回
- Settings を開いたとき
- 送信直前

ABDM を継続的にポーリングすることはありません。

## GoFile リクエスト／レート制限時の動作

Helper は、GoFile API への繰り返しアクセスを意図的に最小化しています。

- Helper プロセスが動作している間は、1 つの GoFile ゲストセッション／トークンを再利用します。
- 成功した resolve は、content ID と SHA-256 パスワードダイジェストをキーとして 20 分間キャッシュします。
- 同一コンテンツをその時間内に再度 resolve した場合は、ローカルメモリから返します。
- 再帰 resolve は直列化され、2 つの resolve が同時に GoFile へ走らないようにします。
- 再帰的な content リクエストは、バーストを避けるためデフォルトで 0.75 秒間隔にします。
- HTTP/API のレート制限レスポンスを受けた場合、その resolve を即座に停止し、再試行しません。

Helper を再起動すると、これらのメモリ内キャッシュは消去され、次回 resolve 時に新しいゲストセッションが作成されます。待機間隔は `GOFILE_REQUEST_INTERVAL`（秒）で上書きできます。`0` にすると待機を無効化します。

## セキュリティ

ヘルパーには意図的に次の制限を設けています。

- Flask は `127.0.0.1` のみにバインドします。
- ABDM の接続先は `127.0.0.1:15151` に固定します。
- ヘルパーが受け付けるのは、検証済みの GoFile `/d/<content-id>` URL または content ID だけです。
- 汎用 URL 取得エンドポイントは用意せず、ヘルパーが SSRF プロキシにならないようにしています。
- API リクエストには独自の `X-GoFile-ABDM: 1` マーカーが必要で、POST リクエストには JSON を要求します。寛容な CORS ヘッダーは追加しません。
- GoFile 由来のファイル名／フォルダセグメントは、ユーザー指定ルートへ追加する前にサニタイズします。
- GoFile 由来のパスセグメントでは、`../`、`..\\`、スラッシュ、バックスラッシュ、NUL／制御文字、Windows ドライブ注入、末尾のドット／スペース、Windows の予約名を無害化します。
- ユーザーが選択した保存先ルート自体は、ABDM API 向けのパス区切り正規化を除き、書き換えません。
- ゲストトークン、Website Token、Cookie、パスワード、Authorization ヘッダー、一時的な直接 URL は意図的にログへ記録しません。
- 1 タスクが失敗しても、残りのタスク処理は継続します。
- 解決済みの直接 URL／ヘッダーは、Helper のメモリ内キャッシュ（TTL 20 分）だけに保存します。Userscript には直接 URL／Cookie ではなく、不透明な file key を返します。

localhost の HTTP サービスはブラウザ上のページから狙われる可能性があるため、ヘルパーは loopback にバインドしたまま使用し、CORS や LAN バインドを追加しないでください。

## 意図的に実装していない機能

- Premium / Account Token 入力
- URL 履歴 / お気に入り
- 検索 / 拡張子フィルター / 並べ替え / プレビュー
- ブラウザからの直接ダウンロード
- Aria2 / IDM / JDownloader
- Python ファイルダウンローダー / Flask ストリーミング
- 転送速度 / ETA
- 一時停止 / 再開 / キャンセル
- ダウンロード履歴データベース
- ダッシュボード
- React / Vue
- Docker
- CLI
- database / Celery / Redis

## テスト

ローカルテストを実行するには:

```bash
python -m unittest discover -s tests -v
```

開発時に使用した静的構文チェック:

```bash
python -m py_compile app.py gofile.py abdm.py
node --check gofile-abdm.user.js
```

ユニットテストは mock を使用し、GoFile や ABDM へ実際の通信は行いません。

## トラブルシューティング

### Python Helper Offline

次がまだ実行中であることを確認してください。

```bash
python app.py
```

また、Userscript に `127.0.0.1` へのアクセス権限があることを確認します。

### ABDM Offline

AB Download Manager を起動し、ローカル REST／ブラウザ連携がポート `15151` で有効になっていることを確認してください。

### `website_token_rejected`

GoFile が Website Token の salt またはブラウザ検証用入力値を変更した可能性があります。まず `GOFILE_WT_SALT` を更新してください。実装を古い固定 `config.js` Website Token へ置き換えないでください。

### レート制限

ヘルパーは GoFile のレート制限レスポンスを**再試行しません**。再帰的な content リクエストはデフォルトで 0.75 秒間隔になっており、429／API レート制限レスポンスを受けると現在の再帰 resolve を即座に停止します。時間を置いてから再試行してください。同一内容の resolve は 20 分のキャッシュ有効期間内であれば、GoFile API へ再アクセスせずローカルメモリから返されます。

### 一部のチェックボックスが表示されない

GoFile のフロントエンド DOM が変更された可能性があります。**Items** のフォールバックセレクターを使用してください。ヘルパー側の resolve／send ロジックは GoFile の行クラスに依存していません。

## ライセンス

このプロジェクトは MIT License のもとで提供されます。`LICENSE` を参照してください。

実装はオリジナルであり、上記 3 つの upstream プロジェクトはコードをコピーするのではなく、挙動／API の参考資料として使用しています。参照プロジェクトに関する通知は `LICENSES/optional-license-notices.txt` を参照してください。