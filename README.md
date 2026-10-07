# RefLens.io（レフレンズ）

> **お試し公開URL**: https://art.wawa-app.me/RefLens.io/
> （Cloudflare Tunnel による公開のため、サーバー停止中はアクセスできません）

**散らばる資料を1枚のキャンバスへ。AIが構図・光・衣装を解剖するスマートリファレンスボード。**

イラストレーターやコンセプトアーティストのために設計された、デスクトップ定番ツール「PureRef」の超高速な操作性と、マルチモーダル Vision LLM による視覚構造解析を融合したリファレンス管理 Web アプリケーションです。

> **本リポジトリについて**: 開発成果物の紹介（サイト説明・技術説明）を目的としており、オープンソースとしてのセットアップ手順の提供・再利用・再配布は想定していません。

---

## サイト説明（できること）

### Canvas（PureRef ライクな無限キャンバス）

- マウスホイールのカーソル中心ズーム（5%〜500%）、中クリック / `Space + ドラッグ` によるパン
- ドラッグ移動・四隅リサイズ・自由回転・15度スナップ
- クリップボード / ドラッグ＆ドロップで OS やブラウザから画像をそのまま配置（`Ctrl+V` ペーストも可）
- グリッドパック整列・水平ライン整列・垂直整列
- 選択アイテムは Undo / Redo（最大30段階）

**アーティスト向けホットキー**

| キー | 動作 |
| --- | --- |
| `H` | 水平左右反転（シルエットの違和感チェック） |
| `V` | 垂直上下反転 |
| `G` | グレースケール切り替え（明暗比・Value スタディ） |
| `Delete` / `Backspace` | 選択アイテムを削除 |
| `Ctrl+A` | 全選択 |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Ctrl+0` | ビュー100%リセット |
| `D` | ライト / ダーク / OS 追従の切り替え |
| `?` / `F1` | ショートカット一覧モーダル |

### AI 解剖（Vision LLM）

アップロードした資料画像を自動スキャンし、プロ絵師視点の構造化 JSON を出力します。

- **構図**: アオリ / 俯瞰 / 三分割法 / 対角線パース、視線誘導
- **ライティング**: 逆光 / リムライト / トップライト / キーライト光源と明暗対比
- **ポーズ・アナトミー**: 重心位置、S字コントラポスト、パースの効き
- **衣装・シワ構造**: レザー / シフォン / 布素材感とテンション・弛みシワ
- **カラーパレット**: 主要5色の Hex を自動サンプリング（クリックで即コピー）
- **セマンティックタグ**: 検索・フィルタに直結するタグを自動生成

解析は `Ollama`（ローカル vision LLM）→ `Gemini Vision` → ヒューリスティック（画像特徴量）の順に自動フォールバックします。取得に失敗してもデモ表示に切り替わるため、UI は止まりません。

### pixiv 連携

- **「Pixivでログイン」**: pixiv 側のログイン画面だけで接続できる PKCE フロー（Refresh Token を手で貼る方式も併設。公開環境では PKCE のみ）
- タグ / キーワード検索、おすすめ、デイリーランキング、フォロー、ブックマーク、作品詳細（複数ページ）
- 作品ごとに**全ページをサーバー経由で一括取り込み**し、Manager へ保存 or キャンバスへ配置
- 同じ作品・同じページは再ダウンロードせず再利用（重複登録を防止）
- pixiv のタグを Vision 解析結果へマージして検索・フィルタに充当
- `i.pximg.net` は `Referer` 必須のため、画像取得は必ずバックエンドの画像プロキシ経由

### Instagram 連携

- Instagram アカウントを接続し、ストックした投稿や保存リファレンス写真をキャンバスへ一括取り込み
- 接続前でも試せるクリエイター向けデモフィードを内蔵

### 検索・フィルタ・UI

- 「逆光」「アオリ」「サイバーパンク」「シフォン素材」などのタグ／自然言語で絞り込み・ハイライト
- フィルタ候補は頻度順に並び、ヒット件数をリアルタイム表示
- ライト / ダーク / OS 追従の3状態テーマ（`localStorage` 保存・タブ間同期、FOUC 防止のインラインスクリプト付き）
- タッチ操作対応（ピンチズーム、2本指パン、タップ選択、長押し / 右クリックのコンテキメニュー）
- トースト通知、背景パターン、アバター画像のアップロード
- ブックマーク（フォルダ管理）とライブラリ（Manager）の2系統で資料を整理

---

## 技術説明

### 全体構成

```text
ブラウザ (Nuxt 3)
├─ フロントエンド: Nuxt 3 (Vue 3 / TypeScript / Vite / Tailwind CSS / Pinia / Lucide)
├─ API サーバー:  Python (FastAPI + SQLAlchemy + Uvicorn)
├─ データベース:  SQLite（既定・ゼロコンフィグ） / MySQL 8.x 構成も可
├─ AI:           Ollama (ローカル vision LLM) → Gemini Vision → ヒューリスティック の自動選択
└─ 画像:         アップロード画像と pixiv 画像をサーバー側でプロキシ / キャッシュ
配信: Cloudflare Tunnel で https://art.wawa-app.me/RefLens.io/ をサブパス配信
      （バックエンドとフロントを別ポートで立て、ROOT_PATH で /RefLens.io/ を剥がす）
