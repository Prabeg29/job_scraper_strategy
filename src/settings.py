import os

from dotenv import load_dotenv
from redis import Redis

load_dotenv(verbose=True)


class Settings:
    app_name = os.getenv("APP_NAME", "Job Scraper")
    app_env = os.getenv("APP_ENV", "development")

    browerless_ws = os.getenv("BROWSERLESS_WS", "")
    
    db_dialect = os.getenv("DB_DIALECT", "postgresql")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", 5432)
    db_database = os.getenv("DB_DATABASE", "")
    db_pgschema = os.getenv("DB_PGSCHEMA", "")
    db_username = os.getenv("DB_USERNAME", "")
    db_password = os.getenv("DB_PASSWORD", "")

    @property
    def db_url(self) -> str:
        if not self.db_database:
            return ""

        return f"{self.db_dialect}://{self.db_username}:{self.db_password}@pgbouncer:{self.db_port}/{self.db_database}"


    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))

    @property
    def redis_conn(self):
        return Redis(host=self.redis_host, port=self.redis_port)
    
    log_level = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
