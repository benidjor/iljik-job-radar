from __future__ import annotations

import logging
import requests

from .base import BaseScraper, JobPosting

logger = logging.getLogger(__name__)

# 원티드 직무 카테고리 tag_type_ids
# 실제 ID는 원티드 개발자 도구 Network 탭에서 확인 필요
WANTED_JOB_TAGS = {
    "DE": 236,
    "DS": 234,
    "DA": 235,
    "MLE": 239,
    "AI Engineer": 1634,
}


class WantedScraper(BaseScraper):
    BASE_URL = "https://www.wanted.co.kr/api/v4/jobs"

    def scrape(self) -> list[JobPosting]:
        jobs = []
        seen_urls: set[str] = set()
        for tag_id in WANTED_JOB_TAGS.values():
            for job in self._fetch_page(tag_id):
                if job.url not in seen_urls:
                    seen_urls.add(job.url)
                    jobs.append(job)
        return jobs

    def _fetch_page(self, tag_id: int) -> list[JobPosting]:
        try:
            res = requests.get(
                self.BASE_URL,
                params={
                    "job_sort": "job.latest_order",
                    "tag_type_ids": tag_id,
                    "limit": 100,
                    "offset": 0,
                },
                timeout=10,
            )
            res.raise_for_status()
            return self._parse(res.json())
        except Exception as e:
            logger.error(f"원티드 스크래핑 실패 (tag_id={tag_id}): {e}")
            return []

    def _parse(self, data: dict) -> list[JobPosting]:
        results = []
        for item in data.get("data", []):
            title = item.get("position", "")
            if not self.is_target_job(title):
                continue
            due_time = item.get("due_time") or ""
            deadline = due_time[:10] if due_time else ""
            results.append(
                JobPosting(
                    company=item["company"]["name"],
                    title=title,
                    url=f"https://www.wanted.co.kr/wd/{item['id']}",
                    deadline=deadline,
                    career_type=item.get("experience_level", {}).get("name", ""),
                    source="원티드",
                )
            )
        return results
