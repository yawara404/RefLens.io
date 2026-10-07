# 公開サイトでpixivを使うために必要なこと

公開環境（`https://art.wawa-app.me/RefLens.io/`、`./start.sh public` / `deploy`）でpixiv連携を動かすには何が必要かをまとめた手順ガイドです。既存のローカル向け手順は [PIXIV_SETUP.md](PIXIV_SETUP.md) を参照してください。

> **前提**: RefLens の pixiv 連携は **非公式のモバイルApp API** を使います（Pixiv公式の開発者向けAPIではありません）。非公式APIの利用はPixivの利用条件・アカウント停止リスクと切り離せません。公開前に必ずこのリスクを許容できるか判断してください。

## 0. 結論（サマリ）

公開でpixivを使うには、次の6つが揃っている必要があります。**Webログイン（PKCE）は有効化済み**ですが、公開前に潰すべきは **主に 2** です。

| # | 要件 | 状態 |
| --- | --- | --- |
| 1 | メール/パスワード認証と個人アカウント | ✅ あり（公開側DB同期も運用中） |
| 2 | **個人ごとのアクセス制御（所有チェック）** | ❌ 詳細系APIに検証なし（→ 2.2）**公開前の必須修正** |
| 3 | 未ログイン（ゲスト）状態でのpixiv実データ遮断 | ✅ 共通ゲストには `_get_account()` が `None` を返す（ゲスト側の明示401は未実装 → 2.1） |
| 4 | 秘密情報の管理（Client ID/Secret・暗号化キー・`SECRET_KEY`） | ⚠️ 値は揃っている前提 / `SECRET_KEY` が既定値のまま（→ 2.3） |
| 5 | 配信経路と判定フラグの整理（`ROOT_PATH` 判定の置き換え） | 🟡 pixiv可否の `ROOT_PATH` 判定は撤廃済み。残りは `token_connect_available`（→ 1, 2.4） |
| 6 | Pixiv側の条件（非公式API・コールバック固定・レート制限・権利） | ✅ 実装済み（公開時も同じ制約 → 2.5） |

---

## 1. 現状: 公開環境で何が無効になっているか

`ROOT_PATH`（公開時は `/RefLens.io`）を理由に pixiv を全面無効にしていた状態は **解除し、Webログイン（PKCE）は公開でも使える**ようにしました。Refresh Token を手で貼る接続だけが公開では無効のままです。

| ファイル | 現状 |
| --- | --- |
| `backend/app/routers/pixiv.py` `_get_account()` | **共通ゲスト（`creator@reflens.io`）にだけ `None`** を返す。ログイン済みユーザーは自分の `pixiv_accounts` 行を使うため、公開でも `live` になる |
| `pixiv.py` `GET /pixiv/status` | `connect_available` = `is_configured()`（公開でも `true`）。Refresh Token 用の `token_connect_available` は公開で `false` |
| `pixiv.py` `POST /pixiv/connect`（Refresh Token方式） | **公開では 403 のまま**（「Pixivでログイン」を案内する文言） |
| `auth.py` `POST /pixiv/start` / `/pixiv/complete` | 公開でも **200**（Webログイン可能） |
| `auth.py` `GET /auth/me` | `pixiv_connected` / `pixiv_username` を実態どおり返す（`ROOT_PATH` での強制は撤廃） |
| `bookmarks.py` `_fetch_pixiv_metadata()` | 未接続ならスキップ（`ROOT_PATH` 判定は撤廃） |
| `frontend/composables/usePixiv.ts` | `canConnect` = `connect_available`、`canConnectWithToken` = `token_connect_available` |

**共通ゲストを遮断している理由**（`PIXIV_SETUP.md` の公開プレビュー節）: 未ログイン訪問者がすべて共通ゲスト（`creator@reflens.io`）で1つのユーザーを共有しており、この状態でpixivトークンを保存すると **他の訪問者が同じPixivアカウントのデータを読めてしまう** からです。Webログインは既存の個人アカウント、または pixiv ごとに新規作成したアカウントにだけ紐づき、共通ゲストへは紐づきません（`auth.py` の 409 ガード）。

**公開前に潰すべき残課題**: 2.2 の所有チェック（詳細・更新系API）。ここが済むまで全ユーザー公開はしないでください。

---

## 2. 有効化に必要な要件

### 2.1 未ログイン状態でpixiv実データを触らせない（要件3）

- `backend/app/routers/auth.py:86-104` の `get_current_user` は **トークンが無い・無効でもゲストユーザーを返します**（未ログイン＝ゲストの設計）。公開サイトもこの挙動のままです。
- 現在守られている部分:
  - ゲストへのRefresh Token連携は 401（`auth.py:218`）、Pixivログイン連携時の重複は 409（`auth.py:250`）、ゲストに紐づいたPixivアカウントでのログインは 409（`auth.py:275`）
  - 画像プロキシ `GET /pixiv/image` は接続アカウントが無いと 403（`pixiv.py:296`）
  - 実データ取得は `_get_account()` が **そのユーザー自身の** `pixiv_accounts` 行を見るため、ログインしていれば自分のデータにしか触れられません
