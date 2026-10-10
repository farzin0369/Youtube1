from app.research import build_research_brief, parse_rss, rank_stories


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
