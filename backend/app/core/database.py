import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

# Engine configuration. Production is explicitly PostgreSQL-only; SQLite is
# retained for local development/tests and never selected as a fallback.
database_url = settings.DATABASE_URL.strip()
if settings.ENVIRONMENT.lower() in ("production", "prod") and database_url.startswith("sqlite"):
    raise RuntimeError("Production requires a PostgreSQL DATABASE_URL; SQLite is development-only.")

connect_args = {}
engine_options = {"pool_pre_ping": True}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif database_url.startswith(("postgresql://", "postgresql+psycopg2://", "postgresql+psycopg://")):
    engine_options.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
    })
    # Optional libpq SSL settings are passed through the URL query string.
    sslmode = settings.DB_SSLMODE.strip()
    if sslmode:
        parts = urlsplit(database_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault("sslmode", sslmode)
        database_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
else:
    raise RuntimeError("Unsupported DATABASE_URL scheme. Use PostgreSQL in production or SQLite in development.")

engine = create_engine(database_url, connect_args=connect_args, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
