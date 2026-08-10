#!/usr/bin/env python3
"""
収集層(①): WEB/SNSから堺・大阪の事故対応/鈑金/旧車・アメ車のトレンド情報を収集する。
GitHub Actions (collect.yml) から毎朝実行される想定。

ソース:
  - Googleニュース RSS (キーワード別・無料)
  - はてなブックマーク ホットエントリRSS (無料)
  - YouTube Data API v3 (環境変数 YOUTUBE_API_KEY があれば・無料枠)

出力: data/raw/YYYY-MM-DD.json
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST).strftime("%Y-%m-%d")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

# 監視キーワード(CLAUDE.md の編集方針と同期させること)
NEWS_QUERIES = [
    "堺 交通",
    "レッカー",
    "板金塗装",
    "旧車",
    "アメ車",
    "車検 費用",
    "自動車保険 制度",
    "中古車 相場",
]
HATENA_FEEDS = [
    "https://b.hatena.ne.jp/search/text?q=%E6%97%A7%E8%BB%8A&mode=rss",
    "https://b.hatena.ne.jp/search/text?q=%E4%BA%A4%E9%80%9A%E4%BA%8B%E6%95%85%20%E5%AF%BE%E5%BF%9C&mode=rss",
]
YOUTUBE_QUERIES = ["アメ車 レストア", "旧車 メンテナンス", "事故 対処 車"]

UA = "Mozilla/5.0 (compatible; PalmsBlogCollector/1.0)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def parse_rss(xml_bytes: bytes, source: str, query: str) -> list[dict]:
    """RSS2.0 / RSS1.0(RDF) 両対応の素朴なパーサー"""
    items = []
    root = ET.fromstring(xml_bytes)
    ns = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rss1": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "hatena": "http://www.hatena.ne.jp/info/xmlns#",
    }
    # RSS 2.0
    for item in root.iter("item"):
        title = item.findtext("title") or item.findtext("rss1:title", namespaces=ns) or ""
        link = item.findtext("link") or item.findtext("rss1:link", namespaces=ns) or ""
        pub = (
            item.findtext("pubDate")
            or item.findtext("dc:date", namespaces=ns)
            or ""
        )
        bookmarks = item.findtext("hatena:bookmarkcount", namespaces=ns)
        if not title:
            continue
        entry = {
            "source": source,
            "query": query,
            "title": title.strip(),
            "url": link.strip(),
            "published": pub.strip(),
        }
        if bookmarks is not None:
            entry["engagement"] = {"bookmarks": int(bookmarks)}
        items.append(entry)
    return items


def collect_google_news() -> list[dict]:
    out = []
    for q in NEWS_QUERIES:
        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote(f"{q} when:2d")
            + "&hl=ja&gl=JP&ceid=JP:ja"
        )
        try:
            out += parse_rss(fetch(url), "google_news", q)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] google_news '{q}': {e}", file=sys.stderr)
    return out


def collect_hatena() -> list[dict]:
    out = []
    for url in HATENA_FEEDS:
        try:
            out += parse_rss(fetch(url), "hatena", url)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] hatena: {e}", file=sys.stderr)
    return out


def collect_youtube() -> list[dict]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("[info] YOUTUBE_API_KEY 未設定のためYouTube収集をスキップ")
        return []
    out = []
    for q in YOUTUBE_QUERIES:
        try:
            search_url = (
                "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video"
                f"&order=viewCount&publishedAfter={_days_ago_iso(7)}"
                f"&q={urllib.parse.quote(q)}&maxResults=10&key={api_key}"
            )
            data = json.loads(fetch(search_url))
            video_ids = [it["id"]["videoId"] for it in data.get("items", [])]
            if not video_ids:
                continue
            stats_url = (
                "https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet"
                f"&id={','.join(video_ids)}&key={api_key}"
            )
            stats = json.loads(fetch(stats_url))
            for v in stats.get("items", []):
                s = v.get("statistics", {})
                sn = v.get("snippet", {})
                out.append(
                    {
                        "source": "youtube",
                        "query": q,
                        "title": sn.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={v['id']}",
                        "published": sn.get("publishedAt", ""),
                        "engagement": {
                            "views": int(s.get("viewCount", 0)),
                            "likes": int(s.get("likeCount", 0)),
                            "comments": int(s.get("commentCount", 0)),
                        },
                    }
                )
        except Exception as e:  # noqa: BLE001
            print(f"[warn] youtube '{q}': {e}", file=sys.stderr)
    return out


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def main() -> None:
    items = collect_google_news() + collect_hatena() + collect_youtube()
    # URL重複排除
    seen: set[str] = set()
    deduped = []
    for it in items:
        key = it.get("url") or it.get("title")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"{TODAY}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"collected_at": datetime.now(JST).isoformat(), "items": deduped},
            f,
            ensure_ascii=False,
            indent=1,
        )
    print(f"collected {len(deduped)} items -> {out_path}")


if __name__ == "__main__":
    main()
