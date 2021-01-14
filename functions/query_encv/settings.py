import os
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    encv_api_key: Optional[str] = None
    log_level: str = "INFO"

    class Config:
        env_file = Path('.') / '.env.prod'


settings = Settings()
