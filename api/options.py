from fastapi import APIRouter, Depends, HTTPException, Query
from models import schemas
from models.database import get_db
from sqlalchemy.orm import Session
from services import prices_service, options_service
from typing import List

# Create an API router for handling Options-related requests
router = APIRouter()


# Get available expiration dates for a given options symbol
@router.get("/{symbol}", response_model=List[str])
def get_options_expiration_dates(
    symbol: str,
    db: Session = Depends(get_db),
):
    # Retrieve expiration dates for the options of a given symbol from the database
    expiration_dates = options_service.get_option_expiration_dates(db, symbol)

    return expiration_dates


# Get available strike prices for a given options symbol and expiration date
@router.get("/{symbol}/{expiration_date}/strikes", response_model=List[float])
def get_options_strikes(
    symbol: str,
    expiration_date: str,
    db: Session = Depends(get_db),
):
    # Retrieve the strike prices for the given symbol and expiration date
    strikes = options_service.get_options_strikes(db, symbol, expiration_date)

    return strikes


# Get price bars (e.g., ask, bid, trades) for a specific option contract
@router.get(
    "/{symbol}/{expiration_date}",
    response_model=List[schemas.PriceBar],
)
def get_options_prices_by_symbol(
    symbol: str,
    expiration_date: str,
    strike: float = Query(
        ..., description="Strike price"
    ),  # Query parameter for the option's strike price
    right: str = Query(
        ..., description="Right e.g., CALL, PUT"
    ),  # Query parameter for option type (CALL/PUT)
    data_type: str = Query(
        ..., description="Data type e.g., ASK, BID, TRADES"
    ),  # Query for the type of price data
    bar_size: int = Query(
        ..., description="Bar size in minutes"
    ),  # Query for the size of the price bars
    order: str = Query(
        "desc", description="Order of the bars"
    ),  # Query for the order of price bars (default desc)
    limit: int = Query(
        500, description="Number of bars to return"
    ),  # Limit the number of price bars returned
    db: Session = Depends(get_db),
):
    # Retrieve the option contract based on the provided symbol, expiration date, strike price, and option right
    contract = options_service.get_option_contract_db(
        db, symbol, expiration_date, strike, right
    )

    # If the contract is not found, raise a 404 error
    if contract is None:
        raise HTTPException(status_code=404, detail="Option contract not found")

    # Retrieve price bars (historical data) from the database for the option contract
    bars = prices_service.get_price_bars_from_db(
        db, contract.id, data_type, bar_size, order, limit
    )

    return bars
