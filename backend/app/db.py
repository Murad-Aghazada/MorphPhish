from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .core.config import settings
connect_args={"check_same_thread":False} if settings.database_url.startswith("sqlite") else {}
engine=create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
if settings.database_url.startswith("sqlite"):
    # SQLite ignores foreign keys (and ON DELETE CASCADE) unless enabled per-connection.
    # Enable it so dev/test behaviour matches PostgreSQL.
    @event.listens_for(engine,"connect")
    def _sqlite_fk(dbapi_connection,_):
        cur=dbapi_connection.cursor(); cur.execute("PRAGMA foreign_keys=ON"); cur.close()
SessionLocal=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
class Base(DeclarativeBase): pass
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
