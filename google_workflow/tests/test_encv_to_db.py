"""Tests the data transformation logic in the code used for writing encv data to a database
"""

import datetime

import app as encv_to_db
import factory
import factory.fuzzy as fuzzy
import pandas as pd
import pytest
from models import ENCVStat
from sqlalchemy import create_engine


@pytest.fixture
def sample_df() -> pd.DataFrame:
    class StatFactory(factory.Factory):
        class Meta:
            model = ENCVStat

        date = fuzzy.FuzzyDateTime(
            datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc))
        codes_claimed = fuzzy.FuzzyInteger(0, 42)
        codes_issued = fuzzy.FuzzyInteger(0, 10000)
        codes_invalid = fuzzy.FuzzyInteger(0, 10000)
        code_claim_mean_age_seconds = fuzzy.FuzzyInteger(0, 10000)
        tokens_claimed = fuzzy.FuzzyInteger(0, 10000)
        tokens_invalid = fuzzy.FuzzyInteger(0, 10000)

    sample_data_iterable = [factory.build(dict, FACTORY_CLASS=StatFactory) for x in range(5)]
    sample_data_df = pd.json_normalize(sample_data_iterable)
    sample_data_df.date = pd.to_datetime(sample_data_df.date)
    sample_data_df = sample_data_df.sort_values("date")
    sample_data_df.reset_index(drop=True,
                               inplace=True)  # Index was mutated by the sort, which isn't helpful in this case
    return sample_data_df


def extract_input(event):
    """
    Returns the data from an object organized in the manner expected
    """
    return event.get("body").get("data")


class SQLiteDB(encv_to_db.SQLAlchemyDB):
    def __init__(self):
        self.database_path = "sqlite://"
        self.engine = create_engine(self.database_path)
        self.session = self.create_session()


def sqlite_compatible_read(db):
    records = db.session.query(ENCVStat).all()
    result_df = pd.DataFrame.from_records([record.__dict__ for record in records])
    result_df.date = pd.DatetimeIndex(result_df.date).tz_localize('UTC')
    result_df = result_df.drop('_sa_instance_state', axis=1)  # Ignore the '_sa_instance_state' column
    return result_df


def test_db_insert(sample_df: pd.DataFrame) -> None:
    """
    Tests insertion of several rows of sample data.
    Confirms that the expected values are stored in the DB.
    """
    db = SQLiteDB()
    encv_to_db.push_to_db(db, sample_df)
    result_df = sqlite_compatible_read(db)
    result_df = result_df[sample_df.columns]  # Reorder columns to match expected data
    assert result_df.equals(sample_df)


def test_db_update(sample_df: pd.DataFrame) -> None:
    """
    Inserts several rows of sample data into the DB.
    Overrides one of the values, updates the DB, and confirms that the DB holds the final correct values.
    """
    db = SQLiteDB()
    encv_to_db.push_to_db(db, sample_df)
    sample_df.loc[0, 'codes_claimed'] = 827
    encv_to_db.push_to_db(db, sample_df)
    result_df = sqlite_compatible_read(db)
    result_df = result_df[sample_df.columns]  # Reorder columns to match expected data
    assert result_df.equals(sample_df)
