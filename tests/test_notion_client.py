import pytest
from unittest.mock import MagicMock
from notion_client_wrapper import NotionClient
from scraper.base import JobPosting

MOCK_JOB = JobPosting(
    company="당근",
    title="MLE",
    url="https://about.daangn.com/job/1",
    deadline="2026-04-17",
    career_type="신입",
    source="직행",
)


def _make_client():
    client = NotionClient.__new__(NotionClient)
    client._client = MagicMock()
    client._job_db_id = "test-job-db-id"
    client._doc_db_id = "test-doc-db-id"
    return client


def test_is_duplicate_returns_true_when_url_exists():
    client = _make_client()
    client._client.databases.query.return_value = {"results": [{"id": "page-id"}]}
    assert client.is_duplicate(MOCK_JOB.url) is True


def test_is_duplicate_returns_false_when_url_not_exists():
    client = _make_client()
    client._client.databases.query.return_value = {"results": []}
    assert client.is_duplicate(MOCK_JOB.url) is False


def test_add_job_calls_pages_create():
    client = _make_client()
    client.add_job(MOCK_JOB)
    client._client.pages.create.assert_called_once()
    call_kwargs = client._client.pages.create.call_args[1]
    props = call_kwargs["properties"]
    assert props["기업명"]["title"][0]["text"]["content"] == "당근"


def test_get_jobs_expiring_in():
    client = _make_client()
    client._client.databases.query.return_value = {
        "results": [
            {
                "id": "p1",
                "properties": {
                    "기업명": {"title": [{"text": {"content": "당근"}}]},
                    "직무명": {"multi_select": [{"name": "MLE"}]},
                    "URL": {"url": "https://about.daangn.com/job/1"},
                    "모집 마감 기간": {"date": {"start": "2026-04-17T00:00:00"}},
                    "신입/경력": {"select": {"name": "신입"}},
                    "지원자": {"people": [{"name": "김협"}]},
                },
            }
        ]
    }
    jobs = client.get_jobs_expiring_in(days=3)
    assert isinstance(jobs, list)
