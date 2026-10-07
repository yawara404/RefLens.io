"""
RefLens.io の AI 視覚解析プロバイダ。

優先順位:
    1. LLM_PROVIDER=ollama   → Ollama ローカルモデル
    2. LLM_PROVIDER=gemini   → Google Gemini API
    3. LLM_PROVIDER=heuristic→ 画像特徴量のヒューリスティックのみ（API 不要）
    未指定時は上記1 → 2 → 3の順に自動で尝试す。

画像解析のフォールバック
    テキストのみモデル（例: qwen3）は画像を読めないため、
    ローカルにある vision 対応モデルへ自動で切り替える。
    それが無い場合は heuristic（画像特徴量のヒューリスティック）へ落ちる。
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from PIL import Image, ImageStat

from app.core.config import settings
from app.services import ollama_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはプロのイラストレーター・コンセプトアーティストのための視覚解析アシスタントです。
提供された画像を分析し、以下のJSONフォーマットのみを返却してください。

{
  "composition": "アオリ / 俯瞰 / アイレベル / 三分割法 / 対角線構図 などの分類と特徴",
  "lighting": "逆光 / トップライト / サイド光 / リムライト / 自然光 などの光源方向とコントラスト特徴",
  "pose_anatomy": "ポーズの重心、S字カーブ、パースの効き具合",
  "costume_structure": "衣装の素材感（硬質/シフォン/レザー等）、シワの溜まりや引っ張りのポイント",
  "palette": ["#Hex1", "#Hex2", "#Hex3", "#Hex4", "#Hex5"],
  "tags": ["アオリ", "夜景", "サイバーパンク", "ビッグシルエット"]
}"""

REQUIRED_KEYS = (
    "composition",
    "lighting",
    "pose_anatomy",
    "costume_structure",
    "palette",
    "tags",
)


# =====================================================================
# 画像ユーティリティ
# =====================================================================
def extract_dominant_colors(image_path: Path, num_colors: int = 5) -> List[str]:
    """Pillowを使って画像から代表的な色パレットを抽出する"""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            # リサイズして計算高速化
            img = img.resize((150, 150))
            # 減色処理
            quantized = img.quantize(colors=num_colors, method=Image.Quantize.FASTOCTREE)
            palette = quantized.getpalette()[: num_colors * 3]
            hex_colors = []
            for i in range(0, len(palette), 3):
                r, g, b = palette[i], palette[i + 1], palette[i + 2]
                hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
            # 不足分を埋める
            while len(hex_colors) < num_colors:
                hex_colors.append("#333333")
            return hex_colors[:num_colors]
    except Exception as e:
        logger.error(f"Error extracting colors: {e}")
        return ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#f8f9fa"]


