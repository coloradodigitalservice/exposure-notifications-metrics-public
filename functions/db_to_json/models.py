
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


@dataclass
class ENCVStat(Base):
    '''
    Object representing ENCV stat - 
    TODO: use for writing as well
    '''
    __tablename__ = "aphl_codes"
    id: int = Column(Integer, primary_key=True)
    date: datetime = Column(DateTime, unique=True)
    codes_claimed: int = Column(Integer, nullable=False)
    codes_issued: int = Column(Integer, nullable=False)
