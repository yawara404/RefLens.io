#!/bin/bash
# ---------------------------------------------------------------------------
# start.sh — RefLens.io のローカル／公開Preview 起動ヘルパー
#
#   使い方:
#     ./start.sh start            バックエンド(8080) + フロントエンド(3000)を起動
#     ./start.sh public           トンネル用の開発サーバー（ローカル確認用）
#     ./start.sh deploy           本番ビルド → トンネル経由の公開（推奨）
#     ./start.sh tunnel           Cloudflare トンネルだけを起動（art.wawa-app.me）
#     ./start.sh status           稼働状況を表示
#     ./start.sh stop             起動したプロセスを停止
#     ./start.sh pixiv-local      公開プレビューとは別のローカル専用環境を起動
#     ./start.sh pixiv-local-stop ローカル専用環境だけを停止
#
#   公開URL:
#     https://art.wawa-app.me/RefLens.io/
#
#   public と deploy の違い:
#     Vite dev server を Cloudflare Tunnel 経由で公開すると、同じアセットURLが
#     <link rel=stylesheet> と module script の両方で要求され、Cloudflare の
#     エッジキャッシュが Content-Type を使い回すため、
#     「Expected a JavaScript module but got text/css」で起動しなくなる。
#     「Expected a JavaScript module but got text/css」で起動しなくなる。
#     deploy は本番ビルド（ハッシュ付きアセットの静的配信）を使うためこの問題が起きない。
#
#   前提:
#     ・cloudflared が必要です（brew install cloudflared）
#     ・バックエンドは backend/venv の Python を使います
#
#   他のプロジェクト（midair / quadtecho / tunedrop / vocaloid.hz）のトンネルとは
#   独立した設定 ~/.cloudflared/reflens.yml を使います。
# ---------------------------------------------------------------------------
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$DIR"

BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PUBLIC_FRONTEND_PORT="${PUBLIC_FRONTEND_PORT:-3121}"
PUBLIC_HOST="${PUBLIC_HOST:-art.wawa-app.me}"
PUBLIC_BASE_PATH="${PUBLIC_BASE_PATH:-/RefLens.io}"
TUNNEL_NAME="${TUNNEL_NAME:-reflens}"
TUNNEL_CONFIG="${TUNNEL_CONFIG:-$DIR/cloudflare/reflens.yml}"
PUBLIC_URL="https://${PUBLIC_HOST}${PUBLIC_BASE_PATH}/"

LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"

BACKEND_PID="$LOG_DIR/backend.pid"
FRONTEND_PID="$LOG_DIR/frontend.pid"
TUNNEL_PID="$LOG_DIR/tunnel.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
TUNNEL_LOG="$LOG_DIR/tunnel.log"

# 公開プレビューと認証済みPixivデータを共有しないローカル環境。
if [ "${1:-}" = "pixiv-local" ] || [ "${1:-}" = "pixiv-local-stop" ] || [ "${1:-}" = "pixiv-local-status" ]; then
  BACKEND_PORT=8081
  FRONTEND_PORT=3002
  BACKEND_PID="$LOG_DIR/pixiv-local-backend.pid"
  FRONTEND_PID="$LOG_DIR/pixiv-local-frontend.pid"
  BACKEND_LOG="$LOG_DIR/pixiv-local-backend.log"
  FRONTEND_LOG="$LOG_DIR/pixiv-local-frontend.log"
  export DATABASE_URL="sqlite:///$DIR/backend/reflens-pixiv-local.db"
  export UPLOAD_DIR="$DIR/backend/pixiv-local-uploads"
  export PIXIV_CACHE_DIR="$DIR/backend/.pixiv-local-cache"
fi

# 公開プレビューはローカルのPixiv接続や既存の8080/3000と分離する。
if [ "${1:-}" = "public" ] || [ "${1:-}" = "deploy" ] || [ "${1:-}" = "public-status" ] || [ "${1:-}" = "public-stop" ]; then
  BACKEND_PORT=8082
  FRONTEND_PORT="$PUBLIC_FRONTEND_PORT"
  BACKEND_PID="$LOG_DIR/public-backend.pid"
  FRONTEND_PID="$LOG_DIR/public-frontend.pid"
  BACKEND_LOG="$LOG_DIR/public-backend.log"
  FRONTEND_LOG="$LOG_DIR/public-frontend.log"
  export DATABASE_URL="sqlite:///$DIR/backend/reflens-public.db"
  export UPLOAD_DIR="$DIR/backend/public-uploads"
  export PIXIV_CACHE_DIR="$DIR/backend/.pixiv-public-cache"
fi

PYTHON="$DIR/backend/venv/bin/python"

