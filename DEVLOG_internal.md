# 삼직이(samjik-job-radar) 구축 작업기

> **작성일:** 2026년 4월
> **작성자:** 전상택
> **공유 대상:** 스터디 내부 팀원

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택](#2-기술-스택)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [Notion DB 구조](#4-notion-db-구조)
5. [Discord 알림 형식](#5-discord-알림-형식)
6. [개발 과정](#6-개발-과정)
7. [트러블슈팅](#7-트러블슈팅)
8. [배운 점 및 회고](#8-배운-점-및-회고)
9. [향후 개선 방향](#9-향후-개선-방향)

---

## 1. 프로젝트 개요

### 배경

스터디를 하면서 2가지 불편함 반복.

**첫째, 채용 공고 수집 비효율**
데이터 직군 공고는 원티드, 직행 등 여러 플랫폼에 흩어져 있음.
팀원 각자가 플랫폼을 돌아다니며 공고를 찾아 Notion에 수동 등록하는 방식으로 운영했으나, 놓치는 공고 발생 및 반복 작업 피로 누적.

**둘째, 서류 리뷰 마감 누락**
스터디 특성상 서로 서류를 리뷰해주는 마니또 시스템 운영 중.
별도 알림 없이 Notion을 직접 열어 확인해야 해서 마감을 놓치는 경우 발생.

### 목표

| 목표 | 내용 |
|---|---|
| 채용 공고 자동화 | 직행 API에서 데이터 직군 공고를 자동 수집하여 Notion DB에 저장 |
| 리뷰 알림 자동화 | D-3 / D-1 / D-DAY에 Discord로 마니또에게 멘션 알림 발송 |
| 알림 품질 개선 | 리뷰 완료한 마니또는 멘션 제외, Notion 페이지 직접 링크 삽입 |
| 완전 자동화 | GitHub Actions cron으로 하루 2회 무인 실행 |

---

## 2. 기술 스택

| 구분 | 기술 | 선택 이유 |
|---|---|---|
| 언어 | Python 3.9 | 팀 공통 언어, 풍부한 API 클라이언트 라이브러리 |
| 스크래핑 | Zighang JSON API | Playwright 없이 JSON API 직접 호출로 빠르고 안정적 |
| DB 연동 | Notion API (`notion-client`) | 팀이 이미 사용 중인 Notion 그대로 활용 |
| 알림 | Discord Webhook | 봇 없이 Webhook URL만으로 메시지 발송 가능 |
| 자동화 | GitHub Actions cron | 별도 서버 없이 무료로 스케줄 실행 가능 |

---

## 3. 시스템 아키텍처

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
    │    Discord     │     │       Discord          │
    │  신규 공고 요약   │     │  D-DAY / D-1 / D-3 알림  │
    │  직무별 건수      │     │  마니또 멘션              │
    │  Notion 링크    │     │  리뷰 완료자 제외          │
    └────────────────┘     └────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions                       │
│  cron: 매일 12:00 KST (UTC 03:00)                        │
│  cron: 매일 19:00 KST (UTC 10:00)                        │
│  → python main.py --mode all                            │
└─────────────────────────────────────────────────────────┘
```

> **참고 — GitHub Actions cron 지연**
> cron은 예약 시각에 정확히 실행되지 않음. 정각 스케줄은 수요 집중으로 수십 분 지연 가능.
> 스크래핑은 GitHub Actions가 **실제로 실행된 시각** 기준으로 동작 (`datetime.now()` 사용).
> 정확한 실행 시각이 중요한 경우 별도 서버 cron 사용 필요.

---

## 4. Notion DB 구조

### 채용 공고 DB

봇(삼직이)이 자동 수집한 공고를 저장.

| 컬럼명 | 타입 | 설명 |
|---|---|---|
| 기업명 | title | 회사명 |
| 직무명 | multi_select | 공고 직무명 (쉼표 → `·` 치환, Notion 제약) |
| **직무 분류** | select | AE / DE / DA / DS / MLE / AIE 자동 태깅 |
| URL | url | 공고 원문 링크 |
| 모집 마감 기간 | date | 채용 마감일 |
| 신입/경력 | multi_select | 신입 / 경력 / 신입·경력 |
| **등록 날짜** | date | 스크래핑 일자 자동 기록 |
| 봇 | multi_select | 자동 수집 표시 (`삼직이`) |

### 서류 작성 DB

팀원 서류 작성 현황 관리. `지원 공고` relation 컬럼으로 채용 공고 DB와 연결.
삼직이는 **`리뷰해주세요` 날짜 컬럼 기준**으로 D-3 / D-1 / D-DAY 알림 발송.

| 컬럼명 | 타입 | 설명 |
|---|---|---|
| - | title | 지원자 이름 |
| 지원 공고 | relation | 채용 공고 DB와 연결 |
| 지원 직무 | rich_text | 지원 직무명 |
| Status | status | 서류 작성 진행 상태 |
| 이때까지 낼게요 | date | 초안 제출 마감일 |
| **리뷰해주세요** | date | 알림 기준 날짜 (D-3/D-1/D-DAY) |
| 마니또 | people | 리뷰 담당자 (멘션 대상) |
| 리뷰완(상택) | checkbox | 상택 리뷰 완료 여부 |
| 리뷰완(채원) | checkbox | 채원 리뷰 완료 여부 |
| 리뷰완(협) | checkbox | 협 리뷰 완료 여부 |
| 리뷰이 요청사항 | rich_text | 리뷰 요청 메모 |

---

## 5. Discord 알림 형식

### 스크래핑 요약 메시지

신규 수집 공고를 직무 카테고리별로 묶어 요약. 직무명 클릭 시 해당 직무로 필터링된 Notion 뷰로 이동.

```
# 신규 채용 공고 요약
-# 2026-04-10

> [Data Engineer](Notion 필터 뷰 URL)  3건
> [Data Analyst](Notion 필터 뷰 URL)  2건
> [Analytics Engineer](Notion 필터 뷰 URL)  1건

-# 총 6건 노션에 추가되었습니다.
```

  <table>
    <tr>
      <td align="center"><b>개편 전</b></td>
      <td align="center"><b>개편 후</b></td>
    </tr>
    <tr>
      <td><img src="https://i.imgur.com/52mJnsX.png" width="400"/></td>
      <td><img src="https://i.imgur.com/j0rhrnW.png" width="400"/></td>
    </tr>
  </table>

### 리뷰 알림 메시지 (D-3 / D-1 / D-DAY)

- `리뷰해주세요` 컬럼 날짜 기준으로 D-3 / D-1 / D-DAY 각각 발송
- 같은 날짜의 여러 서류는 하나의 메시지로 묶어 발송
- **리뷰 완료(✅)** → 이름만 표시 (멘션 없음)
- **리뷰 미완료(⬜)** → `@멘션`
- 공고 제목 클릭 시 해당 Notion 서류 작성 페이지로 이동

```
# 리뷰해주세요 D-3
-# 리뷰 마감일: 2026-04-13

### [카카오페이  ·  Data Analyst](Notion 페이지 URL)
-# 지원자: 채원
> • 상태  서류 작성 중
> • 일정  초안 `2026-04-11`  →  제출 `2026-04-15`  →  리뷰 `2026-04-13`
> • 리뷰 현황  ✅ 상택  ⬜ 협
> • 요청사항  자소서 2번 문항 위주로 봐주세요
> • 마니또  상택  @협
```

  <table>
    <tr>
      <td align="center"><b>개편 전</b></td>
      <td align="center"><b>개편 후</b></td>
    </tr>
    <tr>
      <td><img src="https://i.imgur.com/GEaRCF3.png" width="400"/></td>
      <td><img src="https://i.imgur.com/6moP0Zr.png" width="400"/></td>
    </tr>
  </table>


---

## 6. 개발 과정

### [PR #1](https://github.com/benidjor/samjik-job-radar/pull/1) — 기반 파이프라인 구축

원티드와 직행 두 플랫폼에서 공고를 수집하는 기반 파이프라인 구축.

**직행 API 분석**
직행 공식 도메인(jikhae.com) 미존재 확인 → 브라우저 개발자 도구와 Next.js 번들 파일 직접 분석 → 실제 API 엔드포인트(`api.zighang.com/api/recruitments/v3`) 발견.
Playwright HTML 스크래핑 대신 JSON API 직접 호출 방식 채택. 속도와 안정성 대폭 향상.

**미완료 사항**
서류 작성 DB 연동은 Notion 관리자 권한 승인 대기로 다음 PR로 이월.

---

### [PR #2](https://github.com/benidjor/samjik-job-radar/pull/2) — 파이프라인 개편 및 리뷰 알림 전면 개편

가장 많은 작업이 이루어진 단계.

**스크래퍼 단일화**
실제 운영 결과 원티드·직행 공고가 상당 부분 중복됨 확인 → 원티드 스크래퍼 제거, 직행 단일화.

**중복 체크 기준 변경: URL → 기업명 + 직무명**
URL 기반 체크는 키워드별 검색 시 동일 공고가 중복 수집되는 문제 존재.
기업명 + 직무명 복합 조건으로 변경하여 실질적 중복 제거.

**수집 기간 제한: 30일 이내**
직행 API는 전체 공고 반환 → 오래된 마감 공고까지 수집되는 문제 발생.
`createdAt` 기준 30일 이내 공고만 수집하도록 필터 추가.

**서류 작성 DB 연동 완료**
관리자 권한 취득 후 DB 접근 시도 → 여러 단계에 걸친 오류 발생 (트러블슈팅 TS-2, TS-3 참고).

**리뷰 알림 전면 개편**
기존 단순 텍스트 형식 → D-3 / D-1 / D-DAY 단계별 알림으로 세분화. (리뷰 리마인더 기능 강화 목적)
Discord 마크다운 문법 적용으로 가독성 향상.
같은 날 마감하는 서류를 하나의 메시지로 묶는 기능 추가.

**Sangteck Jeon 처리**
Notion 영문 이름(`Sangteck Jeon`) → Discord 멘션 매핑 실패 문제 해결.
`.env` alias 추가 + 체크박스 매핑 보완, 표시는 `상택` 한글로 통일.

---

### [PR #3](https://github.com/benidjor/samjik-job-radar/pull/3) — Notion 직무 분류 컬럼 연동 및 Discord 링크 삽입

**직무 분류 컬럼 신설 배경**
스크래핑 요약 메시지에 직무별 Notion 필터 뷰 링크 삽입 시도.
→ Notion API가 View 정보를 미공개로 View ID를 프로그래밍으로 가져올 수 없음 확인.

**대안: 직무 분류 컬럼 신설**
Notion에 `직무 분류` (select) 컬럼 추가 → 스크래핑 시 AE / DE / DA / DS / MLE / AIE 자동 저장.
Notion에서 직무별 필터 뷰를 수동으로 한 번만 생성하고 URL을 코드에 매핑.
초기 1회 세팅 후 이후 자동 동작.

![노션 채용공고 DB](https://i.imgur.com/Fj3tEpQ.png)

**Notion 페이지 직접 링크**
리뷰 알림 메시지 공고 헤딩에 Notion 서류 작성 페이지 링크 삽입.
Notion API 응답의 `page["url"]` 필드 활용.

**직행 키워드 개선**
한글 키워드 붙여쓰기 → 띄어쓰기 적용 (직행 API 검색 정확도 향상 확인).
MLE 카테고리에 `ML Engineer`, `ML 엔지니어` 키워드 추가.

---

### [PR #4](https://github.com/benidjor/samjik-job-radar/pull/4) — README 및 프로젝트 명칭 정비

코드 내부에 `job-automation`, `iljik-job-radar` 등 혼재된 프로젝트 명칭을 `samjik-job-radar`로 통일.
Discord 봇 이름 `삼직이`에서 착안. GitHub 레포 이름도 동일하게 변경.
README.md 신규 작성으로 프로젝트 문서화 완성.

---

## 7. 트러블슈팅

### TS-1. GitHub Actions cron 실패 (exit code 1)

**증상**
워크플로우가 매번 `exit code 1`로 실패. 구체적 오류 메시지 미출력.

**원인**
환경변수를 `os.environ["KEY"]` 방식으로 접근 중 GitHub Secrets 미등록으로 `KeyError` 발생 후 즉시 종료.

```python
self._webhook_url = os.environ["DISCORD_WEBHOOK_URL"]  # Secrets 없으면 KeyError
```

**해결**
```bash
# GitHub Secrets 일괄 등록
gh secret set --repo benidjor/samjik-job-radar -f .env
```

---

### TS-2. Notion 서류 작성 DB 접근 불가 (400 Bad Request)

**증상**
채용 공고 DB 조회는 `200 OK` 성공, 서류 작성 DB 조회만 `400 Bad Request` 발생.

```
400 Bad Request
does not contain any data sources accessible by this API bot
```

**원인 파악 과정**

| 단계 | 의심 원인 | 결과 |
|---|---|---|
| 1 | DB ID 불일치 | URL ID와 `.env` ID 일치 → 무관 |
| 2 | 봇 연결 미완료 | 관리자 연결 확인 → 무관 |
| 3 | 워크스페이스 불일치 | 동일 워크스페이스 → 무관 |
| 4 | **링크드 뷰 문제** | **원인 확인** |

**핵심 원인: 링크드 뷰(Linked View) vs 원본 DB**

Notion에서 DB를 다른 페이지에 링크드 뷰로 삽입하면 링크드 뷰 URL ID ≠ 원본 DB ID.
봇을 링크드 뷰 페이지에 연결해도 원본 DB 접근 권한 없음.

```
[채용공고 + 서류작성 통합 페이지]
    ├── 채용 공고 DB  ← 원본 DB (봇 직접 연결됨) ✅
    └── 서류 작성 DB  ← 링크드 뷰 ❌
                              ↓
                       [원본 서류 작성 DB]  ← 봇 미연결 상태
```

**해결**
`client.search()`로 봇 접근 가능한 DB 목록 조회 → 실제 원본 DB ID 확인 → `.env` 수정.

```python
results = client.search(filter={"property": "object", "value": "database"})
for r in results["results"]:
    print(r["id"], r["title"])
```

> **핵심 교훈:** Notion URL 복사 시 링크드 뷰인지 원본 DB인지 반드시 확인.

---

### TS-3. Notion DB 컬럼명 불일치 (Could not find property)

**증상**
DB 접근 성공 후 쿼리 시 오류 발생.

```
APIResponseError: Could not find property with name or id: 서류 마감 기한
```

**원인**
코드 작성 시 컬럼명을 직접 확인하지 않고 예상 이름으로 작성. 실제 DB 컬럼명과 전혀 다름.

| 코드의 가정 | 실제 DB 컬럼명 |
|---|---|
| `서류 마감 기한` | `이때까지 낼게요` |
| `지원자/담당자` | `마니또` |
| `직무` | `지원 직무` |
| `Status` (select 타입) | `Status` (**status** 타입, 구조 상이) |

특히 `select`와 `status`는 이름이 같아도 API 응답 구조가 다름.

```python
# select 타입
props.get("Status", {}).get("select", {}).get("name", "")

# status 타입
props.get("Status", {}).get("status", {}).get("name", "")
```

**해결**
`databases.retrieve()`로 실제 properties 조회 후 코드 전면 수정.

> **핵심 교훈:** DB 연동 시 컬럼명·타입을 `databases.retrieve()`로 먼저 확인.

---

### TS-4. Python 3.9 fromisoformat 소수점 파싱 오류

**증상**
30일 필터 적용 후 대부분의 공고가 파싱 오류로 건너뛰어져 실제 수집 공고 거의 없음.

```
ValueError: Invalid isoformat string: '2026-03-26T14:55:24.22308'
```

**원인**
직행 API `createdAt` 필드가 소수점 **5자리** 형식으로 반환됨.

| Python 버전 | 지원 소수점 자릿수 |
|---|---|
| 3.9 | 0자리, 3자리, 6자리만 지원 |
| 3.11+ | 임의의 자릿수 지원 |

**해결**
`[:19]` 슬라이싱으로 초 단위까지만 파싱.

```python
datetime.fromisoformat(created_at[:19])  # "2026-03-26T14:55:24"
```

---

### TS-5. Sangteck Jeon Discord 멘션 누락

**증상**
Discord 리뷰 알림에서 팀원 전상택의 멘션·이름 모두 미표시.

**원인 (두 단계)**

1. **멘션 매핑 실패** — Notion 마니또 컬럼: `Sangteck Jeon` (영문) / `DISCORD_USER_MAP` 키: `전상택` (한글) → ID 매핑 실패
2. **체크박스 매핑 실패** — `_REVIEW_CHECKBOX_MAP`에 한글 키워드만 존재 → 리뷰 현황 미표시

**해결**

```
# .env — 영문 이름 alias 추가
DISCORD_USER_MAP=전상택:Discord_ID,Sangteck Jeon:Discord_ID,...
```

```python
# 영문 패턴 추가, 표시명은 한글로 통일
_REVIEW_CHECKBOX_MAP = [
    ("상택",     "리뷰완(상택)", "상택"),
    ("Sangteck", "리뷰완(상택)", "상택"),
    ("채원",     "리뷰완(채원)", "채원"),
    ("협",       "리뷰완(협)",   "협"),
]
```

---

### TS-6. gh CLI workflow scope 오류

**증상**
워크플로우 파일 push 시 권한 오류 발생.

```
refusing to allow an OAuth App to create or update workflow
`.github/workflows/job-scraper.yml` without `workflow` scope
```

**원인**
gh CLI 기본 인증 scope에 `workflow` 미포함.

**해결**
```bash
gh auth refresh -h github.com -s workflow
```

---

### TS-7. Python 3.9 타입 힌트 `str | None` 미지원

**증상**
```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

**원인**
`str | None` union 타입 힌트는 Python 3.10+에서만 지원.

**해결**
반환 타입 힌트 제거 (또는 `Optional[str]`로 대체).

---

### TS-8. Notion relation 컬럼 — 연결 페이지 데이터 별도 조회 필요

**증상**
서류 작성 DB 조회 시 `지원 공고` relation으로 연결된 채용 공고의 회사명·마감일 미포함.

**원인**
`databases.query()` 응답에서 relation 컬럼은 연결 페이지 **ID만** 반환. 실제 내용 미포함.

**해결**
relation ID로 `pages.retrieve()` 추가 호출.

```python
relation = page["properties"].get("지원 공고", {}).get("relation", [])
if relation:
    related = self._client.pages.retrieve(page_id=relation[0]["id"])
    company = related["properties"]["기업명"]["title"][0]["text"]["content"]
    deadline = related["properties"]["모집 마감 기간"]["date"]["start"][:10]
```

> 서류 작성 페이지 1건당 추가 API 호출 1회 발생.

---

## 8. 배운 점 및 회고

### Notion API

- **링크드 뷰와 원본 DB ID는 다름** — API 연동은 원본 DB에 직접 연결 필수. DB ID는 `client.search()`로 직접 확인 권장.
- **컬럼명·타입은 API로 먼저 확인** — 눈에 보이는 이름과 API 내부 이름이 다를 수 있음. `select`·`status`처럼 비슷해 보여도 응답 구조가 다른 타입 존재.
- **relation 컬럼은 ID만 반환** — 실제 값이 필요하면 `pages.retrieve()` 추가 호출 필요.

### GitHub Actions

- **cron은 정확하지 않음** — 정각 스케줄은 수십 분 지연 가능. 정확한 실행 시각이 필요하면 별도 서버 cron 사용.
- **`gh secret set -f .env`로 Secrets 일괄 등록 가능** — 하나씩 등록하는 번거로움 제거.

### Python

- **버전 호환성 항상 확인** — `str | None`, `datetime.fromisoformat()` 소수점 처리 등 3.9와 3.10+ 사이에 실질적 차이 존재.

### 설계

- **중복 체크는 의미 단위로** — URL 기반은 파라미터 변화에 취약. 기업명 + 직무명 등 비즈니스 의미 단위가 더 견고.
- **DB 구조는 코드 작성 전에 먼저 확인** — 가정으로 작성한 컬럼명은 나중에 전면 수정 필요.

---

## 9. 향후 개선 방향

- [ ] 스크래퍼 플랫폼 추가 (잡플래닛, 링크드인 등)
- [ ] 채용 공고 모집 마감 임박 알림 추가
- [ ] 테스트 커버리지 확대
- [ ] GitHub Actions 지연 해결을 위한 외부 서버 cron 전환 검토
- [ ] relation 페이지 배치 조회로 Notion API 호출 수 최적화
