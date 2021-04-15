# /usr/bin/env python3

"""
This script pulls data from the postgres database, parses results as ENCVStat objects, and outputs a json representation of the data.

It relies on various environment variables / settings that can be seen below

TODO: Potentially replace with per-update polling / kinesis data stream ?
TODO: Potentially adopt filtering by command line arg
"""

import json
import logging
import os
from dataclasses import asdict
from typing import Dict, List

from models import ENCVStat
from settings import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

logger = logging.getLogger()
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO"))

def create_session() -> Session:
    """
    Creates a session with the configured database
    """
    logger.info("Creating session...")
    user_pass_str = f"{settings.pguser}:{settings.pgpassword}@" if settings.pgpassword else ""
    path = f"postgresql://{user_pass_str}{settings.pghost}/{settings.pgdatabase}"
    engine = create_engine(path)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def clean_stats(data):
    d = dict(data)
    d["date"] = str(d["date"])
    return d


def query_stats(session: Session) -> List[ENCVStat]:
    """
    Query our session to get all database ENCV Stat objects
    """
    logger.info("Querying stats...")
    stats_objects = session.query(ENCVStat).order_by(
        ENCVStat.date.asc())  # pylint disable=no-member
    logger.debug(f"Returned objects: {stats_objects}")
    stats = [asdict(stat_object, dict_factory=clean_stats)
             for stat_object in stats_objects]
    return stats


def stats_json(session: Session) -> List[Dict[str, object]]:
    """
    Returns a JSON representation of our stats data
    """
    results = query_stats(session)
    return json.dumps(results, default=str)


def lambda_handler(event, context):
    logger.info(f"Incoming event: {event}")
    session = create_session()
    return {
        "statusCode": 200,
        "body": {
            "data": query_stats(session)
        }
    }

def main():
    print(lambda_handler(None, None))

if __name__ == "__main__":
    main()
