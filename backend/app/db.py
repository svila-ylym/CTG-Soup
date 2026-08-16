"""Database engine, optional local provisioning, and session lifecycle."""

import logging
from typing import Generator

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import make_url
from sqlmodel import SQLModel, Session, create_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


def ensure_database_exists(database_url: str, enabled: bool) -> None:
    """Create a missing PostgreSQL database when local provisioning is enabled."""
    if not enabled:
        return

    url = make_url(database_url)
    if not url.drivername.startswith("postgresql") or not url.database:
        return

    database_name = url.database
    maintenance_url = url.set(database="postgres")
    connect_args = maintenance_url.translate_connect_args(
        username="user",
        database="dbname",
    )
    connect_args.update(maintenance_url.query)
    connection = psycopg2.connect(**connect_args)
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
                )
                logger.info("Created local PostgreSQL database %s", database_name)
    finally:
        connection.close()


def init_db() -> None:
    """Provision the local database when enabled, then create missing tables."""
    ensure_database_exists(DATABASE_URL, settings.AUTO_CREATE_DATABASE)
    SQLModel.metadata.create_all(bind=engine)
    # Bring pre-existing tables up to the fields used by current models.
    from app.migrations.competition_judging import ensure_competition_judging_schema
    from app.migrations.hall_of_fame import ensure_hall_of_fame_schema

    ensure_competition_judging_schema(engine)
    ensure_hall_of_fame_schema(engine)


def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
