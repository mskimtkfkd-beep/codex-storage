from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Iterable

from .models import ActivityUpload, SubscriptionChannel, VideoDetails

LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeApiError(RuntimeError):
    pass


class YouTubeClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        session: Any | None = None,
        max_retries: int = 3,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.session = session or _new_requests_session()
        self.max_retries = max_retries
        self._access_token: str | None = None

    def refresh_access_token(self) -> str:
        response = self.session.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise YouTubeApiError(f"OAuth token refresh failed: {response.status_code} {response.text}")
        token = response.json().get("access_token")
        if not token:
            raise YouTubeApiError("OAuth token refresh response did not include access_token")
        self._access_token = token
        return token

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._access_token:
            self.refresh_access_token()

        url = f"{YOUTUBE_API_BASE}/{path}"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        for attempt in range(1, self.max_retries + 1):
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 401 and attempt == 1:
                self.refresh_access_token()
                headers = {"Authorization": f"Bearer {self._access_token}"}
                continue
            if response.status_code in {403, 429} or 500 <= response.status_code < 600:
                if attempt < self.max_retries:
                    sleep_seconds = 2 ** (attempt - 1)
                    LOGGER.warning(
                        "YouTube API retry path=%s status=%s attempt=%s sleep=%s",
                        path,
                        response.status_code,
                        attempt,
                        sleep_seconds,
                    )
                    time.sleep(sleep_seconds)
                    continue
            if response.status_code >= 400:
                raise YouTubeApiError(f"YouTube API error {path}: {response.status_code} {response.text}")
            return response.json()

        raise YouTubeApiError(f"YouTube API retry limit exceeded for {path}")

    def _paged_request(self, path: str, params: dict[str, Any]) -> Iterable[dict[str, Any]]:
        page_token: str | None = None
        while True:
            page_params = dict(params)
            if page_token:
                page_params["pageToken"] = page_token
            data = self._request(path, page_params)
            yield data
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    def list_subscriptions(self) -> list[SubscriptionChannel]:
        channels: list[SubscriptionChannel] = []
        params = {
            "part": "snippet",
            "mine": "true",
            "maxResults": 50,
        }
        for page in self._paged_request("subscriptions", params):
            for item in page.get("items", []):
                snippet = item.get("snippet", {})
                resource_id = snippet.get("resourceId", {})
                channel_id = resource_id.get("channelId")
                if not channel_id:
                    continue
                thumbnails = snippet.get("thumbnails", {})
                thumbnail_url = _best_thumbnail(thumbnails)
                channels.append(
                    SubscriptionChannel(
                        channel_id=channel_id,
                        title=snippet.get("title", ""),
                        description=snippet.get("description", ""),
                        thumbnail_url=thumbnail_url,
                    )
                )
        LOGGER.info("Fetched subscribed channels count=%s", len(channels))
        return channels

    def list_recent_upload_activities(
        self,
        channel: SubscriptionChannel,
        published_after: datetime,
    ) -> list[ActivityUpload]:
        params = {
            "part": "snippet,contentDetails",
            "channelId": channel.channel_id,
            "publishedAfter": _format_youtube_datetime(published_after),
            "maxResults": 50,
        }
        uploads: list[ActivityUpload] = []
        for page in self._paged_request("activities", params):
            for item in page.get("items", []):
                snippet = item.get("snippet", {})
                if snippet.get("type") != "upload":
                    continue
                video_id = (
                    item.get("contentDetails", {})
                    .get("upload", {})
                    .get("videoId")
                )
                if not video_id:
                    continue
                published_at = parse_youtube_datetime(snippet["publishedAt"])
                uploads.append(
                    ActivityUpload(
                        video_id=video_id,
                        channel_id=channel.channel_id,
                        channel_title=channel.title,
                        published_at=published_at,
                    )
                )
        LOGGER.info("Fetched upload activities channel=%s count=%s", channel.title, len(uploads))
        return uploads

    def get_videos(self, video_ids: list[str]) -> list[VideoDetails]:
        videos: list[VideoDetails] = []
        for batch in _chunks(_dedupe(video_ids), 50):
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(batch),
                "maxResults": 50,
            }
            data = self._request("videos", params)
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                thumbnails = snippet.get("thumbnails", {})
                video_id = item["id"]
                videos.append(
                    VideoDetails(
                        video_id=video_id,
                        title=snippet.get("title", ""),
                        description=snippet.get("description", ""),
                        channel_id=snippet.get("channelId", ""),
                        channel_title=snippet.get("channelTitle", ""),
                        published_at=parse_youtube_datetime(snippet["publishedAt"]),
                        thumbnail_url=_best_thumbnail(thumbnails),
                        duration=item.get("contentDetails", {}).get("duration", ""),
                        view_count=_parse_int(statistics.get("viewCount")),
                        url=f"https://www.youtube.com/watch?v={video_id}",
                    )
                )
        LOGGER.info("Fetched video details count=%s", len(videos))
        return videos


def parse_youtube_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _format_youtube_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _best_thumbnail(thumbnails: dict[str, Any]) -> str:
    for key in ("maxres", "standard", "high", "medium", "default"):
        url = thumbnails.get(key, {}).get("url")
        if url:
            return url
    return ""


def _parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _new_requests_session() -> Any:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("requests package is not installed. Run pip install -r requirements.txt") from exc
    return requests.Session()
