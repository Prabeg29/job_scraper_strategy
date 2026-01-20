from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import job_scrape_router
from .job_scrapers import ScraperRegistry, SeekJobScraper


@asynccontextmanager
async def lifespan(app: FastAPI):
    ScraperRegistry.register("seek.com", SeekJobScraper)

    app.state.scraper_registry = ScraperRegistry

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(job_scrape_router)
