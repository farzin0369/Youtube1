from app.research import build_research_brief, is_iran_related, parse_rss, pick_topic, rank_stories


def test_parse_rss_keeps_source_link_publisher_and_timestamp():
    xml = b"""<?xml version="1.0"?>
    <rss><channel><item>
      <title>Global climate agreement announced</title>
      <link>https://example.com/world/climate</link>
      <description><![CDATA[Officials announced a new framework &amp; timeline.]]></description>
      <pubDate>Sat, 10 Oct 2026 12:00:00 GMT</pubDate>
      <source url="https://example.com">Example News</source>
    </item></channel></rss>"""
    stories = parse_rss(xml, "world", "https://feeds.example.com/world.xml")
    assert len(stories) == 1
    assert stories[0]["url"] == "https://example.com/world/climate"
    assert stories[0]["publisher"] == "Example News"
    assert stories[0]["published_at"].startswith("2026-10-10T12:00:00")
    assert "timeline" in stories[0]["description"]


def test_rank_stories_limits_five_and_spreads_categories():
    stories = [
        {"title": f"Story {i}", "url": f"https://example.com/{i}", "category": category}
        for i, category in enumerate(["world", "world", "technology", "business", "science", "sports", "health"])
    ]
    ranked = rank_stories(stories, limit=5)
    assert len(ranked) == 5
    assert len({story["category"] for story in ranked[:5]}) >= 4
    assert all(story["url"].startswith("https://") for story in ranked)


def test_research_brief_refuses_items_without_source_links():
    try:
        build_research_brief({"stories": []})
    except RuntimeError as exc:
        assert "source-linked" in str(exc)
    else:
        raise AssertionError("brief must not be created without linked sources")


def test_iran_relevance_accepts_english_and_persian_but_rejects_unrelated_news():
    assert is_iran_related({"title": "Iran and EU discuss nuclear deal"})
    assert is_iran_related({"title": "خبر تازه دربارهٔ تهران"})
    assert is_iran_related({"title": "Shipping disrupted in the Strait of Hormuz"})
    assert not is_iran_related({"title": "Hurricane Simon hits Mexico"})


def test_pick_topic_uses_prefetched_news_without_network(tmp_path, monkeypatch):
    import json
    import app.research as research

    stories = [
        {"id": "1", "title": "Iran and EU discuss nuclear deal", "url": "https://example.com/iran", "publisher": "World News", "category": "iran_world", "category_fa": "ایران و جهان", "published_at": "2026-10-10T12:00:00+00:00", "description": "A report on Iran."},
        {"id": "2", "title": "خبر تازه درباره تهران", "url": "https://example.com/tehran", "publisher": "Tech News", "category": "iran_fa", "category_fa": "ایران", "published_at": "2026-10-10T11:00:00+00:00", "description": "گزارش درباره ایران."},
        {"id": "3", "title": "Shipping disrupted in Strait of Hormuz", "url": "https://example.com/hormuz", "publisher": "Business News", "category": "iran_world", "category_fa": "ایران و جهان", "published_at": "2026-10-10T10:00:00+00:00", "description": "A shipping report."},
        {"id": "4", "title": "Hurricane Simon hits Mexico", "url": "https://example.com/mexico", "publisher": "World News", "category": "world", "category_fa": "جهان", "published_at": "2026-10-10T09:00:00+00:00", "description": "Unrelated news."},
    ]
    path = tmp_path / "news.json"
    path.write_text(json.dumps({"stories": stories}), encoding="utf-8")
    monkeypatch.setattr(research, "env", lambda key: str(path) if key == "TT_KHABAR_NEWS_FILE" else None)
    monkeypatch.setattr(research, "fetch_news", lambda: (_ for _ in ()).throw(AssertionError("network fetch must not run")))
    topic = pick_topic("long")
    assert len(topic["stories"]) == 3
    assert topic["source_type"] == "current_news_rss"
    assert all(is_iran_related(story) for story in topic["stories"])
