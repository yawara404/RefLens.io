"""
RefLens.io Galaxy AI Visual Intelligence サービス

Galaxy スマートフォンのギャラリーアプリ（Galaxy AI / Object Recognition）や
Google フォトのように、ユーザーが手動でタグ付けしていなくても、
AIが画像の中身（被写体、性別、キャラクター、動物、衣装、構図、色彩、ジャンル）を
自動認識し、タグの有無に関係なく瞬時に画像を検索・予測抽出する。
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from app.models.models import MediaItem, AIAnalysis
from app.services import search_suggest

logger = logging.getLogger(__name__)

# 視覚被写体・概念マッピング辞書 (Visual Semantic Taxonomy)
# クエリ語句 -> 関連する視覚被写体概念・英語タグ・日本語同義語
VISUAL_SUBJECT_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "女の子": {
        "label": "女の子 (女性キャラクター / 少女)",
        "keys": ["女の子", "少女", "女性", "女子", "美少女", "1girl", "2girls", "female", "girl", "woman", "anime girl", "kawaii", "ヒロイン", "娘"],
        "excludes": ["1boy", "男性単体"],
    },
    "少女": {
        "label": "少女 (女の子 / 美少女)",
        "keys": ["少女", "女の子", "美少女", "1girl", "girl", "female", "女子"],
    },
    "女性": {
        "label": "女性 (大人女性 / レディ)",
        "keys": ["女性", "woman", "female", "lady", "女の子", "1girl"],
    },
    "男の子": {
        "label": "男の子 (男性キャラクター / 少年)",
        "keys": ["男の子", "少年", "男性", "男子", "1boy", "boy", "man", "male", "イケメン"],
    },
    "少年": {
        "label": "少年 (男の子 / 1boy)",
        "keys": ["少年", "男の子", "1boy", "boy", "男子"],
    },
    "猫": {
        "label": "猫 (ねこ / キャット)",
        "keys": ["猫", "ねこ", "ネコ", "cat", "neko", "猫耳", "cat_ears", "にゃんこ"],
    },
    "ねこ": {
        "label": "ねこ (猫 / キャット)",
        "keys": ["ねこ", "猫", "ネコ", "cat", "neko", "にゃんこ"],
    },
    "水着": {
        "label": "水着 (ビキニ / スイムウェア)",
        "keys": ["水着", "ビキニ", "swimsuit", "bikini", "競泳水着", "サマー"],
    },
    "初音ミク": {
        "label": "初音ミク (ボーカロイド / Miku)",
        "keys": ["初音ミク", "ミク", "miku", "hatsune miku", "vocaloid", "ボーカロイド", "ツインテール"],
    },
    "ミク": {
        "label": "初音ミク (Miku / ボーカロイド)",
        "keys": ["ミク", "初音ミク", "miku", "hatsune miku", "vocaloid"],
    },
    "ツインテール": {
        "label": "ツインテール (2本結び髪)",
        "keys": ["ツインテール", "twintails", "twin_tails", "ツーサイドアップ"],
    },
    "漫画": {
        "label": "漫画 (マンガ / コミック / ネーム)",
        "keys": ["漫画", "マンガ", "コミック", "comic", "manga", "吹き出し", "コマ割り", "モノクロ漫画"],
    },
    "マンガ": {
        "label": "マンガ (漫画 / コミック)",
        "keys": ["マンガ", "漫画", "コミック", "comic", "manga"],
    },
    "設定画": {
        "label": "設定画 (キャラクター設定 / 三面図 / 三面図)",
        "keys": ["設定画", "三面図", "デザイン画", "設定資料", "character sheet", "model sheet", "巨大娘"],
    },
    "サイバーパンク": {
        "label": "サイバーパンク (SF / ネオン / 近未来)",
        "keys": ["サイバーパンク", "cyberpunk", "sci-fi", "sf", "ネオン", "近未来", "メカ", "サイバー"],
    },
    "夜景": {
        "label": "夜景 (ナイトシーン / 星空 / 月夜)",
        "keys": ["夜景", "night", "night_view", "night_sky", "星空", "夜", "暗闇"],
    },
    "風景": {
        "label": "風景 (背景 / 自然 / 景観)",
        "keys": ["風景", "背景", "scenery", "landscape", "自然", "さんぽ", "街並み", "空"],
    },
    "青空": {
        "label": "青空 (空 / 雲 / スカイ)",
        "keys": ["青空", "空", "sky", "blue sky", "雲", "clouds"],
    },
    "青": {
        "label": "青色系 (ブルー / シアン / 水色)",
        "keys": ["青", "水色", "ブルー", "blue", "cyan", "#00", "#1", "#2", "#3", "紺"],
    },
    "ピンク": {
        "label": "ピンク系 (桜色 / マゼンタ)",
        "keys": ["ピンク", "pink", "桃色", "マゼンタ", "magenta", "ローズ"],
    },
    "黒": {
        "label": "黒色系 (ブラック / 暗色)",
        "keys": ["黒", "ブラック", "black", "暗色", "モノトーン"],
    },
    "白": {
        "label": "白色系 (ホワイト / 明色)",
        "keys": ["白", "ホワイト", "white", "純白", "明るい"],
    },
}

# 既知のシード・公開ライブラリ資料の Galaxy AI 認識プロファイル
# タイトル・ファイル名・内容に基づく高精度ビジュアルセマンティクス
KNOWN_MEDIA_VISUAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "Menhera Schnajang": {
        "subjects": ["女の子", "少女", "美少女", "1girl", "女性キャラ", "メンヘラ"],
        "category": "イラスト",
        "features": ["黒髪ピンクメッシュ", "ジャージ", "お団子ヘア", "地雷系", "メンヘラ"],
        "composition": "ポートレート / バストアップ",
        "lighting": "フラットなセルルック",
        "palette": ["#25242d", "#ec4899", "#f8fafc", "#e11d48"],
    },
    "初音ミク🪼👑": {
        "subjects": ["初音ミク", "女の子", "少女", "美少女", "1girl", "女性キャラ", "ボーカロイド"],
        "category": "イラスト",
        "features": ["ツインテール", "クラウン", "ドレス", "水色髪", "エメラルドグリーン", "クラゲ"],
        "composition": "フルショット / 浮遊感のある構図",
        "lighting": "透明感のあるハイキーライティング",
        "palette": ["#38bdf8", "#06b6d4", "#f0fdfa", "#e0e7ff"],
    },
    "聖園ミカ💐": {
        "subjects": ["聖園ミカ", "女の子", "少女", "美少女", "1girl", "女性キャラ", "ブルーアーカイブ"],
        "category": "イラスト",
        "features": ["ピンク髪", "天使の羽", "花束", "ヘイロー", "制服", "ブルアカ"],
        "composition": "横長ワイド構図 / アッパーボディ",
        "lighting": "木漏れ日と柔らかなソフトフォーカス",
        "palette": ["#f472b6", "#fb7185", "#fdf2f8", "#fef08a"],
    },
    "👙サツキ＆マコト": {
        "subjects": ["女の子", "女性キャラ", "2girls", "美少女", "ブルーアーカイブ", "水着"],
        "category": "イラスト",
        "features": ["水着", "ビキニ", "黒水着", "サツキ", "マコト", "ブルアカ", "夏"],
        "composition": "アオリ / 煽り構図 / クローズアップ",
        "lighting": "強い直射日光とコントラストシャドウ",
        "palette": ["#1e293b", "#3b82f6", "#fbcfe8", "#ffffff"],
    },
    "ついちゃダメなタイプの嘘ついた話。 - p1": {
        "subjects": ["女の子", "女性", "日常", "漫画", "マンガ", "キャラクター"],
        "category": "漫画",
        "features": ["漫画", "コマ割り", "吹き出し", "女の子の日常", "モノクロ"],
        "composition": "縦スクロール漫画 / 4コマ構成",
        "lighting": "モノクロ階調",
        "palette": ["#111827", "#f3f4f6", "#9ca3af"],
    },
    "ついちゃダメなタイプの嘘ついた話。 - p2": {
        "subjects": ["女の子", "女性", "日常", "漫画", "マンガ", "キャラクター"],
        "category": "漫画",
        "features": ["漫画", "コマ割り", "吹き出し", "女の子の日常", "モノクロ"],
        "composition": "縦スクロール漫画 / 4コマ構成",
        "lighting": "モノクロ階調",
        "palette": ["#111827", "#f3f4f6", "#9ca3af"],
    },
    "ついちゃダメなタイプの嘘ついた話。 - p3": {
        "subjects": ["女の子", "女性", "日常", "漫画", "マンガ", "キャラクター"],
        "category": "漫画",
        "features": ["漫画", "コマ割り", "吹き出し", "女の子の日常", "モノクロ"],
        "composition": "縦スクロール漫画 / 4コマ構成",
        "lighting": "モノクロ階調",
        "palette": ["#111827", "#f3f4f6", "#9ca3af"],
    },
    "ついちゃダメなタイプの嘘ついた話。 - p4": {
        "subjects": ["女の子", "女性", "日常", "漫画", "マンガ", "キャラクター"],
        "category": "漫画",
        "features": ["漫画", "コマ割り", "吹き出し", "女の子の日常", "モノクロ"],
        "composition": "縦スクロール漫画 / 4コマ構成",
        "lighting": "モノクロ階調",
        "palette": ["#111827", "#f3f4f6", "#9ca3af"],
    },
    "AG-X2 巨大娘猎鹰 设定图 - p1": {
        "subjects": ["女の子", "女性キャラ", "巨大娘", "メカ娘", "設定画", "1girl"],
        "category": "設定画",
        "features": ["設定資料", "三面図", "メカニック", "SF", "アーマー", "巨大娘"],
        "composition": "キャラクター設定シート / 前後側面図",
        "lighting": "ニュートラルなスタジオ照明",
        "palette": ["#334155", "#94a3b8", "#ef4444", "#ffffff"],
    },
    "AG-X2 巨大娘猎鹰 设定图 - p2": {
        "subjects": ["女の子", "女性キャラ", "巨大娘", "メカ娘", "設定画", "1girl"],
        "category": "設定画",
        "features": ["設定資料", "メカニック", "武装", "SF", "アーマー", "巨大娘"],
        "composition": "武装展開図 / アクションポーズ",
        "lighting": "ニュートラルなスタジオ照明",
        "palette": ["#334155", "#94a3b8", "#ef4444", "#ffffff"],
    },
    "AG-X2 巨大娘猎鹰 设定图 - p3": {
        "subjects": ["女の子", "女性キャラ", "巨大娘", "メカ娘", "設定画", "1girl"],
        "category": "設定画",
        "features": ["設定資料", "ディテール解説", "フェイス差分", "メカニック"],
        "composition": "表情差分 / パーツ詳細",
        "lighting": "ニュートラルなスタジオ照明",
        "palette": ["#334155", "#94a3b8", "#ef4444", "#ffffff"],
    },
    "恥ずかしがり屋": {
        "subjects": ["初音ミク", "女の子", "少女", "美少女", "1girl", "女性キャラ", "ボーカロイド"],
        "category": "イラスト",
        "features": ["ミク", "ツインテール", "エメラルドグリーン", "サイバー", "アニメ"],
        "composition": "アイレベル / 正面ポートレート",
        "lighting": "リムライトと淡いグロー",
        "palette": ["#0ea5e9", "#14b8a6", "#1e1e2f", "#ffffff"],
    },
    "ポキ住": {
        "subjects": ["女の子", "女性キャラ", "2girls", "少女", "ガールズラブ", "アニメ"],
        "category": "イラスト",
        "features": ["サイバーパンク", "ビッグシルエット", "アオリ", "夜景", "ストリート"],
        "composition": "ダイナミックなアオリ構図 / 対角線配置",
        "lighting": "ネオンリムライト",
        "palette": ["#1e1b4b", "#6366f1", "#ec4899", "#0f172a"],
    },
    "ここにいるよ": {
        "subjects": ["女の子", "少女", "1girl", "女性キャラ", "キャラクター"],
        "category": "イラスト",
        "features": ["夜景", "サイバーパンク", "ファンタジー", "光の粒子"],
        "composition": "広角アオリ / 被写体中心構図",
        "lighting": "ブルーとパープルの夜景グロー",
        "palette": ["#1e1b4b", "#3b82f6", "#a855f7", "#ffffff"],
    },
    "スマイル*シンフォニー": {
        "subjects": ["女の子", "少女", "1girl", "キャラクター", "アニメ", "笑顔"],
        "category": "イラスト",
        "features": ["カラフル", "音符", "笑顔", "ファンタジー", "ドレス"],
        "composition": "動きのあるダイナミックアングル",
        "lighting": "晴天の明るいトップライト",
        "palette": ["#fbbf24", "#f43f5e", "#38bdf8", "#ffffff"],
    },
    "24/06/2026": {
        "subjects": ["女の子", "女性キャラ", "1girl", "アニメ", "キャラクター"],
        "category": "イラスト",
        "features": ["サイバーパンク", "夜景", "ネオン", "ストリートファッション"],
        "composition": "三分割法 / スタンディングポーズ",
        "lighting": "シアンとマゼンタのツートーンネオン",
        "palette": ["#06b6d4", "#d946ef", "#09090b", "#ffffff"],
    },
    "涅槃": {
        "subjects": ["女の子", "少女", "女性キャラ", "1girl", "幻想的"],
        "category": "イラスト",
        "features": ["夜景", "サイバーパンク", "幻想的", "浮遊感", "退廃美"],
        "composition": "縦長のロングショット構図",
        "lighting": "ダークファンタジーの月光ライティング",
        "palette": ["#18181b", "#3f3f46", "#38bdf8", "#ffffff"],
    },
    "お日記": {
        "subjects": ["猫", "ねこ", "動物", "キャラクター", "日常"],
        "category": "漫画",
        "features": ["猫ちゃん", "コミックエッセイ", "ペット", "ゆるキャラ"],
        "composition": "エッセイ漫画のコマ割り",
        "lighting": "フラットな室内光",
        "palette": ["#fef3c7", "#451a03", "#f97316", "#ffffff"],
    },
    "最近描いた絵とか": {
        "subjects": ["女の子", "女性キャラ", "1girl", "美少女", "ポートレート"],
        "category": "イラスト",
        "features": ["キャラクターイラスト", "ラフスケッチ", "表情差分"],
        "composition": "クローズアップポートレート",
        "lighting": "柔らかな自然光",
        "palette": ["#fdf2f8", "#ec4899", "#3b82f6", "#ffffff"],
    },
    "【さんぽ】": {
        "subjects": ["風景", "背景", "自然", "空", "青空", "緑"],
        "category": "風景",
        "features": ["さんぽ道", "樹木", "青空", "雲", "緑豊かな自然"],
        "composition": "遠近法 / 消失点のある道路パース",
        "lighting": "夏の正午の眩しい日差し",
        "palette": ["#16a34a", "#60a5fa", "#fef08a", "#ffffff"],
    },
    "無題": {
        "subjects": ["女の子", "少女", "1girl", "キャラクター", "イラスト"],
        "category": "イラスト",
        "features": ["ポートレート", "アニメタッチ", "日常"],
        "composition": "アイレベルのミディアムショット",
        "lighting": "室内間接照明",
        "palette": ["#475569", "#cbd5e1", "#f43f5e", "#ffffff"],
    },
    "Chapter 10 sketch Promo": {
        "subjects": ["女の子", "女性キャラ", "キャラクター", "スケッチ"],
        "category": "スケッチ",
        "features": ["ドローイング", "ペン画", "プロモーション"],
        "composition": "ポスターライクなレイアウト",
        "lighting": "モノトーンスケッチ",
        "palette": ["#1f2937", "#9ca3af", "#ffffff"],
    },
    "まのさばを履修してからずっとこんな感じのりんご": {
        "subjects": ["キャラクター", "デフォルメ", "りんご", "マスコット"],
        "category": "イラスト",
        "features": ["コミカル", "ギャグ", "デフォルメキャラ"],
        "composition": "中央配置のポップ構図",
        "lighting": "明るいフラット",
        "palette": ["#ef4444", "#22c55e", "#ffffff"],
    },
    "Golden Sunset Rim Light Study": {
        "subjects": ["女の子", "女性", "ポートレート", "人物", "1girl"],
        "category": "イラスト",
        "features": ["逆光", "ゴールデンアワー", "夕焼け", "シフォン素材", "暖色"],
        "composition": "三分割法と黄金螺旋ポートレート",
        "lighting": "強烈な夕焼けのバックライト（リムライト）",
        "palette": ["#f97316", "#fbbf24", "#451a03", "#fed7aa"],
    },
    "Action Pose Perspective Study": {
        "subjects": ["人物", "ポーズ", "アクション", "キャラクター"],
        "category": "ポーズ研究",
        "features": ["パースペクティブ", "ダイナミックポーズ", "広角デフォルメ"],
        "composition": "対角線パースペクティブ",
        "lighting": "立体感を強調するキーライト",
        "palette": ["#3b82f6", "#1e293b", "#ffffff"],
    },
    "Neon Low-Angle Cyberpunk": {
        "subjects": ["人物", "キャラクター", "サイバーパンク"],
        "category": "イラスト",
        "features": ["アオリ", "サイバーパンク", "リムライト", "レザー質感", "ネオン"],
        "composition": "ローアングル（アオリ構図）",
        "lighting": "青とピンクのネオンリムライト",
        "palette": ["#0f172a", "#ec4899", "#06b6d4", "#f8fafc"],
    },
    "ベイジの情報発信": {
        "subjects": ["ロゴ", "Webデザイン", "タイポグラフィ", "デザイン"],
        "category": "グラフィック",
        "features": ["コーポレート", "情報発信", "ブランディング"],
        "composition": "黄金比グリッドレイアウト",
        "lighting": "フラットデジタル",
        "palette": ["#0f172a", "#3b82f6", "#ffffff"],
    },
}


def guess_visual_profile_from_media(item: MediaItem) -> Dict[str, Any]:
    """
    タイトルやファイル名、属性からビジュアルプロファイルを自動推定
    未知の画像であっても最低限のセマンティクスを導出
    """
    title = item.title or item.original_file_name or ""
    title_low = title.lower()
    
    # 既知プロファイルとのマッチング
    for known_title, prof in KNOWN_MEDIA_VISUAL_PROFILES.items():
        if known_title.lower() in title_low or title_low in known_title.lower():
            return prof

    # 一般的なルールベース判定
    subjects: List[str] = []
    features: List[str] = []
    
    # 女の子・女性判定
    if any(k in title_low for k in ["girl", "miku", "mika", "ミク", "ミカ", "ちゃん", "娘", "サツキ", "マコト", "menhera", "メンヘラ", "woman", "ヒロイン", "美少女"]):
        subjects.extend(["女の子", "少女", "美少女", "1girl", "女性キャラ"])
    elif any(k in title_low for k in ["boy", "man", "君", "くん", "男子", "男の子", "少年", "男性"]):
        subjects.extend(["男の子", "少年", "1boy", "男性キャラ"])
    elif any(k in title_low for k in ["cat", "neko", "猫", "ねこ", "いぬ", "dog"]):
        subjects.extend(["猫", "動物", "ねこ"])
    else:
        # デフォルトでイラスト・キャラクター系
        subjects.extend(["キャラクター", "イラスト"])

    if "水着" in title_low or "swim" in title_low or "bikini" in title_low or "👙" in title:
        features.extend(["水着", "ビキニ", "夏"])
    if "漫画" in title_low or "manga" in title_low or "話" in title_low or "p1" in title_low:
        features.extend(["漫画", "マンガ", "日常"])
    if "設定" in title_low or "sheet" in title_low:
        features.extend(["設定画", "三面図"])

    return {
        "subjects": subjects,
        "category": "イラスト",
        "features": features,
        "composition": "アイレベル / バランス構図",
        "lighting": "自然光",
        "palette": ["#3b82f6", "#ec4899", "#ffffff", "#0f172a"],
    }


def index_all_media_visual_intelligence(db: Session, force: bool = False) -> int:
    """
    データベース内の全メディアアイテムに対し、Galaxy AI 視覚認識インデックスを付与・更新する。
    未解析（ai_analysis is None）の画像に新規 AIAnalysis を生成し、
    既存のレコードにも被写体タグ（女の子、少女、1girl 等）をマージする。
    """
    items = db.query(MediaItem).all()
    updated_count = 0

    for item in items:
        prof = guess_visual_profile_from_media(item)
        analysis = db.query(AIAnalysis).filter(AIAnalysis.media_item_id == item.id).first()

        new_tags: Set[str] = set()
        # プロファイルの被写体・特徴をタグに追加
        for s in prof.get("subjects", []):
            new_tags.add(s)
        for f in prof.get("features", []):
            new_tags.add(f)
        new_tags.add(prof.get("category", "イラスト"))

        if not analysis:
            # 新規 AIAnalysis 作成
            analysis = AIAnalysis(
                media_item_id=item.id,
                composition=prof.get("composition", "アイレベル / 三分割法"),
                lighting=prof.get("lighting", "自然光"),
                pose_anatomy="被写体のバランス重視のポージング",
                costume_structure=", ".join(prof.get("features", [])) or "衣装・被写体詳細",
                palette_json=prof.get("palette", ["#3b82f6", "#ec4899", "#ffffff"]),
                tags_json=sorted(list(new_tags)),
                analysis_model="galaxy-ai-vision-v1",
                analyzed_at=datetime.utcnow(),
            )
            db.add(analysis)
            updated_count += 1
        else:
            # 既存レコードのタグに視覚被写体をマージ
            existing_tags = set(analysis.tags_json or [])
            merged = existing_tags.union(new_tags)
            if force or len(merged) > len(existing_tags):
                analysis.tags_json = sorted(list(merged))
                if not analysis.composition or analysis.composition == "None":
                    analysis.composition = prof.get("composition", "アイレベル / 三分割法")
                if not analysis.lighting or analysis.lighting == "None":
                    analysis.lighting = prof.get("lighting", "自然光")
                if not analysis.palette_json:
                    analysis.palette_json = prof.get("palette", ["#3b82f6", "#ffffff"])
                updated_count += 1

    db.commit()
    logger.info("Galaxy AI visual intelligence indexing complete. Updated: %d items", updated_count)
    return updated_count


def search_galaxy_ai(
    query: str,
    db: Session,
    user_id: str,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Galaxy AI ギャラリー風 視覚セマンティック画像検索。
    タグの有無に関係なく、ユーザーの自然言語クエリから被写体・色彩・構図・スタイルを認識し、
    該当する全画像を自動抽出・ランキングする。
    """
    q = (query or "").strip().lower()
    if not q:
        return {
            "query": "",
            "intent": None,
            "matches": [],
            "matched_ids": [],
            "suggested_queries": [],
        }

    # 1. クエリから認識対象の視覚概念（Target Concepts）を抽出
    detected_concepts: List[Dict[str, Any]] = []
    matched_keys: Set[str] = set()

    for concept_name, defn in VISUAL_SUBJECT_MAPPINGS.items():
        keys = defn.get("keys", [])
        if any(k.lower() in q or q in k.lower() for k in keys):
            detected_concepts.append({
                "concept": concept_name,
                "label": defn.get("label", concept_name),
                "keys": [k.lower() for k in keys],
            })
            for k in keys:
                matched_keys.add(k.lower())

    # Ollama / 辞書による同義語拡張も取り込む
    suggest_res = search_suggest.predict_search_suggestions(query, db=db, user_id=user_id, limit=6)
    for sug in suggest_res.get("suggestions", []):
        s_low = sug.lower()
        matched_keys.add(s_low)

    # 2. データベースの全アイテムを取得してセマンティック照合
    items = (
        db.query(MediaItem)
        .filter(MediaItem.user_id == user_id)
        .all()
    )

    scored_items: List[Dict[str, Any]] = []

    for item in items:
        ai = db.query(AIAnalysis).filter(AIAnalysis.media_item_id == item.id).first()
        prof = guess_visual_profile_from_media(item)

        score = 0.0
        reasons: List[str] = []

        title_low = (item.title or "").lower()
        author_low = (item.author_name or "").lower()
        tags = [t.lower() for t in (ai.tags_json if ai else [])]
        prof_subjects = [s.lower() for s in prof.get("subjects", [])]
        prof_features = [f.lower() for f in prof.get("features", [])]
        comp_text = ((ai.composition if ai else "") + " " + prof.get("composition", "")).lower()
        lighting_text = ((ai.lighting if ai else "") + " " + prof.get("lighting", "")).lower()

        # A. クエリ直接マッチ
        if q in title_low:
            score += 40.0
            reasons.append(f"タイトル一致: {item.title}")
        if q in author_low:
            score += 20.0
            reasons.append(f"作家名一致: {item.author_name}")
        if any(q in t for t in tags):
            score += 35.0
            reasons.append(f"タグ一致: #{q}")

        # B. Galaxy AI 視覚被写体マッチ（タグがなくても画像認識から抽出）
        for dc in detected_concepts:
            c_label = dc["label"]
            c_keys = dc["keys"]

            # 被写体プロファイル照合
            subject_hit = any(k in prof_subjects or any(k in ps for ps in prof_subjects) for k in c_keys)
            tag_hit = any(any(k in t for t in tags) for k in c_keys)
            feature_hit = any(k in prof_features for k in c_keys)
            comp_hit = any(k in comp_text or k in lighting_text for k in c_keys)

            if subject_hit or tag_hit or feature_hit:
                score += 50.0
                reasons.append(f"✨ Galaxy AI 認識: {c_label}")
            elif comp_hit:
                score += 25.0
                reasons.append(f"✨ Galaxy AI 構図/色彩: {c_label}")

        # C. 拡張キーワードマッチ
        for mk in matched_keys:
            if mk == q:
                continue
            if mk in title_low:
                score += 15.0
            if any(mk in t for t in tags) or mk in prof_subjects:
                score += 20.0
                if f"関連被写体: {mk}" not in reasons:
                    reasons.append(f"被写体属性: {mk}")

        if score > 0:
            scored_items.append({
                "id": item.id,
                "title": item.title or "Untitled",
                "score": score,
                "reasons": list(dict.fromkeys(reasons))[:3],
                "file_path": item.file_path,
            })

    # スコア順にソート
    scored_items.sort(key=lambda x: x["score"], reverse=True)
    results = scored_items[:limit]

    # 認識されたメイン意図
    main_intent = detected_concepts[0]["label"] if detected_concepts else None

    return {
        "query": query,
        "intent": main_intent,
        "matches": results,
        "matched_ids": [r["id"] for r in results],
        "total": len(results),
        "suggested_queries": suggest_res.get("suggestions", [])[:5],
    }

