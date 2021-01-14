import logging
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from .models import Base

logger = logging.getLogger()

class SQLAlchemyDB:
    def __init__(self, database_path: str , credentials_info: Dict[str, str] ):
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
