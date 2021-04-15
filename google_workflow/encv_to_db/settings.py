import os
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    google_application_credentials_json: Optional[str] = None  # If supplied, we will read this json blob right away as the credentials
    google_application_credentials: Optional[str] = None # If supplied, we read from this file to get the json. If even this is not supplied, we will query secrets manager for the value
    log_level: str = "INFO"

    class Config:
        env_file = Path('.') / '.env.prod'


settings = Settings()
