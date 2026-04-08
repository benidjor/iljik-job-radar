from unittest.mock import patch, MagicMock
from main import run_scrape, run_notify


@patch("main.WantedScraper")
@patch("main.ZighangScraper")
@patch("main.NotionClient")
def test_run_scrape_adds_new_jobs(MockNotion, MockZighang, MockWanted):
    from scraper.base import JobPosting
    mock_job = JobPosting("A사", "DE", "https://a.com/1", "2026-05-01", "신입", "원티드")
    MockWanted.return_value.scrape.return_value = [mock_job]
    MockZighang.return_value.scrape.return_value = []
    notion = MockNotion.return_value
    notion.is_duplicate.return_value = False
    count = run_scrape()
    notion.add_job.assert_called_once_with(mock_job)
    assert count == 1


@patch("main.NotionClient")
@patch("main.DiscordNotifier")
def test_run_notify_sends_alerts(MockDiscord, MockNotion):
    MockNotion.return_value.get_jobs_expiring_in.return_value = []
    MockNotion.return_value.get_docs_expiring_in.return_value = []
    run_notify(new_count=0, hour=9)
    MockDiscord.return_value.send_morning_summary.assert_called_once()
