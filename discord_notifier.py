from __future__ import annotations

import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


def extract_job_page_info(page: dict) -> dict:
    """상단 채용 공고 DB 페이지에서 정보 추출."""
    props = page["properties"]
    company = props.get("기업명", {}).get("title", [{}])[0].get("text", {}).get("content", "")
    titles = props.get("직무명", {}).get("multi_select", [])
    title = titles[0]["name"] if titles else ""
    url = props.get("URL", {}).get("url", "")
    date_obj = props.get("모집 마감 기간", {}).get("date")
    deadline = date_obj["start"][:10] if date_obj else ""
    return {"company": company, "title": title, "url": url, "deadline": deadline}


# (매칭 키워드, 체크박스 컬럼명, 표시 이름)
_REVIEW_CHECKBOX_MAP = [
    ("상택",     "리뷰완(상택)", "상택"),
    ("Sangteck", "리뷰완(상택)", "상택"),
    ("채원",     "리뷰완(채원)", "채원"),
    ("협",       "리뷰완(협)",   "협"),
]


def _get_review_info(name: str) -> tuple:
    """(체크박스 컬럼명, 표시 이름) 반환. 매칭 없으면 (None, 원본 이름)."""
    for keyword, col, display in _REVIEW_CHECKBOX_MAP:
        if keyword in name:
            return col, display
    return None, name


def extract_doc_page_info(page: dict) -> dict:
    """하단 서류 작성 DB 페이지에서 정보 추출. _company/_job_deadline 키는 NotionClient에서 주입됨."""
    props = page["properties"]
    company = page.get("_company", "")
    job_deadline = page.get("_job_deadline", "")

    applicant_prop = props.get("-", {}).get("title", [])
    applicant = applicant_prop[0]["text"]["content"] if applicant_prop else ""

    rt = props.get("지원 직무", {}).get("rich_text", [{}])
    job_title = rt[0].get("text", {}).get("content", "") if rt else ""

    review_date_obj = props.get("리뷰해주세요", {}).get("date")
    doc_deadline = review_date_obj["start"][:10] if review_date_obj else ""

    draft_date_obj = props.get("이때까지 낼게요", {}).get("date")
    draft_deadline = draft_date_obj["start"][:10] if draft_date_obj else ""

    status = props.get("Status", {}).get("status", {}).get("name", "")
    assignees = [p["name"] for p in props.get("마니또", {}).get("people", [])]

    review_status = []
    for name in assignees:
        col, display = _get_review_info(name)
        if col:
            done = props.get(col, {}).get("checkbox", False)
            review_status.append(("✅" if done else "⬜", display))

    req_rt = props.get("리뷰이 요청사항", {}).get("rich_text", [])
    request_notes = req_rt[0]["text"]["content"] if req_rt else ""

    return {
        "company": company,
        "applicant": applicant,
        "job_title": job_title,
        "doc_deadline": doc_deadline,
        "draft_deadline": draft_deadline,
        "job_deadline": job_deadline,
        "status": status,
        "assignees": assignees,
        "review_status": review_status,
        "request_notes": request_notes,
    }


class DiscordNotifier:
    def __init__(self):
        self._webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        user_map_raw = os.environ.get("DISCORD_USER_MAP", "")
        self._user_map = dict(
            item.split(":") for item in user_map_raw.split(",") if ":" in item
        )

    def _post_webhook(self, content: str) -> None:
        try:
            res = requests.post(self._webhook_url, json={"content": content}, timeout=10)
            res.raise_for_status()
        except Exception as e:
            logger.error(f"Discord webhook 전송 실패: {e}")

    def send_morning_summary(self, new_count: int, expiring_job_pages: list[dict]) -> None:
        """매일 아침: 신규 공고 수 + 채용 공고 마감 임박 목록 (상단 DB 참조)."""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"📋 **오늘의 채용 공고 요약** ({today})",
            "─" * 30,
            f"• 신규 공고 **{new_count}건** 추가됨",
        ]
        if expiring_job_pages:
            lines.append("• 채용 마감 임박:")
            for page in expiring_job_pages:
                info = extract_job_page_info(page)
                lines.append(f"  - [{info['company']}] {info['title']} ~ {info['deadline']}")
        self._post_webhook("\n".join(lines))

    def send_job_deadline_alert(self, page: dict, days_left: int) -> None:
        """채용 공고 마감 임박 알림 (상단 DB 참조)."""
        info = extract_job_page_info(page)
        label = f"D-{days_left}" if days_left > 0 else "D-DAY"
        content = (
            f"⚠️ **채용 공고 마감 {label}**\n"
            f"[{info['company']}] {info['title']}\n"
            f"마감일: {info['deadline']}\n"
            f"🔗 {info['url']}"
        )
        self._post_webhook(content)

    def send_separator(self) -> None:
        """메시지 사이 시각적 구분선 전송."""
        self._post_webhook("─" * 40)

    def send_scrape_summary(self, counts: dict) -> None:
        """스크래핑 결과 직무별 요약 메시지 전송."""
        today = datetime.now().strftime("%Y-%m-%d")
        total = sum(counts.values())
        lines = [f"# 📊 신규 채용 공고 요약", f"-# {today}", ""]
        if counts:
            for category, count in sorted(counts.items(), key=lambda x: -x[1]):
                lines.append(f"> **{category}**  {count}건")
            lines.append("")
            lines.append(f"-# 총 **{total}건** 노션에 추가되었습니다.")
        else:
            lines.append("> 신규 공고 없음")
        self._post_webhook("\n".join(lines))

    def send_doc_deadline_reminder(self, pages: list[dict], days_left: int) -> None:
        """리뷰 마감 리마인드. 리뷰 완료자는 이름만, 미완료자는 @멘션. 같은 날짜 항목을 한 메시지로 묶음."""
        if not pages:
            return
        label = f"D-{days_left}" if days_left > 0 else "D-DAY"
        infos = [extract_doc_page_info(p) for p in pages]
        review_deadline = infos[0]["doc_deadline"]
        lines = [
            f"# 📝 리뷰해주세요 {label}",
            f"-# 리뷰 마감일: {review_deadline}",
        ]
        for info in infos:
            reviewed = {name for icon, name in info["review_status"] if icon == "✅"}
            manicotto_parts = []
            for name in info["assignees"]:
                if name in reviewed:
                    manicotto_parts.append(name)
                elif name in self._user_map:
                    manicotto_parts.append(f"<@{self._user_map[name]}>")
                else:
                    manicotto_parts.append(name)

            lines.append("")
            lines.append(f"### {info['company']}  ·  {info['job_title']}")
            lines.append(f"-# 지원자: {info['applicant']}")
            lines.append(f"> • **상태** {info['status']}")
            lines.append(f"> • **일정** 초안 `{info['draft_deadline']}`  →  제출 `{info['job_deadline']}`  →  리뷰 `{info['doc_deadline']}`")
            if info["review_status"]:
                review_str = "  ".join(f"{icon} {name}" for icon, name in info["review_status"])
                lines.append(f"> • **리뷰 현황** {review_str}")
            if info["request_notes"]:
                lines.append(f"> • **요청사항** {info['request_notes']}")
            lines.append(f"> • **마니또** {' '.join(manicotto_parts)}")
        self._post_webhook("\n".join(lines))
