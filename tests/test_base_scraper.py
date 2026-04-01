import pytest
from scraper.base import BaseScraper, JobPosting


def test_job_posting_dataclass():
    job = JobPosting(
        company="당근",
        title="MLE",
        url="https://about.daangn.com/job/1",
        deadline="2026-04-17",
        career_type="신입",
        source="직행"
    )
    assert job.company == "당근"
    assert job.url == "https://about.daangn.com/job/1"


def test_base_scraper_is_abstract():
    with pytest.raises(TypeError):
        BaseScraper()


def test_base_scraper_target_jobs():
    class ConcreteScraper(BaseScraper):
        def scrape(self):
            return []
    s = ConcreteScraper()
    assert "DE" in s.TARGET_JOBS
    assert "MLE" in s.TARGET_JOBS
    assert "DS" in s.TARGET_JOBS


def test_is_target_job_matches_korean():
    class ConcreteScraper(BaseScraper):
        def scrape(self):
            return []
    s = ConcreteScraper()
    assert s.is_target_job("데이터 엔지니어 채용") is True
    assert s.is_target_job("마케터 채용") is False