- ただし公開で足りないのは「**未ログインのままpixiv実データAPIにアクセスできないこと**」。次のいずれかで統一してください。
  1. （推奨）pixiv ルーター共通の依存を追加し、**ゲストユーザーなら 401** を返す（デモフィードは許可するなら `mode=demo` のみ 200）
  2. 未ログイン時に `/view` へログインダイアログを強制し、API側も併せて遮断
- フロント（`frontend/pages/view.vue:307, 462`、`PixivImportModal.vue:220`）は `canConnect` だけを見ているので、**未ログイン時はログインを促す導線**を足す必要があります。

### 2.2 個人ごとのアクセス制御（要件2・**公開前の必須修正**）

現状の一覧系APIは `user_id` でフィルタしていますが（`boards.py:57`、`bookmarks.py:212`、`pixiv.py:601` など）、**詳細・更新系に所有チェックがありません**。IDを知るだけで他人のデータを読・改・削できます。ローカル1人運用なら実害が小さいものの、公開で複数ユーザーがpixivデータを持ち始める状態では **放置不可** です。

| 場所 | 問題 |
| --- | --- |
| `backend/app/routers/boards.py:128` `GET /{board_id}` | `user_id` 検証なし → 他人のボードとキャンバスアイテムが読める |
| `backend/app/routers/boards.py:202` `PUT /{board_id}` | 所有チェックなし → 他人のボードを更新できる |
| `backend/app/routers/boards.py:229, 269` `items/batch`・`arrange` | 所有チェックなし |
| `backend/app/routers/boards.py:321, 334` `DELETE` 系 | 所有チェックなし → 他人のボード/アイテムを削除できる |
| `backend/app/routers/bookmarks.py:472, 487` | `folder` 変更・削除に `user_id` 検証なし |
| `backend/app/routers/media.py:314` `POST /{media_id}/reanalyze` | **認証依存すら未使用**（`user` 未取得） |
| `backend/app/routers/media.py:320` | `MediaItem.id` のみで参照 |
| `backend/app/main.py:40` `/uploads` 静的マウント | **認証なし**。Tunnelも `/RefLens.io/uploads/*` を公開（`cloudflare/reflens.yml`） |

対処:

1. 詳細・更新・削除系の先頭で `obj.user_id != user.id → 404` を返す（一覧系と同じ `user_id` フィルタで統一）
2. `reanalyze` に `get_current_user` と所有チェックを追加
3. `/uploads` を **認証付きエンドポイント経由**にするか、共有ライブラリの画像だけ意図的に公開する方針を明記する（pixiv から取り込んだ画像は必ず非公開側に回す）
4. 直したことをテストで固定する（→ 4. 検証チェックリスト）

### 2.3 秘密情報とキーの管理（要件4）

- **公開バックエンドも同じ `backend/.env` を読みます**（`start.sh` が `backend/` で uvicorn を起動）。つまり `PIXIV_CLIENT_ID` / `PIXIV_CLIENT_SECRET` / `PIXIV_TOKEN_ENCRYPTION_KEY` が設定済みなら公開側でも `is_configured()` は `true`（`pixiv_client.py:38`）。**足りないのは設定値ではなくポリシー（2.1〜2.2）です。**
- `backend/app/core/config.py` の `SECRET_KEY` に固定の既定値は置いていません（未設定時はプロセスごとのランダム鍵）。**公開前に `backend/.env` の `SECRET_KEY` を必ず固有の長い値へ変更**してください（この値でJWTを発行しているため、公開中の変更は全ユーザーのトークンを失効させます。変わる前にログインし直せる状態にしておく）。
- `PIXIV_TOKEN_ENCRYPTION_KEY` は生成後に変更しないこと。失うと保存済みトークンが復号不能（再接続が必要）。`.env` とDBバックアップをリポジトリ外で管理する。
- `backend/scripts/sync_public_accounts.py` は **`instagram_accounts` を同期しません**。`pixiv_accounts` も**既定は同期しない**が、`PIXIV_SYNC_USERS`（`backend/.env`、カンマ区切りの username / email）で名指ししたユーザーだけ例外的に移す（段階公開 ①「管理者のみ」。共通ゲストは常に除外）。移す運用に踏み込んだ以上、**暗号化キーの共有と、トークン平文がDBに残っていないことの確認**は必須。
  - トークンはリフレッシュのたびに入れ替わるため、スクリプトは `expires_at` が**公開側の方が新しい行を上書きしない**（公開側で更新したトークンを古い側で潰さないため）。
  - 指定が空なら従来どおり 1 本も移さない。
