# Commit Hero MVP 구조

## 결론

Commit Hero MVP는 Vercel 배포에 최적화된 Next.js 앱으로 시작한다. 사용자는 GitHub username만 입력하고, 서버 API가 공개 GitHub 데이터를 분석한 뒤, 한국어 중심의 고급 판타지 RPG 개발자 프로필 카드를 생성한다.

핵심은 많은 기능이 아니라 다음 1개 흐름이다.

`username 입력 -> GitHub 공개 데이터 분석 -> 랭크/클래스/스탯/업적 산출 -> 카드 화면 생성 -> 이미지 저장/공유`

## 제품 방향

| 항목 | 결정 |
|---|---|
| 목적 | 포트폴리오처럼 쓸 수 있는 개발자 프로필 카드 |
| 입력 | GitHub username |
| 결과물 | 고급 판타지 RPG 카드 |
| 캐릭터 | 성별 없는 판타지 캐릭터 |
| 언어 | 한국어 중심, 영어 보조 |
| 핵심 메시지 | 꾸준한 개발자 |
| 공유 이유 | 결과가 멋있어서 공유 |
| 레벨 시스템 | 사용하지 않음 |
| 주요 성취 표현 | 랭크 |

## 추천 기술 스택

| 영역 | MVP 선택 |
|---|---|
| 프레임워크 | Next.js App Router |
| 배포 | Vercel |
| 스타일 | Tailwind CSS |
| 서버 API | Next.js Route Handlers |
| GitHub API | GitHub REST API + 필요 시 GraphQL API |
| 이미지 저장 | MVP에서는 클라이언트 다운로드 우선 |
| DB | MVP 1차에서는 없음, 공유 URL이 필요해지는 순간 도입 |
| 추후 DB 후보 | Vercel Postgres, Supabase, Neon |
| 캐시 후보 | Vercel KV 또는 Upstash Redis |

## Vercel 배포 전략

MVP는 Next.js와 Vercel 조합으로 간다.

- `/app` 페이지는 정적/서버 렌더링 혼합으로 구성한다.
- `/app/api/*` 라우트는 Vercel 서버리스 함수로 동작한다.
- GitHub 토큰은 Vercel Environment Variables에 저장한다.
- 브라우저에 노출되면 안 되는 값은 `NEXT_PUBLIC_` 접두사를 쓰지 않는다.
- preview, production 환경 변수를 분리한다.

필수 환경 변수:

```txt
GITHUB_TOKEN=
GITHUB_API_VERSION=2022-11-28
```

선택 환경 변수:

```txt
NEXT_PUBLIC_APP_URL=
IMAGE_PROVIDER_API_KEY=
```

## MVP 페이지 구조

```txt
/
  username 입력 화면
  최근 생성 예시 카드 또는 샘플 카드

/hero/[username]
  생성된 카드 결과 화면
  카드 이미지 저장 버튼
  공유 버튼
  분석 근거 요약

/about
  서비스 설명
  GitHub 공개 활동 기반 안내
```

MVP에서는 `/hero/[username]`을 서버에서 매번 분석해도 된다. 트래픽이 늘면 username별 분석 결과를 캐시한다.

## API 구조

```txt
GET /api/github/[username]
  GitHub 공개 프로필, 저장소, 언어, 활동 데이터를 수집한다.

POST /api/analyze
  수집 데이터를 Commit Hero 카드 데이터로 변환한다.

GET /api/hero/[username]
  카드 화면에 필요한 최종 데이터를 반환한다.
```

초기에는 `/api/hero/[username]` 하나로 합쳐도 된다. 다만 분석 로직을 분리하기 위해 내부 모듈은 나눠둔다.

## 추천 폴더 구조

```txt
commit-hero/
  app/
    page.tsx
    hero/
      [username]/
        page.tsx
    api/
      hero/
        [username]/
          route.ts
  components/
    HeroCard.tsx
    StatBar.tsx
    RankBadge.tsx
    AchievementBadge.tsx
    UsernameForm.tsx
  lib/
    github/
      client.ts
      fetch-user.ts
      fetch-repos.ts
      fetch-contributions.ts
    analysis/
      score.ts
      rank.ts
      class.ts
      achievements.ts
      summary.ts
    card/
      image-map.ts
      theme.ts
  types/
    github.ts
    hero.ts
  public/
    characters/
      code-paladin.webp
      frontend-mage.webp
      backend-knight.webp
      devops-ranger.webp
      opensource-bard.webp
      algorithm-monk.webp
    frames/
      bronze.webp
      silver.webp
      gold.webp
      platinum.webp
      diamond.webp
      mythic.webp
```

## 카드 데이터 모델

```ts
type HeroCard = {
  username: string;
  displayName?: string;
  rank: HeroRank;
  classNameKo: string;
  classNameEn: string;
  title: string;
  summary: string;
  stats: {
    consistency: number;
    craft: number;
    focus: number;
    impact: number;
  };
  achievements: Achievement[];
  languages: string[];
  evidence: {
    publicRepos: number;
    totalStars: number;
    totalForks: number;
    recentlyUpdatedRepos: number;
    analyzedAt: string;
  };
};
```

