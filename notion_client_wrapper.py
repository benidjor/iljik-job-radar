from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

from notion_client import Client

from scraper.base import JobPosting

logger = logging.getLogger(__name__)


class NotionClient:
    def __init__(self):
        self._client = Client(auth=os.environ["NOTION_TOKEN"])
        self._job_db_id = os.environ["NOTION_JOB_DB_ID"]
        self._doc_db_id = os.environ["NOTION_DOC_DB_ID"]

    def is_duplicate(self, url: str) -> bool:
        res = self._client.databases.query(
            database_id=self._job_db_id,
            filter={"property": "URL", "url": {"equals": url}},
        )
        return len(res["results"]) > 0

    def add_job(self, job: JobPosting) -> None:
        properties: dict = {
            "기업명": {"title": [{"text": {"content": job.company}}]},
            "직무명": {"multi_select": [{"name": job.title.replace(",", "·")}]},
            "URL": {"url": job.url},
            "봇": {"multi_select": [{"name": "삼직이"}]},
        }
        if job.deadline:
            properties["모집 마감 기간"] = {"date": {"start": job.deadline}}
        if job.career_type:
            properties["신입/경력"] = {"multi_select": [{"name": job.career_type}]}
        self._client.pages.create(
            parent={"database_id": self._job_db_id},
            properties=properties,
        )

    def get_jobs_expiring_in(self, days: int) -> list[dict]:
        """상단 채용 공고 DB에서 N일 후 마감 공고를 조회합니다."""
        target_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        res = self._client.databases.query(
            database_id=self._job_db_id,
            filter={"property": "모집 마감 기간", "date": {"equals": target_date}},
        )
        return res["results"]

    def get_docs_expiring_in(self, days: int) -> list[dict]:
        """하단 서류 작성 DB에서 N일 후 서류 마감 항목을 조회합니다."""
        target_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        res = self._client.databases.query(
            database_id=self._doc_db_id,
            filter={"property": "서류 마감 기한", "date": {"equals": target_date}},
        )
        return res["results"]

    def get_all_jobs(self) -> list[dict]:
        res = self._client.databases.query(database_id=self._job_db_id)
        return res["results"]