```

### フロントエンド

- Nuxt 3（`srcDir: '.'` / `serverDir: 'server'` を明示し、Nuxt 4 へ上げても生成先がずれないようにした構成）
- 状態管理は Pinia の Options Store。`reflens:auth-changed` イベントで認証変更を各ストアへ伝播
- 認証トークンは `localStorage` の `reflens-auth-token` に保存し、`frontend/plugins/api-auth.client.ts` が該当する API へ自動付与
- 期限切れ・改竄されたトークンは自動破棄され、共通ゲスト領域へ戻る
- 配色は CSS 変数（`frontend/assets/css/main.css` の `:root` / `.dark`）で一元管理
- VS Code 拡張 [Nuxtr](https://marketplace.visualstudio.com/items?itemName=Nuxtr.nuxtr-vscode) 対応（`nuxtr.monorepoMode.DirectoryName: "frontend"`）

### バックエンド

- FastAPI。ルーターは `backend/app/routers/`（`auth` / `boards` / `media` / `bookmarks` / `pixiv` / `instagram`）
- JWT（HS256）で認証。パスワードは `backend/app/core/security.py` で bcrypt によりハッシュ化
  （passlib を介さず bcrypt を直接使い、`sha256` → base64 の前処理で 72 バイト制限を回避）
- 画像はアップロードごとに最適化して `backend/uploads/` へ保存し、バックエンド経由で配信
- pixiv / Instagram のトークンは暗号化して DB に保存（暗号化キーはサーバー側のみ）

### AI 解析パイプライン

- `LLM_PROVIDER` で `ollama` / `gemini` / `heuristic` を指定。空欄なら自動選択
- 解析結果はアイテムに JSON で保存され、タグ・パレット・分類へ展開
- 取得失敗時はデモデータへフォールバック（UI が止まらないことを優先）
- pixiv 経由の画像は取り込み元の権利設定に応じて解析ポリシーを切り替える（`pixiv_ai_policy`）

### 認証・アカウント

| エンドポイント | 内容 |
| --- | --- |
| `POST /api/v1/auth/register` | アカウント作成（重複メールは 409）。空のボードを1つ自動生成 |
| `POST /api/v1/auth/login` | トークン発行（認証失敗は 401） |
| `POST /api/v1/auth/guest` | ゲストとして使う（トークン発行のみ） |
| `GET /api/v1/auth/me` | ログインユーザーの情報を返す |
| `POST /api/v1/auth/pixiv/start` | pixiv ログイン（PKCE）の開始 |
| `POST /api/v1/auth/pixiv/complete` | 認可コードの交換と（または）pixiv 連携 |

未ログインでも共通のゲスト領域でそのまま使え、ログインすると自分の領域へ切り替わります。

### pixiv 非公式 App API

- pixiv の非公開モバイル App API を使う非公式機能です。pixiv Developers のアプリ登録方式ではありません
- 認証は **Pixiv のログイン画面だけで完結する PKCE（Web ログイン）** を既定とし、取得済み Refresh Token の手入力はローカル環境専用
- コールバック先が pixiv 側のドメインに固定されているため、認可コードは開発者ツールのネットワークログから取得して貼り付ける手順になります（[PIXIV_SETUP.md](PIXIV_SETUP.md)）
- 公開環境で pixiv を動かすための要件は [PIXIV_PUBLIC.md](PIXIV_PUBLIC.md)
- 未設定時はデモフィードに切り替わります

### 配信（Cloudflare Tunnel）

- `cloudflare/reflens.yml.example` を元にトンネル設定を用意し、`/RefLens.io/` のサブパスで公開
- バックエンドは `ROOT_PATH` を読み、付いたプレフィックスを剥がしてからルーティング
- フロントは `appBase` / `apiBase` / `mediaBase` がサブパス前提で組み立てられる

---

## ライセンス・注意事項

- pixiv / Instagram の連携は各サービスの仕様変更により利用できなくなる場合があります
- 取り込んだ画像は作者の権利と各サービスの利用条件に従って扱ってください
- 本リポジトリは開発成果物の紹介を目的としています
