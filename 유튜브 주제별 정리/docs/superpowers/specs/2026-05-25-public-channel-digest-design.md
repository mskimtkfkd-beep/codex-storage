# Public Channel Digest Design

## Decision

The first version will collect recent videos from a manually maintained public channel list instead of reading the authenticated user's YouTube subscriptions. Channel add and exclude operations will be done by editing a repository config file.

## Goals

- Collect videos uploaded within the last 24 hours from configured public YouTube channels.
- Support both scheduled runs and irregular manual runs.
- Keep channel management simple for the first version.
- Store channel-level importance, default topic, and summary requirement.
- Preserve the existing digest output direction: topic grouping, newest-first ordering, thumbnails, Korean summary, and value/priority classification.

## Non-Goals

- No UI for managing channels in the first version.
- No command-line `channels add` or `channels remove` workflow in the first version.
- No authenticated YouTube subscription lookup in the new default path.
- No scraping of YouTube web pages as the primary collection path.

## Configuration

Add a new `config/channels.yaml` file. Each channel entry will include:

- `id`: YouTube channel ID.
- `title`: human-readable channel title.
- `enabled`: whether the channel is included in collection.
- `importance`: channel-level priority such as `high`, `medium`, or `low`.
- `default_topic`: fallback topic when classifier confidence is low or no better topic is found.
- `summary_required`: whether the video should receive a Korean summary.

Example:

```yaml
channels:
  - id: UCxxxx
    title: CONNECT AI LAB
    enabled: true
    importance: high
    default_topic: AI/기술
    summary_required: true
```

## Data Flow

1. Load topic rules from `config/topics.yaml`.
2. Load tracked public channels from `config/channels.yaml`.
3. Ignore channels where `enabled` is false.
4. For each enabled channel, retrieve the channel upload playlist ID through the YouTube Data API.
5. Read recent playlist items from the upload playlist.
6. Keep only videos where `publishedAt` is within the rolling 24-hour window.
7. Enrich video metadata with `videos.list`.
8. Classify topic and priority using the existing classifier, with channel metadata available as defaults.
9. Write the digest to Google Sheets, preserving duplicate suppression by `videoId`.

## Execution

Scheduled execution will use GitHub Actions `schedule` at the chosen daily time. Manual execution will use GitHub Actions `workflow_dispatch`. Local manual testing remains available through the existing dry-run mode.

## Error Handling

- Missing or malformed `config/channels.yaml` should fail with a clear message.
- Disabled channels should be skipped silently.
- Unknown channel IDs should log a warning and continue with the remaining channels.
- API failures should keep the current retry behavior.
- If a channel has no videos in the 24-hour window, it should not create empty rows.

## Testing

- Add config parsing tests for channel entries, disabled channels, and required fields.
- Add collector tests proving it uses configured channels instead of subscriptions.
- Add YouTube client tests for channel upload playlist lookup and playlist item pagination.
- Keep existing cutoff and newest-first behavior tests.

