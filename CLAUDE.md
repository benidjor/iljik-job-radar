# job-automation

채용 공고 자동 수집 → Notion 아카이빙 → Discord 알림 파이프라인.

## 프로젝트 구조
- scraper/                 : 사이트별 스크래퍼 모듈 (현재: 원티드, 직행)
- tests/                   : pytest 테스트
- tests/fixtures/          : 스크래퍼 테스트용 HTML/JSON 픽스처
- main.py                  : 진입점 (실행 모드: scrape / notify / all)
- notion_client_wrapper.py : Notion DB 연동 (채용공고 DB + 서류작성 DB)
- discord_notifier.py      : Discord 알림 3종

## Notion DB 구조
- NOTION_JOB_DB_ID : 상단 채용 공고 아카이빙 DB (봇이 자동 저장)
- NOTION_DOC_DB_ID : 하단 서류 작성 DB (사람이 직접 작성, 지원공고 관계형 컬럼으로 상단 DB 참조)

## 환경변수
.env 파일 참고 (.env.example 복사 후 작성)

## 요구 사항
- Python 3.11+
- pip

## 초기 설정
```bash
cp .env.example .env
# .env 파일을 열어 실제 값 입력

pip install -r requirements.txt -r requirements-dev.txt
playwright install chromium
```

## 실행
python main.py --mode all       # 스크래핑 + 알림
python main.py --mode scrape    # 스크래핑만
python main.py --mode notify    # 알림만

## 테스트
pytest tests/ -v

## GitHub Actions
.github/workflows/job-scraper.yml — cron 09:00/13:00/18:00 KST

## Claude Code Hooks
.claude/settings.json — Edit/Write 후 pytest 자동 실행 (PostToolUse hook)

## 커밋 & PR 작성 규칙

- 언어: 한국어, 존댓말
- 이모지 사용 금지

### 커밋 메시지 형식

```
<type>: <한 줄 요약>

## <변경 섹션 제목>

- 변경 내용을 존댓말로 상세하게 작성합니다.
- 표(table)가 필요한 경우 마크다운 표를 사용합니다.

## 트러블슈팅 (해당되는 경우)

### <문제 제목>

**증상:** ...
**원인:** ...
**해결:** ...

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### PR 본문 형식

```
## 작업 개요

작업 내용을 2~3줄로 요약합니다.

---

## 주요 변경 사항

### 1. <변경 항목>

- 상세 내용을 존댓말로 작성합니다.
- 표가 필요한 경우 마크다운 표를 사용합니다.

---

## 트러블슈팅 (해당되는 경우)

### <문제 제목>

**증상:** ...
**원인:** ...
**해결:** ...

---

## 테스트

- [x] 테스트 항목

---

## 관련 이슈 (해당되는 경우)

- 관련 PR 또는 이슈 내용

🤖 Generated with Claude Code
```
