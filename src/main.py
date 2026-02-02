import time
import uuid

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from .api import job_scrape_router
from .job_scrapers import ScraperRegistry, SeekJobScraper
from .logger import REQUEST_ID_CTX, logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    ScraperRegistry.register("seek.com.au", SeekJobScraper)

    app.state.scraper_registry = ScraperRegistry

    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = request.headers.get("X-REQUEST-ID") or str(uuid.uuid4())
    REQUEST_ID_CTX.set(req_id)

    start = time.perf_counter()

    response = await call_next(request)
    
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "HTTP Request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
    )
    response.headers["X-REQUEST-ID"] = req_id
    return response


app.include_router(job_scrape_router)
