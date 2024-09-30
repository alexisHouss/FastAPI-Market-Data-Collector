from celery_app import celery_app
from models.database import get_celery_db
from services import (
    calendar_service,
    prices_service,
    ibapi_service,
    contracts_service,
    options_service,
)
from models.models import Stock, Future, Forex, Index
from typing import List, Optional
from ib_insync import (
    Stock as ib_stock,
    IB,
)
from sqlalchemy.orm import Session


# Celery task to fetch market data for stocks, futures, forex, and indices
@celery_app.task
def get_market_data() -> None:
    expiration_date: str = (
        calendar_service.get_0dte_expiration_date()
    )  # Get today's 0DTE expiration date
    print(f"Expiration date: {expiration_date}")

    # Connect to Interactive Brokers (IB)
    with ibapi_service.connect_to_ib() as ib:
        with get_celery_db() as db:
            # Process all tradable stocks
            process_contracts(db, ib, Stock, "Stock", expiration_date)

            # Process futures, forex, and indices
            process_contracts(db, ib, Future, "Future")
            process_contracts(db, ib, Forex, "Forex")
            process_contracts(db, ib, Index, "Index")


# Helper function to process contracts (stocks, futures, forex, etc.)
def process_contracts(
    db: Session,
    ib: IB,
    model,
    contract_type: str,
    expiration_date: Optional[str] = None,
) -> None:
    contracts = db.query(model).all()

    for contract in contracts:
        if contract_type == "Stock":
            underlying = ib_stock(
                contract.symbol,
                contract.exchange,
                contract.currency,
                conId=contract.conId,
            )
            # Retrieve or create option contracts for the stock
            options_service.process_options(
                db, ib, contract, expiration_date, underlying
            )

        # Trigger price data collection
        get_price_data.delay(
            contract.id,
            contract_type,
            contract.symbol,
            contract.exchange,
            contract.currency,
            5,
            contract.conId if contract_type == "Stock" else None,
        )


# Celery task to fetch price data for a contract (Stock, Option, Future, etc.)
@celery_app.task
def get_price_data(
    contract_db_id: str,
    contract_type: str,
    symbol: str,
    exchange: str,
    currency: str,
    bar_size: int = 5,
    conId: Optional[int] = None,
    lastTradeDateOrContractMonth: Optional[str] = None,
    strike: Optional[float] = None,
    right: Optional[str] = None,
) -> None:
    data_types: List[str] = (
        ["BID", "ASK", "TRADES"] if contract_type != "Forex" else ["ASK", "BID"]
    )

    if contract_type == "Index":
        data_types = ["TRADES"]

    # Create the appropriate contract object
    contract = contracts_service.create_ib_contract(
        contract_type,
        symbol,
        exchange,
        currency,
        conId,
        lastTradeDateOrContractMonth,
        strike,
        right,
    )
    if not contract:
        return  # Skip if conditions for 0DTE options are not met

    with ibapi_service.connect_to_ib() as ib:
        with get_celery_db() as db:
            bars_to_create: List = []

            # Collect price bars for all data types
            for data_type in data_types:
                bars_to_create = prices_service.get_add_price_bars(
                    ib,
                    contract,
                    data_type,
                    contract_db_id,
                    contract_type,
                    bar_size,
                    bars_to_create,
                    db,
                )

                print(f"Got {len(bars_to_create)} bars for {data_type} and {symbol}")

            # Add the collected bars to the database
            db.add_all(bars_to_create)
            db.commit()