# ---------------------------------------------------------------- 補助関数 --
pid_of() {
  # $1 = pidファイル。稼働中なら PID を標準出力（無ければ戻り値1）
  [ -f "$1" ] || return 1
  local pid
  pid="$(cat "$1" 2>/dev/null)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && { echo "$pid"; return 0; }
  return 1
}

port_up() {
  # $1 = ポート番号
  curl -s -m 2 -o /dev/null "http://127.0.0.1:$1/" 2>/dev/null
}

# ------------------------------------------------------------ backend 起動 --
# $1 = ROOT_PATH（サブパス配信用。ローカル起動では空）
start_backend() {
  if pid_of "$BACKEND_PID" >/dev/null; then
    echo "バックエンドは起動済み (PID $(cat "$BACKEND_PID")) → http://127.0.0.1:${BACKEND_PORT}"
    return 0
  fi
  if port_up "$BACKEND_PORT"; then
    echo "バックエンドは起動済み（PID 管理外）→ http://127.0.0.1:${BACKEND_PORT}"
    return 0
  fi
  if [ ! -x "$PYTHON" ]; then
    echo "エラー: $PYTHON が見つかりません。次を実行してください:" >&2
    echo "  cd backend && python3 -m venv venv && venv/bin/pip install -r requirements.txt" >&2
    return 1
  fi

  local root_path="${1:-}"
  if [ -n "$root_path" ]; then
    echo "バックエンドを起動しています (port ${BACKEND_PORT}, root-path ${root_path})..."
  else
    echo "バックエンドを起動しています (port ${BACKEND_PORT})..."
  fi
  (
    cd "$DIR/backend"
    # ROOT_PATH を読むのは .env ではなく環境変数（サブパス公開時のみ設定する）
    ROOT_PATH="$root_path" \
      nohup "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
      >> "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID"
  )

  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s -m 2 "http://127.0.0.1:${BACKEND_PORT}/" >/dev/null 2>&1; then
      echo "  → 起動しました（ログ: ${BACKEND_LOG#"$DIR"/}）"
      return 0
    fi
    sleep 1
  done
  echo "  → 起動に失敗した可能性があります。${BACKEND_LOG#"$DIR"/} を確認してください" >&2
  return 1
}

