#!/usr/bin/env python3
"""ネットワーク不要のローカルテスト: RSSパーサーとスコアリングを検証する。"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from collect import parse_rss  # noqa: E402
import score  # noqa: E402

RSS2_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>t</title>
<item><title>堺市で事故が急増、レッカー需要と板金塗装の相場が話題に</title>
<link>https://example.com/a</link>
<pubDate>{recent}</pubDate></item>
<item><title>無関係な株価ニュース</title>
<link>https://example.com/b</link>
<pubDate>{recent}</pubDate></item>
</channel></rss>"""

RDF_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns="http://purl.org/rss/1.0/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:hatena="http://www.hatena.ne.jp/info/xmlns#">
<item rdf:about="https://example.com/c">
<title>旧車 アメ車の維持費に関する新常識</title>
<link>https://example.com/c</link>
<dc:date>2026-07-21T00:00:00+09:00</dc:date>
<hatena:bookmarkcount>120</hatena:bookmarkcount>
</item>
</rdf:RDF>"""


def test_rss2():
    recent = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    items = parse_rss(RSS2_SAMPLE.format(recent=recent).encode(), "google_news", "堺 交通")
    assert len(items) == 2, items
    assert items[0]["title"].startswith("堺市"), items[0]
    print("  ok: RSS2.0 parse")
    return items


def test_rdf():
    # RSS1.0(RDF)形式: 名前空間付きitem
    import xml.etree.ElementTree as ET
    root = ET.fromstring(RDF_SAMPLE.encode())
    ns_items = root.findall("{http://purl.org/rss/1.0/}item")
    assert len(ns_items) == 1
    print("  ok: RDF structure detected (hatena feed)")


def test_scoring(items):
    # raw ファイルを作ってscore.pyのmainを通す
    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = os.path.join(tmp, "data", "raw")
        os.makedirs(raw_dir)
        date = "2099-01-01"
        items[0]["engagement"] = {"bookmarks": 200}
        with open(os.path.join(raw_dir, f"{date}.json"), "w", encoding="utf-8") as f:
            json.dump({"collected_at": "", "items": items}, f, ensure_ascii=False)
        score.BASE = tmp
        sys.argv = ["score.py", date]
        score.main()
        with open(os.path.join(tmp, "data", "scored", f"{date}.json"), encoding="utf-8") as f:
            result = json.load(f)
    cands = result["candidates"]
    assert cands, "候補が0件"
    assert cands[0]["title"].startswith("堺市"), cands
    titles = [c["title"] for c in cands]
    assert "無関係な株価ニュース" not in titles, "除外パターンが効いていない"
    print(f"  ok: scoring (top='{cands[0]['title']}' score={cands[0]['score']})")


if __name__ == "__main__":
    print("running pipeline tests...")
    items = test_rss2()
    test_rdf()
    test_scoring(items)
    print("all tests passed")
