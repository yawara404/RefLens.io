#!/usr/bin/env bash
#
# SNS のカード画像 (OGP / Twitter Card) を再生成する。
#
#   tools/og-card.html  →  frontend/public/card-<version>.png  (1200x630)
#
# frontend/public/ の中身はビルド時に配信ディレクトリ直下へコピーされるので、
# 公開サイトでは https://art.wawa-app.me/RefLens.io/card-v2.png として参照される。
#
# ファイル名にバージョンを付けているのは、Cloudflare のエッジキャッシュと
# SNS 側のカードキャッシュが URL 単位で残るため。デザインを変えたら
# 下の CARD_FILE を card-v3.png などへ上げ、参照側（nuxt.config.ts /
# composables/useSeo.ts / sitemap.xml）も同じ名前に更新すること。
#
# 使い方:
#   tools/make-og-card.sh
#   CARD_FILE=card-v3.png tools/make-og-card.sh
#   CHROME=/path/to/chrome tools/make-og-card.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
CARD_FILE="${CARD_FILE:-card-v2.png}"
OUT="$ROOT/frontend/public/$CARD_FILE"

if [ ! -x "$CHROME" ]; then
  echo "Chrome が見つかりません: $CHROME" >&2
  echo "CHROME=/path/to/chrome tools/make-og-card.sh のように指定してください。" >&2
  exit 1
fi

echo "カード画像を生成しています..."

"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --hide-scrollbars \
  --force-device-scale-factor=1 \
  --window-size=1200,630 \
  --screenshot="$OUT" \
  "file://$ROOT/tools/og-card.html" 2>/dev/null

if [ ! -f "$OUT" ]; then
  echo "生成に失敗しました。" >&2
  exit 1
fi

SIZE=$(python3 - "$OUT" <<'PY'
import struct, sys
d = open(sys.argv[1], 'rb').read()
w, h = struct.unpack('>II', d[16:24])
print(f"{w}x{h} {len(d) / 1024:.1f}KB")
PY
)

echo "完了: frontend/public/$CARD_FILE ($SIZE)"
