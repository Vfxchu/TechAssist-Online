from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import get_settings

settings = get_settings()

# Handle SQLite specific arguments only if needed
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    engine = create_engine(settings.database_url, connect_args=_connect_args)
else:
    engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import models.ticket   # noqa: F401
    import models.message  # noqa: F401
    import models.solution # noqa: F401
    Base.metadata.create_all(bind=engine)
