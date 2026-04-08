from __future__ import annotations

import json
import responses as resp_mock
from scraper.zighang import ZighangScraper

ZIGHANG_API_URL = "https://api.zighang.com/api/recruitments/v3"

MOCK_RESPONSE = {
    "success": True,
    "data": {
        "content": [
            {
                "id": "abc-123",
                "title": "데이터 엔지니어",
                "company": {"id": "cmp-1", "name": "테스트컴퍼니"},
                "endDate": "2026-04-30T23:59:59",
                "careerMin": 0,
                "careerMax": 0,
            },
            {
                "id": "abc-456",
                "title": "AI 엔지니어",
                "company": {"id": "cmp-2", "name": "AI스타트업"},
                "endDate": None,
                "careerMin": 3,
                "careerMax": 7,
            },
            {
                "id": "abc-789",
                "title": "마케팅 담당자",
                "company": {"id": "cmp-3", "name": "마케팅회사"},
                "endDate": "2026-05-01T23:59:59",
                "careerMin": 0,
                "careerMax": 0,
            },
        ]
    },
}


@resp_mock.activate
def test_zighang_scraper_returns_target_jobs_only():
    """픽스처 3개 공고 중 타깃 직무(데이터엔지니어, AI엔지니어)만 반환"""
    resp_mock.add(
        resp_mock.GET,
        ZIGHANG_API_URL,
        json=MOCK_RESPONSE,
        status=200,
    )
    scraper = ZighangScraper()
    jobs = scraper._fetch("데이터엔지니어")
    target_titles = [j.title for j in jobs]
    assert any("데이터 엔지니어" in t for t in target_titles)
    assert not any("마케팅" in t for t in target_titles)


@resp_mock.activate
def test_zighang_scraper_parses_fields_correctly():
    """공고 필드(회사명, URL, 마감일, 경력구분, source)가 올바르게 파싱되는지"""
    resp_mock.add(
        resp_mock.GET,
        ZIGHANG_API_URL,
        json=MOCK_RESPONSE,
        status=200,
    )
    scraper = ZighangScraper()
    jobs = scraper._fetch("데이터엔지니어")
    job = next(j for j in jobs if "데이터 엔지니어" in j.title)
    assert job.company == "테스트컴퍼니"
    assert job.url == "https://zighang.com/recruitment/abc-123"
    assert job.deadline == "2026-04-30T23:59:59"
    assert job.career_type == "신입"
    assert job.source == "직행"


@resp_mock.activate
def test_zighang_scraper_handles_empty_deadline():
    """마감일이 없는 공고는 deadline을 빈 문자열로 처리"""
    resp_mock.add(
        resp_mock.GET,
        ZIGHANG_API_URL,
        json=MOCK_RESPONSE,
        status=200,
    )
    scraper = ZighangScraper()
    jobs = scraper._fetch("AI엔지니어")
    ai_jobs = [j for j in jobs if "AI" in j.title]
    assert len(ai_jobs) >= 1
    assert ai_jobs[0].deadline == ""


@resp_mock.activate
def test_zighang_scraper_handles_http_failure():
    """HTTP 오류 시 빈 리스트 반환"""
    resp_mock.add(
        resp_mock.GET,
        ZIGHANG_API_URL,
        status=403,
    )
    scraper = ZighangScraper()
    jobs = scraper._fetch("데이터엔지니어")
    assert jobs == []
