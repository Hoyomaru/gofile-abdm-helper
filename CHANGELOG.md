# 変更履歴

このプロジェクトの正式な公開リリース履歴を記録します。

正式な公開リリース履歴は **`v1.0.0` から開始**します。

## [Unreleased]

次回Release向けの変更はここへ記録します。

### Fixed

- ABDM接続確認中に送信操作を連続すると、同じ選択の登録処理が複数開始し得る競合を修正。最初の非同期処理より前にsend operationを予約し、preflight中もgeneration / cancellation guardを適用。
- 極端に深い・大きいGoFile treeがPythonの再帰上限や過大な処理へ進む前に、nested folder depth 128 / node 100,000の安全上限で停止し、Helperから`422 tree_limit_exceeded`を返すよう変更。
- resolved treeの公開用serializationとsize / file count集計を反復処理にし、同じ部分木を繰り返し再帰集計する処理を削減。

### Tests

- ABDM接続確認を保留した状態で連続送信し、preflight requestが1回だけになるUserscript回帰テストを追加。
- resolve depth / node上限、深いconstructed treeのserialization、Helperの`tree_limit_exceeded`応答を回帰テストに追加。

### Operations / Documentation

- `docs/ARCHITECTURE.md` と `DEVELOPMENT.md` をv1.2.0時点のsend/navigation/uncertain behaviorへ同期。
- release smoke testに連続送信競合の確認と結果記録欄を追加。
- 正式releaseで解決済みPython依存を`python-dependencies-v<version>.txt`として記録し、GitHub Release assetへ添付するようrelease workflowを更新。

## [1.2.0] - 2026-09-27

GoFile上の送信UIを簡潔にし、Windows導入とHelper/ABDM接続診断を大幅に分かりやすくしたbackward-compatible feature releaseです。

### Added

- Windowsで `setup-windows.cmd` を実行するだけでlocal `.venv` 作成、dependency install、import検証、tray起動まで行うone-step setupを追加。
- Helperへread-only `GET /api/diagnostics` を追加し、Helper version / ABDM接続 / Queue件数を確認可能にした。
- Userscript Settingsへ **自己診断** を追加し、Helper offlineとABDM offlineを画面上で切り分け可能にした。
- setup / diagnosticsの回帰テストとWindows runner上の実setup smoke testを追加。

### Changed

- GoFile toolbarの通常送信操作を **ABDMへ送信** 1つに統合し、**フォルダ構造を維持** checkboxでstructure / flatを切り替えるUIへ変更。
- DOM row matchingが必要な場合だけ **一覧から選択** fallbackを表示し、通常時のtoolbar情報量を削減。
- toolbar、Settings、送信結果の主要文言を日本語へ統一し、`Uncertain` はUI上で **確認が必要** と説明。
- `start-tray.cmd` はprojectの `.venv\\Scripts\\pythonw.exe` が存在する場合、それを優先して起動。
- Windows setupは既存`.venv`内のPython versionも再検証し、3.10未満なら安全に停止。

### Security

- diagnosticsはABDMのread-only `GET /queues` だけをprobeし、GoFile credential / password / token / direct URL / save pathを返さない。
- localhost bind、request marker、uncertain POSTのblind retry禁止など既存trust boundaryを維持。

### Validation

- GitHub Actions Python / Userscript regression suite: PASS。
- Windows runnerでone-step setup、local venv、dependency import、2回目setupのidempotent reuseを確認。
- 2026-09-27実機でWindows setup / tray / Helper↔ABDM自己診断 / 送信UIを確認。

## [1.1.0] - 2026-09-15

信頼性・復旧性を中心に、送信キャンセル、結果不明の ABDM POST の分離、`resolve_id` 期限切れ後の安全な再開、tray recovery、CI を追加した backward-compatible feature release。

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
- `DEVELOPMENT.md` / `docs/RELEASE.md` を現在仕様・CI・release 手順へ同期。
- custom binary asset なしで、GitHub が自動生成する source archive を配布物として利用する方針を維持。

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
