from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import os


class Database:
    def __init__(self, database_url: str | None = None):
        url = database_url or os.getenv(
            "DATABASE_URL",
            "sqlite:///./manus.db"
        )
        self.engine = create_engine(
            url,
            poolclass=QueuePool if "postgresql" in url else None,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def create_tables(self):
        from manus.queue.models import Base
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


_db: Database | None = None


def get_database(database_url: str | None = None) -> Database:
    global _db
    if _db is None:
        _db = Database(database_url)
    return _db


def init_database(database_url: str | None = None) -> Database:
    db = get_database(database_url)
    db.create_tables()
    return db
