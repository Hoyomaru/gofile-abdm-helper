# リリース手順

この文書は GoFile ABDM Helper の Version・コード・ドキュメント・Git tag・GitHub Release を同期するための手順です。

基準日: **2026-09-27**

---

## 1. 現在のリリース状況

正式な公開リリース体系は **`v1.0.0` から開始**しています。

- `v1.0.0`: 2026-09-14 公開の初回正式リリース
- `v1.1.0`: 2026-09-15 公開済み。reliability / recovery 改善と backward-compatible feature を含む
- `v1.2.0`: 2026-09-27 公開済み。送信UI簡略化、Windows one-step setup、自己診断を含む

`v1.1.0` の公開済み release metadata:

```text
VERSION:             1.1.0
Userscript @version: 1.1.0
CHANGELOG:           ## [1.1.0] - 2026-09-15
Git tag:             v1.1.0
Tag target commit:   e755a4abceeae53e82b081267923c773511568a8
GitHub Release:      v1.1.0
Release title:       GoFile ABDM Helper v1.1.0
Published:           2026-09-15
Draft:               false
Prerelease:          false
Custom assets:       なし
```

公開済み Release の実体は GitHub Release ページを正とし、文書内の値だけで判断しません。

https://github.com/Hoyomaru/gofile-abdm-helper/releases

GitHub Actions の `Tests` workflow を導入済みです。`main` push と pull request で Python / Userscript regression test、Windows setup smoke、syntax checkを実行します。Release publish workflowも同じ主要Gateを再実行してからtag/Releaseを作成します。

---

## 2. 配布単位

専用 installer、wheel、exe、Docker image、独自 build archive の自動生成工程はありません。

GitHub Release では GitHub が release tag から自動生成する次の source archive を主配布物として利用します。加えて、今後の release workflow は、その release gate で実際に解決した Python 依存一式を `python-dependencies-v<version>.txt` として添付します。

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

`v1.1.0` の公開済み値:

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

### v1.2.0

- published: 2026-09-27
- tag: `v1.2.0`
- tag target: `8f19bd750e27adc182251bdee9d008423a87cbcb`
- title: `GoFile ABDM Helper v1.2.0`
- draft: false
- prerelease: false
- custom assets: なし
- GitHub-generated source archive: あり
- Python / Userscript validation: PASS
- Windows one-step setup smoke / idempotent reuse: PASS
- 2026-09-27 real-hardware setup / tray / self-diagnostics: PASS


### v1.1.0

- published: 2026-09-15
- tag: `v1.1.0`
- tag target: `e755a4abceeae53e82b081267923c773511568a8`
- title: `GoFile ABDM Helper v1.1.0`
- draft: false
- prerelease: false
- custom assets: なし
- GitHub-generated source archive: あり

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

### Python tests / dependency snapshot

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py gofile.py abdm.py tray.py
```

正式 release の `Publish Release` workflow は `requirements.txt` を解決した直後に `pip freeze --all` を記録し、Python / pip version と合わせて `python-dependencies-v<version>.txt` を artifact 化します。publish job は同じ file を GitHub Release asset へ添付します。これにより、range 指定の `requirements.txt` を維持しつつ、実際に release gate を通過した依存セットを後から再現・調査できます。

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

- fresh Windows folderで `setup-windows.cmd` を実行し、`.venv` 作成 / dependency install / tray起動
- 空白を含む展開先pathでもtrayが起動
- `start-tray.cmd` が作成済み `.venv` を再利用
- Settings → **自己診断** で Helper version / ABDM接続 / Queue件数を確認
- ABDM停止時にHelper正常 / ABDM異常を分けて表示
- Helper停止時にsetup/tray起動案内を表示
- Helper `/health`
- ABDM `/queues` connection
- 通常 GoFile share resolve
- password protected root / child folder
- parent / child different password
- wrong password → retry
- file 1件 send
- folder recursive selection
- **フォルダ構造を維持** OFF で flat send
- structure preserve + explicit Save folder
- queue selection
- Retry Failed
- Cancel Send
- ABDM接続確認を意図的に遅らせた状態で送信を連続操作し、同じ選択の登録が1回だけ開始される
- ABDM接続確認失敗後に送信操作が再度可能になる
- send 中の SPA navigation
- `resolve_id` expiry / Helper restart 後の残り送信再開
- ABDM uncertain result の表示と blind retry 防止
- Windows tray start / restart / exit
- hung-but-alive Helper の health failure threshold 後 restart
- Start with Windows on/off
- rate-limit stop behavior

実施結果は release commit / PR に対して最低限次を残します。未実施項目を PASS と記録しません。

| 項目 | 記録内容 |
|---|---|
| 実施日 | `YYYY-MM-DD` |
| release commit | full SHA |
| OS / browser / Userscript manager / Python / ABDM | 実際の環境 |
| GoFile resolve / send | PASS / FAIL / NOT RUN |
| password / retry / navigation / uncertain | PASS / FAIL / NOT RUN |
| Windows setup / tray | PASS / FAIL / NOT RUN |
| 備考 | 再現条件、未実施理由、関連 issue / PR |

---

## 7. Security regression check

- [ ] Helper bind は `127.0.0.1`
- [ ] ABDM target は `127.0.0.1:15151`
- [ ] `/api/*` marker guard が有効
- [ ] `/api/diagnostics` がpassword / token / direct URL / save pathを返さない
- [ ] ABDM offline時もdiagnosticsでHelper正常とABDM異常を分離できる
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

source-only release でも GitHub-generated source archive を主配布物とします。`python-dependencies-v<version>.txt` は実行環境再現・障害調査用の運用assetであり、installerやbinary配布物ではありません。

### v1.1.0 release notes の要点

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
- [ ] `python-dependencies-v<version>.txt` が Release asset として添付され、Python / pip version と resolved package version を含む
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
