from ib_insync import Contract, IB, BarDataList
import math
from typing import List
from models.models import PriceBar
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from pytz import timezone


# Function to get the latest price for a given contract from IB
def get_latest_price(contract: Contract, ib: IB):
    # Request market data for the contract
    market_data = ib.reqMktData(contract, "", False, False)

    cur_iter = 0

    # Wait until valid data is received or after 20 iterations (to avoid infinite loop)
    while (market_data.last is None or math.isnan(market_data.last)) and cur_iter < 20:
        ib.sleep(0.1)  # Sleep for 100 ms before checking again
        cur_iter += 1

    # Return the last price once received
    return market_data.last


# Function to retrieve historical bars for a given contract from IB
def get_historical_bars(
    ib: IB,
    contract: Contract,
    whatToShow: str,
    endDateTime: str = "",
    durationStr: str = "1 D",
    barSizeSetting: str = "1 min",
    useRTH: bool = False,
    formatDate: int = 1,
) -> BarDataList:
    # Request historical data for the contract (e.g., 1-minute bars for 1 day)
    print(durationStr)
    return ib.reqHistoricalData(
        contract,
        endDateTime=endDateTime,
        durationStr=durationStr,  # Example: 1 day of data
        barSizeSetting=barSizeSetting,  # Example: 1-minute bars
        whatToShow=whatToShow,  # Type of data to request (e.g., bid/ask)
        useRTH=useRTH,  # Whether to use Regular Trading Hours
        formatDate=formatDate,  # Format the dates as integers
    )


# Function to check if a price bar already exists in the database for a specific date and contract
def check_bar_exists(
    db: Session,
    date: date,
    contract_id: str,
    contract_type: str,
    data_type: str,
    bar_size: int,
) -> PriceBar:
    # Query the database to check if a price bar with the same contract, date, data type, and bar size exists
    return (
        db.query(PriceBar)
        .filter(
            PriceBar.contract_id == contract_id,
            PriceBar.date == date,
            PriceBar.data_type == data_type,
            PriceBar.bar_size == bar_size,
        )
        .first()  # Return the first matching record
    )


# Function to retrieve historical price bars and add them to the database if not already present
def get_add_price_bars(
    ib: IB,
    contract: Contract,
    data_type: str,
    contract_id: str,
    contract_type: str,
    bar_size: int,
    bars_to_create: List,
    db: Session,
):
    # Check the most recent price bar in the database for this contract
    last_bar = db.query(PriceBar).filter(
        PriceBar.bar_size == bar_size,
        PriceBar.data_type == data_type,
        PriceBar.contract_id == contract_id,
    )

    durationStr = "1 D"  # Default duration

    # Adjust duration based on contract type (longer for certain types)
    if contract_type in ["Stock", "Index", "Forex", "Future"]:
        durationStr = "10 D"

    # Order by date descending and get the last bar
    last_bar = last_bar.order_by(PriceBar.date.desc()).first()

    # If we have a last bar, calculate the time difference and adjust duration accordingly
    if last_bar:
        difference = datetime.now(timezone("America/New_York")) - last_bar.date
        difference_insec = difference.total_seconds()

        # Set duration based on the time difference since the last bar
        if difference_insec < 3600:
            durationStr = (
                f"{math.ceil(difference_insec / 60) * 60} S"  # Seconds duration
            )
        else:
            durationStr = (
                f"{math.ceil(difference_insec / 3600 / 6.5)} D"  # Days duration
            )

    # Fetch all existing bars for the contract in the relevant time range from the database
    existing_bars = get_existing_bars(db, contract_id, data_type, bar_size)

    # Convert existing bars to a set of bar dates for fast lookup
    existing_bar_dates = {bar.date for bar in existing_bars}

    # Fetch historical bars from IB based on the adjusted duration
    for bar in get_historical_bars(
        ib,
        contract,
        data_type,
        durationStr=durationStr,
        barSizeSetting=f"{bar_size} mins",
    ):
        # Skip bars that are too recent or already exist in the fetched set of existing bars
        if (
            bar.date + timedelta(minutes=bar_size)
            > datetime.now(timezone("America/New_York"))
            or bar.date in existing_bar_dates
        ):
            continue

        # Append new price bars to the list to be added to the database
        bars_to_create.append(
            PriceBar(
                contract_id=contract_id,
                date=bar.date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                bar_size=bar_size,
                data_type=data_type,
            )
        )

    return bars_to_create


def get_existing_bars(db: Session, contract_id: int, data_type: str, bar_size: int):
    # Query the database for all bars that match the contract_id, data_type, and bar_size
    return (
        db.query(PriceBar)
        .filter(
            PriceBar.contract_id == contract_id,
            PriceBar.data_type == data_type,
            PriceBar.bar_size == bar_size,
        )
        .all()
    )


# Function to retrieve price bars from the database based on specific criteria
def get_price_bars_from_db(
    db: Session,
    contract_id: str,
    data_type: str,
    bar_size: int,
    order: str,
    limit: int,
) -> List[PriceBar]:
    # Query price bars from the database based on the contract ID, data type, and bar size
    query = (
        db.query(PriceBar)
        .filter(
            PriceBar.data_type == data_type,
            PriceBar.bar_size == bar_size,
            PriceBar.contract_id == contract_id,
        )
        .order_by(
            PriceBar.date.desc()
        )  # Always order by date descending first to get latest bars
    )

    # Apply the limit to get the most recent 'limit' bars
    if limit > 0:
        recent_bars = query.limit(limit).all()
    else:
        recent_bars = query.all()

    # Return the bars in the requested order: if 'desc', keep descending, else reverse to ascending
    if order == "desc":
        return recent_bars  # Already in descending order
    else:
        return recent_bars[::-1]  # Reverse to ascending order