def smart_heuristic_fallback(image_path: Path) -> Dict[str, Any]:
    """LLM が使えない場合、画像特徴量に基づいてリアルな視覚解析データを生成"""
    palette = extract_dominant_colors(image_path, 5)

    try:
        with Image.open(image_path) as img:
            w, h = img.size
            ratio = w / h
            stat = ImageStat.Stat(img.convert("L"))
            brightness = stat.mean[0]  # 0 to 255
    except Exception:
        ratio = 1.0
        brightness = 128

    # 構図の推測
    if ratio > 1.3:
        comp = "シネマティックなワイド構図（対角線構図）。水平ラインが強調され、広がりと環境の空気感を持たせるレイアウト。"
        tags_comp = ["ワイド構図", "背景重視", "パノラマ感"]
    elif ratio < 0.75:
        comp = "垂直方向のダイナミックなアオリ〜アイレベル構図。被写体の立ち姿や縦のプロポーションが引き立ちます。"
        tags_comp = ["縦長構図", "全身立ち絵", "プロポーション重視"]
    else:
        comp = "三分割法を意識した安定感のある構図。視線誘導の中心に主要モチーフが配置されています。"
        tags_comp = ["三分割法", "安定構図", "アイレベル"]

    # ライティングの推測
    if brightness < 85:
        light = "低照度のドラマティックな逆光・サイド光。エッジに強いハイライト（リムライト）が入り、深い影とのコントラストが強調されています。"
        tags_light = ["ローキー", "逆光", "リムライト", "ドラマティック"]
    elif brightness > 170:
        light = "柔らかな自然光・トップ拡散光。シャドウが淡く、全体のディテールと固有色が鮮やかに表現されています。"
        tags_light = ["ハイキー", "自然光", "拡散光", "透明感"]
    else:
        light = "立体感を際立たせる斜光（キーライト＋フィルライト）。明暗境界線（ターミネーター）が美しく形を浮き彫りにしています。"
        tags_light = ["斜光", "立体感", "コントラスト良好"]

    # ポーズ・アナトミー
    pose = "自然なコントラポストが効いた立ち姿。片足への重心移動により骨盤と肩の傾きが心地よいS字ラインを形成しています。"

    # 衣装・素材感
    costume = "適度なハリ感としなやかさを持つ布地。関節可動部や重心のかかるポイントに規則的な放射状の引っ張りシワが見られます。"

    all_tags = tags_comp + tags_light + ["リファレンス", "キャラクター表現"]

    return {
        "composition": comp,
        "lighting": light,
        "pose_anatomy": pose,
        "costume_structure": costume,
        "palette": palette,
        "tags": all_tags[:6],
    }


# =====================================================================
# レスポンスの正規化
# =====================================================================
def _normalize_hex(value: str) -> str:
    """LLM が返した色文字列を #RRGGBB に寄せる"""
    s = str(value).strip()
    if not s.startswith("#"):
        s = f"#{s}"
    if len(s) == 4:  # #abc
        s = "#" + "".join(c * 2 for c in s[1:])
    if len(s) != 7:
        raise ValueError(f"不正な色コード: {value}")
    int(s[1:], 16)  # 16進として妥当か確認
    return s.lower()


def normalize_analysis(
    raw: Dict[str, Any],
    image_path: Path,
) -> Dict[str, Any]:
    """LLM の応答をapps必需キーの形へ補正する"""
    result: Dict[str, Any] = {}

    for key in ("composition", "lighting", "pose_anatomy", "costume_structure"):
        value = raw.get(key)
        result[key] = str(value).strip() if value else "解析データなし"

    # パレット: 5色を #RRGGBB に揃える（不正値は抽出パレットで補う）
    extracted = extract_dominant_colors(image_path, 5)
    palette: List[str] = []
    for item in raw.get("palette") or []:
        try:
            palette.append(_normalize_hex(item))
        except ValueError:
            continue
    palette = palette[:5]
    while len(palette) < 5:
        palette.append(extracted[len(palette)])
    result["palette"] = palette

    # タグ: 文字列のリストに揃える
    tags: List[str] = []
    for item in raw.get("tags") or []:
        text = str(item).strip()
        if text and text not in tags:
            tags.append(text)
    result["tags"] = tags[:10] or ["リファレンス"]

    return result


def model_name_for(analysis_data: Dict[str, Any]) -> str:
    """どのプロバイダ/モデルの結果かを表示用の名前として返す"""
    return analysis_data.pop("_model", "") or "heuristic-vision-v1"


