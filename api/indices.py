from fastapi import APIRouter, Depends, HTTPException, Query, Response
from models import schemas, models
from models.database import get_db
from sqlalchemy.orm import Session
from services import contracts_service, prices_service
from typing import List

# Create an API router for handling Index-related requests
router = APIRouter()


# Get a list of all Index contracts from the database
@router.get("/", response_model=List[schemas.Contract])
def get_indices(db: Session = Depends(get_db)):
    # Retrieve any contracts classified as "Index" from the database
    indices = contracts_service.get_any_contracts(db, "Index")
    return indices


# Create a new Index contract in the database
@router.post("/", response_model=schemas.Contract)
def create_index(index: schemas.Contract, db: Session = Depends(get_db)):
    # Check if the Index contract already exists in the database
    if contracts_service.check_contract_exist(db, index, "Index"):
        raise HTTPException(status_code=400, detail="Index already exists")

    # Create a new Index contract model instance
    db_contract = models.Index(
        symbol=index.symbol,
        contract_type="Index",
        exchange=index.exchange,
        currency=index.currency,
    )

    # Add the new contract to the database and commit the transaction
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)  # Refresh the instance with the updated data from the DB

    # Return the newly created contract
    return db_contract


# Delete an Index contract by its ID
@router.delete("/{index_id}")
def delete_index(index_id: int, db: Session = Depends(get_db)):
    # Retrieve the Index contract by its ID
    index = contracts_service.get_contract_by_id(db, index_id, "Index")

    # If the contract is not found, raise a 404 error
    if index is None:
        raise HTTPException(status_code=404, detail="Index not found")

    # Delete the contract and commit the transaction to the database
    db.delete(index)
    db.commit()

    # Return a 204 (No Content) response to indicate successful deletion
    return Response(status_code=204)


# Retrieve historical price bars (data like ask, bid, trades) for a specific Index symbol
@router.get("/{symbol}/bars", response_model=List[schemas.PriceBar])
def get_stock_prices_by_symbol(
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
    # Retrieve the Index contract by its symbol
    index = contracts_service.get_contract_by_symbol(db, symbol, "Index")

    # If the contract is not found, raise a 404 error
    if index is None:
        raise HTTPException(status_code=404, detail="Index not found")

    # Retrieve price bars (historical data) from the database for the Index contract
    bars = prices_service.get_price_bars_from_db(
        db, index.id, data_type, bar_size, order, limit
    )

    # Return the list of price bars
    return bars
