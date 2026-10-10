from app.channel_ops import _has_our_reply, _looks_like_spam


def test_short_sincere_comments_are_not_flagged_as_spam():
    assert not _looks_like_spam("آمین")
    assert not _looks_like_spam("ممنون از شما")
    assert not _looks_like_spam("خدا خیرتان بدهد")


def test_obvious_promotion_and_multiple_links_are_flagged():
    assert _looks_like_spam("subscribe my channel")
    assert _looks_like_spam("visit https://one.example and https://two.example")


def test_existing_reply_by_our_channel_is_detected():
    thread = {
        "replies": {
            "comments": [
                {"snippet": {"authorChannelId": {"value": "other"}}},
                {"snippet": {"authorChannelId": {"value": "our-channel"}}},
            ]
        }
    }
    assert _has_our_reply(thread, "our-channel")
    assert not _has_our_reply(thread, "different-channel")
