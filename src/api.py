import logging

from dataclasses import dataclass

from fastapi import APIRouter, Depends, status
from playwright.async_api import TimeoutError, async_playwright
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .deps import get_job_registry
from .job_scrapers import ScraperRegistry
from .logger import logger
from .settings import settings


job_scrape_router = APIRouter(prefix="/jobs", tags=["Jobs"])


@retry(
    before_sleep=before_sleep_log(logger=logger, log_level=logging.ERROR),
    retry=retry_if_exception_type(TimeoutError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def _scrape_job(job_url: str, job_scraper):
    async with async_playwright() as p:
        browser = await p.firefox.connect(
            ws_endpoint=settings.browerless_ws,
        )
        try:
            page = await browser.new_page()
        
            await page.route("**/*.{png,jpg,jpeg,gif,css,woff2}", lambda route: route.abort())
            await page.goto(
                url=job_url,
                wait_until="domcontentloaded",
            )
            return await job_scraper.scrape(page)
        finally:
            await browser.close()


@dataclass
class JobScrapePayload:
    job_url: str


@job_scrape_router.post("/scrape", status_code=status.HTTP_200_OK)
async def scrape_job(
    payload: JobScrapePayload,
    scraper_registry: ScraperRegistry = Depends(get_job_registry),
):
    job_scraper = scraper_registry.resolve(payload.job_url)

    job_data = await _scrape_job(payload.job_url, job_scraper)

    return {
        "message": "Job data scraped successfully",
        "job_data": job_data
    }
