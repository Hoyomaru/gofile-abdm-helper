# パスワード付きフォルダ対応 — Luna 向け実装手順書

調査日: 2026-09-08（Asia/Tokyo）  
対象: `D:\Tools\gofile-abdm-helper`  
調査時の HEAD: `e9bbb50` / `v1.0.3`  
成果物: 調査結果と実装指示。アプリケーションコードの変更、実装の別タスクへの送信、公開はこの調査では行っていない。

## 1. 実装目標

既存の Userscript → localhost Helper → ABDM の構成を保ち、パスワード付きフォルダを解除して再帰的に解決し、選択したファイルを ABDM に登録できるようにする。

対象はルートのパスワード、親と異なるパスワードを持つ子フォルダ、入力間違い、入力中断、SPA 遷移である。GoFile 画面で既に解除している場合は、そのフォルダの既存の SHA-256 値を利用できるようにする。

認証なしのフォルダ、`Send Flat`、階層保持、queue、`Retry Failed`、暫定選択は維持する。Premium/account token 入力、新しいダウンローダー、汎用 URL fetch、永続的なパスワード保管、部分的な成功ツリーの送信は追加しない。

実装前に `git status`、最新 HEAD、プロジェクト固有ルールを再確認する。以下の行番号は調査時点の目安であり、関数名を基準に作業する。

## 2. 調査で確認したこと

### 2.1 ローカル実装

| 箇所 | 現在の動作 | 必要な対応 |
| --- | --- | --- |
| `gofile.py:238` `_password_hash()` | 平文の UTF-8 を SHA-256 に変換する | 維持。既にハッシュ済みの入力と区別する |
| `gofile.py:244` `_request_folder_page()` | `status == "ok"` なら即座に成功を返す | `data.canAccess` とパスワード状態を成功判定前に確認する |
| `gofile.py:368` `resolve()` / 内部 `walk()` | 単一の `password` を全フォルダへ渡す | フォルダ別の指定と親からの継承を扱う |
| `app.py:155` `gofile_resolve()` | ルートの `password` のみ受付。例外に対象フォルダ情報がない | 後方互換の入力追加と challenge 情報の返却 |
| `app.py:81` `_source_cache_key()` | ルート ID と単一のパスワード digest でキャッシュを識別する | フォルダ別の認証情報も含める |
| `gofile-abdm.user.js:413` `resolveContent()` | パスワード例外で再帰呼び出し。単一の `state.password` を交換する | 一つの操作内での再試行ループとフォルダ別の管理 |
| `gofile-abdm.user.js:638` `openModal()` | 背景クリック・別モーダル表示で DOM を削除する | パスワード入力 Promise も必ず終了させる |
| `gofile-abdm.user.js:656` `promptPassword()` | `Cancel`、`Unlock`、Enter のみ Promise を終了する | 全閉鎖経路のキャンセルと二重確定防止 |

前回レビューの問題は `v1.0.3` で修正済み。`resolveContent()` の `finally` にある暫定チェックボックス復元と、resolve 用の `gmRequest(..., 0)` を維持する。180秒の固定 timeout に戻さない。

### 2.2 GoFile 公式ソースで確認した契約

以下は調査日に公開 JavaScript を直接取得して確認した内容。第三者サイトの説明から推定した仕様ではない。

