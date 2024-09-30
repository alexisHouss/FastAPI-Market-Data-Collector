from ib_insync import (
    IB,
    Contract,
    Option,
    ContractDetails,
    OptionChain,
    ContFuture,
    Forex,
    Index,
    Stock,
)
from sqlalchemy.orm import Session
from datetime import date, datetime
from models.models import (
    Option as dbOption,
    Forex as dbForex,
    Future as dbFuture,
    Stock as dbStock,
    Index as dbIndex,
)
from models.schemas import IBOptionWithID, Contract as schemasContract
from typing import List, Optional
from fastapi import HTTPException
from pytz import timezone


# Fetches contract details for a given contract using Interactive Brokers API
def get_contract_details(ib: IB, contract: Contract) -> List[ContractDetails]:
    contract_details = ib.reqContractDetails(contract)

    # Raise an error if no contract details are found
    if not contract_details:
        raise ValueError("Contract details not found.")

    return contract_details


# Fetches option chains (i.e., available options) for a given underlying asset
def get_option_chains(ib: IB, underlying: Contract) -> List[OptionChain]:
    chains = ib.reqSecDefOptParams(
        underlying.symbol, "", underlying.secType, underlying.conId
    )

    # Raise an error if no option chains are found
    if not chains:
        raise ValueError("Option chains not found.")

    return chains


# Retrieves option contracts from the database based on the underlying asset's ID and expiration date
def get_db_option_contracts(
    db: Session,
    underlying_id: int,
    expiration_date: date,
) -> List[dbOption]:
    return (
        db.query(dbOption)
        .filter(
            dbOption.underlying_id == underlying_id,
            dbOption.lastTradeDateOrContractMonth == expiration_date,
        )
        .all()
    )


# Fetches option contracts from IB for a given underlying asset, expiration date, and price range
def get_ib_option_contracts(
    ib: IB,
    underlying: Contract,
    expiration_date: date,
    latest_price: float,
    spread_around_spot: float,
) -> List[Option]:
    # Get all option chains for the underlying asset
    chains = get_option_chains(ib, underlying)

    # Filter the option chains for the "SMART" exchange
    chain = [chain for chain in chains if chain.exchange == "SMART"][0]

    # Raise an error if the specified expiration date is not found in the chain
    if expiration_date not in chain.expirations:
        raise ValueError("Expiration date not found in chain.")

    # Filter the strikes around the latest price to limit the range of options fetched
    strikes_to_fetch = [
        strike
        for strike in chain.strikes
        if strike > latest_price - spread_around_spot
        and strike < latest_price + spread_around_spot
    ]

    # Create a list of option contracts for the filtered strikes and both call (C) and put (P) options
    option_contracts = []
    for strike in strikes_to_fetch:
        for right in [
            "C",
            "P",
        ]:  # Right "C" represents Call options, "P" represents Put options
            contract = Option(
                symbol=underlying.symbol,
                lastTradeDateOrContractMonth=expiration_date,
                strike=strike,
                right=right,
                exchange="SMART",
            )
            option_contracts.append(contract)

    return option_contracts


# Converts a list of database option contracts to IB option contracts, preserving the database ID
def db_to_ib_option_contracts(option_contracts: List[dbOption]) -> List[IBOptionWithID]:
    return [
        IBOptionWithID(
            option=Option(
                symbol=contract.symbol,
                lastTradeDateOrContractMonth=contract.lastTradeDateOrContractMonth.strftime(
                    "%Y%m%d"
                ),
                strike=contract.strike,
                right=contract.right,
                exchange=contract.exchange,
                currency=contract.currency,
            ),
            db_id=contract.id,  # Preserve the database ID for reference
        )
        for contract in option_contracts
    ]


