from fastapi import Request

from .job_scrapers import JobScraper


def get_job_registry(request: Request) -> JobScraper:
    return request.app.state.job_registry
