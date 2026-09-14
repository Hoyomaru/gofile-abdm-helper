# リリース手順

この文書は GoFile ABDM Helper の Version・コード・ドキュメント・Git tag・GitHub Release を同期するための手順です。

基準日: **2026-09-14**

---

## 1. 現在の公開状況

正式な公開リリース体系は **`v1.0.0` から開始**しています。

`v1.0.0` は **2026-09-14 に公開済み**の初回正式リリースです。

現在確認できる release metadata:

```text
VERSION:             1.0.0
Userscript @version: 1.0.0
Git tag:             v1.0.0
Tag target commit:   e4fcf3a2ce0cee18f9320a9ff5df683acf78912a
GitHub Release:      v1.0.0
Release title:       GoFile ABDM Helper v1.0.0
Release date:        2026-09-14
Draft:               false
Prerelease:          false
Custom assets:       なし
```

GitHub Release:

https://github.com/Hoyomaru/gofile-abdm-helper/releases/tag/v1.0.0

`v1.0.0` tag は公開時点の snapshot を指します。公開後に `main` へ追加された documentation-only change は `[Unreleased]` として扱い、**既存の `v1.0.0` tag を移動しません**。

GitHub Actions / CI は未導入です。

---

## 2. 配布単位

専用 installer、wheel、exe、Docker image、独自 build archive の自動生成工程はありません。

`v1.0.0` では GitHub Release に custom asset を追加していません。GitHub が release tag から自動生成する次の source archive を配布物として利用できます。

- `Source code (zip)`
- `Source code (tar.gz)`

主な source tree:

- `gofile-abdm.user.js`
- `app.py`
- `gofile.py`
- `abdm.py`
- `tray.py`
- `start-tray.cmd`
- `requirements.txt`
- documentation

Userscript metadata に `@updateURL` / `@downloadURL` はありません。

利用者向けの導入方法は `README.md` を正とします。

---

## 3. Version 同期ルール

正式 release では次を一致させます。

```text
VERSION
Userscript @version
CHANGELOG version heading
Git tag v<version>
GitHub Release tag/title
README release version
```

`v1.0.0` の公開済み値:

```text
VERSION             = 1.0.0
Userscript @version = 1.0.0
CHANGELOG           = ## [1.0.0] - 2026-09-14
Git tag             = v1.0.0
GitHub Release tag  = v1.0.0
GitHub Release title= GoFile ABDM Helper v1.0.0
```

一部だけ別 version のまま tag / Release を作成しないでください。

---

## 4. v1.0.0 公開記録

`v1.0.0` は次の状態で公開されています。

- 通常 Release
- draft ではない
- prerelease ではない
- tag: `v1.0.0`
- tag target: `e4fcf3a2ce0cee18f9320a9ff5df683acf78912a`
- title: `GoFile ABDM Helper v1.0.0`
- published: `2026-09-14`
- custom asset: なし
- GitHub-generated source archive: あり

Release notes には、主な機能、安全設計、既知の制限、README への案内を記載しています。

公開済み Release の実体を確認する場合は GitHub Release ページを参照し、この文書内の古い予定値だけを根拠にしないでください。

---

## 5. 今後のリリース前チェック

### Source / docs

- [ ] `VERSION` と予定 version が一致
- [ ] Userscript `@version` と予定 version が一致
- [ ] `CHANGELOG.md` に release entry
- [ ] README の current release 表記を更新
- [ ] DEVELOPMENT が現在仕様と一致
- [ ] ARCHITECTURE / TROUBLESHOOTING が現在仕様と一致
- [ ] 古い Tag / Release を前提にした説明が残っていない
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

## 6. 実機 smoke test

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

## 7. Security regression check

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

## 8. 今後の Tag / GitHub Release 作成

release 対象 commit を確定した後、**その commit に** `v<version>` tag を作成します。

GitHub Release は同じ tag を選びます。

注意:

- tag を古い commit に付けない
- docs/version sync 前の commit に tag を付けない
- `VERSION` / Userscript / CHANGELOG / README と tag version を一致させる
- title / notes / tag が同じ version を指すことを確認する
- 公開済み tag を、公開後の documentation fix のためだけに移動しない

custom asset が必要になるのは、exe / installer / standalone archive 等を正式な配布物として用意した場合です。source-only release では GitHub-generated source archive だけでも問題ありません。

---

## 9. Release 後の確認

- [ ] Git tag が期待する release commit を指す
- [ ] GitHub Release が同じ tag を使用
- [ ] Release title / notes が予定 version と一致
- [ ] `VERSION` と Userscript `@version` が一致
- [ ] CHANGELOG / README が一致
- [ ] broken link がない
- [ ] `[Unreleased]` に release 済み内容が重複していない
- [ ] 公開後に `main` へ追加した変更は `[Unreleased]` に記録

---

## 10. 今後の versioning

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
8. release 後の整合性確認

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