## 스탯 정의

| 스탯 | 한국어 | 의미 | MVP 데이터 |
|---|---|---|---|
| Consistency | 꾸준함 | 활동이 지속적인지 | 최근 업데이트, 커밋/이벤트 흔적 |
| Craft | 완성도 | 프로젝트를 관리하고 다듬는지 | README, repo 수, 최근 관리 |
| Focus | 집중도 | 주력 기술이 뚜렷한지 | 주요 언어 비중 |
| Impact | 영향력 | 공개 활동 반응이 있는지 | stars, forks, followers |

랭크 점수 가중치:

| 스탯 | 가중치 |
|---|---:|
| Consistency | 40% |
| Craft | 25% |
| Focus | 20% |
| Impact | 15% |

## 랭크 구조

| 랭크 | 점수 구간 |
|---|---:|
| Bronze | 0-39 |
| Silver | 40-54 |
| Gold | 55-69 |
| Platinum | 70-82 |
| Diamond | 83-94 |
| Mythic | 95-100 |

## 클래스 구조

| 클래스 | 영어 | 기준 |
|---|---|---|
| 코드 성기사 | Code Paladin | 꾸준함, 유지보수, 안정성 |
| 프론트엔드 마법사 | Frontend Mage | JavaScript, TypeScript, CSS 중심 |
| 백엔드 기사 | Backend Knight | 서버, API, DB 성향 |
| 데브옵스 순찰자 | DevOps Ranger | Docker, CI, infra 흔적 |
| 오픈소스 음유시인 | Open Source Bard | stars, forks, public 협업 |
| 알고리즘 수도승 | Algorithm Monk | 알고리즘/문제풀이 레포 |
| 풀스택 대마법사 | Fullstack Archmage | 프론트/백엔드 기술 혼합 |
| 데이터 연금술사 | Data Alchemist | 데이터, 분석, ML 성향 |

## 업적 배지

| 업적 | 조건 예시 |
|---|---|
| 90일의 단련 | 최근 90일 활동 흔적이 충분함 |
| 저장소 수호자 | 여러 레포가 최근까지 관리됨 |
| 주력 기술의 장인 | 특정 언어 비중이 높음 |
| 오픈소스의 흔적 | star/fork/follower 반응이 있음 |
| 꾸준한 빌더 | 최근 업데이트 레포가 많음 |
| 새벽의 커밋 | 활동 시간 데이터가 확보될 때 V2에서 적용 |

## MVP 범위

### 반드시 포함

- GitHub username 입력
- 공개 프로필/저장소 데이터 수집
- 4개 스탯 계산
- 랭크 계산
- 클래스 부여
- 성별 없는 판타지 캐릭터 카드 렌더링
- 카드 이미지 저장
- 결과 URL 공유

### MVP 이후

- GitHub OAuth 로그인
- 실제 contribution calendar 정밀 분석
- 사용자별 카드 저장
- 소셜 공유용 OG 이미지 자동 생성
- AI 기반 개인화 캐릭터 이미지 생성
- 팀/친구 비교 카드
- 영문 버전

## 사용자 흐름

1. 사용자가 첫 화면에서 GitHub username을 입력한다.
2. `/hero/[username]`으로 이동한다.
3. 서버 API가 GitHub 공개 데이터를 가져온다.
4. 분석 로직이 스탯, 랭크, 클래스, 업적을 계산한다.
5. 카드 UI가 결과를 렌더링한다.
6. 사용자는 이미지를 저장하거나 결과 URL을 공유한다.

## 구현 우선순위

| 순서 | 작업 |
|---:|---|
| 1 | Next.js 프로젝트 생성 |
| 2 | 기본 랜딩/입력 화면 구현 |
| 3 | GitHub API 클라이언트 구현 |
| 4 | 스탯/랭크/클래스 분석 로직 구현 |
| 5 | 카드 UI 구현 |
| 6 | 이미지 저장 기능 구현 |
| 7 | Vercel 환경 변수 설정 |
| 8 | Vercel production 배포 |

## 리스크

| 리스크 | 대응 |
|---|---|
| GitHub API rate limit | 서버 토큰 사용, 캐시 도입 |
| 공개 데이터만으로 점수 왜곡 | "공개 GitHub 활동 기반" 문구 명시 |
| 낮은 점수로 인한 사용자 실망 | 업적/칭호를 긍정적으로 설계 |
| 이미지 생성 비용 | MVP에서는 클래스별 템플릿 이미지 사용 |
| 공유 이미지 품질 | 카드 비율과 폰트 렌더링을 먼저 고정 |

## 참고 출처

- Vercel Environment Variables: https://vercel.com/docs/environment-variables
- Vercel Deploy CLI: https://vercel.com/docs/cli/deploy
- GitHub REST API Rate Limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub REST API Repositories: https://docs.github.com/en/rest/repos/repos
- GitHub GraphQL ContributionsCollection: https://docs.github.com/en/graphql/reference/objects#contributionscollection