- 平文トークンの残存確認:

  ```bash
  sqlite3 backend/reflens-public.db "select id, user_id, access_token, refresh_token from pixiv_accounts;" | head
  # 開頭が fernet:gAAAAA（Fernet 暗号文）でなければ平文。その行は再接続させて暗号化し直す。
  ```

- ログ（`logs/*.log`）、`.env`、DB、トンネル認証情報を第三者に渡さない。Pixiv側のトークン失効は画面上の「接続解除」では行わないため、漏えい時はPixivの設定から直接無効化する。

### 2.4 配信経路と判定フラグ（要件5）

- 現在の経路（`cloudflare/reflens.yml`）:

  | パス | 行き先 |
  | --- | --- |
  | `/RefLens.io/api/*` | `127.0.0.1:8082`（バックエンド、`ROOT_PATH=/RefLens.io`、DB=`reflens-public.db`） |
  | `/RefLens.io/uploads/*` | `127.0.0.1:8082`（無認証の静的配信） |
  | それ以外 | `127.0.0.1:3121`（フロント、base `/RefLens.io/`） |

- **`ROOT_PATH` はサブパス配信の設定であって、pixiv可否の判定には使わない** 方針に切り替えます。現状は `ROOT_PATH` の有無が9箇所以上に直書きされており、配信形態の変更と機能のON/OFFが巻き込まれます。代わりに専用フラグを用意します。

  ```env
  # backend/.env
  PIXIV_PUBLIC_ENABLED=true   # 公開環境でpixivを有効にする（未ログイン遮断は必須）
  ```

  そのうえで pixiv可否の `settings.ROOT_PATH` 判定は撤廃済みです（`_get_account()` は共通ゲストのみ、`/pixiv/start`・`/pixiv/complete`・`/auth/me`・`bookmarks.py` の各ガードは削除）。残っている `ROOT_PATH` 判定は公開でのみ Refresh Token 接続を切る `token_connect_available`（`pixiv.py`）と、`main.py:16` のルーティング用途だけです。
- 画像は `i.pximg.net` が `Referer` 必須のため **必ずサーバー経由**（`GET /pixiv/image`、キャッシュ先 `PIXIV_CACHE_DIR`）。公開時は帯域・ディスク・Pixiv側レート制限を考慮し、キャッシュのTTLと容量上限を決めます。
- クロスオリジンでAPIを叩く構成（別ドメイン/ポートのフロント）にする場合、`config.py` の `CORS_ORIGINS` に公開オリジンを追加してください。現状は同一オリジン配信なので未設定でも動きます。

### 2.5 Pixiv側の条件（要件6）

- Client ID / Client Secret は **Pixiv Developersのアプリ登録では取得できません**。非公式App APIクライアントの認証方式に対応する値が必要（取得例は `PIXIV_SETUP.md` に記載）。値はサーバーにのみ置く。
- コールバック先がPixivドメインに固定されているため、**ログイン後に発生した `callback?code=...` のURLを一度手動で貼り付ける** 手順になります（`auth.py` の `PIXIV_CALLBACK` 検証、state/PKCE は600秒で失効）。公開サイトでも手順は同じ。このUXを許容できるか、または **RefLens用に登録したOAuthクライアント＋許可済みリダイレクトURI** を別途用意するかを選んでください。PixivのパスワードをRefLensに入力させる方式にはしません。
- レート制限・仕様変更に備えて、取得失敗時はデモフィードへフォールバックする現挙動を維持します。
- 1つのPixivアカウントは1つのRefLensアカウントにしか連携できません（重複は409）。アカウント停止時に備え、連携解除の手順を用意してください。
- 取り込んだ画像は作者の権利とPixivの利用条件に従って扱う（保存先ディレクトリの容量確認も含む）。

---

## 3. 推奨する実装ステップ

| フェーズ | 内容 | 対象ファイル |
| --- | --- | --- |
| 0 | 秘密情報の整備: `SECRET_KEY` を固有値へ、`PIXIV_TOKEN_ENCRYPTION_KEY` のバックアップ、平文トークンの確認 | `backend/.env` |
| 1 | 所有チェックの追加（2.2の一覧を潰す）+ `reanalyze` に認証依存を追加 | `boards.py` / `bookmarks.py` / `media.py` |
| 1 | `/uploads` の認証付き配信へ移行（または非公開画像を別ディレクトリに分離） | `main.py`、`cloudflare/reflens.yml` |
| 2 | ゲスト（未ログイン）に対する pixiv 実データAPIの401化（`_get_account` での遮断は実装済み。明示401を足す） | `pixiv.py` / `auth.py` |
| 3 | ~~`PIXIV_PUBLIC_ENABLED` フラグ導入と `ROOT_PATH` 判定の置き換え~~ **pixiv可否の `ROOT_PATH` 判定は撤廃済み**。残るは `token_connect_available`（公開で Refresh Token 接続を切る専用フラグ）と `main.py:16` のルーティング用途 | `config.py`、`pixiv.py` |
| 4 | フロント導線: 未ログイン時のログイン促進、接続ボタン表示条件 | `usePixiv.ts`、`view.vue`、`PixivConnectDialog.vue` |
| 5 | デプロイ: `./start.sh deploy` → 実ブラウザでE2E確認（→ 4） | — |
| 6 | 段階公開: ①**管理者のみ（実装済み）** `PIXIV_SYNC_USERS` に名指ししたユーザーだけ `pixiv_accounts` を公開側へ同期 → ②招待制 → ③全ユーザー | 運用 |

