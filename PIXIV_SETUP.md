# pixivをRefLensで使う（非公式・ローカル利用）

RefLensの `/view` はpixivの**非公開モバイルApp API**を利用します。Pixiv公式の開発者向けAPIやPixiv公認アプリではありません。Pixiv側の仕様変更で予告なく動作しなくなる可能性があります。

この実装はPixivのブラウザログイン（PKCE）または取得済みの **Refresh Token** を使います。PixivのパスワードをRefLensへ入力する機能はありません。Refresh Tokenや認可コードは重要な認証情報です。他人、公開チャット、Issue、スクリーンショット、`.env` のコミットに渡さないでください。

## 事前に用意するもの

- 自分のPixivアカウント（Refresh Token方式を使う場合のみ、その有効なRefresh Token）
- App API用のClient IDとClient Secret
- ローカルで動くRefLensのバックエンドとフロントエンド

Client IDとClient Secretは、従来のREADMEにあった「pixiv Developersにアプリ登録して発行する」手順では取得できません。非公式App APIクライアントの認証方式に対応する値が必要です。公開されている [Pixiv OAuth Flowの実装例](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362) の `pixiv_auth.py` にある `CLIENT_ID` / `CLIENT_SECRET` は参照例です。使用前にPixivの利用条件と値の有効性を確認してください。認証画面のドメインが `.pixiv.net` であることを確認し、パスワードをRefLensや第三者のページに入力しないでください。

Palleriaなど別クライアントに入力したRefresh Tokenがある場合も、値をRefLensに渡す前にそのクライアントの保存・エクスポート方法を確認してください。RefLensには他アプリからトークンを取り出す機能はありません。

## 1. サーバー設定

`backend/.env.example` を `backend/.env` にコピーして、以下を設定します。

```bash
cp backend/.env.example backend/.env
```

```env
PIXIV_CLIENT_ID=App_API用のClient_ID
PIXIV_CLIENT_SECRET=App_API用のClient_Secret
PIXIV_TOKEN_ENCRYPTION_KEY=生成したFernetキー
```

暗号化キーの生成例（プロジェクトのルートで実行）:

```bash
backend/venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

出力を `PIXIV_TOKEN_ENCRYPTION_KEY` に貼り付けます。このキーはDBに保存したトークンの復号に必要です。キーをなくしたり変更したりした場合はPixivを再接続してください。`.env` とDBのバックアップを安全に管理してください。

バックエンドを再起動します。`./start.sh start` を使う場合、既に起動中なら一度 `./start.sh stop` してから起動します。

公開プレビュー（`./start.sh public` / `deploy`）も動かしている場合は、公開側を停止せずに次のローカル専用環境を起動できます。現在の構成ではこちらを使ってください。

```bash
./start.sh pixiv-local
```

ローカル専用画面は `http://127.0.0.1:3002/view` です。APIは8081番を使い、DBは `backend/reflens-pixiv-local.db`、取り込み画像は `backend/pixiv-local-uploads` に保存します。公開プレビュー側のDBや画像保存先とは分離されます。停止するときは `./start.sh pixiv-local-stop` です。

フロントエンドを既定以外のホストやポートから開く場合は、`backend/app/core/config.py` の `CORS_ORIGINS` にそのオリジンを追加してください。

## 2. Pixivでログイン（推奨）

現在の設定はPixivモバイルApp APIのクライアントを利用しています。このクライアントのコールバック先はPixiv側のURLに固定され、RefLensのWebページへ直接戻すことはできません。RefLensだけで完結する通常の「Pixivでログイン」ボタンではなく、下記のURL手動入力を含む方式です。RefLensに自動で戻る方式を作るには、RefLens用に登録されたOAuthクライアントと許可済みのリダイレクトURIが別途必要です。PixivのパスワードやCookieをRefLensが代理取得する方式にはしません。

ローカル専用画面 `http://127.0.0.1:3002/view` で「Pixivに接続」→「Pixivでログイン」を押します。Pixiv側のログイン画面が別タブで開きます。ログイン後の `app-api.pixiv.net/.../callback?code=...` のURLをコピーしてRefLensに貼り、「RefLensに接続」を押してください。認可コードは短時間で失効し、一度しか使えません。失敗時は「最初からやり直す」で再取得します。

