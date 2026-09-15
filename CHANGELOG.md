# 変更履歴

このプロジェクトの正式な公開リリース履歴を記録します。

正式な公開リリース履歴は **`v1.0.0` から開始**します。

## [Unreleased]

### Added

- GitHub Actions を追加し、Python regression tests / `py_compile` / Userscript Node tests / Userscript syntax check を push / pull request で実行。
- Userscript に送信 generation guard、**Cancel Send**、persistent **Retry Failed** を追加。
- ABDM 送信結果に `uncertain` 分類を追加し、結果不明の POST を通常 failure / automatic retry 候補から分離。
- send / Website Token / Windows path / sanitize collision / tray recovery の regression tests を追加。

### Changed

- `resolve_id` expiry 時、残り file を GoFile content ID で保持して再 resolve 後の新しい file key へ remap し、同一 page の送信を安全に再開するよう変更。
- SPA navigation / manual Load / user cancel で旧 send operation を無効化し、古い response で新しい page state を更新しないよう変更。
- send result modal に file-level error detail と uncertain result を表示。uncertain item は ABDM 側を確認してから判断するよう案内。
- tray health check は HTTP 200 だけでなく `service: gofile-abdm-helper` を確認するよう変更。
- tray が所有する Helper process が生存したまま health check に連続失敗した場合、短時間の一時失敗を許容した後に自動再起動するよう変更。

### Fixed

- GoFile content request timeout の通常 retry が誤って前の 4-hour Website Token window を使う問題を修正。前 window fallback は Website Token rejection 時だけ行う。
- Windows drive root `C:\\` / `C:/` が `C:` に縮退し、ABDM の保存先 semantics が変わる問題を修正。
- sanitize 後に異なる GoFile file / folder 名が同一 target path へ衝突し得る問題を、stable suffix による deterministic disambiguation で修正。
- 長い filename の sanitize で extension が失われやすい問題を改善。
- `/api/abdm/send` が JSON object 以外の truthy JSON を受けた場合に 500 になり得る問題を修正。
- ABDM POST の timeout / connection error を definite failure として扱い、Retry Failed による duplicate task を誘発し得る問題を修正。
- send 中の SPA navigation で旧 page の残り task registration loop が継続する問題を修正。
- tray-managed Helper が process alive / health down のまま永久に `Starting` へ留まる問題を修正。

### Tests

- `tests/test_review_regressions.py`: Website Token retry、Windows drive root、sanitize collision。
- `tests/test_send_regressions.py`: non-object send body、ABDM uncertain outcome、Helper uncertain propagation。
- `tests/test_send_userscript.cjs`: send generation / source guard、content ID remap、navigation invalidation、resolve-expiry resume、uncertain retry separation。
- `tests/test_tray_source.py`: Helper identity health check、hung Helper restart guard。
- Userscript CI は `node --test tests/*.cjs` で全 Node regression test を実行。

### Implementation note

- Userscript → Helper の send は引き続き通常 **1 file / request**。大きな batch は navigation / cancel 後にも Helper 側で複数 task が継続し得るため、今回の reliability 改善では採用しない。

### Documentation

- `README.md` のインストール手順を、GitHub Release の `Source code (zip)` から始める初見ユーザー向けの流れへ補強。
- Python version 確認、Userscript の導入方法、正常導入の確認手順を追加。
- `DEVELOPMENT.md` / `docs/RELEASE.md` を、`v1.0.0` が 2026-09-14 に公開済みである現在の状態へ同期。
- `v1.0.0` は custom binary asset なしで、GitHub が自動生成する source archive を配布物として利用する方針を明記。

## [1.0.0] - 2026-09-14

初回正式リリース。

### Added

