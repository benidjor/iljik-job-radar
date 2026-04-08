from unittest.mock import patch
from discord_notifier import DiscordNotifier, extract_job_page_info, extract_doc_page_info

# 상단 DB (채용 공고) 페이지 형태
MOCK_JOB_PAGE = {
    "id": "p1",
    "properties": {
        "기업명": {"title": [{"text": {"content": "당근"}}]},
        "직무명": {"multi_select": [{"name": "MLE"}]},
        "URL": {"url": "https://about.daangn.com/job/1"},
        "모집 마감 기간": {"date": {"start": "2026-04-17T00:00:00"}},
        "신입/경력": {"select": {"name": "신입"}},
    },
}

# 하단 DB (서류 작성) 페이지 형태
MOCK_DOC_PAGE = {
    "id": "d1",
    "properties": {
        "기업명": {"title": [{"text": {"content": "당근"}}]},
        "직무": {"rich_text": [{"text": {"content": "MLE"}}]},
        "서류 마감 기한": {"date": {"start": "2026-04-18T00:00:00"}},
        "Status": {"select": {"name": "서류 작성중"}},
        "지원자/담당자": {"people": [{"name": "김협"}]},
        "지원공고": {"relation": [{"id": "p1"}]},
    },
}


def test_extract_job_page_info():
    info = extract_job_page_info(MOCK_JOB_PAGE)
    assert info["company"] == "당근"
    assert info["title"] == "MLE"
    assert info["deadline"] == "2026-04-17"


def test_extract_doc_page_info():
    info = extract_doc_page_info(MOCK_DOC_PAGE)
    assert info["company"] == "당근"
    assert info["doc_deadline"] == "2026-04-18"
    assert info["assignees"] == ["김협"]
    assert info["status"] == "서류 작성중"


@patch("discord_notifier.requests.post")
def test_send_morning_summary(mock_post):
    mock_post.return_value.status_code = 204
    notifier = DiscordNotifier.__new__(DiscordNotifier)
    notifier._webhook_url = "https://discord.com/api/webhooks/test"
    notifier.send_morning_summary(new_count=5, expiring_job_pages=[MOCK_JOB_PAGE])
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert "오늘의 채용 공고 요약" in payload["content"]
    assert "5건" in payload["content"]


@patch("discord_notifier.requests.post")
def test_send_job_deadline_alert(mock_post):
    mock_post.return_value.status_code = 204
    notifier = DiscordNotifier.__new__(DiscordNotifier)
    notifier._webhook_url = "https://discord.com/api/webhooks/test"
    notifier.send_job_deadline_alert(MOCK_JOB_PAGE, days_left=1)
    payload = mock_post.call_args[1]["json"]
    assert "채용 공고 마감" in payload["content"]
    assert "D-1" in payload["content"]


@patch("discord_notifier.requests.post")
def test_send_doc_deadline_reminder(mock_post):
    mock_post.return_value.status_code = 204
    notifier = DiscordNotifier.__new__(DiscordNotifier)
    notifier._webhook_url = "https://discord.com/api/webhooks/test"
    notifier._user_map = {"김협": "123456789"}
    notifier.send_doc_deadline_reminder(MOCK_DOC_PAGE, days_left=1)
    payload = mock_post.call_args[1]["json"]
    assert "서류 마감" in payload["content"]
    assert "<@123456789>" in payload["content"]
