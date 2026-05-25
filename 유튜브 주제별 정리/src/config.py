from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import TrackedChannel


DEFAULT_TOPIC = "기타"


@dataclass(frozen=True)
class TopicConfig:
    topics: list[str]
    keyword_map: dict[str, list[str]]
    include_topics: list[str]
    tracked_channels: list[str]
    channel_topic_map: dict[str, str]


@dataclass(frozen=True)
class AppConfig:
    youtube_api_key: str
    youtube_client_id: str | None
    youtube_client_secret: str | None
    youtube_refresh_token: str | None
    openai_api_key: str | None
    google_spreadsheet_id: str
    google_sheet_name: str
    google_service_account_json: str | None
    google_application_credentials: str | None
    google_sheets_refresh_token: str | None
    topic_config: TopicConfig
    channels: list[TrackedChannel]
    allow_rule_based_classifier: bool = False


def load_topic_config(path: str | Path = "config/topics.yaml") -> TopicConfig:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML package is not installed. Run pip install -r requirements.txt") from exc

    with Path(path).open("r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    topics = [str(topic) for topic in data.get("topics", [])]
    include_topics = [str(topic) for topic in data.get("include_topics", topics)]
    tracked_channels = [str(channel) for channel in data.get("tracked_channels", [])]
    channel_topic_map = {
        str(channel): str(topic)
        for channel, topic in (data.get("channel_topic_map", {}) or {}).items()
    }
    schema_topics = list(dict.fromkeys([*topics, DEFAULT_TOPIC]))

    raw_keyword_map = data.get("keyword_map", {})
    keyword_map = {
        str(topic): [str(keyword).lower() for keyword in keywords]
        for topic, keywords in raw_keyword_map.items()
    }
    return TopicConfig(
        topics=schema_topics,
        keyword_map=keyword_map,
        include_topics=include_topics,
        tracked_channels=tracked_channels,
        channel_topic_map=channel_topic_map,
    )


def load_channel_config(path: str | Path = "config/channels.yaml") -> list[TrackedChannel]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML package is not installed. Run pip install -r requirements.txt") from exc

    config_path = Path(path)
    if not config_path.exists():
        raise RuntimeError(f"Channel config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    raw_channels = data.get("channels", [])
    if not isinstance(raw_channels, list):
        raise RuntimeError("channels must be a list")

    channels: list[TrackedChannel] = []
    for index, raw_channel in enumerate(raw_channels):
        if not isinstance(raw_channel, dict):
            raise RuntimeError(f"channels[{index}] must be a mapping")
        if raw_channel.get("enabled", True) is False:
            continue

        channel_id = str(raw_channel.get("id") or "").strip()
        if not channel_id:
            raise RuntimeError(f"Missing required channel config value: channels[{index}].id")

        channels.append(
            TrackedChannel(
                channel_id=channel_id,
                title=str(raw_channel.get("title") or channel_id).strip(),
                importance=str(raw_channel.get("importance") or "medium").strip().lower(),
                default_topic=str(raw_channel.get("default_topic") or DEFAULT_TOPIC).strip(),
                summary_required=bool(raw_channel.get("summary_required", True)),
            )
        )
    return channels


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_app_config(
    topic_path: str | Path = "config/topics.yaml",
    channel_path: str | Path | None = None,
) -> AppConfig:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    allow_rule_based = _bool_env("ALLOW_RULE_BASED_CLASSIFIER", default=False)
    if not openai_api_key and not allow_rule_based:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Set ALLOW_RULE_BASED_CLASSIFIER=true only for local dry runs."
        )

    resolved_channel_path = channel_path or os.getenv("CHANNEL_CONFIG_PATH", "config/channels.yaml")

    return AppConfig(
        youtube_api_key=_required_env("YOUTUBE_API_KEY"),
        youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID"),
        youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
        youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
        openai_api_key=openai_api_key,
        google_spreadsheet_id=os.getenv("GOOGLE_SPREADSHEET_ID", ""),
        google_sheet_name=os.getenv("GOOGLE_SHEET_NAME", "__RUN_TIMESTAMP__"),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        google_application_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        google_sheets_refresh_token=os.getenv("GOOGLE_SHEETS_REFRESH_TOKEN") or os.getenv("YOUTUBE_REFRESH_TOKEN"),
        topic_config=load_topic_config(topic_path),
        channels=load_channel_config(resolved_channel_path),
        allow_rule_based_classifier=allow_rule_based,
    )
