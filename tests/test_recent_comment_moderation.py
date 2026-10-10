from app import channel_ops


class _Request:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _Resource:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return _Request(self.payload)


class _FakeYouTube:
    def __init__(self):
        self.channels_resource = _Resource({"items": [{
            "contentDetails": {"relatedPlaylists": {"uploads": "uploads-id"}}
        }]})
        self.playlist_resource = _Resource({"items": [
            {"contentDetails": {"videoId": "private-video"}},
            {"contentDetails": {"videoId": "public-video"}},
            {"contentDetails": {"videoId": "unlisted-video"}},
        ]})
        self.videos_resource = _Resource({"items": [
            {"id": "private-video", "status": {"privacyStatus": "private"}},
            {"id": "public-video", "status": {"privacyStatus": "public"}},
            {"id": "unlisted-video", "status": {"privacyStatus": "unlisted"}},
        ]})

    def channels(self):
        return self.channels_resource

    def playlistItems(self):
        return self.playlist_resource

    def videos(self):
        return self.videos_resource


def test_recent_comment_moderation_skips_private_videos(monkeypatch):
    fake = _FakeYouTube()
    replied_to = []
    monkeypatch.setattr(channel_ops, "_youtube", lambda: fake)
    monkeypatch.setattr(
        channel_ops,
        "reply_to_comments",
        lambda video_id, max_comments=10: (replied_to.append(video_id) or {"ok": True, "replied": 1}),
    )
    result = channel_ops.reply_to_recent_comments(max_videos=3, max_comments_per_video=7)
    assert result["ok"]
    assert result["videos_checked"] == 2
    assert result["videos_skipped_private"] == 1
    assert replied_to == ["public-video", "unlisted-video"]
