#!/usr/bin/env python3
"""RefLens.io の favicon.svg / favicon-card.png (512x512) / favicon.ico を生成するスクリプト。

Tunedropの方式を踏襲:
1. favicon.svg: ブラウザタブ用の軽量ベクター (Lucide Compass と同一意匠のインディゴ背景)
2. favicon-card.png: 512x512 のラスタPNG (Apple Touch Icon / SNS OGP / Google 検索用)
3. favicon.ico: レガシーブラウザ向けマルチサイズアイコン (16x16, 32x32, 48x48)
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / 'public'
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

SVG_PATH = PUBLIC_DIR / 'favicon.svg'
PNG_PATH = PUBLIC_DIR / 'favicon-card.png'
ICO_PATH = PUBLIC_DIR / 'favicon.ico'

# 1. favicon.svg を生成
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#4f46e5"/>
      <stop offset="100%" stop-color="#3730a3"/>
    </linearGradient>
  </defs>
  <!-- 背景角丸 -->
  <rect x="2" y="2" width="60" height="60" rx="14" fill="url(#bg)"/>
  
  <!-- コンパス外周リング -->
  <circle cx="32" cy="32" r="19" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  
  <!-- コンパス針（Lucide Compass準拠） -->
  <polygon points="41.33,22.67 36.66,36.66 22.67,41.33 27.34,27.34" fill="#ffffff" fill-opacity="0.25" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  
  <!-- 北針ハイライト（塗り） -->
  <polygon points="41.33,22.67 36.66,36.66 32,32 27.34,27.34" fill="#ffffff"/>
  
  <!-- センターピボット -->
  <circle cx="32" cy="32" r="2.2" fill="#ffffff"/>
</svg>
"""
SVG_PATH.write_text(svg_content.strip() + '\n', encoding='utf-8')
print(f'生成: {SVG_PATH}')

# 2. favicon-card.png (512x512) を高精細レンダリング (超解像 4x SSAA)
TARGET_SIZE = 512
SSAA = 4
SIZE = TARGET_SIZE * SSAA  # 2048x2048

# 透過背景ではなく、SNSで正しく表示されるよう濃い背景またはブランドカラーのカード
# Tunedrop同様、アイコン意匠を中央に大きく配置した正方形カード
img = Image.new('RGBA', (SIZE, SIZE), (15, 17, 22, 255)) # #0f1116
draw = ImageDraw.Draw(img)

# メインアイコンの角丸四角
PADDING = int(32 * SSAA)
RECT = [PADDING, PADDING, SIZE - PADDING, SIZE - PADDING]
RADIUS = int(108 * SSAA)

# グラデーション塗り（#4f46e5 -> #3730a3）
c1 = (79, 70, 229)
c2 = (55, 48, 163)
for y in range(PADDING, SIZE - PADDING):
    ratio = (y - PADDING) / (SIZE - 2 * PADDING)
    r = int(c1[0] + (c2[0] - c1[0]) * ratio)
    g = int(c1[1] + (c2[1] - c1[1]) * ratio)
    b = int(c1[2] + (c2[2] - c1[2]) * ratio)
    # 角丸マスク用ではなく行単位で引く
# 綺麗に描くためマスクを使って角丸矩形をグラデーション合成
mask = Image.new('L', (SIZE, SIZE), 0)
mask_draw = ImageDraw.Draw(mask)
mask_draw.rounded_rectangle(RECT, radius=RADIUS, fill=255)

grad = Image.new('RGB', (SIZE, SIZE), c1)
grad_draw = ImageDraw.Draw(grad)
for y in range(SIZE):
    ratio = y / SIZE
    r = int(c1[0] + (c2[0] - c1[0]) * ratio)
    g = int(c1[1] + (c2[1] - c1[1]) * ratio)
    b = int(c1[2] + (c2[2] - c1[2]) * ratio)
    grad_draw.line([(0, y), (SIZE, y)], fill=(r, g, b))

# カード背景にグラデーション角丸を貼り付け
img.paste(grad, (0, 0), mask)
draw = ImageDraw.Draw(img)

# コンパスの描画
CX, CY = SIZE // 2, SIZE // 2
RING_RADIUS = int(152 * SSAA)
RING_WIDTH = int(24 * SSAA)

# 外周リング
draw.ellipse(
    [CX - RING_RADIUS, CY - RING_RADIUS, CX + RING_RADIUS, CY + RING_RADIUS],
    outline=(255, 255, 255, 255),
    width=RING_WIDTH,
)

# 針の座標計算
# Tip 1 (NE), Tip 2 (SW), Corner 1 (SE), Corner 2 (NW)
TIP_LEN = int(196 * SSAA)
CORNER_LEN = int(68 * SSAA)

def pt(length, angle_deg):
    rad = math.radians(angle_deg)
    return (CX + length * math.cos(rad), CY - length * math.sin(rad))

P_NE = pt(TIP_LEN, 45)
P_SW = pt(TIP_LEN, 225)
P_SE = pt(CORNER_LEN, -45)
P_NW = pt(CORNER_LEN, 135)
P_CTR = (CX, CY)

# 針全体（半透明ホワイト）
needle_layer = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
needle_draw = ImageDraw.Draw(needle_layer)
needle_draw.polygon([P_NE, P_SE, P_SW, P_NW], fill=(255, 255, 255, 80))
img.alpha_composite(needle_layer)
draw = ImageDraw.Draw(img)

# 針の枠線
NEEDLE_LINE = int(18 * SSAA)
draw.polygon([P_NE, P_SE, P_SW, P_NW], outline=(255, 255, 255, 255), width=NEEDLE_LINE)

# 北針（NE側）を白で塗りつぶし
draw.polygon([P_NE, P_SE, P_CTR, P_NW], fill=(255, 255, 255, 255))

# センターピボット
PIVOT_R = int(20 * SSAA)
draw.ellipse([CX - PIVOT_R, CY - PIVOT_R, CX + PIVOT_R, CY + PIVOT_R], fill=(255, 255, 255, 255))

# 512x512 へ高品質リサイズ
final_img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
final_img.convert('RGB').save(PNG_PATH, format='PNG', optimize=True)
print(f'生成: {PNG_PATH} ({TARGET_SIZE}x{TARGET_SIZE}, {PNG_PATH.stat().st_size // 1024}KB)')

# 3. favicon.ico を生成 (16, 32, 48)
ico_sizes = [(16, 16), (32, 32), (48, 48)]
final_img.save(ICO_PATH, format='ICO', sizes=ico_sizes)
print(f'生成: {ICO_PATH}')

