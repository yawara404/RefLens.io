"""
RefLens.io Galaxy AI 風 視覚画像検索（Visual Search / かこって検索）サービス。

画像全体または「かこって選択」した切り抜き領域（Crop）から、
被写体・衣装・ポーズ・構図・ライティング・色彩を AI 解析し、
ライブラリ内の類似リファレンス資料を検索・スコアリングして返却する。
"""

from __future__ import annotations

import base64
import io
import logging
import math
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.models import AIAnalysis, MediaItem
from app.services.llm_analyzer import analyze_image_with_vision, extract_dominant_colors
from app.services.search_suggest import predict_search_suggestions

logger = logging.getLogger(__name__)


def _hex_to_rgb(hex_code: str) -> Optional[Tuple[int, int, int]]:
    clean = (hex_code or "").strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return None
    try:
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
    except ValueError:
        return None


def _color_distance(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """知覚加重ユークリッド色差"""
    r_mean = (rgb1[0] + rgb2[0]) / 2.0
    dr = rgb1[0] - rgb2[0]
    dg = rgb1[1] - rgb2[1]
    db = rgb1[2] - rgb2[2]
    return math.sqrt(
        (2.0 + r_mean / 256.0) * (dr ** 2)
        + 4.0 * (dg ** 2)
        + (2.0 + (255.0 - r_mean) / 256.0) * (db ** 2)
    )


def _palette_min_distance(palette1: List[str], palette2: List[str]) -> float:
    """2つのパレット間の最小平均色差"""
    rgb_list1 = [_hex_to_rgb(h) for h in palette1 if _hex_to_rgb(h)]
    rgb_list2 = [_hex_to_rgb(h) for h in palette2 if _hex_to_rgb(h)]
    if not rgb_list1 or not rgb_list2:
        return 999.0

    min_distances = []
    for c1 in rgb_list1:
        dist = min(_color_distance(c1, c2) for c2 in rgb_list2)
        min_distances.append(dist)
    return sum(min_distances) / len(min_distances)


async def execute_visual_search(
    image_bytes: bytes,
    user_id: str,
    db: Session,
    limit: int = 15,
) -> Dict[str, Any]:
    """画像を読み込み、視覚特徴量と類似リファレンスを検索"""
    # 1. 一時画像として保存（Pillow でリサイズして高速化）
    crop_id = str(uuid.uuid4())
    temp_dir = Path("/tmp/reflens_crops")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"crop_{crop_id}.jpg"

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            rgb_img = img.convert("RGB")
            # 解析用に最大 800px に縮小
            rgb_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            rgb_img.save(temp_path, "JPEG", quality=85)
    except Exception as exc:
        logger.error("Failed to process visual search image: %s", exc)
        raise ValueError("画像データの読み込みに失敗しました") from exc

    # 2. 視覚解析の実行（Vision LLM または特徴量フォールバック）
    analysis = await analyze_image_with_vision(temp_path)
    detected_tags: List[str] = [str(t).strip() for t in (analysis.get("tags") or []) if str(t).strip()]
    detected_palette: List[str] = analysis.get("palette") or extract_dominant_colors(temp_path, 5)
    detected_comp = str(analysis.get("composition") or "")
    detected_lighting = str(analysis.get("lighting") or "")
    detected_pose = str(analysis.get("pose_anatomy") or "")
    detected_costume = str(analysis.get("costume_structure") or "")

    # 予測タグ・同義語によるクエリ拡張（例: 少女 -> 1girl, girl）
    expanded_tags = set(t.lower() for t in detected_tags)
    for tag in detected_tags[:4]:
        suggest_res = predict_search_suggestions(tag, db=db, user_id=user_id, limit=4)
        for s in suggest_res.get("suggestions", []):
            expanded_tags.add(s.lower())

    # 3. ユーザーのライブラリ全件と照合・スコアリング
    items = (
        db.query(MediaItem)
        .options(joinedload(MediaItem.ai_analysis))
        .filter(MediaItem.user_id == user_id)
        .all()
    )

    scored_items: List[Tuple[float, List[str], MediaItem]] = []

    for item in items:
        score = 0.0
        reasons: List[str] = []

        item_ai = item.ai_analysis
        item_tags = [str(t).strip() for t in (item_ai.tags_json or [])] if item_ai else []
        item_tags_low = set(t.lower() for t in item_tags)

        # A. タグ一致スコア (最大 50点)
        matched_tags = []
        for t in item_tags:
            t_low = t.lower()
            if t_low in expanded_tags:
                matched_tags.append(t)

        if matched_tags:
            tag_score = min(50.0, len(matched_tags) * 15.0)
            score += tag_score
            reasons.append(f"タグ一致: {', '.join(matched_tags[:3])}")

        # B. 色合い・パレット近似スコア (最大 30点)
        item_palette = (item_ai.palette_json if item_ai else None) or []
        if item_palette and detected_palette:
            p_dist = _palette_min_distance(detected_palette, item_palette)
            if p_dist < 60.0:
                score += 30.0
                reasons.append("カラーパレット・色相が酷似")
            elif p_dist < 110.0:
                score += 20.0
                reasons.append("色合い・トーンが近似")
            elif p_dist < 160.0:
                score += 10.0

        # C. 構図・ライティング類似スコア (最大 20点)
        if item_ai:
            c_text = f"{item_ai.composition} {item_ai.lighting} {item_ai.pose_anatomy} {item_ai.costume_structure}"
            matched_keywords = []
            for kw in ["アオリ", "俯瞰", "逆光", "トップライト", "自然光", "夜景", "サイバー", "三分割法", "立ち絵", "バストアップ"]:
                if (kw in detected_comp or kw in detected_lighting or kw in detected_pose or kw in detected_costume) and kw in c_text:
                    matched_keywords.append(kw)

            if matched_keywords:
                score += min(20.0, len(matched_keywords) * 10.0)
                reasons.append(f"構図/光が共通: {', '.join(matched_keywords[:2])}")

        # タイトルやフォルダ名のテキスト一致も加味
        item_title_low = (item.title or "").lower()
        for t in detected_tags:
            if t.lower() in item_title_low:
                score += 8.0
                break

        # 最低類似度 20% 以上のものを候補とする（候補が少ない場合は下限なし）
        if score > 0:
            sim_pct = min(98, max(25, int(score * 1.05)))
            scored_items.append((sim_pct, reasons, item))

    # スコア降順にソート
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # 上位候補をレスポンスに整形
    matches = []
    for sim_pct, reasons, it in scored_items[:limit]:
        matches.append({
            "id": it.id,
            "title": it.title or it.original_file_name or "Untitled Reference",
            "file_path": it.file_path,
            "thumbnail_url": it.thumbnail_path or it.file_path,
            "source_type": it.source_type,
            "folder_name": it.folder_name,
            "author_name": it.author_name,
            "similarity": sim_pct,
            "reasons": reasons[:2] if reasons else ["視覚特徴が近似"],
            "tags": (it.ai_analysis.tags_json or []) if it.ai_analysis else [],
            "palette": (it.ai_analysis.palette_json or []) if it.ai_analysis else [],
        })

    # 切り抜き画像のプレビュー用 Base64 サムネイル
    thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(temp_path.read_bytes()).decode('utf-8')}"

    # 要約ラベル生成
    summary_parts = []
    if detected_tags:
        summary_parts.append(", ".join(detected_tags[:3]))
    if detected_lighting:
        summary_parts.append(f"{detected_lighting.split(' / ')[0]}の光")
    summary = " / ".join(summary_parts) if summary_parts else "選択領域の視覚特徴"

    return {
        "crop_thumbnail": thumb_b64,
        "detected": {
            "summary": summary,
            "tags": detected_tags[:8],
            "palette": detected_palette[:5],
            "composition": detected_comp,
            "lighting": detected_lighting,
            "pose": detected_pose,
            "costume": detected_costume,
        },
        "total_matches": len(matches),
        "matches": matches,
    }