- Violentmonkey / Tampermonkey Userscript による GoFile ページ統合。
- file / folder 選択と recursive folder resolve。
- GoFile の表示行に対する checkbox 統合。
- DOM row matching ができない場合の **Items** fallback selector。
- Helper resolve 前や一時失敗中にも選択できる provisional selection。
- **Send to ABDM** による folder structure 保持モード。
- **Send Flat** による flat download task 登録。
- Save folder、Save preset、ABDM queue 選択。
- file 単位の送信結果と **Retry Failed**。
- GoFile guest account / guest token の再利用。
- dynamic `X-Website-Token` 生成。
- UUID を含む GoFile content ID 対応。
- root / child folder の password challenge 対応。
- folder ごとの SHA-256 password digest と parent credential 継承。
- GoFile `sessionStorage` の password digest を一度だけ補助候補として利用する経路。
- password modal の Cancel / Escape / 背景 click / modal replacement / SPA navigation の安全な終了処理。
- password challenge / access denied の対象 folder context 返却。
- GoFile content pagination。
- 20分の resolved-content cache。
- credential map 全体を含めた cache separation。
- recursive resolve の process 内直列化。
- GoFile content request のデフォルト 0.75 秒 pacing。
- Windows system tray launcher。
- Helper process health monitoring / restart。
- user-level **Start with Windows**。
- `helper.log` / `helper.log.1`。

### Changed

- GoFile HTTP/API rate limit は blind retry せず、その resolve を即停止する方針へ統一。
- HTTP 200 でも `canAccess: false` を空の成功 tree として扱わず、password challenge / access denied として分類。
- GoFile row matching は `data-content-id`, `data-id`, `data-item-id`, `data-uuid` を優先し、link / filename fallback を使用。
- recursive resolve に Userscript 側の固定 180 秒 deadline を設けず、Helper 側の個別 HTTP timeout を使用。
- direct download URL / Cookie を Userscript へ返さず、opaque file key を介して Helper memory 内で保持。

### Fixed

- resolve 失敗後に provisional checkbox が消えたままになる回帰を修正。
- 大規模 recursive resolve が Userscript 側の固定 timeout だけで失敗する問題を修正。
- password prompt を背景 click などで閉じた際に Promise / resolving state が残り得る問題を修正。
- stale resolve response が SPA navigation 後の新しい page state を上書きしないよう generation guard を追加。
- password-protected folder が `status: ok` / `canAccess: false` の場合に空 folder 成功扱いになる問題を修正。

### Security

- Flask Helper は `127.0.0.1` のみに bind。
- ABDM 接続先は `127.0.0.1:15151` に固定。
- `/api/*` は `X-GoFile-ABDM: 1` marker を要求。
- mutation request は JSON を要求。
- GoFile URL / content ID を検証し、generic URL proxy を提供しない。
- GoFile direct download URL は HTTPS + `gofile.io` / subdomain のみ許可。
- GoFile 由来 path segment を sanitize。
- Userscript は `@connect *` / `unsafeWindow` を使用しない。
- password、guest token、Website Token、Cookie、Authorization header、一時 direct URL を意図的に log しない。

### Tests

- Python regression tests: `tests/test_core.py`
- Userscript Node tests: `tests/test_userscript.cjs`
- path safety、ABDM payload、queue、recursive resolve、rate-limit、cache、password challenge、credential inheritance、stale response、modal completion 等を対象に test を用意。

### Documentation

- `README.md`: 利用者向け導入・使用・設定・復旧・セキュリティ・制限。
- `DEVELOPMENT.md`: 開発・保守・AI 引き継ぎ用の詳細資料。
- `docs/ARCHITECTURE.md`: component / trust boundary / data flow。
- `docs/RELEASE.md`: release 手順。
- `docs/TROUBLESHOOTING.md`: 詳細な障害切り分け。

### Known limitations

- `resolve_id` expiry 後の自動再 resolve では、元 selection の保持と自動再送を保証していません。
- send 中の SPA navigation では旧 page の残り task 登録が続く可能性があります。
- ABDM POST の結果が network 上不明な場合、手動 Retry Failed により重複 task になる可能性があります。
- `helper.log` rotation は Helper 起動時判定です。
- Save folder が空の structure mode では、ABDM の unknown default folder に relative subfolder だけを確実に追加できません。
