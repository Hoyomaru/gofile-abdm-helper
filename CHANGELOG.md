# 変更履歴

このプロジェクトの主な変更点をこのファイルに記録します。

## [Unreleased]

### 追加

- パスワード保護されたフォルダツリーについて、フォルダ単位の SHA-256 digest、親資格情報の継承、challenge path、同一 root からの再試行に対応。
- Helper の `password_hashes` 入力を検証し、credential map 全体によって resolve cache を分離するよう変更。
- HTTP 200 の envelope でも `canAccess: false` を空の成功ツリーとして扱わず、password challenge / access denied として分類する処理を追加。
- Userscript に resolve generation guard、1操作内の password retry state、GoFile `sessionStorage` の一度限りの補助利用を追加。
- password modal の Cancel、背景クリック、Escape、modal replacement、SPA navigation で Promise が未完了のまま残らない処理を追加。
- access envelope、credential inheritance、cache separation、stale response、storage assistance、password modal completion を対象に Python / Node regression tests を追加。

### ドキュメント

- `DEVELOPMENT.md` を追加し、現在の状態、主要コード、状態遷移、API、永続化、retry、復旧、安全条件、過去バグ、既知問題、開発ルールを整理。
- `docs/ARCHITECTURE.md` を追加し、component、trust boundary、resolve/send data flow、cache / lock、path model を整理。
- `docs/RELEASE.md` を追加し、現在の tag / GitHub Release / CI 状況と今後の標準 release 手順を分離して記録。
- `docs/TROUBLESHOOTING.md` を追加し、代表的な障害の症状・原因候補・確認・対処を整理。
- `README.md` を利用者向け主要文書として再整理し、更新、アンインストール、診断、developer docs、stable と `main` の差、既知制限を明記。

### 注記

- これらの機能変更はまだ正式 release ではありません。`VERSION` と Userscript `@version` は `1.0.3` のままです。
- 2026-09-14 の repository 調査時点で、Git tag は `v1.0.0` と `v1.0.3`、GitHub Releases は0件、GitHub Actions / `.github/` は未導入であることを確認しました。

## [1.0.3] - 2026-09-08

レビューで確認された回帰問題の修正。

### 修正

- GoFile の resolve が失敗した場合、ページ DOM がその後変化しないケースを含め、暫定選択用の行チェックボックスを復元するよう修正。
- Helper 側の各 GoFile API リクエストのタイムアウトは維持しつつ、再帰 resolve リクエストに設定されていた Userscript 側の固定 180 秒期限を削除。
- 242 件の待機付き content リクエスト（180.75 秒）、resolve 失敗時のチェックボックス復元、Userscript 側期限なしの再帰 resolve に対する回帰テストを追加。

## [1.0.2] - 2026-09-06

選択処理とレート制限耐性の改善。

### 修正

- 既存の ID 属性に加えて `data-item-id` と `data-uuid` にも対応するよう GoFile 行マッチングを拡張。
- 現在のフォルダを検出するとき、ファイル名テキスト一致へフォールバックする前に、表示中の content ID を優先するよう変更。
- GoFile の DOM 行マッチングが変化しても選択機能を使えるよう、**Items** フォールバックセレクターを常時表示するよう変更。
- 現在階層の検出結果が空の場合、**Select All** が何もせず終了するのではなく、解決済みルート直下の要素へフォールバックするよう修正。
- Helper の resolve 成功前でも、表示中の GoFile 行を暫定的に選択できるよう変更。後の resolve 成功時に、それらの content ID を解決済みツリーと照合。
- API へのバーストを抑えつつ 429 では即停止する挙動を維持するため、再帰的な GoFile content リクエストをデフォルト 0.75 秒間隔に変更。

## [1.0.1] - 2026-09-05

レート制限対策の更新。

### 修正

- Python Helper の稼働中は 1 つの GoFile ゲストセッション／トークンを再利用するよう変更。
- 解決済み GoFile コンテンツを content ID とパスワードダイジェスト単位で 20 分間キャッシュし、同一ページの再 resolve では GoFile API リクエストを 0 件にできるよう変更。
- GoFile の HTTP/API レート制限レスポンスを再試行せず、即座に停止するよう変更。
- 再帰的な GoFile resolve を直列化し、resolve リクエストが重なってバーストしないよう修正。

## [1.0.0] - 2026-09-05

初回安定版リリース。

### 機能

- Violentmonkey/Tampermonkey Userscript による GoFile ページ統合。
- ファイル／フォルダ選択と、フォルダの再帰解決。
- GoFile ゲストアクセス、動的 Website Token 処理、パスワード保護コンテンツ、UUID content ID、レート制限時のリトライ。
- 文書化済み localhost REST API を使った AB Download Manager へのタスク登録。
- フォルダ階層保持モードと Flat 送信モード。
- 保存先フォルダのプリセットと ABDM キュー選択。
- ファイル単位の送信結果と Retry Failed。
- ユーザー単位のログイン時自動起動に対応した Windows システムトレイランチャー。
- localhost 専用ヘルパー、パスのサニタイズ、SSRF 制限、秘密情報を安全に扱うログ動作。
