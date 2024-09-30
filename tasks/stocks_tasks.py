from celery_app import celery_app
from models.database import get_celery_db
from services import ibapi_service, contracts_service
from models.models import Stock
from ib_insync import Stock as ib_stock


@celery_app.task
def fetch_stock(symbol: str, exchange: str, currency: str, to_trade: bool) -> None:
    """
    Task to fetch stock details from IB and store them in the database.

    Args:
        symbol (str): The stock symbol.
        exchange (str): The exchange where the stock is traded.
        currency (str): The currency in which the stock is traded.
        to_trade (bool): Whether the stock is marked for trading or not.
    """
    # Connect to Interactive Brokers (IB)
    with ibapi_service.connect_to_ib() as ib:
        # Create an IB stock contract
        stock = ib_stock(symbol, exchange, currency)

        # Get contract details, including the conId
        contract_details = contracts_service.get_contract_details(ib, stock)
        conId = contract_details[0].contract.conId

        # Connect to the database and store stock details
        with get_celery_db() as db:
            db_stock = Stock(
                symbol=symbol,
                contract_type="Stock",
                exchange=exchange,
                currency=currency,
                conId=conId,
                to_trade=to_trade,  # Mark whether the stock is marked for trading
            )
            db.add(db_stock)  # Add the stock to the database
            db.commit()  # Commit the transaction
            db.refresh(db_stock)  # Refresh the instance with the updated state
