from dataclasses import dataclass

from fastapi import APIRouter, Depends, status
from playwright.async_api import async_playwright

from .deps import get_job_registry
from .job_scrapers import ScraperRegistry
from .settings import settings


job_scrape_router = APIRouter(prefix="/jobs", tags=["Jobs"])


@dataclass
class JobScrapePayload:
    job_url: str


@job_scrape_router.post("/scrape", status_code=status.HTTP_200_OK)
async def scrape_job(
    payload: JobScrapePayload,
    scraper_registry: ScraperRegistry = Depends(get_job_registry),
):
    job_scraper = scraper_registry.resolve(payload.job_url)
    async with async_playwright() as p:
        browser = await p.firefox.connect(
            ws_endpoint=settings.browerless_ws,
        )
        try:
            page = await browser.new_page()
        
            await page.route("**/*.{png,jpg,jpeg,gif,css,woff2}", lambda route: route.abort())
            await page.goto(
                url=payload.job_url,
                wait_until="domcontentloaded",
            )
            job_data = await job_scraper.scrape(page)
        finally:
            await browser.close()

    return {
        "message": "Job data scraped successfully",
        "job_data": job_data
    }