# ---------------------------------------------------------- frontend 起動 --
# モード: default（ローカル / ベースパスなし） / public（/RefLens.io/）
start_frontend() {
  local mode="${1:-default}"

  if pid_of "$FRONTEND_PID" >/dev/null; then
    echo "フロントエンドは起動済み (PID $(cat "$FRONTEND_PID"))"
    return 0
  fi

  local port="$FRONTEND_PORT"
  local base=""
  local hosts=""
  # 公開モードでは API も Same-Origin の相対パスで叩く（トンネルの ingress が
  # /RefLens.io/api/* を backend へ、/RefLens.io/* を frontend へ振り分けるため）
  local api_base="http://127.0.0.1:${BACKEND_PORT}/api/v1"
  local media_base="http://127.0.0.1:${BACKEND_PORT}"

  if [ "$mode" = "public" ] || [ "$mode" = "deploy" ]; then
    port="$PUBLIC_FRONTEND_PORT"
    # 末尾スラッシュを補う（Nuxt の baseURL と揃える）
    case "$PUBLIC_BASE_PATH" in
      */) base="$PUBLIC_BASE_PATH" ;;
      *)  base="${PUBLIC_BASE_PATH}/" ;;
    esac
    hosts="$PUBLIC_HOST,localhost,127.0.0.1"
    # ベースパスは app.baseURL（runtimeConfig.public.appBase）側の責務なので、
    # ここでは素のパスだけを渡す。appBase を含む値を渡すと実行時に
    # /RefLens.io/RefLens.io/... と二重化される。
    api_base="/api/v1"
    media_base="/"
  fi

  if curl -fsS -m 2 -o /dev/null "http://127.0.0.1:${port}${base}" 2>/dev/null; then
    echo "フロントエンドは起動済み（PID 管理外）→ http://127.0.0.1:${port}${base}"
    return 0
  fi

  if [ "$mode" = "deploy" ]; then
    # ---------------------------------------------------------------
    # 公開は本番ビルドを配信する（Vite dev server は使わない）
    #
    # Vite dev server を Cloudflare Tunnel 経由Florenceで開くと、
    # 同じアセットURLが <link rel=stylesheet>（text/css）と
    # module script（text/javascript）の両方で要求される。Cloudflare の
    # エッジキャッシュが先勝ちした側の Content-Type を使い回すため、
    # 「Expected a JavaScript module but got text/css」で起動しなくなる。
    # 本番ビルドはハッシュ付きアセットを静的に配信するため競合しない。
    # ---------------------------------------------------------------
    echo "フロントエンドをビルドしています（公開モード: base ${base}）..."
    if ! (
      cd "$DIR/frontend"
      NUXT_APP_BASE_URL="$base" \
      NUXT_PUBLIC_API_BASE="$api_base" \
      NUXT_PUBLIC_MEDIA_BASE="$media_base" \
      NUXT_DEV_ALLOWED_HOSTS="$hosts" \
        npm run build > "$FRONTEND_LOG" 2>&1
    ); then
      echo "  → ビルドに失敗しました。logs/public-frontend.log を確認してください" >&2
      return 1
    fi
    if [ ! -f "$DIR/frontend/.output/server/index.mjs" ]; then
      echo "  → ビルドに失敗しました。logs/frontend.log を確認してください" >&2
      return 1
    fi
    echo "  → ビルド完了"

    (
      cd "$DIR/frontend"
      # 本番サーバーは .env を読まないので、必要な変数をすべて渡す
      NUXT_APP_BASE_URL="$base" \
      NUXT_PUBLIC_API_BASE="$api_base" \
      NUXT_PUBLIC_MEDIA_BASE="$media_base" \
      NITRO_HOST="127.0.0.1" \
      NITRO_PORT="$port" \
        nohup node .output/server/index.mjs >> "$FRONTEND_LOG" 2>&1 &
      echo $! > "$FRONTEND_PID"
    )

    for _ in $(seq 1 30); do
      if curl -s -m 3 -o /dev/null "http://127.0.0.1:${port}${base}" 2>/dev/null; then
        echo "  → 起動しました（ログ: logs/frontend.log）"
        return 0
      fi
      sleep 1
    done
    echo "  → 起動に失敗した可能性があります。logs/frontend.log を確認してください" >&2
    return 1
  fi

  if [ "$mode" = "public" ]; then
    echo "フロントエンドを起動しています（開発モード: port ${port}, base ${base}）..."
  else
    echo "フロントエンドを起動しています (port ${port})..."
  fi

  (
    cd "$DIR/frontend"
    # 環境変数は子プロセスへ明示的に渡す
    NUXT_APP_BASE_URL="$base" \
    NUXT_DEV_ALLOWED_HOSTS="$hosts" \
    PORT="$port" \
    NUXT_PUBLIC_API_BASE="$api_base" \
    NUXT_PUBLIC_MEDIA_BASE="$media_base" \
      nohup npm run dev -- --port "$port" >> "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID"
  )

  for _ in $(seq 1 40); do
    if curl -s -m 3 -o /dev/null "http://127.0.0.1:${port}${base}" 2>/dev/null; then
      echo "  → 起動しました（ログ: logs/frontend.log）"
      return 0
    fi
    sleep 1
  done
  echo "  → 起動に失敗した可能性があります。logs/frontend.log を確認してください" >&2
  return 1
}

# ---------------------------------------------- 公開DBアカウント同期 --
# 公開プレビューは reflens-public.db を使うため、ローカルで作ったアカウントは
# そのままでは公開サイトで 401 になる。バックエンド起動直後にローカルDBから
# 同期しておく（冪等・削除はしない。失敗しても起動は続行する）。
sync_public_accounts() {
  local script="$DIR/backend/scripts/sync_public_accounts.py"
  if [ ! -x "$PYTHON" ] || [ ! -f "$script" ] || [ ! -f "$DIR/backend/reflens.db" ]; then
    return 0
  fi
  local out
  if out="$("$PYTHON" "$script" --quiet 2>&1)"; then
    [ -n "$out" ] && echo "$out"
    return 0
  fi
  echo "  → アカウントの公開DB同期に失敗しました（公開側のDBにのみログインできます）" >&2
  [ -n "$out" ] && echo "$out" >&2
  return 0
}

# ---------------------------------------------------------- tunnel 起動 --
start_tunnel() {
  if pid_of "$TUNNEL_PID" >/dev/null; then
    echo "トンネルは起動済み (PID $(cat "$TUNNEL_PID")) → $PUBLIC_URL"
    return 0
  fi
  if curl -fsS -m 5 -o /dev/null "$PUBLIC_URL" 2>/dev/null; then
    echo "トンネルは接続済み（PID 管理外）→ $PUBLIC_URL"
    return 0
  fi
  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "エラー: cloudflared が見つかりません（brew install cloudflared）" >&2
    return 1
  fi
  if [ ! -f "$TUNNEL_CONFIG" ]; then
    echo "エラー: トンネル設定が見つかりません: $TUNNEL_CONFIG" >&2
    return 1
  fi

  nohup cloudflared tunnel --config "$TUNNEL_CONFIG" run "$TUNNEL_NAME" >> "$TUNNEL_LOG" 2>&1 &
  echo $! > "$TUNNEL_PID"
  sleep 4
  if pid_of "$TUNNEL_PID" >/dev/null; then
    echo "トンネル起動しました → $PUBLIC_URL"
  else
    echo "トンネルの起動に失敗しました。logs/tunnel.log を確認してください" >&2
    return 1
  fi
}