1. `getFolder()` は SHA-256 済みの値を query parameter `password` として送る。アクセス制限は HTTP 200 の `data.canAccess === false` でも表現される。[公式 `services/contents.js`](https://gofile.io/js/services/contents.js)
2. 公式 FileManager は `canAccess === false` の場合、`password === true` をパスワード画面へ振り分ける。`passwordStatus === 'passwordWrong'` なら入力間違いとする。その他の制限は `public`、`expire` などで区別する。[公式 `files/manager.js`](https://gofile.io/js/files/manager.js)
3. 公式 `unlockFolder(plainPassword)` は `sha256Hex(plainPassword)` を計算し、`sessionStorage` の `password|<現在の URL の ID>` に保存する。URL の share code / UUID が正規化された場合には保存キーも移す。[公式 `files/manager.js`](https://gofile.io/js/files/manager.js)
4. フォルダ作成時にパスワードなどのアクセス設定を親から継承し、その後個別に変更できる。読み取りの `password` は SHA-256 である。[公式 API ページのソース](https://gofile.io/js/pages/api.js)

この公開実装が将来も同じであることは保証できない。特に `sessionStorage` 連携は補助経路とし、利用できなくても手入力で完了できる実装にする。

### 2.3 ローカル再現結果

外部通信を行わず、現在の関数を用いた最小再現で次を確認した。

- `status: "ok"`、`canAccess: false`、`password: true`、`passwordStatus: "passwordRequired"` を返すと、`resolve()` は例外にせず `file_count == 0` の成功結果を返す。
- 同条件の `passwordWrong` でも、誤った入力を空フォルダの成功として返す。
- `promptPassword()` の背景クリックでモーダルは削除されるが Promise は未完了のままになる。呼び出し元の `state.resolving` も解除されず、次の Load が早期 return する。

Python の再現では通信層の `requests` をスタブ化した。通常の全テスト実行とは別であり、全テスト成功を意味しない。調査環境の bundled Python には `requests` がなく、前回の通常テスト実行は `ModuleNotFoundError: No module named 'requests'` で停止している。

実際のパスワード付き共有 URL とテスト用パスワードは提供されていない。実サーバーでの解除、Userscript manager ごとの storage 可視性、ABDM による実ファイル取得は未検証。以下の JSON は公式コードが扱う条件から作ったテスト用データで、実レスポンスの採取結果ではない。

```json
{
  "status": "ok",
  "data": {
    "id": "folder01",
    "type": "folder",
    "name": "Locked",
    "canAccess": false,
    "password": true,
    "passwordStatus": "passwordRequired"
  }
}
```

## 3. 採用する振る舞いと API 契約

以下は GoFile の既存 API ではなく、この Helper に追加する実装方針。

### 3.1 Helper の入力

`POST /api/gofile/resolve` の既存の `url` / `content_id`、`password` は残し、任意の `password_hashes` を追加する。

```json
{
  "url": "https://gofile.io/d/root123",
  "password_hashes": {
    "root123": "<64桁のSHA-256 hex>",
    "folder01": "<64桁のSHA-256 hex>"
  }
}
```

- `password` は従来どおりルート用の平文。64桁の hex に見えても必ず平文として1回ハッシュする。自動判別しない。
- `password_hashes` の値は SHA-256 済み。二重ハッシュしない。検証後は小文字に正規化する。
- 両方がある場合、要求ルート ID に対応する `password_hashes` を優先し、ない場合だけ `password` をルート用 digest に変換する。
- `password_hashes` は JSON object。キーは bare content ID の既存の検証規則に従い、値は厳密に64桁の hex。配列、null、数値、不正なキーや値は `400 invalid_password_hashes` にする。未指定は空 map とする。
- 入力 body 自体が object であることも確認してから `.get()` を使う。既存クライアントの通常入力は維持する。
- 推奨上限は1リクエスト1000件。これは Helper の入力上限として明記し、GoFile の仕様として説明しない。上限超過も400にする。
- 平文入力の前後空白を削除しない。日本語や空白を含む入力を UTF-8 のまま扱う。

### 3.2 パスワード要求の出力

既存の `401`、`password_required` / `wrong_password` を維持し、`error` に対象を追加する。

```json
{
  "ok": false,
  "error": {
    "code": "password_required",
    "message": "This GoFile content requires a password.",
    "content_id": "folder01",
    "folder_name": "Subs",
    "relative_path": "Root/Subs"
  }
}
```

- `content_id` は、失敗した content request に使用した ID とする。そのまま `password_hashes` のキーにして再試行できることが重要。
- ルートが短縮 ID、レスポンス `data.id` が UUID の場合にも、応答内の別 ID に無条件で置き換えない。
- `folder_name` / `relative_path` は分かる場合だけ付ける。子の名前は親の listing から渡し、重名フォルダを区別できる表示に使う。HTML として挿入しない。
- password、digest、token、Cookie、direct URL は応答やエラーメッセージへ追加しない。
- パスワードによらない `canAccess: false` は `403 content_access_denied` として止め、パスワード画面を出さない。正確な理由が不明なら断定しない。
- ツリーの途中で制限に当たった場合は全体を未解決として返す。成功した範囲だけを完成したツリーとしてキャッシュしたり送ったりしない。

## 4. 実装手順

### Step 1 — GoFile のアクセス制限を成功扱いしない

`gofile.py` の `_request_folder_page()` で、`status == "ok"` の分岐にアクセス判定を追加する。

1. `data` が dict であることを確認する。
2. `data.get("canAccess") is False` の場合は成功を返さない。
3. `password is True` なら、`passwordStatus == "passwordWrong"` を `WrongPassword`、その他を `PasswordRequired` にする。送信した digest の有無だけで `passwordRequired` を `WrongPassword` に変換しない。
4. パスワードでないアクセス拒否は専用の `GoFileError` 派生例外にする。
5. `canAccess` が未指定の従来の成功 payload は受け入れる。`password: true` だけで再入力要求にしない。解除後にも保護属性は残り得る。
6. 既存のトップレベル `error-passwordRequired` / `error-passwordWrong` 系も維持する。既知の required / wrong の区別を先に行い、互換用の既存フォールバックはその後に置く。
7. HTTP 429 の JSON 解析前の判定、API rate limit の即時停止、`WebsiteTokenRejected` の分類と既存のリクエスト間隔を維持する。

例外に対象 ID を持たせ、`walk()` で表示用の path を補う。`fetch_folder()` の全ページに同じ判定を適用し、2ページ目の拒否も成功済みの1ページ目と混ぜない。

### Step 2 — フォルダ別 digest と継承を扱う

公開の `resolve(value, password=None)` の互換性を保ちながら、`password_hashes` を keyword-only の任意引数として追加する。`fetch_folder()` と `_request_folder_page()` には明示的な `password_hash` 経路を追加するなど、平文と digest を型・引数名で区別する。

各 `walk(folder_id, ...)` が使う digest の優先順は次のとおり。

1. `password_hashes[folder_id]` の明示指定。
2. 親から渡された有効 digest。
3. ルートなら、既存 `password` をハッシュした値。
4. どれもなければ未指定。

同じ digest を同じフォルダの全ページに使い、子にはそのフォルダで使った digest を渡す。兄弟で異なる入力をしても、親や他の兄弟の値を書き換えない。credential map を共有 `GoFileClient` の属性に置かず、1回の resolve のローカル状態にする。

異なるパスワードの子に到達したら、子の ID を challenge として返す。Userscript が子の digest を追加し、元のルート URL から再試行する。子 URL を新しいルートにすると相対パスと選択対象が変わるため、それは行わない。

再試行で取得済みの親を再取得する点は今回許容する。パスワード入力ごとの有限の再試行と既存の pacing を使う。新しい部分ツリーキャッシュやバックグラウンドジョブはこの対応には不要。

### Step 3 — キャッシュを認証情報ごとに分離する

`app.py` で入力を検証・正規化し、同じ正規化結果をキャッシュキー生成と resolver に渡す。

- ルート ID と、ID 順に並べた `(content_id, digest)` の正規化表現からキャッシュ識別子を作る。既存の単一 digest だけのキーでは子のパスワード変更を区別できない。
- legacy `password` はルート digest に正規化してから含める。同じ資格情報なら map の挿入順や hex の大文字小文字に依存しないキーにする。
- 入力された map 全体をキーの計算に含める。ルートの digest が同じでも子の値が異なれば別結果とする。
- `_source_cache` には完全成功だけを入れる。`canAccess: false` の空ツリーを絶対に保存しない。
- `_cache` の opaque `resolve_id`、20分 TTL、`_resolve_lock`、ロック内の再キャッシュ確認を維持する。
- 例外の ID/path を `_api_error()` から必要なときだけ返す。`gmRequest()` でその情報を Error に取り込む。

導入時には Helper を再起動する。旧版が保存した偽の空フォルダ成功キャッシュが残ったままだと、新しいアクセス判定に到達しないためである。ブラウザ側の Userscript も更新する。

### Step 4 — Userscript の入力・再試行を一つの操作として管理する

`state.password` 一つを交換する方式から、現在の resolve 対象に属する ID → digest の map に移す。手入力は `crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))` でハッシュし、平文は永続保存しない。既存の API 平文経路は旧クライアント向けに残す。

`resolveContent()` の再帰的な自己呼び出しを、1つの操作が所有するループに置き換える。

1. 開始時に source、credential map、選択、操作番号を管理する。reset は操作開始時に一度だけ行う。
2. 既存の暫定 ID に加え、再読み込み前の選択ノード ID を保存する。同じ source の再解決成功時だけ再照合する。
3. Helper へ送信し、challenge の対象 ID/path を表示して入力を待つ。
4. 入力があればその ID の digest だけ更新し、同じルートで再試行する。誤入力を自動で繰り返さない。
5. `Cancel` はこの操作の終了。`state.resolving` を解除し、進捗をキャンセル状態にし、暫定チェックボックスを復元する。直ちに自動で再開しない。
6. 正常終了時は保存した選択を再照合する。Send 起点の場合のみ既存の送信処理へ進み、認証失敗・キャンセル時は ABDM へ送らない。
7. `Load` を同じ source に対して押した場合は、そのページ内の digest を再利用する。別 source やページ移動時は古い入力と選択を破棄する。

操作番号（例: `resolveGeneration`）を用い、各 `await` 後に現在の操作か確認する。SPA 遷移時には古いパスワード画面をキャンセルし、操作を無効化する。古い応答、遅れて返った入力、古い `finally` が新しい `state.root` / `state.resolving` を上書きしてはいけない。ネットワーク自体を abort しない場合も、古い結果は採用しない。

既存の `if (state.resolving) return` だけではページ移動を取りこぼす。新しい source の操作を開始できるように、操作の所有権とフラグを一緒に整理する。既存の `sendSelected()` が解決完了前・キャンセル後に進まないことも確認する。

### Step 5 — モーダルを必ず終了させる

`promptPassword()` に「一度だけ確定する」終了関数を用意する。`openModal()` の背景クリック、`closeModal()`、別モーダルでの置き換え、SPA 遷移でもキャンセルコールバックを通すよう、既存 modal helper に任意の終了 callback を追加する程度の変更に留める。

- `Cancel`、背景クリック、Escape、置き換え、ページ移動は `null` で終了する。
- `Unlock` と Enter は一度だけ確定する。IME 変換中の Enter (`event.isComposing`) は送信しない。
- 空文字は画面内で入力を促して送信しない。`trim()` で有効な空白文字を消さない。
- 閉じたらイベント listener と入力欄を片付ける。digest も credential として扱いログに出さない。
- `Settings` など他の既存モーダルの閉鎖動作を壊さない。

### Step 6 — GoFile 画面で解除済みの場合の補助連携

公式サイトの `sessionStorage.getItem('password|' + contentId)` を必要な ID だけ参照する。例外を捕捉し、64桁の hex のみ候補にする。ルートは現在の source ID、子は Helper の challenge ID を使う。

- 明示入力した現在の map を優先し、値がない場合だけ既存 storage を候補にする。
- 同じ操作内で同じ `(content_id, digest)` を自動再試行するのは一度まで。失敗した候補を読み直して無限再試行しない。
- 候補の取得不可・不正・拒否時は手入力に戻る。
- 全 storage の走査、account token / Cookie の取得、`unsafeWindow`、公式モジュールの monkey patch は追加しない。
- Helper 自身は `sessionStorage` や GM storage に password / digest を書き込まない。公式サイトが既に持つ値を読み取るだけにする。
- share code と UUID の関連付けを推測しない。現在の URL 変更で key が移る場合は新しい操作で新しいキーを見る。子の UUID のキーがなければ手入力する。
- Violentmonkey と Tampermonkey の両方で確認する。どちらかで storage 参照が使えなくても手入力の完了を必須とする。

### Step 7 — 文書を実際の対応範囲に合わせる

`README.md` のパスワード節に、Helper 側の入力、子フォルダ別の入力、キャンセル、既存 storage の補助利用、再起動でのキャッシュ破棄を記載する。「ブラウザで解除済みなら常に自動対応」とは書かない。

`CHANGELOG.md` に変更を記載する。リリースを行う場合だけ、プロジェクトの既存手順に従って `VERSION` と Userscript の `@version` を揃える。この手順書だけを根拠に push、tag、公開は行わない。

## 5. 回帰テストと受け入れ条件

Python は既存の `unittest` と通信モックを使う。Userscript はソース文字列の存在確認だけでは不十分。Node の `node:test` / `vm` と小さな DOM・GM モックで実際の Promise と状態遷移を検証する。巨大なテスト依存を追加する必要はない。

| 対象 | セットアップ | 期待結果 |
| --- | --- | --- |
| 成功 envelope 内の未解除 | HTTP 200 / `status: ok` / `canAccess: false` / `password: true` | `401 password_required`。空ツリーも cache entry も作らない |
| 誤パスワード | 同上、`passwordStatus: passwordWrong` | `401 wrong_password` と正しい対象 ID |
| 解除成功 | `canAccess: true`、保護属性は true、children あり | 再入力要求なし、正しい file count |
| 真の空フォルダ | アクセス可能、children 空 | 0件の正常成功 |
| 非パスワード制限 | `canAccess: false` / `password` false または未指定 | `403 content_access_denied`、入力画面なし |
| 旧 payload | `canAccess` 未指定の正常結果、旧トップレベル password error | 従来の成功と認証例外を維持 |
| ハッシュ | 日本語・前後空白・64桁 hex に見える平文、明示 digest | 平文は正確に1回ハッシュ。明示 digest はそのまま送信 |
| 入力検証 | 不正 body、map、ID、digest、上限超過 | 400。GoFile に通信しない |
| 入れ子 | ルート A、子 B、孫は B 継承、兄弟 C | A を保持したまま B/C を入力でき、最終ツリーが完全になる |
| challenge の ID | root share code と返却 UUID が異なる、同名の子2つ | 再試行の map key が要求 ID と一致し、表示で対象を区別できる |
| ページング | protected folder の2ページ目が認証拒否 | 全体を成功扱いせず、部分結果を保存しない |
| キャッシュ | ルート同一、子 digest だけ変更 | 別の cache key。誤った子入力で以前の成功を返さない |
| キャッシュの正規化 | map 挿入順と hex 大文字小文字だけ変更 | 同一キーで再利用できる |
| 429 | 初回、パスワード再試行中それぞれで429 | 追加の自動再試行なし。暫定選択を復元 |
| 全キャンセル経路 | Cancel、背景、Escape、置き換え、ページ移動 | Promise が一度だけ終了し、次の Load が可能 |
| 再入力 | wrong → 正しい入力、Enter/クリックの連続操作 | 同時に2つの resolve を送らず、成功に進む |
| 遅延応答 | A の通信/入力中に B へ遷移し、A が後で終了 | A は B の UI・資格情報・busy 状態を書き換えない |
| storage 補助 | 有効 digest、不正値、読取例外、古い digest | 有効値は二重ハッシュなし。その他は手入力へ。自動ループなし |
| 選択と送信 | 暫定選択後に解除。Send 起点で解除中断 | 成功時は対象を保持、中断時は ABDM POST が0回 |
| 非永続化 | 手入力→解除→終了 | GM_setValue、storage 書込、ログに password/digest を残さない |

通常の開発環境で次を実行する。Python が PATH にない場合は利用可能な interpreter の絶対パスを使う。依存不足はプロジェクト用 venv に `requirements.txt` を導入して解消する。

```powershell
python -m unittest discover -s tests -v
python -m py_compile app.py gofile.py abdm.py
node --check gofile-abdm.user.js
node --test tests/test_userscript.cjs
```

最後のパスは今回追加する実行可能な JS テストの推奨名。まだ存在しないファイルを既存のテストとして報告しない。

実機受け入れでは、利用権限のあるテスト共有を使い、ルート保護・異なる子パスワード・誤入力・キャンセル・SPA 移動・ABDM の1ファイル登録と取得を確認する。パスワードや digest をテスト fixture、スクリーンショット、ログへ残さない。実機共有を用意できなければ、自動テスト完了と実機未検証を分けて報告する。

## 6. Luna への実装依頼文

以下をそのまま渡せる。

> `D:\Tools\gofile-abdm-helper\docs\Password-Protected-Folders-Luna-Implementation-Plan.md` を読み、現在の checkout に対してパスワード付きフォルダ対応を実装してください。手順書は `e9bbb50` / `v1.0.3` を調査したものなので、作業開始時に差分とルールを再確認してください。GoFile の `status: ok` 内のアクセス拒否を最優先で修正し、続いてフォルダ別 digest、cache 分離、challenge、入力の全キャンセル経路、SPA の古い応答排除、既存 storage の補助利用を実装してください。既存 API の `password` と v1.0.3 の暫定選択・timeout 修正を維持してください。実際の状態遷移を検証する Python/JS テストを追加し、結果と実機未検証事項を日本語で報告してください。変更は実装・テスト・関連文書に留め、push/tag/公開は行わないでください。