RefLensへ未ログインなら、Pixiv IDに紐づく専用のRefLensアカウントを作成・ログインします。既存RefLensアカウントへログイン中なら、そのアカウントにPixivを連携します。RefLensの通常ログイン画面にも「Pixiv」タブがあります。同じPixivアカウントを別のRefLensアカウントに重複連携することはできません。

非公式App APIではコールバック先がPixivドメインに固定されており、RefLensへ自動で戻る公式OAuth連携ではありません。そのため、ログイン後のURLを一度だけ手動で渡す必要があります。URLや認可コードはブラウザのアドレスバー以外に共有しないでください。Pixivの仕様変更でこの手順が使えなくなる可能性があります。

## 3. Refresh Tokenを使う場合（代替）

このリポジトリには認証補助スクリプト [pixiv_auth.py](pixiv_auth.py) が入っています。上のClient ID/Secretを `backend/.env` に設定してから、**プロジェクトのルート**で次を実行します。

```bash
# リポジトリのルートで実行
python3 pixiv_auth.py login
```

`backend/.env` がない、またはClient ID/Secretが空なら、スクリプトがその旨を表示して終了します。`python3 pixiv_auth.py --help` なら設定なしで実行できます。

スクリプトがPixivのログインURLをブラウザで開きます。ブラウザの開発者ツールで **Network → Preserve log** を有効にし、`callback?` を検索してからログインしてください。`https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback?...` のリクエストURL（またはその `code` パラメータ）を端末の入力欄へ貼り付けます。認可コードは短時間で失効するため、失敗したらコマンドからやり直してください。スクリプトはRefresh Tokenを端末に表示しますが、ファイルには保存しません。

前回案内した外部の実装例にある `python pixiv_auth.py login` を実行しても、そのファイルをダウンロードしていなければ今回のように `can't open file` になります。このリポジトリでは上記のコマンドを使用してください。

## 4. RefLensに接続

1. `./start.sh pixiv-local` を使った場合は `http://127.0.0.1:3002/view` を開きます。通常の `./start.sh start` なら `http://localhost:3000/view` です。
2. 「Pixivに接続」→「Refresh Tokenを使う」を押します。
3. 手順3で表示されたRefresh Tokenを入力して「接続」を押します。
4. アカウント名と実際の作品一覧が表示されれば完了です。

Refresh Token方式は先にRefLensアカウントへログインしている場合だけ利用できます。共通ゲストへのPixivトークン保存は許可しません。PixivアカウントでRefLensに入りたい場合は手順2の「Pixivでログイン」を使ってください。

入力したトークンはブラウザのlocalStorageに保存しません。バックエンドがPixivに交換を依頼し、Access TokenとRefresh Tokenを暗号化してDBに保存します。画面上の接続解除では保存したPixivアカウント行を削除します。Pixiv側でのトークン失効操作は行いません。

`pixiv-local` の接続状態の確認先は `http://127.0.0.1:8081/api/v1/pixiv/status` です。通常の `start` なら8080番です。`configured: true` はサーバーの3つの設定が揃っていること、`connected: true` はこのRefLensユーザーにPixivの接続情報があることを示します。実際にAPIが使えるかは `/view` のフィード取得で確認してください。

## 利用できる機能

| 画面 | 内容 |
| --- | --- |
| おすすめ・人気 | Pixivのおすすめ作品とデイリーランキング |
| 検索 | タグ・キーワード検索、並び順と期間の指定 |
| フォロー・ブックマーク | 接続アカウントの作品一覧 |
| 作品詳細 | 複数ページ作品の表示 |
| ライブラリ・キャンバス | 選んだ作品画像をバックエンド経由で保存・配置 |

Pixiv画像には`Referer`が必要なため、画像の取得と取り込みはバックエンド経由です。通常起動の閲覧用キャッシュは `backend/.pixiv-cache`、取り込み画像は `backend/uploads` に保存されます。`pixiv-local` ではそれぞれ `backend/.pixiv-local-cache` と `backend/pixiv-local-uploads` です。ディスク容量を確認し、作者の権利とPixivの利用条件を守って利用してください。

