#!/usr/bin/env python3
"""
This script pulls data from the encv server, prints the results to stdout, and pushes the data to a postgres database.
It relies on various environment variables to be set in order to get access to remote resources. These can be seen
immediately below.
"""

import json
import logging
import sys
from typing import Dict

import pandas as pd
from flask import jsonify

from encv_to_db.models import ENCVStat
from encv_to_db.settings import settings
from encv_to_db.SQLAlchemyDB import SQLAlchemyDB

logging.basicConfig(
    level=settings.log_level
)
logger = logging.getLogger()

# [START functions_encv_to_db_setup]

def get_credentials_info() -> Dict[str, str] :
    credentials_info = None
    if settings.google_application_credentials_json:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS_JSON key found, loading directly from this")
        credentials_info = json.loads(settings.google_application_credentials_json)
    elif settings.google_application_credentials:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS supplied, using this")
        with open(settings.google_application_credentials) as f:
            credentials_info = json.load(f)
    else:
        logger.info("No credentials supplied! Exiting")
        sys.exit()
    logger.debug(f"Credentials info: {credentials_info}")
    return credentials_info

project = "co-metrics-workflow" # "covidtech-public-assets"
dataset = "encv"
database_path = f"bigquery://{project}/{dataset}"
credentials_info = get_credentials_info()
db = SQLAlchemyDB(database_path=database_path, credentials_info=credentials_info)

# [END functions_encv_to_db_setup]


def flatten_data(entry: Dict[str, object]):
    new_obj = {}
    new_obj["date"] = entry["date"]
    for data_point, val in entry["data"].items():
        new_obj[data_point] = val
    del new_obj["code_claim_age_distribution"]
    return new_obj

# [START functions_encv_to_db]
def encv_to_db(request):
    global db 
    
    request_json = request.get_json(silent=True)

    logger.info(f"Incoming event: {request_json}")
    data = map(flatten_data, request_json)
    stats_df = pd.json_normalize(data)

    db.create_tables()
    success = db.upsert(stats_df=stats_df, Table=ENCVStat)
    return jsonify({"success": success})
# [END functions_encv_to_db]



if __name__ == "__main__":
    with open("data.json", "r") as infile:
        data = json.load(infile)
    print(encv_to_db(data))