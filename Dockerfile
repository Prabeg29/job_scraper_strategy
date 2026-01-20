# Stage: base
FROM python:3.14-alpine AS base

ARG UID=1000
ARG GID=1000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --gid ${GID} job_scraper && \
    useradd --uid ${UID} --gid ${GID}  --create-home --shell /bin/bash job_scraper

WORKDIR /opt/app

# Stage: dependencies
FROM base AS dependencies

COPY ./requirements.txt . 

RUN pip install --no-cache-dir -r requirements.txt

# Stage: runner
FROM base AS runner

COPY --from=dependencies /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin
COPY --chown=job_scraper:job_scraper . /opt/app/

USER job_scraper
