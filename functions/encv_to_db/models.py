
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


@dataclass
class ENCVStat(Base):
    '''
    Object representing ENCV stat
    '''
    __tablename__ = "aphl_codes"
    date: datetime = Column(TIMESTAMP, nullable=False, primary_key=True)
    codes_claimed: int = Column(Integer, nullable=False)
    codes_issued: int = Column(Integer, nullable=False)
    codes_invalid: int = Column(Integer, nullable=False)
    code_claim_mean_age_seconds: int = Column(Integer, nullable=False)
    tokens_claimed: int = Column(Integer, nullable=False)
    tokens_invalid: int = Column(Integer, nullable=False)