## AI解析と作者の「AI学習禁止」表示

RefLensは取り込んだ画像でモデルを追加学習・ファインチューニングしません。AI機能は既存モデルによる画像の解析ですが、作者の意思を尊重するため、Pixiv作品のタイトル・タグ・説明文に「AI学習禁止」「Do not train」等の明示があれば、解析画像をOllamaやGeminiへ送らず、ローカルの画像解析も実行しません。

Pixivの「AI生成作品」設定は、AI学習の許諾を示すものではありません。明示的な禁止表示がない作品でも、Danbooruで同じPixiv作品ID（`pixiv_id`）の掲載が確認できた場合だけAI解析・解析結果の表示を許可します。Pixivで禁止されていればDanbooruに掲載されていても解析しません。Danbooruにない場合や照合に失敗した場合も解析しません。作品画像そのものの表示はこの判定で制限しません。

既存のPixivブックマークは、CanvasのAIパネルから作品情報と掲載を再確認できます。Danbooru掲載は作者の許諾を証明するものではなく、この照合はユーザー指定の表示条件です。また、テキスト上の禁止表示を検出する安全策であり、画像内の透かしや外部サイトの利用条件を完全には判定できません。

## 公開プレビューと安全性

現在のRefLensは未ログイン時に共通ゲストユーザーを使います。この状態でPixivトークンを公開サーバーに接続すると、他の訪問者が同じPixivアカウントのデータを読めてしまうため、**共通ゲストには pixiv セッションを渡さない**ようにしています（`_get_account()` がゲストに対して `None` を返す）。ログイン済みユーザーは自分の `pixiv_accounts` 行だけを見るので、他人のデータには到達できません。

このため公開プレビューでも **「Pixivでログイン」（Webログイン / PKCE）は使えます**。Refresh Token を手で貼る接続だけは公開では 403 で、ローカル専用です。ただしローカルで既にライブラリへ取り込んだ画像は共有ライブラリと `/uploads` に残るため、同じDB・保存先を公開プレビューと共用しないでください。また詳細・更新系APIの所有チェックは未実装（`PIXIV_PUBLIC.md` 2.2）なので、全ユーザーへ公開する前に対応してください。

公開サイトでpixiv連携を実際に有効化するための要件（アクセス制御・未ログイン遮断・秘密情報の管理・検証手順）は [PIXIV_PUBLIC.md](PIXIV_PUBLIC.md) にまとめています。

メール / パスワード認証だけは公開サイトでも使えるよう、`./start.sh public` / `deploy` の起動時に `backend/scripts/sync_public_accounts.py` がローカルDBのアカウント（とボード・画像）を公開側の `reflens-public.db` へ同期します。`pixiv_accounts` / `instagram_accounts` は同期対象外で、トークンは公開側DBにコピーされません。

サーバーの`.env`、DB、ログを第三者に公開しないでください。既存の古い平文トークンは、次回の有効期限更新時に暗号化して保存されます。既存DBを外部へ出す前には平文行が残っていないか確認してください。

## うまくいかない場合

- 「サーバー設定が未完了」: `backend/.env` の3項目とバックエンド再起動を確認します。
- HTTP 400で接続失敗: Refresh Tokenが有効か、Client ID/Secretが同じApp APIの認証方式に対応しているかを確認します。非公開APIの仕様変更でも失敗します。
- HTTP 401または期限切れ: 接続を解除し、有効なRefresh Tokenで再接続します。
- 公開プレビューで接続ボタンが出ない場合: サーバー設定（`backend/.env` の3項目）を確認してください。設定済みなら接続ボタンは表示されます（公開では「Pixivでログイン」のみ、Refresh Token 入力はローカル専用です）。
- 画像が表示されない: Pixiv側の閲覧権限、画像URL、バックエンドのログを確認します。取得できない画像は保存されません。

この機能は[Palleria](https://github.com/yunfie-twitter/Palleria)とは独立しており、Palleriaのコードを取り込んでいません。