各フェーズの後にバックアップ（`sqlite3 backend/reflens-public.db ".backup backup.db"`）を取ってから次へ進むと安全です。

---

## 4. 検証チェックリスト（E2E）

| # | 手順 | 期待値 |
| --- | --- | --- |
| 1 | 未ログインで `GET /api/v1/pixiv/feed` | デモのみ、実データが出ない / 指定通り401 |
| 2 | 未ログインで `POST /api/v1/pixiv/connect`（公開） | 403（「Pixivでログイン」を案内）。`/pixiv/start` は 200 でログインフローを開始できる |
| 3 | ユーザーAでログインしpixiv接続 → 自分のフィードが実データ | `mode: live` |
| 4 | ユーザーBでログイン（別ブラウザ/シークレット） | Aのボード・ライブラリ・pixivデータが見えない |
| 5 | Bのセッションで `GET /api/v1/boards/{AのボードID}` | 404 |
| 6 | Bのセッションで `PUT` / `DELETE /api/v1/boards/{AのボードID}` | 404、Aのデータは無変更 |
| 7 | Bのセッションで `DELETE /api/v1/bookmarks/{AのアイテムID}` | 404 |
| 8 | 未ログインで `POST /api/v1/media/{id}/reanalyze` | 401 |
| 9 | 未ログインで `GET /RefLens.io/uploads/{他人の画像}` | 403/404（方針どおり） |
| 10 | ログアウト後、pixiv実データ系の画面/API | デモ表示に戻る、実データが出ない |
| 11 | `select ... from pixiv_accounts` でトークン列 | `gAAAAA...`（暗号化済み）のみ |
| 12 | `GET /`（ヘルスチェック）とトップページ | タイトル・ログイン・ボード作成が通常どおり |
| 13 | コンソール・`logs/*.log` | 401/403の想定外ログ、500エラーなし |

---

## 5. リスク判断メモ

- **非公式APIのリスク**: 仕様変更で即座に停止、Pixiv側の判断でアカウント（連携に使った自分のアカウント）が制限される可能性があります。公開サービスのSLAには組み込めません。
- **トークンの保管**: 公開サーバーのDBに複数人のRefresh Tokenが平文で無いか、定期的に確認してください。漏えい時はPixiv側の設定でトークンを失効させてください。
- **画像の扱い**: 公開配信で外部に取り込んだ画像を配る場合、帯域コストと権利面の確認が必要です。
- **最小構成の代替案**: 「自分のアカウントだけpixivを有効化し、他のユーザーにはデモのみ見せる」運用なら、2.1のゲスト遮断と2.2の所有チェックだけで足り、実装量は大幅に減らせます。

---

## 6. 参照ファイル

| ファイル | 役割 |
| --- | --- |
| `PIXIV_SETUP.md` | ローカルでのpixiv接続手順・注意事項 |
| `backend/app/routers/pixiv.py` | フィード・画像プロキシ・取り込み（ゲスト遮断は `_get_account()`、公開でのみ Refresh Token 接続を 403） |
| `backend/app/routers/auth.py` | Pixivログイン（PKCE）・ゲストの扱い |
| `backend/app/services/pixiv_client.py` | App APIクライアント・`is_configured()` |
| `backend/app/core/pixiv_tokens.py` | トークンの暗号化/復号（Fernet） |
| `backend/app/core/config.py` | `PIXIV_*` / `ROOT_PATH` / `CORS_ORIGINS` |
| `frontend/composables/usePixiv.ts` | 接続可否（`connect_available` / `token_connect_available`）とフィード取得 |
| `start.sh` | `public` / `deploy` / `pixiv-local` の起動条件 |
| `cloudflare/reflens.yml` | Tunnel の ingress（api / uploads / 本体の振り分け） |
| `backend/scripts/sync_public_accounts.py` | 公開側DBへの同期（pixivトークンは `PIXIV_SYNC_USERS` の分だけ / 既定は移さない） |
