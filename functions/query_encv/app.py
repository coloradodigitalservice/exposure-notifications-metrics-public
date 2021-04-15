#!/usr/bin/env python3

"""
This script pulls data from the encv server

It relies on the following configuration parameters:
* ENCV API a string with the API key for encv.org.
or
* ENCV_SECRET_NAME and ENCV_SECRET_KEY the secret name and key in AWS secrets manager which holds the encv.org API key.

"""


import json
import logging
from typing import Dict

import requests
from requests.exceptions import HTTPError

from secrets_manager import SecretsManager
from settings import settings

logging.basicConfig(
    level=settings.log_level
)
logger = logging.getLogger()


def get_encv_stats() -> Dict[str, object]:
    """
    Retrieve statistics concerning issued codes, as outlined here:
    https://github.com/google/exposure-notifications-verification-server/blob/main/docs/api.md#apistats-preview

    Includes data for the previous month.
    """
    base_url = "adminapi.encv.org"
    encv_stats_url = f"https://{base_url}/api/stats/realm.json"
    headers = {
        "content-type": "application/json",
        "accept": "application/json",
        "x-api-key": settings.encv_api_key,
    }
    try:
        logger.info("Calling ENCV API...")
        response = requests.get(encv_stats_url, headers=headers)
        response.raise_for_status()
        return response.json().get("statistics")
    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        raise
    except Exception as err:
        logger.error(f"Other error occurred: {err}")
        raise
    finally:
        logger.info("encv call completed")


def lambda_handler(event, context):
    secrets_manager = SecretsManager()
    if not settings.encv_api_key:
        logger.info("ENCV API key not found, querying secrets manager...")
        settings.encv_api_key = secrets_manager.get(
            secret_name=settings.ENCV_SECRET_NAME, secret_key=settings.ENCV_SECRET_KEY)
    data = get_encv_stats()
    return {
        "statusCode": 200,
        "body": {
            "data": data
        }
    }


def main():
    print(json.dumps(lambda_handler(None, None)))


if __name__ == "__main__":
    main()
