# YouTube Public Channel Digest

Configured public YouTube channels are checked on a rolling 24-hour window, classified by topic and value, summarized in Korean, and written to Google Sheets.

## Features

- Collects from channels listed in `config/channels.yaml`.
- Supports channel add/exclude by editing `enabled`.
- Stores channel-level `importance`, `default_topic`, and `summary_required`.
- Uses YouTube Data API key for public channel reads.
- Keeps manual runs through `python -m src.main --dry-run`.
- Keeps GitHub Actions scheduled runs and `workflow_dispatch` manual runs.
- Writes newest videos to Google Sheets with `videoId` duplicate suppression.

## Channel Config

Edit `config/channels.yaml`.

```yaml
channels:
  - id: UCxxxx
    title: CONNECT AI LAB
    enabled: true
    importance: high
    default_topic: AI/기술
    summary_required: true
```

Use YouTube channel IDs as the stable key. Set `enabled: false` to exclude a channel without deleting it.

## Environment

Required:

- `YOUTUBE_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_SPREADSHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`

Optional:

- `CHANNEL_CONFIG_PATH`: defaults to `config/channels.yaml`
- `GOOGLE_SHEET_NAME`: defaults to `__RUN_TIMESTAMP__`
- `ALLOW_RULE_BASED_CLASSIFIER=true`: local fallback without OpenAI
- `GOOGLE_SHEETS_REFRESH_TOKEN`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`: OAuth Sheets fallback

## Run Locally

```powershell
pip install -r requirements.txt
$env:YOUTUBE_API_KEY="your-api-key"
$env:OPENAI_API_KEY="your-openai-api-key"
$env:ALLOW_RULE_BASED_CLASSIFIER="true"
python -m src.main --dry-run
```

## GitHub Actions

`.github/workflows/daily-youtube-digest.yml` runs daily at 08:00 KST and can also be started manually with `Run workflow`.

Add these repository secrets:

- `YOUTUBE_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_SPREADSHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

## Sources

- YouTube Data API `channels.list`: https://developers.google.com/youtube/v3/docs/channels/list
- YouTube Data API `playlistItems.list`: https://developers.google.com/youtube/v3/docs/playlistItems/list
- YouTube Data API `videos.list`: https://developers.google.com/youtube/v3/docs/videos/list
- YouTube Data API quota: https://developers.google.com/youtube/v3/determine_quota_cost
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
