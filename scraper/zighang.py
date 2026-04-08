from __future__ import annotations

import logging
import requests
from datetime import datetime, timedelta

from .base import BaseScraper, JobPosting

logger = logging.getLogger(__name__)

SEARCH_KEYWORDS = [
    # DE
    "데이터엔지니어", "Data Engineer",
    # DAE
    "데이터애널리틱스엔지니어", "Analytics Engineer",
    # DA
    "데이터분석가", "Data Analyst",
    # DS
    "데이터사이언티스트", "Data Scientist",
    # MLE
    "머신러닝엔지니어", "Machine Learning Engineer", "MLOps",
    # AIE
    "AI엔지니어", "AI Engineer",
]


class ZighangScraper(BaseScraper):
    API_URL = "https://api.zighang.com/api/recruitments/v3"
    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://zighang.com",
        "Origin": "https://zighang.com",
    }

    def scrape(self) -> list[JobPosting]:
        seen_urls: set[str] = set()
        jobs = []
        for kw in SEARCH_KEYWORDS:
            for job in self._fetch(kw):
                if job.url not in seen_urls:
                    seen_urls.add(job.url)
                    jobs.append(job)
        return jobs

    def _fetch(self, keyword: str) -> list[JobPosting]:
        try:
            res = requests.get(
                self.API_URL,
                params={"keyword": keyword, "page": 0, "size": 100},
                headers=self.HEADERS,
                timeout=10,
            )
            res.raise_for_status()
            return self._parse(res.json())
        except Exception as e:
            logger.error(f"직행 스크래핑 실패 (keyword={keyword}): {e}")
            return []

    def _parse(self, data: dict) -> list[JobPosting]:
        results = []
        content = data.get("data", {}).get("content", [])
        cutoff = datetime.now() - timedelta(days=30)
        for item in content:
            try:
                created_at = item.get("createdAt", "")
                if created_at and datetime.fromisoformat(created_at[:19]) < cutoff:
                    continue
                title = item.get("title", "").strip()
                if not self.is_target_job(title):
                    continue
                career_min = item.get("careerMin")
                if career_min is not None and career_min > 3:
                    continue
                company = item.get("company", {}).get("name", "")
                job_id = item.get("id", "")
                url = f"https://zighang.com/recruitment/{job_id}"
                end_date = item.get("endDate") or ""
                deadline = end_date if end_date else ""
                career_min = item.get("careerMin")
                career_max = item.get("careerMax")
                if career_min is None:
                    career_type = "경력 무관"
                elif career_min == 0 and career_max == 0:
                    career_type = "신입"
                else:
                    career_type = "0~3년차"
                results.append(JobPosting(
                    company=company,
                    title=title,
                    url=url,
                    deadline=deadline,
                    career_type=career_type,
                    source="직행",
                ))
            except Exception as e:
                logger.warning(f"직행 파싱 오류: {e}")
        return results
