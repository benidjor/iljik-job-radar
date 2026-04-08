import argparse
import logging
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from scraper.wanted import WantedScraper
from scraper.zighang import ZighangScraper
from notion_client_wrapper import NotionClient
from discord_notifier import DiscordNotifier


def run_scrape() -> int:
    scrapers = [WantedScraper(), ZighangScraper()]
    notion = NotionClient()
    new_count = 0
    for scraper in scrapers:
        jobs = scraper.scrape()
        for job in jobs:
            if not notion.is_duplicate(job.url):
                notion.add_job(job)
                new_count += 1
                logger.info(f"추가: [{job.source}] {job.company} - {job.title}")
    logger.info(f"총 {new_count}건 신규 공고 추가됨")
    return new_count


def run_notify(new_count: int, hour: int) -> None:
    notion = NotionClient()
    discord = DiscordNotifier()

    # 상단 채용 공고 DB 기준 마감 알림
    job_expiring_1 = notion.get_jobs_expiring_in(days=1)
    job_expiring_3 = notion.get_jobs_expiring_in(days=3)

    # 하단 서류 작성 DB 기준 서류 마감 리마인드
    doc_expiring_1 = notion.get_docs_expiring_in(days=1)
    doc_expiring_3 = notion.get_docs_expiring_in(days=3)

    if hour == 9:
        discord.send_morning_summary(
            new_count=new_count,
            expiring_job_pages=job_expiring_1 + job_expiring_3,
        )

    for page in job_expiring_1:
        discord.send_job_deadline_alert(page, days_left=1)
    for page in job_expiring_3:
        discord.send_job_deadline_alert(page, days_left=3)

    for page in doc_expiring_1:
        discord.send_doc_deadline_reminder(page, days_left=1)
    for page in doc_expiring_3:
        discord.send_doc_deadline_reminder(page, days_left=3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["scrape", "notify", "all"], default="all")
    args = parser.parse_args()
    hour = datetime.now().hour
    new_count = 0

    if args.mode in ("scrape", "all"):
        new_count = run_scrape()
    if args.mode in ("notify", "all"):
        run_notify(new_count=new_count, hour=hour)
