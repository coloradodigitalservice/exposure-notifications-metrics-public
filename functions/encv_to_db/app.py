#!/usr/bin/env python3

"""
This script pulls data from the encv server, prints the results to stdout, and pushes the data to a BigQuery database.
It relies on the following configuration parameters:
* GOOGLE_APPLICATION_CREDENTIALS_JSON a json string with the entire set of Google project credentials, which can be
  obtained for your project using the instructions at: https://cloud.google.com/docs/authentication/getting-started
  If provided, this takes precedence over GOOGLE_APPLICATION_CREDENTIALS.
* GOOGLE_APPLICATION_CREDENTIALS the name of a file with a Google project credentials JSON string inside it. This can be
  used in lieu of GOOGLE_APPLICATION_CREDENTIALS_JSON.
* GOOGLE_APPLICATION_CREDENTIALS_SECRET if neither of the above two settings are supplied, this should contain the name
  of a secret stored in AWS secrets manager, with the value of the secret containing the full Google project credentials
  JSON string.
* GOOGLE_CLOUD_PROJECT the name for the Google Cloud project in which your BigQuery database is hosted.
* GOOGLE_CLOUD_DATASET the name of the dataset inside your BigQuery database.

"""
import json
import logging
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from models import Base, ENCVStat
from secrets_manager import SecretsManager
from settings import settings

logging.basicConfig(
    level=settings.log_level
)
logger = logging.getLogger()


class SQLAlchemyDB:
    def __init__(self, database_path: str, credentials_info: Dict[str, str] ):
        self.database_path = database_path
        self.engine = create_engine(self.database_path, credentials_info=credentials_info)
        self.session = self.create_session()

    def create_session(self) -> Session:
        """
        Creates a session with the configured database
        """
        logger.info("Creating session...")
        Session = sessionmaker(bind=self.engine)
        session = Session()
        return session

    def read(self, Table: DeclarativeMeta) -> pd.DataFrame:
        """Read all data from DB"""
        logger.info("Fetching records...")
        records = self.session.query(Table).all()
        logger.info(f"Retrieved the following records: {records}")

        df = pd.DataFrame.from_records([record.__dict__ for record in records])
        df.date = pd.DatetimeIndex(df.date).tz_convert('UTC')
        return df

    def upsert(self, stats_df: pd.DataFrame, Table: DeclarativeMeta) -> bool:
        """
        Adds or updates rows in the database.

        stats_df : A dictionary or list of dictionaries where the keys must at least include 'date'
        """
        success = True
        logger.info("Upserting data...")
        supported_fields = set(f.name for f in Table.__table__.columns)
        input_fields = set(stats_df.columns)
        stats_df = stats_df.loc[:, supported_fields & input_fields]
        try:
            data_objects = []
            for index_row_pair in stats_df.iterrows():
                row = index_row_pair[1]
                db_row = self.session.query(Table).filter(
                    Table.date == row.date).first()
                row_dict = row.to_dict()
                logger.debug(f"Processing {row_dict}...")
                if db_row is None:
                    # This date is not yet in the database. Add a new entry.
                    data_obj = Table(**row_dict)
                    logger.info(f"Adding {data_obj} to the session...")
                    data_objects.append(data_obj)
                else:
                    # This date is already in the database. Update anything that has changed.
                    for key in row.drop('date').keys():
                        if row[key] != getattr(db_row, key):
                            logger.info(
                                f"Updating {row.date} {key} from {getattr(db_row, key)} to {row[key]}")
                            setattr(db_row, key, row[key])
            self.session.add_all(data_objects)
            self.session.commit()
        except Exception as e:
            logger.error(f"Error writing to database: {e}")
            success = False
        return success

    def drop_table(self, Table: DeclarativeMeta):
        """Drops a given table"""
        logger.info(f"Dropping table {Table}...")
        Table.__table__.drop(self.engine)

    def create_tables(self):
        """Create tables from this session"""
        logger.info("Creating tables...")
        Base.metadata.create_all(self.engine)

    @property
    def row_count(self, Table: DeclarativeMeta) -> int:
        """Return number of rows"""
        logger.info(f"Obtaining row count for {Table}...")
        return len(self.read(Table))


def push_to_db(db: SQLAlchemyDB, stats_df: pd.DataFrame) -> bool:
    """
    Adds or updates rows in the database.

    session : SQLAlchemy Session
    data : A dictionary or list of dictionaries where the keys must at least include 'date', and
        will typically also have at least 'codes_claimed' and 'codes_issued'.
    """
    db.create_tables()
    success = db.upsert(stats_df=stats_df, Table=ENCVStat)
    return success

def flatten_data(entry: Dict[str, object]):
    new_obj = {}
    new_obj["date"] = entry["date"]
    for data_point, val in entry["data"].items():
        new_obj[data_point] = val
    del new_obj["code_claim_age_distribution"]
    return new_obj

def get_credentials_info() -> Dict[str, str] :
    secrets_manager = SecretsManager()
    credentials_info = None
    if settings.google_application_credentials_json:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS_JSON key found, loading directly from this")
        credentials_info = json.loads(settings.google_application_credentials_json)
    elif settings.google_application_credentials:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS supplied, using this")
        with open(settings.google_application_credentials) as f:
            credentials_info = json.load(f)
    else:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS key not found, querying secrets manager...")
        credentials_info = secrets_manager.get(
            secret_name=settings.GOOGLE_APPLICATION_CREDENTIALS_SECRET)
    logger.debug(f"Credentials info: {credentials_info}")
    return credentials_info

def lambda_handler(event, context):
    logger.info(f"Incoming event: {event}")
    data = map(flatten_data, event)
    stats_df = pd.json_normalize(data)
    project = settings.GOOGLE_CLOUD_PROJECT
    dataset = settings.GOOGLE_CLOUD_DATASET
    database_path = f"bigquery://{project}/{dataset}"
    credentials_info = get_credentials_info()
    db = SQLAlchemyDB(database_path=database_path, credentials_info=credentials_info)
    success = push_to_db(db, stats_df)
    return {
        "statusCode": 200,
        "body": {
            "success": success
        }
    }


def main():
    with open("data.json", "r") as infile:
        data = json.load(infile)
    print(lambda_handler(data, None))


if __name__ == "__main__":
    main()
