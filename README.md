# samjik-job-radar

채용 공고 자동 수집 → Notion 아카이빙 → Discord 알림 파이프라인

신입/주니어 데이터 직군 채용 공고를 직행(Zighang)에서 자동 수집하여 Notion DB에 저장하고,
서류 작성 마감일이 임박한 항목을 Discord로 알림 발송합니다.

> 구축 과정 상세 기록: [GitHub Wiki](https://github.com/benidjor/samjik-job-radar/wiki)

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| 채용 공고 자동 수집 | 직행 API에서 6개 직무 카테고리 공고를 수집합니다 |
| Notion DB 저장 | 수집된 공고를 Notion 채용 공고 DB에 자동 저장합니다 |
| Discord 스크래핑 요약 | 직무별 신규 공고 건수와 Notion 필터 뷰 링크를 발송합니다 |
| Discord 리뷰 알림 | 서류 리뷰 마감 D-3 / D-1 / D-DAY에 마니또에게 멘션 알림을 발송합니다 |
| GitHub Actions 자동화 | 매일 정오(12:00 KST), 저녁(19:00 KST) 자동 실행합니다 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                       직행(Zighang) API                  │
└──────────────────────────┬──────────────────────────────┘
                           │ 키워드 검색 (AE/DE/DA/DS/MLE/AIE)
                           │ 30일 이내 공고 필터
                           │ 기업명 + 직무명 중복 체크
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  main.py --mode scrape                  │
└──────────────────────────┬──────────────────────────────┘
                           │ add_job(job, category)
                           ▼
                ┌──────────────────────┐
                │  Notion 채용 공고 DB  │
                │  · 직무 분류 자동 태깅 │
                │  · 등록 날짜 자동 기록 │
                └──────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  main.py --mode notify                  │
└────────────┬────────────────────────┬───────────────────┘
             │                        │
             ▼                        ▼
  send_scrape_summary()    get_docs_expiring_in(0/1/3)
             │                        │
             │               relation → pages.retrieve()
             │               회사명, 마감일 resolve
             │                        │
             ▼                        ▼
    ┌────────────────┐     ┌────────────────────────┐
    │    Discord     │     │       Discord           │
    │  신규 공고 요약   │     │  D-DAY / D-1 / D-3 알림 │
    │  직무별 건수      │     │  마니또 멘션             │
    │  Notion 링크    │     │  리뷰 완료자 제외         │
    └────────────────┘     └────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions                       │
│  cron: 매일 12:00 KST (UTC 03:00)                        │
│  cron: 매일 19:00 KST (UTC 10:00)                        │
│  → python main.py --mode all                            │
└─────────────────────────────────────────────────────────┘
```

---

## 직무 카테고리

| 축약어 | 풀네임 | 주요 검색 키워드 |
|---|---|---|
| AE | Analytics Engineer | 데이터 애널리틱스 엔지니어, Analytics Engineer |
| DE | Data Engineer | 데이터 엔지니어, Data Engineer |
| DA | Data Analyst | 데이터 분석가, Data Analyst |
| DS | Data Scientist | 데이터 사이언티스트, Data Scientist |
| MLE | ML Engineer | 머신러닝 엔지니어, ML Engineer, Machine Learning Engineer, MLOps |
| AIE | AI Engineer | AI 엔지니어, AI Engineer |

**수집 제외 키워드:** 시니어, Senior, Sr., 병역특례, 멘토, 강사

---

## 프로젝트 구조

```
samjik-job-radar/
├── main.py                  # 진입점 (scrape / notify / all 모드)
├── notion_client_wrapper.py # Notion API 연동 (채용 공고 DB + 서류 작성 DB)
├── discord_notifier.py      # Discord Webhook 알림 발송
├── scraper/
│   ├── base.py              # 스크래퍼 추상 클래스, JobPosting 데이터클래스
│   └── zighang.py           # 직행(Zighang) API 스크래퍼
├── tests/
│   ├── fixtures/            # 스크래퍼 테스트용 JSON 픽스처
│   └── test_*.py            # pytest 테스트
├── .github/
│   └── workflows/
│       └── job-scraper.yml  # GitHub Actions cron 워크플로우
├── .env.example             # 환경변수 템플릿
├── requirements.txt         # 런타임 의존성
└── requirements-dev.txt     # 개발/테스트 의존성
```

---

## Notion DB 구조

### 채용 공고 DB (`NOTION_JOB_DB_ID`)

봇이 자동 수집한 공고를 저장하는 DB입니다.

| 컬럼명 | 타입 | 설명 |
|---|---|---|
| 기업명 | title | 회사명 |
| 직무명 | multi_select | 공고 직무명 |
| 직무 분류 | select | AE / DE / DA / DS / MLE / AIE |
| URL | url | 공고 원문 링크 |
| 모집 마감 기간 | date | 채용 마감일 |
| 신입/경력 | multi_select | 신입 / 경력 / 신입·경력 |
| 등록 날짜 | date | 스크래핑 일자 |
| 봇 | multi_select | 자동 수집 출처 표시 (삼직이) |

### 서류 작성 DB (`NOTION_DOC_DB_ID`)

팀원이 지원할 공고의 서류 작성 현황을 관리하는 DB입니다.

| 컬럼명 | 타입 | 설명 |
|---|---|---|
| - | title | 지원자 이름 |
| 지원 공고 | relation | 채용 공고 DB와 연결 |
| 지원 직무 | rich_text | 지원 직무명 |
| Status | status | 서류 작성 진행 상태 |
| 이때까지 낼게요 | date | 초안 제출 마감일 |
| 리뷰해주세요 | date | 리뷰 마감일 (D-3/D-1/D-DAY 알림 기준) |
| 마니또 | people | 리뷰 담당자 (멘션 대상) |
| 리뷰완(상택) | checkbox | 상택 리뷰 완료 여부 |
| 리뷰완(채원) | checkbox | 채원 리뷰 완료 여부 |
| 리뷰완(협) | checkbox | 협 리뷰 완료 여부 |
| 리뷰이 요청사항 | rich_text | 리뷰 요청 메모 |

---

## Discord 알림 형식

### 스크래핑 요약 메시지

스크래핑 완료 후 직무 카테고리별 신규 공고 건수를 요약하여 발송합니다.
각 직무명은 Notion 필터 뷰로 연결되는 링크로 표시됩니다.

```
# 신규 채용 공고 요약
-# YYYY-MM-DD

> [Data Engineer](<Notion 필터 뷰 URL>)  3건
> [Data Analyst](<Notion 필터 뷰 URL>)  2건

-# 총 5건 노션에 추가되었습니다.
```

### 리뷰 알림 메시지 (D-3 / D-1 / D-DAY)

`리뷰해주세요` 컬럼의 날짜 기준으로 D-3, D-1, D-DAY에 발송합니다.
리뷰를 완료한 마니또는 이름만 표시하고, 미완료자는 `@멘션` 처리합니다.

```
# 리뷰해주세요 D-3
-# 리뷰 마감일: YYYY-MM-DD

### [회사명  ·  직무명](<Notion 페이지 URL>)
-# 지원자: 홍길동
> • 상태  서류 작성 중
> • 일정  초안 `YYYY-MM-DD`  →  제출 `YYYY-MM-DD`  →  리뷰 `YYYY-MM-DD`
> • 리뷰 현황  ✅ 상택  ⬜ 채원  ⬜ 협
> • 요청사항  분량이 많으니 꼼꼼히 봐주세요
> • 마니또  상택  @채원  @협
```

---

## 설치 및 실행

### 요구 사항

- Python 3.9+
- pip

### 초기 설정

```bash
git clone https://github.com/benidjor/samjik-job-radar.git
cd samjik-job-radar

pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env
# .env 파일을 열어 실제 값 입력
```

### 실행

```bash
python3 main.py --mode all      # 스크래핑 + 알림
python3 main.py --mode scrape   # 스크래핑만 (Notion 저장)
python3 main.py --mode notify   # 알림만 (Discord 발송)
```

### 테스트

```bash
pytest tests/ -v
```

---

## 환경변수 설정

`.env.example`을 복사하여 `.env`를 작성합니다.

| 변수명 | 설명 |
|---|---|
| `NOTION_TOKEN` | Notion Integration Token |
| `NOTION_JOB_DB_ID` | 채용 공고 DB ID |
| `NOTION_DOC_DB_ID` | 서류 작성 DB ID |
| `DISCORD_WEBHOOK_URL` | Discord 채널 Webhook URL |
| `DISCORD_USER_MAP` | Notion 이름 → Discord User ID 매핑 (예: `홍길동:123456789`) |

#### DISCORD_USER_MAP 설정 방법

Discord 개발자 모드를 활성화(`설정 → 고급 → 개발자 모드`)한 뒤,
사용자 프로필에서 우클릭 → **ID 복사**로 확인합니다.

```
DISCORD_USER_MAP=홍길동:111111111111,김철수:222222222222
```

Notion에 영문 이름으로 저장된 경우 alias를 추가합니다.

```
DISCORD_USER_MAP=홍길동:111111111111,Hong Gildong:111111111111
```

---

## GitHub Actions 자동화

GitHub Secrets에 위 환경변수를 등록하면 자동으로 실행됩니다.

| 실행 시각 | UTC | KST |
|---|---|---|
| 정오 | 03:00 | 12:00 |
| 저녁 | 10:00 | 19:00 |

수동 실행은 GitHub Actions 탭 → **Run workflow**에서 가능합니다.

#### GitHub Secrets 등록 (gh CLI)

```bash
gh secret set -f .env --repo <owner>/samjik-job-radar
```
