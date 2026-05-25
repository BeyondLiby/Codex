"""数据库层（MVP 版本）。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import CONFIG

engine = create_engine(CONFIG.db.url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db_session():
    """获取数据库会话。"""
    return SessionLocal()
