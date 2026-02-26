#!/bin/bash
set -e

# Create custom schema
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS job_scraper;
    GRANT ALL ON SCHEMA job_scraper TO $POSTGRES_USER;
EOSQL

echo "Schema 'job_scraper' created successfully"
