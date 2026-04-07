from sqlmodel import SQLModel, create_engine

from app.mongo import get_mongo_db
from app.settings import settings

engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    if settings.storage_backend.strip().lower() == "mongodb":
        db = get_mongo_db()
        db.sessions.create_index("id", unique=True)
        db.sessions.create_index("started_at")
        db.metric_points.create_index([("session_id", 1), ("t_ms", 1)])
        return

    from app.db_models import Session, MetricPoint  # noqa: F401

    SQLModel.metadata.create_all(engine)

