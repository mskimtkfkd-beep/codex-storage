from __future__ import annotations

import pytest

from src.config import load_channel_config


def test_load_channel_config_returns_enabled_channels_with_metadata(tmp_path) -> None:
    path = tmp_path / "channels.yaml"
    path.write_text(
        """
channels:
  - id: UC111
    title: AI Channel
    enabled: true
    importance: high
    default_topic: AI/기술
    summary_required: true
  - id: UC222
    title: Disabled Channel
    enabled: false
    importance: low
    default_topic: 경제/재테크
    summary_required: false
""",
        encoding="utf-8",
    )

    channels = load_channel_config(path)

    assert len(channels) == 1
    assert channels[0].channel_id == "UC111"
    assert channels[0].title == "AI Channel"
    assert channels[0].importance == "high"
    assert channels[0].default_topic == "AI/기술"
    assert channels[0].summary_required is True


def test_load_channel_config_rejects_missing_channel_id(tmp_path) -> None:
    path = tmp_path / "channels.yaml"
    path.write_text(
        """
channels:
  - title: Missing ID
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="channels\\[0\\].id"):
        load_channel_config(path)
