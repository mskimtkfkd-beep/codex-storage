# Public Channel Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect recent YouTube videos from a manually maintained public channel list with channel-level importance, default topic, and summary settings.

**Architecture:** Add a focused channel config model and parser, switch collection from authenticated subscriptions to configured channels, and add public YouTube API methods for upload playlist lookup and playlist item retrieval. Keep the classifier and Sheets writer behavior intact while feeding them richer channel metadata.

**Tech Stack:** Python, PyYAML, pytest, YouTube Data API, GitHub Actions.

---

### Task 1: Channel Config

**Files:**
- Modify: `src/models.py`
- Modify: `src/config.py`
- Create: `config/channels.yaml`
- Test: `tests/test_config.py`

- [ ] Write failing tests for loading enabled channels and rejecting missing IDs.
- [ ] Run `pytest tests/test_config.py -v` and confirm the new tests fail.
- [ ] Add `TrackedChannel` and channel config parsing.
- [ ] Run `pytest tests/test_config.py -v` and confirm the tests pass.

### Task 2: Public YouTube Client

**Files:**
- Modify: `src/youtube_client.py`
- Test: `tests/test_youtube_client.py`

- [ ] Write failing tests for API-key requests, upload playlist lookup, and playlist item pagination.
- [ ] Run `pytest tests/test_youtube_client.py -v` and confirm the new tests fail.
- [ ] Add API-key support plus `get_upload_playlist_id` and `list_recent_playlist_uploads`.
- [ ] Run `pytest tests/test_youtube_client.py -v` and confirm the tests pass.

### Task 3: Collector Switch

**Files:**
- Modify: `src/collector.py`
- Modify: `src/main.py`
- Test: `tests/test_collector.py`

- [ ] Write failing tests proving collection uses configured channels and ignores disabled channels.
- [ ] Run `pytest tests/test_collector.py -v` and confirm the new tests fail.
- [ ] Update collection to use `TrackedChannel` entries.
- [ ] Run `pytest tests/test_collector.py -v` and confirm the tests pass.

### Task 4: Workflow And Docs

**Files:**
- Modify: `.env.example`
- Create or modify: `.github/workflows/daily-youtube-digest.yml`
- Modify: `README.md`

- [ ] Add `YOUTUBE_API_KEY` and `CHANNEL_CONFIG_PATH` documentation.
- [ ] Add scheduled and manual GitHub Actions triggers.
- [ ] Run the full test suite with `pytest -v`.

