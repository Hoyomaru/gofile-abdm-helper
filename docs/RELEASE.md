# リリース手順

この文書は、GoFile ABDM Helper のリリース時に **Version・コード・ドキュメントを同期するための手順**です。

調査基準日: **2026-09-14**

---

## 1. 現在確認できるリリース状況

| 項目 | 状態 |
|---|---|
| `VERSION` | `1.0.3` |
| Userscript `@version` | `1.0.3` |
| `CHANGELOG.md` | `1.0.0`〜`1.0.3` + `[Unreleased]` |
| Git tags | `v1.0.0`, `v1.0.3` |
| GitHub Releases | 0件 |
| GitHub Actions / CI | 未導入 |
| build artifact | 専用 build 工程なし |

履歴には `v1.0.1` / `v1.0.2` の release 名を持つ merge commit / PR / CHANGELOG entry がありますが、調査時点ではそれらの Git tag は確認できません。

また、現在の `main` には `VERSION=1.0.3` のまま `[Unreleased]` の変更が入っています。したがって **main HEAD と stable v1.0.3 を同一視しないでください。**

---

## 2. 現在の配布単位

専用 installer、wheel、exe、Docker image、zip artifact の生成工程はありません。

主な利用物は source tree です。

- `gofile-abdm.user.js`
- `app.py`
- `gofile.py`
- `abdm.py`
- Windows の場合 `tray.py`, `start-tray.cmd`
- `requirements.txt`

Userscript metadata に `@updateURL` / `@downloadURL` はありません。自動配布 pipeline が存在する前提にしないでください。

---

## 3. 自動工程 / 手動工程

### 自動化済み

調査時点では GitHub Actions による release automation はありません。

### 手動

- Version 決定
- tests
- syntax check
- 実機 smoke test
- Version file / Userscript metadata 更新
- CHANGELOG 更新
- README / DEVELOPMENT / docs 更新
- commit
- tag
- GitHub Release を採用する場合、その作成

---

## 4. リリース前チェック

### 4.1 現在の branch と差分

release 対象 commit を固定してください。

最低限確認するもの:

```text
README.md
DEVELOPMENT.md
CHANGELOG.md
VERSION
gofile-abdm.user.js
app.py
gofile.py
abdm.py
tray.py
requirements.txt
tests/
docs/
```

### 4.2 Version

正式 release では次を一致させます。

```text
VERSION
Userscript @version
CHANGELOG version heading
Git tag v<version>
```

例:

```text
1.0.4
@version 1.0.4
## [1.0.4] - YYYY-MM-DD
v1.0.4
```

`VERSION` だけを上げる、または Userscript `@version` だけを上げる状態を残さないでください。

### 4.3 `[Unreleased]`

`CHANGELOG.md` の `[Unreleased]` を確認し、実際に release 対象に含まれる変更だけを version section へ移します。

未完成 / 未採用の変更は release note に混ぜません。

---

## 5. テスト

### Python tests

```bash
python -m unittest discover -s tests -v
```

### Userscript Node tests

```bash
node --test tests/test_userscript.cjs
```

### Syntax checks

```bash
python -m py_compile app.py gofile.py abdm.py tray.py
node --check gofile-abdm.user.js
```

CI はないため、実行結果を release PR / commit / Release note などに残すことを推奨します。

---

## 6. 実機 smoke test

環境が用意できる範囲で、実施したものと未実施のものを明確に分けて記録してください。

候補:

- Helper `/health`
- ABDM connection / queue list
- 通常の GoFile share resolve
- file 1件送信
- folder recursive selection
- `Send Flat`
- structure preserve + explicit Save folder
- `Retry Failed`
- Helper restart 後の recovery
- Windows tray start / restart / exit
- Windows **Start with Windows** on/off
- password protected root
- parent と別 password の child folder
- wrong password → retry
- password modal Cancel / Escape
- rate-limit response 時に blind retry しないこと

実施できなかった項目は **未確認** と明記してください。

---

## 7. Security regression check

release 前に次の境界を再確認します。

- [ ] Helper bind は `127.0.0.1`
- [ ] ABDM は `127.0.0.1:15151` 固定
- [ ] `/api/*` marker guard が有効
- [ ] JSON guard が有効
- [ ] GoFile URL host validation が有効
- [ ] GoFile direct link host validation が有効
- [ ] path sanitization が有効
- [ ] `@connect *` がない
- [ ] `unsafeWindow` がない
- [ ] password / token / Cookie / direct URL が log に出ない
- [ ] 429 を blind retry しない
- [ ] access-denied / password challenge を部分成功として cache しない

---

## 8. ドキュメント同期

release 内容に応じて更新します。

- `README.md`: 一般利用者に影響する変更
- `DEVELOPMENT.md`: API / state / invariant / known issue /内部実装変更
- `docs/ARCHITECTURE.md`: component boundary / data flow の変更
- `docs/TROUBLESHOOTING.md`: 新しい代表的障害と対処
- `CHANGELOG.md`: release summary

同じ長文を複数 file へコピーせず、詳細文書へ link してください。

---

## 9. 推奨する標準リリース手順

これは **今後の推奨手順**です。過去 release がすべてこの手順で行われたという意味ではありません。

1. release 対象 commit / branch を確定
2. tests / syntax checks を実行
3. 実機 smoke test を実施し、未確認項目も記録
4. `VERSION` 更新
5. Userscript `@version` 更新
6. `CHANGELOG.md` の `[Unreleased]` を version/date section へ整理
7. README / DEVELOPMENT / docs を同期
8. 最終 diff review
9. release commit / PR を merge
10. merge commit に `vX.Y.Z` tag を付与
11. GitHub Release 運用を採用する場合は tag から Release を作成
12. Release note に主要変更・既知制限・検証結果を記載
13. GitHub 上の tag / source files / Version 表記を再確認

### Tag の注意

過去履歴では `v1.0.1` / `v1.0.2` の tag が確認できないため、今後は release ごとに tag の存在を明示的に検証してください。

過去版 tag を後から作る場合は、その version が実際に対応する commit を履歴から特定してから行ってください。推測で tag を打たないでください。

---

## 10. GitHub Release について

調査時点では GitHub Releases はありません。

そのため、GitHub Release を新たに運用へ加える場合は「既存必須工程」ではなく **新しい release policy の採用**になります。

採用する場合の release note には少なくとも次を含めることを推奨します。

- version
- release date
- 主な Added / Changed / Fixed
- upgrade 手順に影響する点
- known limitations
- test / smoke test summary
- source tag

現在、アップロード必須の binary asset はありません。

---

## 11. Release 後の確認

- [ ] repository の `VERSION` が期待値
- [ ] Userscript `@version` が期待値
- [ ] CHANGELOG の date / version が一致
- [ ] tag が release commit を指している
- [ ] README の stable version 表記が一致
- [ ] broken link がない
- [ ] `[Unreleased]` に release 済み項目が重複していない
- [ ] code と docs の feature status が一致
- [ ] GitHub Release を採用した場合、その title / tag / notes が一致

---

## 12. Rollback / hotfix

現在、database migration や persistent server schema はありません。とはいえ rollback を「常に安全」とは仮定しないでください。

特に確認するもの:

- Userscript GM storage の互換性
- Helper API request/response compatibility
- GoFile API behavior の変化
- ABDM REST API compatibility
- Windows startup command

hotfix でも `VERSION` / Userscript / CHANGELOG / tag の同期ルールは省略しないでください。
