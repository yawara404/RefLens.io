"""
RefLens.io 検索キーワード予測・同義語拡張サービス。

Ollama ローカル LLM を利用して、ユーザーが入力したキーワード
（例: 「女の子」「サイバーパンク」「風景」など）から
関連するイラストタグ、英語タグ（1girl, girl, solo など）、
同義語・派生語をリアルタイムに予測する。
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AIAnalysis, MediaItem
from app.services import ollama_client

logger = logging.getLogger(__name__)

# インメモリ LRU / TTL キャッシュ (query_lower -> (timestamp, result_dict))
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL = 86400.0  # 24時間キャッシュ
_MAX_CACHE_SIZE = 1000

# イラスト・デザイン検索で頻出する日本語 ↔ 英語・同義語辞書（即応フォールバック・ベース拡張）
COMMON_ART_SYNONYMS: Dict[str, List[str]] = {
    "女の子": ["1girl", "girl", "少女", "女性", "女性キャラ", "anime girl", "cute girl", "kawaii"],
    "女子": ["1girl", "girl", "少女", "女性", "女子高生", "JK"],
    "少女": ["1girl", "girl", "女の子", "young girl", "美少女"],
    "女性": ["woman", "female", "1girl", "大人女性", "lady"],
    "男の子": ["1boy", "boy", "少年", "男性", "男子", "anime boy"],
    "男子": ["1boy", "boy", "少年", "男性", "男子高生"],
    "少年": ["1boy", "boy", "男の子", "shonen", "young boy"],
    "男性": ["man", "male", "1boy", "イケメン", "gentleman"],
    "猫": ["cat", "neko", "猫耳", "cat_ears", "animal"],
    "ねこ": ["cat", "neko", "猫耳", "cat_ears"],
    "犬": ["dog", "inu", "犬耳", "dog_ears"],
    "いぬ": ["dog", "inu", "犬耳", "dog_ears"],
    "うさぎ": ["rabbit", "bunny", "うさ耳", "bunny_ears"],
    "兎": ["rabbit", "bunny", "うさ耳", "bunny_ears"],
    "制服": ["school_uniform", "sailor_uniform", "blazer", "セーラー服", "ブレザー"],
    "スーツ": ["suit", "business_suit", "formal", "ネクタイ"],
    "ドレス": ["dress", "gown", "wedding_dress", "フリル", "ワンピース"],
    "水着": ["swimsuit", "bikini", "水着", "ビキニ", "競泳水着"],
    "着物": ["kimono", "yukata", "和服", "浴衣", "和風"],
    "和風": ["japanese_style", "kimono", "鳥居", "桜", "和服"],
    "背景": ["background", "scenery", "landscape", "風景", "背景重視", "環境"],
    "風景": ["landscape", "scenery", "background", "自然", "空", "街並み"],
    "空": ["sky", "blue_sky", "clouds", "青空", "雲", "夕焼け", "星空"],
    "夜景": ["night_view", "night_sky", "cityscape", "ネオン", "星空"],
    "サイバーパンク": ["cyberpunk", "sci-fi", "neon", "近未来", "メカ", "サイバー"],
    "ファンタジー": ["fantasy", "magic", "medieval", "騎士", "魔法", "異世界"],
    "ポーズ": ["pose", "action_pose", "立ち絵", "ポーズ重視", "構図"],
    "髪": ["hair", "long_hair", "short_hair", "twintails", "ponytail"],
    "ツインテール": ["twintails", "twin_tails", "hair", "髪型"],
    "ポニーテール": ["ponytail", "pony_tail", "hair", "髪型"],
    "ボブ": ["bob_hair", "short_hair", "ボブカット"],
    "黒髪": ["black_hair", "dark_hair", "黒髪ロング"],
    "金髪": ["blonde_hair", "yellow_hair", "金髪"],
    "銀髪": ["silver_hair", "white_hair", "白髪"],
    "白髪": ["white_hair", "silver_hair", "銀髪"],
    "赤髪": ["red_hair"],
    "青髪": ["blue_hair"],
    "緑髪": ["green_hair"],
    "メガネ": ["glasses", "眼鏡", "めがね", "伊達メガネ"],
    "眼鏡": ["glasses", "メガネ", "めがね"],
    "笑顔": ["smile", "happy", "smiling", "微笑み"],
    "光": ["lighting", "rim_light", "逆光", "自然光", "木漏れ日"],
    "ライティング": ["lighting", "rim_light", "逆光", "トップライト", "ドラマティック"],
    "構図": ["composition", "アオリ", "俯瞰", "三分割法", "対角線構図", "パース"],
}


def _clean_text(s: str) -> str:
    cleaned = re.sub(r'[\r\n\t]+', ' ', s).strip()
    return cleaned.strip('"\',.[]')


def parse_suggestions_json(text: str) -> List[str]:
    """LLM の応答から文字列配列（タグ候補）を取り出す"""
    text = (text or "").strip()
    if not text:
        return []

    # マークダウンコードフェンス除去
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 直接 JSON パース
    try:
        data = json.loads(text)
        if isinstance(data, list):
            res = [_clean_text(str(x)) for x in data if str(x).strip()]
            return [x for x in res if x]
        if isinstance(data, dict):
            for k in ("suggestions", "tags", "keywords", "results"):
                if k in data and isinstance(data[k], list):
                    res = [_clean_text(str(x)) for x in data[k] if str(x).strip()]
                    return [x for x in res if x]
    except Exception:
        pass

    # [ ... ] の範囲を切り出して再パース
    s_idx = text.find("[")
    e_idx = text.rfind("]")
    if s_idx != -1 and e_idx > s_idx:
        try:
            arr = json.loads(text[s_idx : e_idx + 1])
            if isinstance(arr, list):
                res = [_clean_text(str(x)) for x in arr if str(x).strip()]
                return [x for x in res if x]
        except Exception:
            pass

    # クォートされた単語の抽出 (fallback)
    matches = re.findall(r'["\']([^"\'\n\r]+)["\']', text)
    filtered = []
    for m in matches:
        w = _clean_text(m)
        if 1 < len(w) < 40 and w not in filtered:
            filtered.append(w)
    return filtered[:10]


def _get_base_heuristics(q: str) -> List[str]:
    """辞書ベースの即応候補"""
    q_norm = q.lower().strip()
    results: List[str] = []

    # 完全一致
    if q_norm in COMMON_ART_SYNONYMS:
        results.extend(COMMON_ART_SYNONYMS[q_norm])

    # 部分一致
    for k, v in COMMON_ART_SYNONYMS.items():
        if k != q_norm and (k in q_norm or q_norm in k):
            for item in v:
                if item not in results:
                    results.append(item)

    return results


def _call_ollama_for_prediction(query: str, timeout: float = 3.0) -> List[str]:
    """Ollama にクエリを送り、同義語・関連タグ・英語タグを生成させる"""
    if not ollama_client.is_available():
        return []

    target_model = settings.OLLAMA_MODEL or "gemma3:4b"

    system_prompt = (
        "You are an art & illustration reference search assistant for concept artists. "
        "Given a search query, output 5 to 7 relevant tags (including Danbooru/Pixiv tags like 1girl, boy, solo, character, etc.) and synonyms. "
        "Return ONLY a valid JSON array of strings: [\"tag1\", \"tag2\"]. No markdown, no explanations."
    )

    prompt = query.strip()

    payload: Dict[str, Any] = {
        "model": target_model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "24h",
        "options": {
            "temperature": 0.1,
            "num_predict": 45,
        },
    }

    try:
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        resp = httpx.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=timeout,
        )
        if resp.status_code == 200:
            raw = resp.json().get("response", "")
            return parse_suggestions_json(raw)
    except Exception as exc:
        logger.debug("Ollama prediction call timed out or failed: %s", exc)

    return []


def get_user_library_tags(db: Session, user_id: str) -> Dict[str, int]:
    """ユーザーが現在登録しているブックマークのAI解析タグを集計"""
    try:
        records = (
            db.query(AIAnalysis.tags_json)
            .join(MediaItem, AIAnalysis.media_item_id == MediaItem.id)
            .filter(MediaItem.user_id == user_id)
            .all()
        )
        counts: Dict[str, int] = {}
        for (tags,) in records:
            if isinstance(tags, list):
                for t in tags:
                    if t and isinstance(t, str):
                        clean = t.strip()
                        counts[clean] = counts.get(clean, 0) + 1
        return counts
    except Exception as exc:
        logger.warning("Failed to count user library tags: %s", exc)
        return {}


def _async_warm_ollama_cache(query: str):
    """バックグラウンドで Ollama を呼び出しキャッシュを更新する"""
    try:
        ollama_list = _call_ollama_for_prediction(query, timeout=12.0)
        if ollama_list:
            q_key = query.strip().lower()
            heuristic_list = _get_base_heuristics(query)
            merged = []
            seen = set()
            for s in ollama_list + heuristic_list:
                c = s.strip()
                low = c.lower()
                if c and low not in seen and low != q_key:
                    seen.add(low)
                    merged.append(c)
            now = time.time()
            if q_key in _CACHE:
                _, old_val = _CACHE[q_key]
                old_val["suggestions"] = merged[:10]
                old_val["source"] = "ollama"
                _CACHE[q_key] = (now, old_val)
            else:
                _CACHE[q_key] = (now, {
                    "query": query,
                    "source": "ollama",
                    "suggestions": merged[:10],
                    "library_tags": [],
                })
    except Exception as exc:
        logger.debug("Background Ollama warming error: %s", exc)


def predict_search_suggestions(
    query: str,
    db: Optional[Session] = None,
    user_id: Optional[str] = None,
    limit: int = 8,
) -> Dict[str, Any]:
    """検索キーワードに対する予測タグ・同義語・ライブラリ内ヒットタグを返す"""
    q = query.strip()
    if not q:
        return {
            "query": "",
            "source": "empty",
            "suggestions": [],
            "library_tags": [],
        }

    q_key = q.lower()
    now = time.time()

    # 1. すでに Ollama の推論結果がキャッシュにある場合は即返却 (<1ms)
    if q_key in _CACHE:
        cached_time, cached_val = _CACHE[q_key]
        if now - cached_time < _CACHE_TTL:
            res = dict(cached_val)
            if db and user_id:
                lib_tags = get_user_library_tags(db, user_id)
                seen_tags = {s.lower() for s in res.get("suggestions", [])}
                matched_tags = []
                for tag_name, count in lib_tags.items():
                    t_low = tag_name.lower()
                    if t_low in seen_tags or q_key in t_low or t_low in q_key:
                        matched_tags.append((tag_name, count))
                matched_tags.sort(key=lambda x: x[1], reverse=True)
                res["library_tags"] = [{"tag": name, "count": count} for name, count in matched_tags[:10]]
            return res

    # 2. 辞書ベースの即応候補
    heuristic_list = _get_base_heuristics(q)

    # 3. Ollama による予測（モデルが温まっていれば ~1s 以内に返却）
    # タイムアウトは 2.5 秒。これを超える場合は即応フォールバックを返し、バックグラウンドで温める
    ollama_list = _call_ollama_for_prediction(q, timeout=2.5)

    # Ollama がタイムアウトした場合、バックグラウンドスレッドで実行して次回用にキャッシュ
    if not ollama_list and ollama_client.is_available():
        threading.Thread(target=_async_warm_ollama_cache, args=(q,), daemon=True).start()

    # 重複排除しながら結合
    merged_suggestions: List[str] = []
    seen = set()

    def add_item(item: str):
        cleaned = item.strip()
        low = cleaned.lower()
        if not cleaned or low in seen or low == q_key:
            return
        seen.add(low)
        merged_suggestions.append(cleaned)

    # Ollama が取得できた場合は Ollama を優先、できなければ辞書
    for s in ollama_list:
        add_item(s)
    for s in heuristic_list:
        add_item(s)

    suggestions = merged_suggestions[:limit]

    # 4. ユーザーのライブラリに実際に存在するタグと照合
    library_matches: List[Dict[str, Any]] = []
    if db and user_id:
        lib_tags = get_user_library_tags(db, user_id)
        matched_tags: List[Tuple[str, int]] = []
        for tag_name, count in lib_tags.items():
            t_low = tag_name.lower()
            if t_low in seen or q_key in t_low or t_low in q_key:
                matched_tags.append((tag_name, count))

        matched_tags.sort(key=lambda x: x[1], reverse=True)
        library_matches = [{"tag": name, "count": count} for name, count in matched_tags[:10]]

    result = {
        "query": q,
        "source": "ollama" if ollama_list else "heuristic",
        "suggestions": suggestions,
        "library_tags": library_matches,
    }

    # キャッシュ保存
    if len(_CACHE) >= _MAX_CACHE_SIZE:
        oldest_key = min(_CACHE.keys(), key=lambda k: _CACHE[k][0])
        _CACHE.pop(oldest_key, None)
    _CACHE[q_key] = (now, result)

    return result
