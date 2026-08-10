#!/usr/bin/env python3
"""
スコアリング層(②): data/raw/YYYY-MM-DD.json のネタを点数化し、
上位候補を data/scored/YYYY-MM-DD.json に出力する。

スコア重みは data/scoring-weights.json で管理し、
週次のFABLE分析セッションで更新する(=学習ループの実体)。

テーマ適合度の最終判断・採否は editor エージェント(OPUS)が行うため、
ここでは機械的に計算できる指標のみ扱う。
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timezone, timedelta

BASE = os.path.join(os.path.dirname(__file__), "..")
JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST).strftime("%Y-%m-%d")

DEFAULT_WEIGHTS = {
    "recency": 0.30,       # 鮮度(伸び率の代理指標)
    "engagement": 0.20,    # 反応量(ブクマ/再生/いいね)
    "keyword_hit": 0.20,   # 重要キーワード合致
    "theme_fit": 0.20,     # テーマ適合度(機械判定の仮値。最終判断はeditor)
    "novelty": 0.10,       # 既出でないか(過去候補との重複)
}

# CLAUDE.mdの編集方針と同期させるキーワード辞書
PRIORITY_KEYWORDS = {
    "high": ["レッカー", "事故", "板金", "堺", "旧車", "アメ車"],
    "mid": ["保険", "代車", "車検", "修理", "中古車", "大阪", "レストア"],
    "theme": ["車"],
}
EXCLUDE_PATTERNS = [
    r"求人", r"採用", r"株価", r"パチンコ", r"事件", r"事故.*死亡",
    r"死亡", r"ひき逃げ", r"飲酒運転.*逮捕",
    # 同業他社の店舗動向は扱わない(商圏バッティング回避・トピック集中のため)
    r"グランドオープン", r"オープン", r"開店", r"出店", r"新店舗", r"移転オープン",
    r"キャンペーン", r"セール", r"フェア", r"来店特典", r"支店", r"○周年",
]


def load_weights() -> dict:
    path = os.path.join(BASE, "data", "scoring-weights.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_WEIGHTS


def recency_score(published: str) -> float:
    """公開からの経過時間で減衰(48hで0)"""
    if not published:
        return 0.3
    try:
        from email.utils import parsedate_to_datetime

        try:
            dt = parsedate_to_datetime(published)
        except (TypeError, ValueError):
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return max(0.0, 1.0 - hours / 48.0)
    except Exception:  # noqa: BLE001
        return 0.3


def engagement_score(item: dict) -> float:
    e = item.get("engagement", {})
    raw = (
        e.get("bookmarks", 0) * 5
        + e.get("views", 0) / 1000
        + e.get("likes", 0) / 10
        + e.get("comments", 0)
    )
    return min(1.0, math.log10(raw + 1) / 3)  # 1000ポイントで満点


def keyword_score(title: str) -> float:
    score = 0.0
    for kw in PRIORITY_KEYWORDS["high"]:
        if kw in title:
            score += 0.5
    for kw in PRIORITY_KEYWORDS["mid"]:
        if kw in title:
            score += 0.25
    return min(1.0, score)


def theme_fit_score(title: str) -> float:
    if any(re.search(p, title) for p in EXCLUDE_PATTERNS):
        return 0.0
    return 1.0 if any(kw in title for kw in PRIORITY_KEYWORDS["theme"]) else 0.4


def novelty_score(title: str, past_titles: set[str]) -> float:
    words = set(re.findall(r"[\w一-龠ぁ-んァ-ヶー]+", title))
    for past in past_titles:
        past_words = set(re.findall(r"[\w一-龠ぁ-んァ-ヶー]+", past))
        if words and len(words & past_words) / len(words) > 0.6:
            return 0.0
    return 1.0


def load_past_titles(days: int = 14) -> set[str]:
    titles: set[str] = set()
    scored_dir = os.path.join(BASE, "data", "scored")
    if not os.path.isdir(scored_dir):
        return titles
    for fname in sorted(os.listdir(scored_dir))[-days:]:
        try:
            with open(os.path.join(scored_dir, fname), encoding="utf-8") as f:
                for it in json.load(f).get("candidates", []):
                    titles.add(it["title"])
        except Exception:  # noqa: BLE001
            continue
    return titles


def main() -> None:
    date = sys.argv[1] if len(sys.argv) > 1 else TODAY
    raw_path = os.path.join(BASE, "data", "raw", f"{date}.json")
    if not os.path.exists(raw_path):
        sys.exit(f"raw data not found: {raw_path}")

    with open(raw_path, encoding="utf-8") as f:
        items = json.load(f)["items"]

    weights = load_weights()
    past_titles = load_past_titles()

    for it in items:
        title = it["title"]
        parts = {
            "recency": recency_score(it.get("published", "")),
            "engagement": engagement_score(it),
            "keyword_hit": keyword_score(title),
            "theme_fit": theme_fit_score(title),
            "novelty": novelty_score(title, past_titles),
        }
        it["score_parts"] = {k: round(v, 3) for k, v in parts.items()}
        if parts["theme_fit"] == 0.0:
            # 除外パターン該当は問答無用で落とす(専門性の希釈防止)
            it["score"] = 0.0
        else:
            it["score"] = round(
                sum(parts[k] * weights[k] for k in weights if k in parts), 3
            )

    items.sort(key=lambda x: x["score"], reverse=True)
    threshold = weights.get("threshold", 0.35)
    candidates = [it for it in items if it["score"] >= threshold][:15]

    out_dir = os.path.join(BASE, "data", "scored")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": date,
                "weights": weights,
                "total_items": len(items),
                "candidates": candidates,
            },
            f,
            ensure_ascii=False,
            indent=1,
        )
    print(f"scored {len(items)} items, {len(candidates)} candidates -> {out_path}")


if __name__ == "__main__":
    main()
