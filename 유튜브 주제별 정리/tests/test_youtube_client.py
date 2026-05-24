from __future__ import annotations

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

    def post(self, *args, **kwargs) -> FakeResponse:
        return FakeResponse(self.payloads.pop(0))

    def get(self, *args, **kwargs) -> FakeResponse:
        return FakeResponse(self.payloads.pop(0))


def subscription_snippet(channel_id: str) -> dict:
    return {
        "title": f"Channel {channel_id}",
        "description": "",
        "resourceId": {"channelId": channel_id},
        "thumbnails": {"default": {"url": "https://example.com/thumb.jpg"}},
    }

