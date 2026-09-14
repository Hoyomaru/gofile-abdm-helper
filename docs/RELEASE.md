# リリース手順

この文書は GoFile ABDM Helper の Version・コード・ドキュメント・Git tag・GitHub Release を同期するための手順です。

基準日: **2026-09-14**

---

## 1. 現在のリリース方針

正式な公開リリース体系は **`v1.0.0` から開始**します。

開発途中の commit / PR には `v1.0.1`～`v1.0.3` という名称がありますが、それらは今後の正式リリース履歴としては扱いません。Tag / GitHub Release の公開履歴を整理したうえで、現在の `main` に含まれる完成状態を `v1.0.0` として最初に公開します。

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
VERSION            = 1.0.0
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

推奨 title:

```text
GoFile ABDM Helper v1.0.0 — Initial Release
```

推奨 note は README / CHANGELOG と矛盾しない内容にします。

最低限含める内容:

- 初回正式リリースであること
- GoFile → ABDM の localhost bridge であること
- file / folder selection
- recursive resolve
- Send to ABDM / Send Flat
- queue / Save folder / preset
- password-protected root / child folder
- rate-limit / cache safety
- Windows tray / startup
- security boundary
- known limitations
- installation は README を参照

この repository には必須 binary asset はありません。

---

## 8. Tag / GitHub Release 作成

release 対象 commit を確定した後、**その commit に** `v1.0.0` tag を作成します。

GitHub Release は同じ `v1.0.0` tag を選びます。

注意:

- tag を古い commit に付けない
- docs/version sync 前の commit に tag を付けない
- draft / prerelease にするかは release policy に従う。今回の目的は初回正式リリースなので通常 release を想定
- title / notes / tag が同じ version を指すことを確認

---

## 9. Release 後の確認

- [ ] Git tag `v1.0.0` が期待する commit を指す
- [ ] GitHub Release が `v1.0.0` tag を使用
- [ ] GitHub Release title が `v1.0.0`
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
