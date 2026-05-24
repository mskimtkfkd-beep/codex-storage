from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from .models import ClassifiedVideo

LOGGER = logging.getLogger(__name__)
FIRST_SHEET = "__FIRST_SHEET__"
RUN_TIMESTAMP_SHEET = "__RUN_TIMESTAMP__"
KST = timezone(timedelta(hours=9), name="KST")

HEADERS = [
    "수집일시",
    "게시일시",
    "주제",
    "세부주제",
    "채널명",
    "제목",
    "썸네일URL",
    "영상URL",
    "요약",
    "가치구분",
    "볼가치",
    "키워드",
    "영상길이",
    "조회수",
    "videoId",
]


class GoogleSheetsWriter:
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        service_account_json: str | None = None,
        application_credentials: str | None = None,
        oauth_client_id: str | None = None,
        oauth_client_secret: str | None = None,
        oauth_refresh_token: str | None = None,
        retention_days: int = 7,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.service_account_json = service_account_json
        self.application_credentials = application_credentials
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.oauth_refresh_token = oauth_refresh_token
        self.retention_days = retention_days
        self.service = self._build_service()
        self.sheet_name = self._resolve_sheet_name(sheet_name)

    def write_digest(self, videos: list[ClassifiedVideo]) -> int:
        self.delete_expired_run_sheets()
        self._ensure_header()
        self._ensure_basic_filter()
        existing_ids = self._existing_video_ids()
        rows = [
            self._row(video)
            for video in _sort_for_sheet(videos)
            if video.video.video_id not in existing_ids
        ]
        if not rows:
            LOGGER.info("No new rows to append to Google Sheets")
            return 0

        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_name}'!A:O",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
        LOGGER.info("Appended Google Sheets rows count=%s", len(rows))
        return len(rows)

    def delete_expired_run_sheets(self, now: datetime | None = None) -> int:
        metadata = self._sheet_metadata(fields="sheets(properties(sheetId,title))")
        sheets = metadata.get("sheets", [])
        titles = [sheet.get("properties", {}).get("title", "") for sheet in sheets]
        if len(sheets) <= 1:
            return 0

        cutoff = (now or datetime.now(KST)).astimezone(KST) - timedelta(days=self.retention_days)
        requests = []
        for sheet in sheets:
            properties = sheet.get("properties", {})
            title = properties.get("title", "")
            sheet_datetime = parse_run_sheet_title(title, now=now)
            if not sheet_datetime or sheet_datetime >= cutoff:
                continue
            if title == self.sheet_name and len(titles) == len(requests) + 1:
                continue
            requests.append({"deleteSheet": {"sheetId": properties["sheetId"]}})

        if not requests:
            return 0

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"requests": requests},
        ).execute()
        LOGGER.info("Deleted expired run sheets count=%s", len(requests))
        return len(requests)

    def _build_service(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Google Sheets dependencies are not installed. Run pip install -r requirements.txt"
            ) from exc

        credentials_path = self.application_credentials
        temp_file_name: str | None = None
        if self.service_account_json:
            parsed = json.loads(self.service_account_json)
            with NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
                json.dump(parsed, f)
                temp_file_name = f.name
            credentials_path = temp_file_name

        if not credentials_path:
            return self._build_oauth_service()

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

        if temp_file_name:
            try:
                Path(temp_file_name).unlink(missing_ok=True)
            except OSError:
                LOGGER.warning("Could not remove temporary service account file: %s", temp_file_name)

        return service

    def _build_oauth_service(self):
        if not self.oauth_client_id or not self.oauth_client_secret or not self.oauth_refresh_token:
            raise RuntimeError(
                "Set GOOGLE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS or OAuth Sheets credentials"
            )
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Google Sheets dependencies are not installed. Run pip install -r requirements.txt"
            ) from exc

        credentials = Credentials(
            token=None,
            refresh_token=self.oauth_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.oauth_client_id,
            client_secret=self.oauth_client_secret,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def _ensure_header(self) -> None:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_name}'!A1:O1",
        ).execute()
        values = result.get("values", [])
        if values and values[0] == HEADERS:
            return
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_name}'!A1:O1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()

    def _ensure_basic_filter(self) -> None:
        sheet_id = self._sheet_id()
        if sheet_id is None:
            LOGGER.warning("Could not find sheet id for filter setup sheet=%s", self.sheet_name)
            return
        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    "requests": [
                        {
                            "setBasicFilter": {
                                "filter": {
                                    "range": {
                                        "sheetId": sheet_id,
                                        "startRowIndex": 0,
                                        "startColumnIndex": 0,
                                        "endColumnIndex": len(HEADERS),
                                    }
                                }
                            }
                        },
                        {
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": sheet_id,
                                    "gridProperties": {"frozenRowCount": 1},
                                },
                                "fields": "gridProperties.frozenRowCount",
                            }
                        },
                    ]
                },
            ).execute()
        except Exception as exc:
            LOGGER.warning("Could not apply basic filter/frozen header: %s", exc)

    def _sheet_id(self) -> int | None:
        metadata = self._sheet_metadata(fields="sheets(properties(sheetId,title))")
        for sheet in metadata.get("sheets", []):
            properties = sheet.get("properties", {})
            if properties.get("title") == self.sheet_name:
                return properties.get("sheetId")
        return None

    def _resolve_sheet_name(self, requested_sheet_name: str) -> str:
        if not requested_sheet_name or requested_sheet_name == RUN_TIMESTAMP_SHEET:
            return self._create_run_sheet()
        if requested_sheet_name and requested_sheet_name != FIRST_SHEET:
            return requested_sheet_name
        metadata = self._sheet_metadata(fields="sheets(properties(title))")
        sheets = metadata.get("sheets", [])
        if not sheets:
            raise RuntimeError("Spreadsheet does not contain any sheets")
        return sheets[0]["properties"]["title"]

    def _create_run_sheet(self, now: datetime | None = None) -> str:
        metadata = self._sheet_metadata(fields="sheets(properties(title))")
        existing_titles = {
            sheet.get("properties", {}).get("title", "")
            for sheet in metadata.get("sheets", [])
        }
        title = unique_sheet_title(format_run_sheet_title(now), existing_titles)
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": title,
                                "gridProperties": {"frozenRowCount": 1},
                            }
                        }
                    }
                ]
            },
        ).execute()
        LOGGER.info("Created run sheet title=%s", title)
        return title

    def _sheet_metadata(self, fields: str) -> dict:
        return self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id,
            fields=fields,
        ).execute()

    def _existing_video_ids(self) -> set[str]:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_name}'!O2:O",
        ).execute()
        return {row[0] for row in result.get("values", []) if row}

    def _row(self, classified: ClassifiedVideo) -> list[str | int]:
        video = classified.video
        collected_at = datetime.now(KST).isoformat(timespec="seconds")
        return [
            collected_at,
            video.published_at.isoformat(timespec="seconds"),
            classified.topic,
            classified.subtopic,
            video.channel_title,
            video.title,
            video.thumbnail_url,
            video.url,
            classified.summary_ko,
            _value_label(classified.watch_priority),
            classified.watch_priority,
            ", ".join(classified.keywords),
            video.duration,
            video.view_count if video.view_count is not None else "",
            video.video_id,
        ]


