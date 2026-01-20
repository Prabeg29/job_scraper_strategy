import os

from dotenv import load_dotenv

load_dotenv(verbose=True)


class Settings:
    app_name = os.getenv("APP_NAME", "Job Scraper")
    app_env = os.getenv("APP_ENV", "development")

    browerless_ws = os.getenv("BROWSERLESS_WS", "")
    
    log_level = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
