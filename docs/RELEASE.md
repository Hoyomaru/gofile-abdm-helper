# リリース手順

この文書は GoFile ABDM Helper の Version・コード・ドキュメント・Git tag・GitHub Release を同期するための手順です。

基準日: **2026-09-14**

---

## 1. 現在のリリース方針

正式な公開リリース体系は **`v1.0.0` から開始**します。

現在の `main` に含まれる完成状態を、最初の正式公開版 `v1.0.0` としてリリースします。

現在の release metadata:

```text
VERSION: 1.0.0
Git tag target: v1.0.0
GitHub Release target: v1.0.0
Release date: 2026-09-14
```

GitHub Actions / CI は未導入です。

---

## 2. 配布単位

専用 installer、wheel、exe、Docker image、build archive の自動生成工程はありません。

主な配布物は source tree です。

- `gofile-abdm.user.js`
- `app.py`
- `gofile.py`
- `abdm.py`
- `tray.py`
- `start-tray.cmd`
- `requirements.txt`
- documentation

Userscript metadata に `@updateURL` / `@downloadURL` はありません。

---

## 3. Version 同期

正式 release では次を一致させます。

```text
VERSION
Userscript @version
CHANGELOG version heading
Git tag v<version>
GitHub Release tag/title
README release version
```

`v1.0.0` の期待値:

```text
VERSION             = 1.0.0
Userscript @version = 1.0.0
CHANGELOG           = ## [1.0.0] - 2026-09-14
Git tag             = v1.0.0
GitHub Release      = v1.0.0
```

一部だけ別 version のまま tag を作成しないでください。

---

## 4. v1.0.0 リリース前チェック

### Source / docs

- [ ] `VERSION` = `1.0.0`
- [ ] Userscript `@version` = `1.0.0`
- [ ] `CHANGELOG.md` に `1.0.0` entry
- [ ] README が `v1.0.0` を初回正式リリースとして説明
- [ ] DEVELOPMENT が現在仕様と一致
- [ ] ARCHITECTURE / TROUBLESHOOTING に削除済み資料へのリンクがない
- [ ] 古い公開 Tag を前提にした説明がない
- [ ] secrets / credential が混入していない

### Python tests

```bash
python -m unittest discover -s tests -v
```

### Userscript tests

```bash
node --test tests/test_userscript.cjs
```

### Syntax checks

