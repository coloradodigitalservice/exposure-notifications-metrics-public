import os
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    pghost: str
    pgdatabase: str
    pguser: str
    pgpassword: str

    class Config:
        env_file = Path('.') / '.env'


settings = Settings()