# ------------------------------------------------------------------ stop --
stop_one() {
  local label="$1" pidfile="$2"
  if pid="$(pid_of "$pidfile")"; then
    # 子プロセス（npm→node など）もまとめて止める
    pkill -P "$pid" 2>/dev/null
    kill "$pid" 2>/dev/null
    sleep 1
    kill -9 "$pid" 2>/dev/null
    echo "  $label を停止しました (PID $pid)"
  fi
  rm -f "$pidfile"
}

# ---------------------------------------------------------------- status --
show_status() {
  echo "=== RefLens.io ==="
  if pid="$(pid_of "$BACKEND_PID")"; then
    echo "  backend    : 稼働中 (PID $pid, http://127.0.0.1:${BACKEND_PORT})"
  elif port_up "$BACKEND_PORT"; then
    echo "  backend    : 稼働中 (PID 管理外, http://127.0.0.1:${BACKEND_PORT})"
  else
    echo "  backend    : 停止中"
  fi
  if pid="$(pid_of "$FRONTEND_PID")"; then
    echo "  frontend   : 稼働中 (PID $pid)"
  elif port_up "$FRONTEND_PORT"; then
    echo "  frontend   : 稼働中 (PID 管理外, http://127.0.0.1:${FRONTEND_PORT})"
  elif [ "${1:-}" = "public" ] && port_up "$PUBLIC_FRONTEND_PORT"; then
    echo "  frontend   : 稼働中 (PID 管理外, http://127.0.0.1:${PUBLIC_FRONTEND_PORT})"
  else
    echo "  frontend   : 停止中"
  fi
  if pid="$(pid_of "$TUNNEL_PID")"; then
    echo "  tunnel     : 稼働中 (PID $pid) → $PUBLIC_URL"
  elif curl -fsS -m 5 -o /dev/null "$PUBLIC_URL" 2>/dev/null; then
    echo "  tunnel     : 稼働中 (公開URL応答) → $PUBLIC_URL"
  else
    echo "  tunnel     : 停止中"
  fi
}

# ------------------------------------------------------------------- 引数 --
case "${1:-start}" in
  start)
    start_backend "" && start_frontend default
    echo
    echo "ローカル: http://127.0.0.1:${FRONTEND_PORT}/"
    ;;
  pixiv-local)
    start_backend "" && start_frontend default
    echo
    echo "Pixivローカル: http://127.0.0.1:${FRONTEND_PORT}/view"
    ;;
  pixiv-local-status)
    show_status
    ;;
  public-status)
    show_status
    ;;
  public-stop)
    stop_one "public backend" "$BACKEND_PID"
    stop_one "public frontend" "$FRONTEND_PID"
    stop_one "tunnel" "$TUNNEL_PID"
    ;;
  pixiv-local-stop)
    stop_one "pixiv-local backend" "$BACKEND_PID"
    stop_one "pixiv-local frontend" "$FRONTEND_PID"
    ;;
  public)
    # backend は /RefLens.io 接頭辞付きで受け、frontend は同じベースパスで配信する
    start_backend "$PUBLIC_BASE_PATH" && sync_public_accounts && start_frontend public && start_tunnel
    echo
    echo "ローカル: http://127.0.0.1:${PUBLIC_FRONTEND_PORT}${PUBLIC_BASE_PATH}/"
    echo "公開URL : $PUBLIC_URL"
    ;;
  deploy)
    # Cloudflare Tunnel 経由の公開は本番ビルドを配信する（Vite dev server は使わない）
    start_backend "$PUBLIC_BASE_PATH" && sync_public_accounts && start_frontend deploy && start_tunnel
    echo
    echo "ローカル: http://127.0.0.1:${PUBLIC_FRONTEND_PORT}${PUBLIC_BASE_PATH}/"
    echo "公開URL : $PUBLIC_URL"
    ;;
  backend)
    start_backend
    ;;
  frontend)
    start_frontend default
    ;;
  tunnel)
    start_tunnel
    ;;
  status)
    show_status
    ;;
  stop)
    echo "停止しています..."
    stop_one "backend" "$BACKEND_PID"
    stop_one "frontend" "$FRONTEND_PID"
    stop_one "tunnel" "$TUNNEL_PID"
    echo "完了しました。"
    ;;
  *)
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
