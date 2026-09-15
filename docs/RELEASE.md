# リリース手順

この文書は GoFile ABDM Helper の Version・コード・ドキュメント・Git tag・GitHub Release を同期するための手順です。

基準日: **2026-09-15**

---

## 1. 現在のリリース状況

正式な公開リリース体系は **`v1.0.0` から開始**しています。

- `v1.0.0`: 2026-09-14 公開の初回正式リリース
- `v1.1.0`: 2026-09-15 の次回 release target。reliability / recovery 改善と backward-compatible feature を含む

`v1.1.0` の release commit では次を一致させます。

```text
VERSION:             1.1.0
Userscript @version: 1.1.0
CHANGELOG:           ## [1.1.0] - 2026-09-15
Git tag:             v1.1.0
GitHub Release:      v1.1.0
Release title:       GoFile ABDM Helper v1.1.0
Release date:        2026-09-15
Draft:               false
Prerelease:          false
Custom assets:       なし
```

公開済み Release の実体は GitHub Release ページを正とし、文書内の予定値だけで公開済みと判断しません。

https://github.com/Hoyomaru/gofile-abdm-helper/releases

GitHub Actions の `Tests` workflow を導入済みです。`main` push と pull request で Python / Userscript regression test と syntax check を実行します。

---

## 2. 配布単位

専用 installer、wheel、exe、Docker image、独自 build archive の自動生成工程はありません。

GitHub Release では custom asset を必須とせず、GitHub が release tag から自動生成する次の source archive を配布物として利用します。

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

Userscript metadata に `@updateURL` / `@downloadURL` はありません。新しい release へ更新する場合は新しい `gofile-abdm.user.js` を Userscript manager へ手動で反映します。

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

一部だけ別 version のまま tag / Release を作成しないでください。

`v1.1.0` の期待値:

```text
VERSION              = 1.1.0
Userscript @version  = 1.1.0
CHANGELOG            = ## [1.1.0] - 2026-09-15
Git tag              = v1.1.0
GitHub Release tag   = v1.1.0
GitHub Release title = GoFile ABDM Helper v1.1.0
```

---

## 4. 公開済み履歴

### v1.0.0

- published: 2026-09-14
- tag: `v1.0.0`
- tag target: `e4fcf3a2ce0cee18f9320a9ff5df683acf78912a`
- title: `GoFile ABDM Helper v1.0.0`
- draft: false
- prerelease: false
- custom assets: なし
- GitHub-generated source archive: あり

公開済み tag は後から移動しません。

---

## 5. リリース前チェック

### Source / docs

- [ ] `VERSION` と予定 version が一致
- [ ] Userscript `@version` と予定 version が一致
- [ ] `CHANGELOG.md` に release entry があり、`[Unreleased]` に release 済み内容が残っていない
- [ ] README の current release 表記・release link・raw Userscript link が予定 version と一致
- [ ] DEVELOPMENT が現在仕様と一致
- [ ] ARCHITECTURE / TROUBLESHOOTING が現在仕様と一致
- [ ] `docs/RELEASE.md` が現在の CI / release flow と一致
- [ ] secrets / credential が混入していない

### Python tests

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py gofile.py abdm.py tray.py
```

### Userscript tests

```bash
node --test tests/*.cjs
node --check gofile-abdm.user.js
```

### GitHub Actions

`Tests` workflow の Python / userscript job が両方 green であることを確認します。

CI は real GoFile / ABDM / Windows GUI の E2E を代替しません。

---

## 6. 実機 smoke test

可能な範囲で実施し、未実施項目を確認済み扱いにしないでください。

候補:

- Helper `/health`
- ABDM `/queues` connection
- 通常 GoFile share resolve
- password protected root / child folder
- parent / child different password
- wrong password → retry
- file 1件 send
- folder recursive selection
- `Send Flat`
- structure preserve + explicit Save folder
- queue selection
- Retry Failed
- Cancel Send
- send 中の SPA navigation
- `resolve_id` expiry / Helper restart 後の残り送信再開
- ABDM uncertain result の表示と blind retry 防止
- Windows tray start / restart / exit
- hung-but-alive Helper の health failure threshold 後 restart
- Start with Windows on/off
- rate-limit stop behavior

---

## 7. Security regression check

- [ ] Helper bind は `127.0.0.1`
- [ ] ABDM target は `127.0.0.1:15151`
- [ ] `/api/*` marker guard が有効
- [ ] JSON mutation guard が有効
- [ ] `/api/abdm/send` は JSON object 以外を拒否
- [ ] GoFile URL / content ID validation が有効
- [ ] GoFile direct-link host validation が有効
- [ ] path sanitization / collision disambiguation が有効
- [ ] `@connect *` がない
- [ ] `unsafeWindow` がない
- [ ] password / token / Cookie / direct URL が log に出ない
- [ ] 429 を blind retry しない
- [ ] access denied / password challenge を部分成功として cache しない
- [ ] uncertain ABDM POST を automatic retry しない

---

## 8. Tag / GitHub Release 作成

release 対象 commit を確定した後、**その commit に** `v<version>` tag を作成します。

GitHub Release は同じ tag を選びます。

注意:

- tag を古い commit に付けない
- docs/version sync 前の commit に tag を付けない
- `VERSION` / Userscript / CHANGELOG / README と tag version を一致させる
- title / notes / tag が同じ version を指すことを確認する
- 公開済み tag を後から移動しない

source-only release では GitHub-generated source archive だけで構いません。

### v1.1.0 release notes に含める要点

- Cancel Send / persistent Retry Failed
- SPA navigation / stale send generation guard
- `resolve_id` expiry 後の content ID remap / resume
- ABDM transport failure の `Uncertain` 分類
- Website Token retry policy 修正
- Windows drive root / sanitize collision / long extension 修正
- tray service identity check / hung Helper recovery
- GitHub Actions regression CI
- send は cancellation safety のため 1 file / Helper request を維持

---

## 9. Release 後の確認

- [ ] Git tag が期待する release commit を指す
- [ ] GitHub Release が同じ tag を使用
- [ ] Release title / notes が予定 version と一致
- [ ] `VERSION` と Userscript `@version` が一致
- [ ] CHANGELOG / README が一致
- [ ] release の raw Userscript URL が開ける
- [ ] source archive が生成されている
- [ ] broken link がない
- [ ] `[Unreleased]` に release 済み内容が重複していない
- [ ] 公開後に `main` へ追加した変更は `[Unreleased]` に記録

---

## 10. Versioning

通常の semantic versioning を前提に version を進めます。

```text
v1.0.1  bug fix
v1.1.0  backward-compatible feature
v2.0.0  breaking change
```

release ごとに:

1. `[Unreleased]` を更新
2. tests / CI
3. docs sync
4. version bump
5. release commit
6. tag
7. GitHub Release
8. release 後の整合性確認

の順を維持します。

---

## 11. Rollback / hotfix

database migration や persistent server schema はありませんが、rollback が常に安全とは仮定しません。

確認対象:

- Userscript GM storage compatibility
- Helper API compatibility
- GoFile API behavior
- ABDM REST API compatibility
- Windows startup command

hotfix でも Version / CHANGELOG / tag / Release の同期ルールを省略しません。