# Saves option contracts to the database and converts them into a form usable by IB, returning the updated list
def save_ib_contracts_to_db_and_convert(
    option_contracts: List[Option],
    underlying_id: int,
    db: Session = None,
) -> List[dbOption]:
    # Create database contract objects from the IB option contracts
    db_contracts = [
        dbOption(
            symbol=contract.symbol,
            contract_type="Option",
            lastTradeDateOrContractMonth=contract.lastTradeDateOrContractMonth,
            strike=contract.strike,
            right=contract.right,
            exchange=contract.exchange,
            currency=contract.currency,
            underlying_id=underlying_id,
        )
        for contract in option_contracts
    ]

    # If a database session is provided, save the contracts to the database
    if db:
        db.add_all(db_contracts)
        db.commit()

        # Refresh the contracts from the database to retrieve the latest state
        for db_contract in db_contracts:
            db.refresh(db_contract)

    # Convert the database contracts into IB contracts with their IDs for further use
    return [
        IBOptionWithID(
            option=Option(
                symbol=contract.symbol,
                lastTradeDateOrContractMonth=contract.lastTradeDateOrContractMonth.strftime(
                    "%Y%m%d"
                ),
                strike=contract.strike,
                right=contract.right,
                exchange=contract.exchange,
                currency=contract.currency,
            ),
            db_id=contract.id,  # Include the database ID for reference
        )
        for contract in db_contracts
    ]


def get_any_contracts(db: Session, contract_type: str):
    if contract_type == "Stock":
        return db.query(dbStock).all()
    elif contract_type == "Option":
        return db.query(dbOption).all()
    elif contract_type == "Future":
        return db.query(dbFuture).all()
    elif contract_type == "Forex":
        return db.query(dbForex).all()
    elif contract_type == "Index":
        return db.query(dbIndex).all()
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")


def check_contract_exist(db: Session, contract: schemasContract, contract_type: str):
    model = None
    if contract_type == "Stock":
        model = dbStock
    elif contract_type == "Option":
        model = dbOption
    elif contract_type == "Future":
        model = dbFuture
    elif contract_type == "Forex":
        model = dbForex
    elif contract_type == "Index":
        model = dbIndex
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")

    return (
        db.query(model)
        .filter(
            model.symbol == contract.symbol,
            model.exchange == contract.exchange,
            model.currency == contract.currency,
            model.to_trade == contract.to_trade,
        )
        .first()
    )


def get_contract_by_id(db: Session, contract_id: int, contract_type: str):
    model = None
    if contract_type == "Stock":
        model = dbStock
    elif contract_type == "Option":
        model = dbOption
    elif contract_type == "Future":
        model = dbFuture
    elif contract_type == "Forex":
        model = dbForex
    elif contract_type == "Index":
        model = dbIndex
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")

    return db.query(model).filter(model.id == contract_id).first()


def get_contract_by_symbol(db: Session, symbol: str, contract_type: str):
    model = None
    if contract_type == "Stock":
        model = dbStock
    elif contract_type == "Option":
        model = dbOption
    elif contract_type == "Future":
        model = dbFuture
    elif contract_type == "Forex":
        model = dbForex
    elif contract_type == "Index":
        model = dbIndex
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")

    return db.query(model).filter(model.symbol == symbol).first()


# Helper function to create the appropriate IB contract object
def create_ib_contract(
    contract_type: str,
    symbol: str,
    exchange: str,
    currency: str,
    conId: Optional[int] = None,
    lastTradeDateOrContractMonth: Optional[str] = None,
    strike: Optional[float] = None,
    right: Optional[str] = None,
):
    if contract_type == "Stock":
        return Stock(symbol, exchange, currency, conId=conId)

    if contract_type == "Option":
        if (
            lastTradeDateOrContractMonth < datetime.now().strftime("%Y%m%d")
            or datetime.now(timezone("America/New_York")).time()
            < datetime.strptime("09:30:00", "%H:%M:%S").time()
        ):
            return None  # Skip expired or pre-market 0DTE options
        return Option(
            symbol, lastTradeDateOrContractMonth, strike, right, exchange, currency
        )

    if contract_type == "Future":
        return ContFuture(symbol, exchange)

    if contract_type == "Forex":
        return Forex(symbol)

    if contract_type == "Index":
        return Index(symbol, exchange)

    return None
