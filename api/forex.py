from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from models import schemas, models
from models.database import get_db
from sqlalchemy.orm import Session
from services import prices_service, contracts_service
from typing import List

# Create an API router for handling Forex-related requests
router = APIRouter()


# Get a list of Forex contracts from the database
@router.get("/", response_model=List[schemas.Contract])
def get_forex(db: Session = Depends(get_db)):
    # Retrieve any contracts classified as "Forex" from the database
    return contracts_service.get_any_contracts(db, "Forex")


# Create a new Forex contract in the database
@router.post("/", response_model=schemas.Contract)
def create_forex(forex: schemas.Contract, db: Session = Depends(get_db)):
    # Check if the Forex contract already exists in the database
    if contracts_service.check_contract_exist(db, forex, "Forex"):
        raise HTTPException(status_code=400, detail="Forex already exists")

    # Create a new Forex contract model instance
    db_contract = models.Forex(
        symbol=forex.symbol,
        contract_type="Forex",
        exchange=forex.exchange,
        currency=forex.currency,
    )

    # Add the new contract to the database and save the changes
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)  # Refresh the instance with the updated data from the DB

    # Return the newly created contract
    return db_contract


# Delete a Forex contract by its ID
@router.delete("/{forex_id}")
def delete_forex(forex_id: int, db: Session = Depends(get_db)):
    # Retrieve the Forex contract by its ID
    forex = contracts_service.get_contract_by_id(db, forex_id, "Forex")

    # If the contract is not found, raise a 404 error
    if forex is None:
        raise HTTPException(status_code=404, detail="Forex not found")

    # Delete the contract and save the changes to the database
    db.delete(forex)
    db.commit()

    # Return a 204 (No Content) response to indicate successful deletion
    return Response(status_code=204)


# Retrieve Forex price bars (historical data) for a specific Forex symbol
@router.get("/{symbol}/bars", response_model=List[schemas.PriceBar])
def get_forex_prices_by_symbol(
    symbol: str,
    data_type: str = Query(..., description="Data type e.g., ASK, BID, TRADES"),
    bar_size: int = Query(..., description="Bar size in mn"),
    order: str = Query(
        "desc", description="Order of the bars"
    ),  # Default to descending order
    limit: int = Query(
        500, description="Number of bars to return"
    ),  # Limit the number of bars to return
    db: Session = Depends(get_db),
):
    # Retrieve the Forex contract by its symbol
    forex = contracts_service.get_contract_by_symbol(db, symbol, "Forex")

    # If the contract is not found, raise a 404 error
    if forex is None:
        raise HTTPException(status_code=404, detail="Forex not found")

    # Get price bars (historical data) from the database based on the Forex contract ID and query parameters
    bars = prices_service.get_price_bars_from_db(
        db, forex.id, data_type, bar_size, order, limit
    )

    # Return the list of price bars
    return bars
