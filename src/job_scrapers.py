import logging
import re

from abc import ABC, abstractmethod
from typing import Any, override
from urllib.parse import (
    parse_qs,
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
)

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
    def normalize(self, url: str) -> str:
        NOISE_PARAMS = {
            "breadcrumbs",
            "fbclid",
            "gclid",
            "ref",
            "session_id",
            "utm_campaign",
            "utm_content",
            "utm_medium",
            "utm_source",
            "utm_term",
        }

        parsed_url = urlparse(url.strip())

        scheme = parsed_url.scheme.lower()
        netloc = parsed_url.netloc.lower()

        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = parsed_url.path

        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        query_params = [
            (k, v)
            for k, v in parse_qsl(parsed_url.query)
            if k.lower() not in NOISE_PARAMS
        ]

        query_params.sort()
        query = urlencode(query_params)

        return urlunparse((scheme, netloc, path, '', query, ''))

    @abstractmethod
    async def scrape(self, page) -> dict[str, Any]:
        pass


class SeekJobScraper(JobScraper):
    JOB_PATH_PATTERN = re.compile(r"^/job/(\d+)$")

    @override
    def normalize(self, url: str) -> str:
        job_id = None

        parsed_url = urlparse(super().normalize(url=url))
        query_params = parse_qs(parsed_url.query)

        job_id = query_params.get("jobId", None)

        if match := self.JOB_PATH_PATTERN.search(parsed_url.path):
            job_id = match.group(1)
        elif "jobId" in query_params:
            job_id = query_params["jobId"][0]
        
        if job_id:
            return f"https://www.seek.com.au/job/{job_id}"

        return urlunparse(parsed_url)

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
