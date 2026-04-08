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
        # DE - 데이터 엔지니어
        "데이터 엔지니어", "데이터엔지니어", "Data Engineer",
        # DAE - 데이터 애널리틱스 엔지니어
        "데이터 애널리틱스 엔지니어", "데이터애널리틱스엔지니어",
        "Data Analytics Engineer", "Analytics Engineer", "애널리틱스 엔지니어",
        # DA - 데이터 분석가
        "데이터 분석가", "데이터분석가", "Data Analyst",
        # DS - 데이터 사이언티스트
        "데이터 사이언티스트", "데이터사이언티스트", "Data Scientist",
        # MLE - 머신러닝 엔지니어
        "머신러닝 엔지니어", "머신러닝엔지니어", "ML 엔지니어", "ML Engineer",
        "Machine Learning Engineer", "MLOps",
        # AIE - AI 엔지니어
        "AI 엔지니어", "AI엔지니어", "AI Engineer", "인공지능 엔지니어",
    ]

    EXCLUDE_KEYWORDS = ["시니어", "Senior", "Sr.", "병역특례", "멘토", "강사"]

    @abstractmethod
    def scrape(self) -> list[JobPosting]:
        """공고 목록을 반환한다."""
        pass

    def is_target_job(self, title: str) -> bool:
        title_lower = title.lower()
        if any(ex.lower() in title_lower for ex in self.EXCLUDE_KEYWORDS):
            return False
        return any(kw.lower() in title_lower for kw in self.TARGET_JOBS)
