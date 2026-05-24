# YouTube Subscription Digest

지정한 28개 YouTube 구독 채널의 최근 24시간 업로드 영상을 모두 수집하고, 주제별로 분류한 뒤 Google Sheets에 실행 시점별 탭으로 저장하는 Python 자동화 프로젝트다.

## 기능

- YouTube OAuth refresh token으로 인증
- `subscriptions.list(mine=true)`로 구독 채널을 조회한 뒤 `config/topics.yaml`의 `tracked_channels` 28개만 추적
- `activities.list(channelId, publishedAfter)`로 최근 업로드 후보 수집
- `videos.list(part=snippet,contentDetails,statistics)`로 썸네일, 영상 길이, 조회수 보강
- OpenAI Structured Outputs로 한국어 요약과 주제 분류 생성
- 주제는 `AI/기술`, `경제/재테크`, `정치/사회`, `비즈니스/마케팅`, `생산성/자기계발`, `교육/커리어`, `문화/미디어`, `기타`로 분류
- Google Sheets에 실행 시점 기준 `MMDD HH:mm` 형식의 새 탭 생성
- 같은 분에 다시 실행하면 `MMDD HH:mm (2)` 형식으로 중복 탭 이름을 자동 회피
- 생성 후 7일이 지난 실행 탭은 자동 삭제
- `가치구분`, `볼가치` 컬럼으로 가치 있는 영상 구분
- 헤더 필터와 첫 행 고정 자동 설정
- GitHub Actions에서 매일 KST 08:00 실행하며 `workflow_dispatch`로 원하는 시점에 수동 최신화 가능

## Google Sheets 컬럼

| 컬럼 | 설명 |
|---|---|
| 수집일시 | 자동화 실행 시각 |
| 게시일시 | YouTube 영상 공개 시각 |
| 주제 | 1차 주제 |
| 세부주제 | LLM 또는 fallback 세부 분류 |
| 채널명 | YouTube 채널명 |
| 제목 | 영상 제목 |
| 썸네일URL | 대표 썸네일 URL |
| 영상URL | YouTube 영상 링크 |
| 요약 | 한국어 짧은 요약 |
| 가치구분 | 가치 있는 영상 / 검토할 영상 / 낮은 우선순위 |
| 볼가치 | High / Medium / Low |
| 키워드 | 요약 키워드 |
| 영상길이 | ISO 8601 duration |
| 조회수 | 조회수 |
| videoId | 중복 방지 키 |

## 설정

1. Google Cloud Console에서 YouTube Data API v3를 활성화한다.
2. OAuth Client ID/Secret을 만들고 최초 동의 절차로 refresh token을 발급한다.
3. Google Sheets API 접근용 service account를 만들고 대상 스프레드시트에 편집 권한을 공유한다.
4. `.env.example`의 값을 GitHub Secrets 또는 로컬 환경 변수로 설정한다.

필수 환경 변수:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `OPENAI_API_KEY`
- `GOOGLE_SPREADSHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON` 또는 `GOOGLE_APPLICATION_CREDENTIALS`

선택 환경 변수:

- `GOOGLE_SHEET_NAME`: 기본값은 `__RUN_TIMESTAMP__`
- `GOOGLE_SHEETS_REFRESH_TOKEN`: 서비스 계정 대신 OAuth로 Sheets에 쓰는 경우 사용
- `ALLOW_RULE_BASED_CLASSIFIER`: OpenAI quota가 없을 때 `true`로 설정하면 키워드 기반 fallback 사용

## 실행

```powershell
pip install -r requirements.txt
python -m src.main
```

YouTube refresh token 발급:

```powershell
python scripts/get_youtube_refresh_token.py --client-id "YOUR_CLIENT_ID" --client-secret "YOUR_CLIENT_SECRET"
```

로컬에서 OpenAI 없이 실행하거나 구조만 확인하려면:

```powershell
$env:ALLOW_RULE_BASED_CLASSIFIER="true"
python -m src.main --dry-run
```

원하는 시점에 최신화하려면 GitHub Actions의 `Daily YouTube Digest` 워크플로우에서 `Run workflow`를 누르거나, 로컬에서 `.secrets.env`를 로드한 뒤 `python -m src.main`을 실행한다.

## 출처

- YouTube Data API `subscriptions.list`: https://developers.google.com/youtube/v3/guides/implementation/subscriptions
- YouTube Data API `activities.list`: https://developers.google.com/youtube/v3/docs/activities/list
- YouTube Data API `videos.list`: https://developers.google.com/youtube/v3/docs/videos/list
- YouTube Data API quota: https://developers.google.com/youtube/v3/determine_quota_cost
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
