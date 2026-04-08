import argparse
import logging

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from scraper.zighang import ZighangScraper
from notion_client_wrapper import NotionClient
from discord_notifier import DiscordNotifier


# 직무 카테고리 분류 (순서 중요: 더 구체적인 것 먼저)
_CATEGORY_KEYWORDS = [
    ("Analytics Engineer", ["analytics engineer", "데이터 애널리틱스", "데이터애널리틱스", "애널리틱스 엔지니어"]),
    ("데이터 엔지니어",    ["데이터 엔지니어", "데이터엔지니어", "data engineer"]),
    ("데이터 분석가",      ["데이터 분석가", "데이터분석가", "data analyst"]),
    ("데이터 사이언티스트", ["데이터 사이언티스트", "데이터사이언티스트", "data scientist"]),
    ("ML/MLOps 엔지니어", ["머신러닝", "ml 엔지니어", "ml engineer", "machine learning", "mlops"]),
    ("AI 엔지니어",       ["ai 엔지니어", "ai엔지니어", "ai engineer", "인공지능 엔지니어"]),
]


def _categorize(title: str) -> str:
    t = title.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in t for kw in keywords):
            return category
    return "기타"


def run_scrape() -> dict:
    notion = NotionClient()
    counts: dict[str, int] = {}
    for job in ZighangScraper().scrape():
        if not notion.is_duplicate(job):
            notion.add_job(job)
            category = _categorize(job.title)
            counts[category] = counts.get(category, 0) + 1
            logger.info(f"추가: {job.company} - {job.title}")
    logger.info(f"총 {sum(counts.values())}건 신규 공고 추가됨")
    return counts


def run_notify(counts: dict) -> None:
    notion = NotionClient()
    discord = DiscordNotifier()

    discord.send_scrape_summary(counts)
    discord.send_separator()

    doc_expiring_0 = notion.get_docs_expiring_in(days=0)
    doc_expiring_1 = notion.get_docs_expiring_in(days=1)
    doc_expiring_3 = notion.get_docs_expiring_in(days=3)

    if doc_expiring_0:
        discord.send_doc_deadline_reminder(doc_expiring_0, days_left=0)
    if doc_expiring_1:
        discord.send_doc_deadline_reminder(doc_expiring_1, days_left=1)
    if doc_expiring_3:
        discord.send_doc_deadline_reminder(doc_expiring_3, days_left=3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["scrape", "notify", "all"], default="all")
    args = parser.parse_args()

    counts = {}
    if args.mode in ("scrape", "all"):
        counts = run_scrape()
    if args.mode in ("notify", "all"):
        run_notify(counts)
