from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict

from .classifier import VideoClassifier
from .collector import collect_recent_videos
from .config import load_app_config
from .sheets_writer import GoogleSheetsWriter
from .youtube_client import YouTubeClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a YouTube subscription digest.")
    parser.add_argument("--dry-run", action="store_true", help="Print classified videos instead of writing Sheets.")
    parser.add_argument("--topic-config", default="config/topics.yaml")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    config = load_app_config(args.topic_config)

    youtube_client = YouTubeClient(
        client_id=config.youtube_client_id,
        client_secret=config.youtube_client_secret,
        refresh_token=config.youtube_refresh_token,
    )
    videos = collect_recent_videos(
        youtube_client,
        tracked_channels=config.topic_config.tracked_channels,
    )

    classifier = VideoClassifier(
        topic_config=config.topic_config,
        openai_api_key=config.openai_api_key,
        allow_rule_based_fallback=config.allow_rule_based_classifier,
    )
    classified = classifier.classify_many(videos)

    if args.dry_run:
        print(json.dumps([asdict(item) for item in classified], ensure_ascii=False, default=str, indent=2))
        return 0

    if not config.google_spreadsheet_id:
        raise RuntimeError("Missing required environment variable: GOOGLE_SPREADSHEET_ID")

    writer = GoogleSheetsWriter(
        spreadsheet_id=config.google_spreadsheet_id,
        sheet_name=config.google_sheet_name,
        service_account_json=config.google_service_account_json,
        application_credentials=config.google_application_credentials,
        oauth_client_id=config.youtube_client_id,
        oauth_client_secret=config.youtube_client_secret,
        oauth_refresh_token=config.google_sheets_refresh_token,
    )
    writer.write_digest(classified)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
