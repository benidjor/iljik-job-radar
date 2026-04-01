from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class JobPosting:
    company: str
    title: str
    url: str
    deadline: str        # "YYYY-MM-DD" 형식, 없으면 ""
    career_type: str     # "신입" | "경력" | "신입/경력"
    source: str          # 사이트명


class BaseScraper(ABC):
    TARGET_JOBS = [
        "DE", "DAE", "DA", "DS", "MLE", "AI Engineer",
        "데이터 엔지니어", "데이터 분석", "데이터 사이언티스",
        "머신러닝", "ML 엔지니어", "AI 엔지니어",
    ]

    @abstractmethod
    def scrape(self) -> list[JobPosting]:
        """공고 목록을 반환한다."""
        pass

    def is_target_job(self, title: str) -> bool:
        return any(kw.lower() in title.lower() for kw in self.TARGET_JOBS)
