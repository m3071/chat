from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __allow_unmapped__ = True


# Import models so Alembic sees the full metadata graph.
from app.models import entities  # noqa: E402,F401
