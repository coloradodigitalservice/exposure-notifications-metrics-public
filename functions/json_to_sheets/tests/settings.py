from typing import Optional

from importlib_resources import files
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    These test settings allow you to specify an extra user who is added to the read permissions of a created
    spreadsheet. By default, spreadsheets created by the service account are only visible by the service account.
    This lets you add another user to see them.
    """
    extra_user: Optional[str]

    class Config:
        env_file = files("tests") / '.env'


settings = Settings()
