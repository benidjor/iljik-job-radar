from __future__ import annotations

import logging
import requests

from .base import BaseScraper, JobPosting

logger = logging.getLogger(__name__)

# 원티드 직무 카테고리 tag_type_ids (API 실측값)
# 개발(518) 하위: 데이터 엔지니어(655), 데이터 사이언티스트(1024),
#                 빅데이터 엔지니어(1025), BI 엔지니어(1022), 머신러닝 엔지니어(1634)
WANTED_JOB_TAGS = {
    "DE": 655,    # 데이터 엔지니어 (개발)
    "DS": 1024,   # 데이터 사이언티스트 (개발)
    "BigData": 1025,  # 빅데이터 엔지니어 (개발)
    "BI": 1022,   # BI 엔지니어 (개발)
    "MLE": 1634,  # 머신러닝 엔지니어 (개발)
    "DA": 656,    # 데이터 분석가 (경영·비즈니스)
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
                    "country": "kr",
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
            annual_from = item.get("annual_from")
            if annual_from is not None and annual_from > 3:
                continue
            due_time = item.get("due_time") or ""
            deadline = due_time if due_time else ""
            annual_from = item.get("annual_from")
            if annual_from is None:
                career_type = "경력 무관"
            elif annual_from == 0:
                career_type = "신입"
            else:
                career_type = "0~3년차"
            results.append(
                JobPosting(
                    company=item["company"]["name"],
                    title=title,
                    url=f"https://www.wanted.co.kr/wd/{item['id']}",
                    deadline=deadline,
                    career_type=career_type,
                    source="원티드",
                )
            )
        return results
