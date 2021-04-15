"""Tests db json serialization logics
"""

import datetime
import json

import app as db_to_json
import factory.fuzzy as fuzzy
import pytest
from factory.alchemy import SQLAlchemyModelFactory
from models import Base, ENCVStat
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import scoped_session


@pytest.fixture
def stat_factory(mock_session):
    """
    Creates randomly-generated ENCVStat objects
    """

    class ENCVStatFactory(SQLAlchemyModelFactory):
        class Meta:
            model = ENCVStat
            sqlalchemy_session = mock_session

        date = fuzzy.FuzzyDateTime(
            datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc))
        codes_claimed = fuzzy.FuzzyInteger(0, 42)
        codes_issued = fuzzy.FuzzyInteger(0, 10000)

    return ENCVStatFactory


@pytest.fixture(scope="function")
def mock_session():
    """
    Removes the need to talk directly to the DB by using a local engine object
    """
    engine = create_engine('sqlite://', echo=True)
    Session = scoped_session(sessionmaker(bind=engine))
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_stats(mock_session, stat_factory) -> None:
    stats = stat_factory.create_batch(10)
    mock_session.add_all([*stats])
    mock_session.commit()
    actual_result = db_to_json.stats_json(mock_session)
    expected_stats = [{
        "id": stat.id,
        "date": str(stat.date),
        "codes_claimed": stat.codes_claimed,
        "codes_issued": stat.codes_issued
    } for stat in stats]
    expected_stats.sort(key=lambda x: x["date"])
    expected_result = json.dumps(expected_stats)
    assert actual_result == expected_result
