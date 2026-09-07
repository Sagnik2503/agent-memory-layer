from datetime import date as dt

from sqlalchemy import Float, Date, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class ExpenseDB(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)
    merchant: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[dt | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
