from __future__ import annotations

from datetime import datetime, timezone

from src.models import TrackedChannel
from src.youtube_client import YouTubeClient


def test_paged_request_follows_next_page_token() -> None:
    session = FakeSession(
        [
            {"access_token": "token"},
            {"items": [{"snippet": subscription_snippet("c1")}], "nextPageToken": "next"},
            {"items": [{"snippet": subscription_snippet("c2")}]},
        ]
    )
    client = YouTubeClient("id", "secret", "refresh", session=session)

    channels = client.list_subscriptions()

    assert [channel.channel_id for channel in channels] == ["c1", "c2"]


def test_api_key_request_adds_key_without_oauth_refresh() -> None:
    session = FakeSession(
        [
            {
                "items": [
                    {
                        "id": "UC111",
                        "snippet": {"title": "Channel 111"},
                        "contentDetails": {"relatedPlaylists": {"uploads": "UU111"}},
                    }
                ]
            }
        ]
    )
    client = YouTubeClient(api_key="api-key", session=session)

    playlist_id = client.get_upload_playlist_id(TrackedChannel(channel_id="UC111", title="Configured"))

    assert playlist_id == "UU111"
    assert session.posts == []
    assert session.gets[0]["params"]["key"] == "api-key"


def test_list_recent_playlist_uploads_follows_pages_and_filters_cutoff() -> None:
    cutoff = datetime(2026, 5, 24, 8, 0, tzinfo=timezone.utc)
    session = FakeSession(
        [
            {
                "items": [
                    playlist_item("new", "2026-05-24T08:00:00Z"),
                    playlist_item("old", "2026-05-24T07:59:59Z"),
                ],
                "nextPageToken": "next",
            },
            {"items": [playlist_item("newer", "2026-05-24T09:00:00Z")]},
        ]
    )
    channel = TrackedChannel(channel_id="UC111", title="Configured")
    client = YouTubeClient(api_key="api-key", session=session)

    uploads = client.list_recent_playlist_uploads(channel, "UU111", cutoff)

    assert [upload.video_id for upload in uploads] == ["new", "newer"]
    assert session.gets[1]["params"]["pageToken"] == "next"


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads
        self.posts: list[dict] = []
        self.gets: list[dict] = []

    def post(self, *args, **kwargs) -> FakeResponse:
        self.posts.append({"args": args, "kwargs": kwargs})
        return FakeResponse(self.payloads.pop(0))

    def get(self, *args, **kwargs) -> FakeResponse:
        self.gets.append({"args": args, "kwargs": kwargs, "params": kwargs.get("params", {})})
        return FakeResponse(self.payloads.pop(0))


def subscription_snippet(channel_id: str) -> dict:
    return {
        "title": f"Channel {channel_id}",
        "description": "",
        "resourceId": {"channelId": channel_id},
        "thumbnails": {"default": {"url": "https://example.com/thumb.jpg"}},
    }


def playlist_item(video_id: str, published_at: str) -> dict:
    return {
        "snippet": {
            "publishedAt": published_at,
            "resourceId": {"videoId": video_id},
        }
    }