def _sort_for_sheet(videos: list[ClassifiedVideo]) -> list[ClassifiedVideo]:
    return sorted(videos, key=lambda item: (item.topic, -item.video.published_at.timestamp()))


def _value_label(watch_priority: str) -> str:
    if watch_priority == "High":
        return "가치 있는 영상"
    if watch_priority == "Medium":
        return "검토할 영상"
    return "낮은 우선순위"


def format_run_sheet_title(now: datetime | None = None) -> str:
    reference = (now or datetime.now(KST)).astimezone(KST)
    return reference.strftime("%m%d %H:%M")


def unique_sheet_title(base_title: str, existing_titles: set[str]) -> str:
    if base_title not in existing_titles:
        return base_title
    suffix = 2
    while f"{base_title} ({suffix})" in existing_titles:
        suffix += 1
    return f"{base_title} ({suffix})"


def parse_run_sheet_title(title: str, now: datetime | None = None) -> datetime | None:
    match = re.fullmatch(r"(?P<month>\d{2})(?P<day>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2})(?: \(\d+\))?", title)
    if not match:
        return None
    reference = (now or datetime.now(KST)).astimezone(KST)
    try:
        parsed = datetime(
            year=reference.year,
            month=int(match.group("month")),
            day=int(match.group("day")),
            hour=int(match.group("hour")),
            minute=int(match.group("minute")),
            tzinfo=KST,
        )
    except ValueError:
        return None
    if parsed > reference + timedelta(days=1):
        parsed = parsed.replace(year=parsed.year - 1)
    return parsed