```bash
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

CI はないため、実行結果は手動で確認します。

---

## 5. 実機 smoke test

可能な範囲で実施し、未実施項目を確認済み扱いにしないでください。

候補:

- Helper `/health`
- ABDM `/queues` connection
- 通常 GoFile share resolve
- file 1件 send
- folder recursive selection
- `Send Flat`
- structure preserve + explicit Save folder
- queue selection
- Retry Failed
- Helper restart
- Windows tray start / restart / exit
- Start with Windows on/off
- password protected root
- password protected child folder
- parent / child different password
- wrong password → retry
- password modal Cancel / Escape
- rate-limit stop behavior

---

## 6. Security regression check

- [ ] Helper bind は `127.0.0.1`
- [ ] ABDM target は `127.0.0.1:15151`
- [ ] `/api/*` marker guard が有効
- [ ] JSON mutation guard が有効
- [ ] GoFile URL / content ID validation が有効
- [ ] GoFile direct-link host validation が有効
- [ ] path sanitization が有効
- [ ] `@connect *` がない
- [ ] `unsafeWindow` がない
- [ ] password / token / Cookie / direct URL が log に出ない
- [ ] 429 を blind retry しない
- [ ] access denied / password challenge を部分成功として cache しない

---

## 7. v1.0.0 Release title / notes

### Title

```text
GoFile ABDM Helper v1.0.0 — Initial Release
```

### Release notes

```markdown
## GoFile ABDM Helper v1.0.0

GoFile の既存ページから、選択したファイル / フォルダを localhost 専用 Helper 経由で **AB Download Manager (ABDM)** へ登録できる GoFile ABDM Helper の初回正式リリースです。

### 主な機能

- GoFile ページへ Userscript の選択 UI / toolbar を統合
- file / folder 選択と recursive folder resolve
- **Send to ABDM** による folder structure 保持
- **Send Flat** による flat task 登録
- ABDM queue、Save folder、Save preset の選択
- file 単位の送信結果と **Retry Failed**
- DOM row を対応付けられない場合の **Items** fallback selector
- Helper resolve 前や一時失敗中にも使える provisional selection
- root / child folder の password challenge
- parent / child で異なる password と credential inheritance
- GoFile guest session / dynamic Website Token
- 20分の resolved-content cache
- recursive resolve の直列化と request pacing
- Windows system tray / Helper 自動監視
- user-level **Start with Windows**

### 安全設計

- Helper は `127.0.0.1` のみに bind
- ABDM 接続先は `127.0.0.1:15151` に固定
- generic URL proxy を提供しない
- GoFile URL / content ID / direct-link host を検証
- GoFile 由来 path segment を sanitize
- rate limit 時は blind retry せず現在の resolve を停止
- password、token、Cookie、Authorization header、一時 direct URL を意図的に log しない
- direct download URL / Cookie を Userscript へ返さず Helper memory 内で管理

### 既知の制限

- Save folder が空の structure mode では、ABDM の default folder に relative subfolder だけを確実に追加できません。folder structure を確実に保持する場合は Save root を明示してください。
- `resolve_id` expiry 後の再 resolve では、元 selection の保持と自動再送を保証していません。
- send 中に GoFile の SPA navigation を行うと、旧ページの残り task 登録が続く可能性があります。
- ABDM POST の結果が network 上不明な場合、手動 **Retry Failed** により duplicate task になる可能性があります。
- `helper.log` の rotation は Helper 起動時判定です。
- Premium / account token 入力、download 進捗 / ETA / pause / resume は実装していません。

### インストール / 使用方法

導入方法、設定、使い方、トラブルシューティングは `README.md` を参照してください。

> このツールは GoFile および AB Download Manager の公式プロジェクトとは無関係の非公式ツールです。
```

この repository には必須 binary asset はありません。

---

## 8. Tag / GitHub Release 作成

release 対象 commit を確定した後、**その commit に** `v1.0.0` tag を作成します。

GitHub Release は同じ `v1.0.0` tag を選びます。

注意:

- tag を古い commit に付けない
- docs/version sync 前の commit に tag を付けない
- 今回は初回正式リリースなので通常 release とする
- title / notes / tag が同じ version を指すことを確認

---

## 9. Release 後の確認

- [ ] Git tag `v1.0.0` が期待する commit を指す
- [ ] GitHub Release が `v1.0.0` tag を使用
- [ ] GitHub Release title が `GoFile ABDM Helper v1.0.0 — Initial Release`
- [ ] `VERSION` = `1.0.0`
- [ ] Userscript `@version` = `1.0.0`
- [ ] CHANGELOG / README が一致
- [ ] broken link がない
- [ ] `[Unreleased]` に release 済み内容が重複していない

---

## 10. 今後の release

`v1.0.0` より後は通常の semantic versioning を前提に version を進めます。

例:

```text
v1.0.1  bug fix
v1.1.0  backward-compatible feature
v2.0.0  breaking change
```

今後は release ごとに:

1. `[Unreleased]` を更新
2. tests
3. docs sync
4. version bump
5. release commit
6. tag
7. GitHub Release

の順を維持してください。

---

## 11. Rollback / hotfix

database migration や persistent server schema はありませんが、rollback が常に安全とは仮定しません。

確認対象:

- Userscript GM storage compatibility
- Helper API compatibility
- GoFile API behavior
- ABDM REST API compatibility
- Windows startup command

hotfix でも Version / CHANGELOG / tag / Release の同期ルールを省略しないでください。
