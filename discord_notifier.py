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


def extract_doc_page_info(page: dict) -> dict:
    """하단 서류 작성 DB 페이지에서 정보 추출."""
    props = page["properties"]
    company = props.get("기업명", {}).get("title", [{}])[0].get("text", {}).get("content", "")
    rt = props.get("직무", {}).get("rich_text", [{}])
    title = rt[0].get("text", {}).get("content", "") if rt else ""
    date_obj = props.get("서류 마감 기한", {}).get("date")
    doc_deadline = date_obj["start"][:10] if date_obj else ""
    status = props.get("Status", {}).get("select", {}).get("name", "")
    assignees = [p["name"] for p in props.get("지원자/담당자", {}).get("people", [])]
    return {
        "company": company,
        "title": title,
        "doc_deadline": doc_deadline,
        "status": status,
        "assignees": assignees,
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

    def send_doc_deadline_reminder(self, page: dict, days_left: int) -> None:
        """서류 마감 리마인드 + 담당자 멘션 (하단 서류 작성 DB 참조)."""
        info = extract_doc_page_info(page)
        label = f"D-{days_left}" if days_left > 0 else "D-DAY"
        mentions = " ".join(
            f"<@{self._user_map[name]}>"
            for name in info["assignees"]
            if name in self._user_map
        )
        content = (
            f"{mentions} 📝 **서류 마감 {label} 알림**\n"
            f"[{info['company']}] {info['title']}\n"
            f"서류 마감일: {info['doc_deadline']}\n"
            f"현재 상태: {info['status']}"
        )
        self._post_webhook(content)
