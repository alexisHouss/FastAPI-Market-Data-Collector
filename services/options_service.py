from models import models
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List
from services import contracts_service, prices_service
from tasks import market_reader_tasks
from ib_insync import IB, Stock as ib_stock


def get_option_expiration_dates(db: Session, symbol: str) -> List[str]:
    """
    Retrieves distinct option expiration dates for a given stock symbol.

    Args:
        db (Session): Database session.
        symbol (str): The stock symbol to retrieve expiration dates for.

    Returns:
        List[str]: A list of expiration dates in 'YYYYMMDD' format.

    Raises:
        HTTPException: If the stock is not found.
    """
    # Get the stock contract by symbol
    stock = contracts_service.get_contract_by_symbol(db, symbol, "Stock")
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Query distinct expiration dates from options tied to the stock
    expiration_dates = (
        db.query(models.Option.lastTradeDateOrContractMonth)
        .filter(models.Option.underlying_id == stock.id)
        .distinct()
    )

    # Convert dates to 'YYYYMMDD' string format and return them as a list
    return [date[0].strftime("%Y%m%d") for date in expiration_dates]


def get_options_strikes(db: Session, symbol: str, expiration_date: str) -> List[float]:
    """
    Retrieves distinct strike prices for options of a given stock symbol and expiration date.

    Args:
        db (Session): Database session.
        symbol (str): The stock symbol to retrieve strikes for.
        expiration_date (str): The expiration date to filter strikes by.

    Returns:
        List[float]: A list of distinct strike prices.

    Raises:
        HTTPException: If the stock is not found.
    """
    # Get the stock contract by symbol
    stock = contracts_service.get_contract_by_symbol(db, symbol, "Stock")
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Query distinct strike prices for the given stock and expiration date
    strikes = (
        db.query(models.Option.strike)
        .filter(
            models.Option.underlying_id == stock.id,
            models.Option.lastTradeDateOrContractMonth == expiration_date,
        )
        .distinct()
        .order_by(models.Option.strike)
    )

    # Return the list of strikes
    return [strike[0] for strike in strikes]


def get_option_contract_db(
    db: Session, symbol: str, expiration_date: str, strike: float, right: str
) -> models.Option:
    """
    Retrieves a specific option contract based on symbol, expiration date, strike price, and right (CALL/PUT).

    Args:
        db (Session): Database session.
        symbol (str): The stock symbol.
        expiration_date (str): The expiration date of the option.
        strike (float): The strike price of the option.
        right (str): The option type (CALL/PUT).

    Returns:
        models.Option: The corresponding option contract.

    Raises:
        HTTPException: If the stock is not found.
    """
    # Get the stock contract by symbol
    stock = contracts_service.get_contract_by_symbol(db, symbol, "Stock")
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Query the option contract with the given parameters
    option = (
        db.query(models.Option)
        .filter(
            models.Option.underlying_id == stock.id,
            models.Option.lastTradeDateOrContractMonth == expiration_date,
            models.Option.strike == strike,
            models.Option.right == right,  # Option type (CALL or PUT)
        )
        .first()  # Return the first matching option
    )

    return option


# Process option contracts for stocks
def process_options(
    db: Session, ib: IB, stock: models.Stock, expiration_date: str, underlying: ib_stock
) -> None:
    db_option_contracts = contracts_service.get_db_option_contracts(
        db, stock.id, expiration_date
    )

    if not db_option_contracts:
        latest_price = prices_service.get_latest_price(underlying, ib)
        option_contracts = contracts_service.get_ib_option_contracts(
            ib, underlying, expiration_date, latest_price, stock.spread_around_spot
        )
        option_contracts = contracts_service.save_ib_contracts_to_db_and_convert(
            option_contracts, stock.id, db
        )
    else:
        option_contracts = contracts_service.db_to_ib_option_contracts(
            db_option_contracts
        )

    # Trigger price data collection for each option contract
    for option_contract in option_contracts:
        market_reader_tasks.get_price_data.delay(
            option_contract.db_id,
            "Option",
            option_contract.option.symbol,
            option_contract.option.exchange,
            option_contract.option.currency,
            1,
            None,
            option_contract.option.lastTradeDateOrContractMonth,
            option_contract.option.strike,
            option_contract.option.right,
        )
