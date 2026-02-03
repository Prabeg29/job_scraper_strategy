import logging

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Page, TimeoutError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .logger import logger


class JobScraper(ABC):
    @abstractmethod
    async def scrape(self, page) -> dict[str, Any]:
        pass


class SeekJobScraper(JobScraper):
    @retry(
        before_sleep=before_sleep_log(logger=logger, log_level=logging.WARNING,),
        retry=retry_if_exception_type(TimeoutError),
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def scrape(self, page: Page) -> dict[str, Any]:
        title = await page.locator('h1[data-automation="job-detail-title"]').inner_text()
        company = await page.locator('span[data-automation="advertiser-name"]').inner_text()
        location = await page.locator('span[data-automation="job-detail-location"]').inner_text()
        details = await page.locator('div[data-automation="jobAdDetails"]').all_text_contents()

        return {
            "title": title, 
            "company": company,
            "location": location,
            "details": details,
        }


class ScraperRegistry:
    _registry: dict[str, type[JobScraper]] = {}

    @classmethod
    def register(cls, domain: str, scraper: type[JobScraper]) -> None:
        cls._registry[domain] = scraper

    @classmethod
    def resolve(cls, domain: str) -> JobScraper:
        parsed_domain = urlparse(domain)
        hostname = parsed_domain.netloc.replace("www.", "")

        if not hostname:
            raise ValueError("URL has no valid hostname")
        
        scraper = cls._registry.get(hostname)

        if not scraper:
            raise ValueError(f"No registered scraper for domain: {domain}")

        return scraper()
