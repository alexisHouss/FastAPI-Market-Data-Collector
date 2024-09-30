from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from models import schemas
from models.database import get_db
from sqlalchemy.orm import Session
from services import contracts_service, prices_service
from tasks import stocks_tasks  # Celery tasks for asynchronous processing
from typing import List

# Create an API router for handling stock-related requests
router = APIRouter()


# Get a list of all Stock contracts from the database
@router.get("/", response_model=List[schemas.Contract])
def get_stocks(db: Session = Depends(get_db)):
    # Retrieve any contracts classified as "Stock" from the database
    stocks = contracts_service.get_any_contracts(db, "Stock")
    return stocks


# Create a new Stock contract in the database
@router.post("/", response_model=schemas.Contract)
def create_stock(stock: schemas.Contract, db: Session = Depends(get_db)):
    # Check if the stock already exists in the database
    if contracts_service.check_contract_exist(db, stock, "Stock"):
        raise HTTPException(status_code=400, detail="Stock already exists")

    # Asynchronously fetch stock data from Interactive Brokers using Celery
    stocks_tasks.fetch_stock.delay(
        stock.symbol, stock.exchange, stock.currency, stock.to_trade
    )

    # Return a 202 Accepted status, indicating that the request has been accepted for processing
    return Response(status_code=202)


# Get price bars (historical data) for a specific stock symbol
@router.get("/{symbol}/bars", response_model=List[schemas.PriceBar])
def get_stock_prices_by_symbol(
    symbol: str,
    data_type: str = Query(
        ..., description="Data type e.g., ASK, BID, TRADES"
    ),  # Query parameter for data type
    bar_size: int = Query(
        ..., description="Bar size in minutes"
    ),  # Query parameter for bar size in minutes
    order: str = Query(
        "desc", description="Order of the bars"
    ),  # Query parameter for the order (default: descending)
    limit: int = Query(
        500, description="Number of bars to return"
    ),  # Limit on the number of price bars
    db: Session = Depends(get_db),
):
    # Retrieve the Stock contract by its symbol
    stock = contracts_service.get_contract_by_symbol(db, symbol, "Stock")

    # If the stock is not found, raise a 404 error
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Retrieve price bars (historical data) from the database for the stock contract
    bars = prices_service.get_price_bars_from_db(
        db, stock.id, data_type, bar_size, order, limit
    )

    # Return the list of price bars
    return bars
