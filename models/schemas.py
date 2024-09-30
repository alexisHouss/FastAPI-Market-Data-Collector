from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from ib_insync import Option as IBOption
import pytz


class Contract(BaseModel):
    id: Optional[int] = None
    symbol: str
    exchange: Optional[str] = "SMART"
    conId: Optional[int] = None
    currency: Optional[str] = "USD"
    to_trade: Optional[bool] = True


class IBOptionWithID(BaseModel):
    option: IBOption
    db_id: int


class PriceBar(BaseModel):
    id: Optional[int] = None
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    @field_validator("date", mode="before")
    def convert_to_ny_time(cls, value):
        # Define the New York time zone
        ny_tz = pytz.timezone("America/New_York")

        # If the date is naive (no timezone), assume it's in UTC and convert
        if value.tzinfo is None:
            value = pytz.utc.localize(value)

        # Convert to New York time zone
        return value.astimezone(ny_tz)
