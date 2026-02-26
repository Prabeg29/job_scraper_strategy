import uuid

from dataclasses import dataclass

from fastapi import APIRouter, Depends, status

from .deps import get_db_connection, get_job_registry
from .job_scrapers import ScraperRegistry
from .logger import logger
from .settings import settings
from .task import scrape_job_details
from .utils import hash_url

job_scrape_router = APIRouter(prefix="/jobs", tags=["Jobs"])


@dataclass
class JobScrapePayload:
    job_url: str


@job_scrape_router.post("/scrape", status_code=status.HTTP_202_ACCEPTED)
async def scrape_job(
    payload: JobScrapePayload,
    db_conn=Depends(get_db_connection),
    scraper_registry: ScraperRegistry = Depends(get_job_registry),
):
    job_scraper = scraper_registry.resolve(payload.job_url)
    normalized_url = job_scraper.normalize(url=payload.job_url)
    url_hash = hash_url(normalized_url=normalized_url)

    if settings.redis_conn.get(f"scrape:{url_hash}"):
        return { "message": "Request has been forwarded"}
    
    async with db_conn.cursor() as cur:
        await cur.execute(
            query="""
                INSERT INTO scraped_jobs (
                    id,
                    normalized_url,
                    url_hash,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (url_hash)
                DO UPDATE SET
                    status = 'queued',
                    updated_at = EXCLUDED.updated_at
                    WHERE scraped_jobs.last_scraped_at < NOW() - INTERVAL '24 hours'
                    AND scraped_jobs.is_archived = false
                    AND scraped_jobs.status NOT IN ('queued', 'scraping')
                RETURNING id;
            """, 
        params=(str(uuid.uuid4()), normalized_url, url_hash))

        row = await cur.fetchone()

    if row:
        logger.info(
            "Queued scraping job details",
            extra={
                "raw_job_url": payload.job_url,
                "normalized_job_url": normalized_url,
                "url_hash": url_hash,
            }
        )

        settings.redis_conn.set(f"scrape:{url_hash}", "1", ex=86400)
        scrape_job_details.delay( # type: ignore
            job_scraper,
            normalized_url,
            url_hash
        )

    return { "message": "Request has been forwarded"}
