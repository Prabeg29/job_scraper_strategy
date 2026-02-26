from fastapi import Request

from .database import db_conn
from .job_scrapers import JobScraper


async def get_db_connection():
    async with db_conn() as conn:
        yield conn


def get_job_registry(request: Request) -> JobScraper:
    return request.app.state.scraper_registry
