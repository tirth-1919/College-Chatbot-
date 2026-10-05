"""
Shared pytest configuration.

Historical note: the build machine exports a global DEBUG=release environment
variable. The application Settings now normalize unrecognized DEBUG values
safely (backend/app/core/config.py), so no environment mangling is required
here any more. This file is kept for future shared test fixtures.
"""
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from backend.app.core.database import Base, SessionLocal, engine

def _ensure_current_sqlite_schema():
    # ``create_all`` does not alter an existing database, so tests that use the
    # shared SQLite file can otherwise see a pre-automation schema. This is a
    # test-environment compatibility step only; PostgreSQL schema ownership
    # remains with Alembic.
    if engine.dialect.name != "sqlite":
        return
    import backend.app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        inspector = inspect(connection)
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {column["name"] for column in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                column_type = column.type.compile(dialect=engine.dialect)
                definition = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column_type}"
                if column.nullable:
                    connection.execute(text(definition))
                elif column.default is not None or column.server_default is not None:
                    connection.execute(text(definition + " DEFAULT 1"))
                else:
                    # Existing rows make a new required column unsafe; current
                    # test models should provide a default for such columns.
                    raise RuntimeError(f"Cannot add required test column {table.name}.{column.name}")

_ensure_current_sqlite_schema()

@pytest.fixture(scope="function")
def db():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    yield session
    session.close()
