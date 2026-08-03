import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base

def get_engine(db_path='dealsourcing.db'):
    # 현재 디렉토리 기준
    return create_engine(f'sqlite:///{db_path}', echo=False)

def init_db(db_path='dealsourcing.db'):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()
