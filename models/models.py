from sqlalchemy import (
    Integer,
    Float,
    DateTime,
    ForeignKey,
    String,
    Date,
    Boolean,
    BigInteger,
)
from datetime import datetime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from models.database import Base


class BaseContract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String)
    contract_type: Mapped[str] = mapped_column(String)  # polymorphic column

    to_trade: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    __mapper_args__ = {"polymorphic_on": "contract_type"}  # polymorphic discriminator


class Stock(BaseContract):
    conId: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    spread_around_spot: Mapped[float | None] = mapped_column(
        Float, default=2, nullable=True
    )

    __mapper_args__ = {
        "polymorphic_identity": "Stock",
    }


class Option(BaseContract):
    # __tablename__ = "options"

    lastTradeDateOrContractMonth: Mapped[datetime | None] = mapped_column(
        Date, nullable=True
    )
    strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    right: Mapped[str | None] = mapped_column(String, nullable=True)

    underlying_id: Mapped[int | None] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), nullable=True
    )
    underlying: Mapped[BaseContract] = relationship(
        "BaseContract"
    )  # references 'Stock', 'Option', 'Future'

    __mapper_args__ = {
        "polymorphic_identity": "Option",
    }


class Future(BaseContract):
    # Only supports Continuous Futures

    __mapper_args__ = {
        "polymorphic_identity": "Future",
    }


class Index(BaseContract):
    __mapper_args__ = {
        "polymorphic_identity": "Index",
    }


class Forex(BaseContract):
    __mapper_args__ = {
        "polymorphic_identity": "Forex",
    }


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
    bar_size: Mapped[int] = mapped_column(Integer)  # In minutes

    data_type: Mapped[str] = mapped_column(String)

    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    contract: Mapped[BaseContract] = relationship(
        "BaseContract"
    )  # references 'Stock', 'Option', 'Future', 'Forex'

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
