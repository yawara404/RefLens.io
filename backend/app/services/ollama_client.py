"""
Ollama ローカル LLM クライアント。

RefLens.io の AI 解析（構図・ライティング・ポーズ・衣装の解剖）を
ローカル LLM で動かすためのクライアント。

使い分け
    * 画像対応モデル（gemma3 など）はそのまま画像解析に使える
    * テキストのみモデル（qwen3 など）は画像解析に使えないため、
      呼び出し側でフォールバック（heuristic / 別モデル）を選ぶ

API: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class OllamaUnavailable(RuntimeError):
    """Ollama サーバーに接続できない、または requisite な機能がない"""


def _base_url() -> str:
    return settings.OLLAMA_BASE_URL.rstrip("/")


def is_available() -> bool:
    """Ollama サーバーが応答するか"""
    try:
        resp = httpx.get(f"{_base_url()}/api/tags", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def list_models() -> List[Dict[str, Any]]:
    """ローカルに用意されているモデル一覧"""
    try:
        resp = httpx.get(f"{_base_url()}/api/tags", timeout=5.0)
        resp.raise_for_status()
        return resp.json().get("models", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to list ollama models: %s", exc)
        return []


def list_vision_models() -> List[str]:
    """画像入力に対応しているモデルの名前だけ返す"""
    result = []
    for m in list_models():
        capabilities = m.get("capabilities") or []
        if "vision" in capabilities:
            result.append(m.get("name") or m.get("model") or "")
    return [n for n in result if n]


def _encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _mime_of(image_path: Path) -> str:
    return _MIME_TYPES.get(image_path.suffix.lower(), "image/jpeg")


def generate_text(
    prompt: str,
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    images: Optional[List[Path]] = None,
    temperature: float = 0.2,
    timeout: float = 180.0,
) -> str:
    """Ollama の /api/generate を叩いてテキストを返す

    images を渡すと Ollama が vision 対応モデルなら画像も受け取る。
    """
    payload: Dict[str, Any] = {
        "model": model or settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": settings.OLLAMA_NUM_CTX,
        },
    }
    if system:
        payload["system"] = system
    if images:
        payload["images"] = [_encode_image(p) for p in images]

    try:
        resp = httpx.post(
            f"{_base_url()}/api/generate",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except httpx.HTTPError as exc:
        raise OllamaUnavailable(f"Ollama リクエストに失敗しました: {exc}") from exc


def generate_json(
    prompt: str,
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    images: Optional[List[Path]] = None,
    temperature: float = 0.2,
    timeout: float = 180.0,
) -> Dict[str, Any]:
    """JSON を返すよう指示してパースする（失敗時は例外）"""
    raw = generate_text(
        prompt,
        model=model,
        system=system,
        images=images,
        temperature=temperature,
        timeout=timeout,
    )

    text = (raw or "").strip()
    if not text:
        raise OllamaUnavailable("Ollama が空のレスポンスを返しました")

    # ```json ... ``` のフェンスを除去
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 前後に余分な文章が混ざっている場合の救済（最初の{...}を採用）
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise OllamaUnavailable(f"Ollama の応答を JSON として解釈できません: {text[:200]}")


def model_supports_vision(model: str) -> bool:
    """指定モデルが画像入力に対応しているか"""
    for m in list_models():
        name = m.get("name") or m.get("model") or ""
        # qwen3:8b と qwen3 の両方にマッチするようにする
        if name == model or name.split(":")[0] == model.split(":")[0]:
            return "vision" in (m.get("capabilities") or [])
    return False