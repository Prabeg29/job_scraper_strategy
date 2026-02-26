from fastapi import status
from playwright.async_api import async_playwright
from psycopg.types.json import Json
from rq import Retry
from rq.decorators import job

from .database import db_conn
from .logger import logger
from .settings import settings


@job(
    queue="default",
    connection=settings.redis_conn,
    retry=Retry(max=3, interval=[1, 4, 10]),
)
async def scrape_job_details(
    job_scraper,
    normalized_url: str,
    url_hash: str,
):
    async with db_conn() as aconn:
        await aconn.execute(
            query="""
                UPDATE job_scraper.scraped_jobs
                SET status = 'scraping',
                    updated_at = NOW()
                WHERE url_hash = %s;
            """,
            params=(url_hash,)
        )

    async with async_playwright() as p:
        browser = await p.firefox.connect(
            ws_endpoint=settings.browerless_ws,
        )
        try:
            page = await browser.new_page()
        
            await page.route("**/*.{png,jpg,jpeg,gif,css,woff2}", lambda route: route.abort())
            resp = await page.goto(
                url=normalized_url,
                wait_until="domcontentloaded",
            )
            
            if (
                resp and 
                resp.status == status.HTTP_404_NOT_FOUND
            ):
                async with db_conn() as aconn:
                    await aconn.execute(
                        query="""
                            UPDATE job_scraper.scraped_jobs
                            SET status = 'scraped',
                                is_archived = true,
                                last_scraped_at = NOW(),
                                updated_at = NOW()
                            WHERE url_hash = %s;
                        """,
                        params=(url_hash,)
                    )
                return
            
            job_data = await job_scraper.scrape(page)
            
            async with db_conn() as aconn:
                await aconn.execute(
                    query="""
                        UPDATE job_scraper.scraped_jobs
                        SET scraped_data = %s,
                            status = 'scraped',
                            last_scraped_at = NOW(),
                            updated_at = NOW()
                        WHERE url_hash = %s;
                    """,
                    params=(Json(job_data), url_hash,)
                )
        except Exception:
            logger.info(
                "Scraping job details failed",
                exc_info=True,
                extra={
                    "normalized_job_url": normalized_url,
                    "url_hash": url_hash,
                }
            )
            async with db_conn() as aconn:
                await aconn.execute(
                    query="""
                        UPDATE job_scraper.scraped_jobs
                        SET status = 'failed',
                            last_scraped_at = NOW(),
                            updated_at = NOW()
                        WHERE url_hash = %s;
                    """,
                    params=(url_hash,)
                )
            raise
        finally:
            await browser.close()
