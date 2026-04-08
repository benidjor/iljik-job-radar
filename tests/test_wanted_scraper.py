from __future__ import annotations

import json
import responses as resp_mock
from scraper.wanted import WantedScraper


FIXTURE = json.loads(open("tests/fixtures/wanted_response.json").read())


@resp_mock.activate
def test_wanted_scraper_returns_only_target_jobs():
    """픽스처에 2개 공고(ML엔지니어, 마케터) 중 타깃 직무만 반환"""
    resp_mock.add(
        resp_mock.GET,
        "https://www.wanted.co.kr/api/v4/jobs",
        json=FIXTURE,
        status=200,
    )
    scraper = WantedScraper()
    # 태그 1개만 테스트하기 위해 _fetch_page 직접 호출
    jobs = scraper._fetch_page(tag_id=999)
    assert len(jobs) == 1
    assert jobs[0].company == "당근"
    assert jobs[0].title == "ML 엔지니어"
    assert jobs[0].source == "원티드"
    assert jobs[0].deadline == "2026-04-17T00:00:00"
    assert jobs[0].career_type == "신입"
    assert jobs[0].url == "https://www.wanted.co.kr/wd/123456"


@resp_mock.activate
def test_wanted_scraper_handles_api_failure():
    """API 500 오류 시 빈 리스트 반환 (예외 전파 안 함)"""
    resp_mock.add(
        resp_mock.GET,
        "https://www.wanted.co.kr/api/v4/jobs",
        status=500,
    )
    scraper = WantedScraper()
    jobs = scraper._fetch_page(tag_id=999)
    assert jobs == []


@resp_mock.activate
def test_wanted_scraper_handles_null_due_time():
    """due_time이 null인 경우 deadline을 빈 문자열로 처리"""
    fixture = {"data": [
        {"id": 1, "position": "데이터 엔지니어", "company": {"name": "테스트"},
         "due_time": None, "experience_level": {"name": "신입"}}
    ]}
    resp_mock.add(resp_mock.GET, "https://www.wanted.co.kr/api/v4/jobs",
                  json=fixture, status=200)
    scraper = WantedScraper()
    jobs = scraper._fetch_page(tag_id=999)
    assert len(jobs) == 1
    assert jobs[0].deadline == ""
