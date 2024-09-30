from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from models import schemas, models
from models.database import get_db
from sqlalchemy.orm import Session
from services import contracts_service, prices_service
from typing import List

# Create an API router for handling Futures-related requests
router = APIRouter()


# Get a list of all Future contracts from the database
@router.get("/", response_model=List[schemas.Contract])
def get_futures(db: Session = Depends(get_db)):
    # Retrieve any contracts classified as "Future" from the database
    futures = contracts_service.get_any_contracts(db, "Future")

    return futures


# Create a new Future contract in the database
@router.post("/", response_model=schemas.Contract)
def create_future(future: schemas.Contract, db: Session = Depends(get_db)):
    # Check if the Future contract already exists in the database
    if contracts_service.check_contract_exist(db, future, "Future"):
        raise HTTPException(status_code=400, detail="Future already exists")

    # Create a new Future contract model instance
    db_contract = models.Future(
        symbol=future.symbol,
        contract_type="Future",
        exchange=future.exchange,
        currency=future.currency,
    )

    # Add the new contract to the database and commit the transaction
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)  # Refresh the instance with the updated data from the DB

    # Return the newly created contract
    return db_contract


# Delete a Future contract by its ID
@router.delete("/{future_id}")
def delete_future(future_id: int, db: Session = Depends(get_db)):
    # Retrieve the Future contract by its ID
    future = contracts_service.get_contract_by_id(db, future_id, "Future")

    # If the contract is not found, raise a 404 error
    if future is None:
        raise HTTPException(status_code=404, detail="Future not found")

    # Delete the contract and commit the transaction to the database
    db.delete(future)
    db.commit()

    # Return a 204 (No Content) response to indicate successful deletion
    return Response(status_code=204)


# Retrieve historical price bars (data like ask, bid, trades) for a specific Future symbol
@router.get("/{symbol}/bars", response_model=List[schemas.PriceBar])
def get_future_prices_by_symbol(
    symbol: str,
    data_type: str = Query(..., description="Data type e.g., ASK, BID, TRADES"),
    bar_size: int = Query(..., description="Bar size in minutes"),
    order: str = Query(
        "desc", description="Order of the bars"
    ),  # Default to descending order
    limit: int = Query(
        500, description="Number of bars to return"
    ),  # Limit the number of bars to return
    db: Session = Depends(get_db),
):
    # Retrieve the Future contract by its symbol
    future = contracts_service.get_contract_by_symbol(db, symbol, "Future")

    # If the contract is not found, raise a 404 error
    if future is None:
        raise HTTPException(status_code=404, detail="Future not found")

    # Retrieve price bars (historical data) from the database for the Future contract
    bars = prices_service.get_price_bars_from_db(
        db, future.id, data_type, bar_size, order, limit
    )

    # Return the list of price bars
    return bars
