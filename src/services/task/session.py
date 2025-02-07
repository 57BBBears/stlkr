from sqlalchemy import NullPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, poolclass=NullPool)
Session_ = sessionmaker()


def get_session() -> Session:
    with Session_() as session:
        yield session
