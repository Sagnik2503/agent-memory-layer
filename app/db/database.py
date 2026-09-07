from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./expense.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

Sessionlocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with Sessionlocal() as db:
        yield db