# =====================================================================
# プロバイダ
# =====================================================================
def _analyze_with_ollama(image_path: Path) -> Dict[str, Any]:
    """Ollama ローカルモデル（gemma3）で解析する

    設定されたモデルが画像を読めない場合（テキストのみモデル）は、
    ローカルにある vision 対応モデルへ自動で切り替える。
    """
    model = settings.OLLAMA_MODEL

    if not ollama_client.model_supports_vision(model):
        vision_models = ollama_client.list_vision_models()
        if not vision_models:
            raise ollama_client.OllamaUnavailable(
                f"{model} は画像を読めず、vision 対応モデルもありません。"
                "OLLAMA_MODEL に gemma3 系のモデルを指定してください。"
            )
        model = vision_models[0]
        logger.info("%s は画像非対応のため %s で解析します", settings.OLLAMA_MODEL, model)

    prompt = f"{SYSTEM_PROMPT}\n\n上のJSON形式で回答してください。説明文は不要です。"

    data = ollama_client.generate_json(
        prompt,
        model=model,
        images=[image_path],
        temperature=0.2,
        timeout=settings.OLLAMA_TIMEOUT,
    )
    data["_model"] = f"ollama:{model}"
    return data


async def _analyze_with_gemini(image_path: Path) -> Dict[str, Any]:
    """Google Gemini Vision API で解析する"""
    import base64

    with open(image_path, "rb") as f:
        image_data = f.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")

    suffix = image_path.suffix.lower()
    mime_type = "image/jpeg"
    if suffix == ".png":
        mime_type = "image/png"
    elif suffix == ".webp":
        mime_type = "image/webp"

    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"inline_data": {"mime_type": mime_type, "data": base64_image}},
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(api_url, json=payload)

    resp.raise_for_status()
    result = resp.json()
    content_text = result["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(content_text)
    data["_model"] = f"gemini:{settings.GEMINI_MODEL}"
    return data


# 旧コードとの互換（他从モジュールが import する名前）
def _require_keys(raw: Dict[str, Any], image_path: Path) -> Dict[str, Any]:
    return normalize_analysis(raw, image_path)


async def analyze_image_with_vision(image_path: Path) -> Dict[str, Any]:
    """画像を解析して apps必需キー（composition / lighting / palette / tags ...）を返す

    LLM_PROVIDER の指定、または自動選択でプロバイダを決める。
    どの経路でも失敗した場合は smart_heuristic_fallback に落ちる。
    """
    provider = settings.LLM_PROVIDER.strip().lower()

    # 明示指定がある場合はそのプロバイダだけを試す
    if provider == "heuristic":
        return await asyncio.to_thread(smart_heuristic_fallback, image_path)

    chain: List[str]
    if provider == "ollama":
        chain = ["ollama"]
    elif provider == "gemini":
        chain = ["gemini"]
    elif provider:
        logger.warning("Unknown LLM_PROVIDER: %s → heuristic にフォールバック", provider)
        chain = ["heuristic"]
    else:
        # 自動選択: Ollama → Gemini → heuristic
        chain = []
        if await asyncio.to_thread(ollama_client.is_available):
            chain.append("ollama")
        if settings.GEMINI_API_KEY:
            chain.append("gemini")
        chain.append("heuristic")

    for name in chain:
        try:
            if name == "ollama":
                raw = await asyncio.to_thread(_analyze_with_ollama, image_path)
            elif name == "gemini":
                raw = await _analyze_with_gemini(image_path)
            else:
                return await asyncio.to_thread(smart_heuristic_fallback, image_path)

            return await asyncio.to_thread(normalize_analysis, raw, image_path)
        except ollama_client.OllamaUnavailable as exc:
            logger.warning("Ollama analysis unavailable: %s", exc)
        except httpx.HTTPError as exc:
            logger.error("%s API error: %s", name, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("%s analysis failed: %s", name, exc, exc_info=True)

        # 明示指定のxies場合は次へ進まず heuristic に落とす
        if provider in ("ollama", "gemini"):
            break

    return await asyncio.to_thread(smart_heuristic_fallback, image_path)


def describe_active_provider() -> Dict[str, Any]:
    """UI / ログ向けの現在プロバイダ情報"""
    return {
        "configured_provider": settings.LLM_PROVIDER or "auto",
        "ollama_available": ollama_client.is_available(),
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_models": [m.get("name") for m in ollama_client.list_models()],
        "ollama_vision_models": ollama_client.list_vision_models(),
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
    }
