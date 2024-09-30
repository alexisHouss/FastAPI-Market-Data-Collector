
# FastAPI Application for Automatic Historical Market Data Fetching via IBKR API

This project provides a fully functional market data reader. The system components are orchestrated using a Docker Compose file, which includes:

- A FastAPI app for requesting and retrieving market data.
- A Celery worker for processing query tasks.
- Celery Beat to schedule periodic data-fetching tasks.
- A PostgreSQL database for storing market data.
- A Redis database for task management and caching.
- An IB Gateway, containerized to connect with the market data APIs.

The code leverages ib_insync to make data collection much simpler and more efficient compared to IBapi:
https://github.com/erdewit/ib_insync?tab=readme-ov-file

### Requisites
You need to be subscribed to the following market data in IBKR:
- US Securities Snapshot Bundle
- US equity and Options Add-on Streaming Bundle


## Environment Variables

To run this project, you will need to add the following environment variables to a .env/.dev-sample file

```bash
DB_USER=postgres
DB_PASS=postgres
DB_HOST=db
DB_NAME=streamer
DB_PORT=5432

CELERY_BROKER_URL=redis://redis:6379/0

IB_GATEWAY_IP=ib-gateway
IB_GATEWAY_PORT=4004
```


###
Additionally, you'll need to create another `.env` file for the IB Gateway configuration (.env/.ibgateway)
```bash
TWS_USERID=your-ibkr-user-id
TWS_PASSWORD=your-ibkr-password
TRADING_MODE=paper
READ_ONLY_API=no
VNC_SERVER_PASSWORD=myVncPassword
TWOFA_TIMEOUT_ACTION=restart
AUTO_RESTART_TIME=11:59 PM
RELOGIN_AFTER_TWOFA_TIMEOUT=yes
EXISTING_SESSION_DETECTED_ACTION=primary
ALLOW_BLIND_TRADING=no
TIME_ZONE=America/New_York
```

## Deployment

To deploy this project, run the following command in the project's root directory:

```bash
  docker compose up --build -f
```

To view the logs

```bash
  docker compose logs -f
```

By default, Celery Beat will request historical bars for contracts in the database every minute. If you'd like to manually trigger a data collection, run the following commands:

```bash
  docker compose exec algo python
```
Then, within the Python environment:
```python
  from tasks import market_reader_tasks
  market_reader_tasks.get_market_data()
```


## API Reference

To request the stream of new tickers, you can request the API to add the contracts to the db. Their historical data will then be collected automatically.
To request a new `Index`, `Future`, `Stock`, or `Forex` contract:

```python
  import requests

  contract_type = "futures" | "stocks" | "forex" | "indices"

  url = f"http://localhost:8000/{contract_type}/"

  data = {
    "symbol": "GC",
    "exchange": "COMEX"
  }

  requests.post(url, data=data)

```

### Get Historical Data
Once the data collection has been processed, you can retrieve the historical data:

```python
  import requests

  contract_type = "futures" | "stocks" | "forex" | "indices"
  symbol = "SPY"

  url = f"http://localhost:8000/{contract_type}/{symbol}/bars"
  params = {
    "data_type": "TRADES" | "BID" | "ASK",
    "bar_size": 5, # in minutes
    "order": "desc",
    "limit": 100
  }

  bars = requests.get(url, params=params) 
```

### Collect Option Contract Bars
```python
  import requests

  contract_type = "options"
  underlying_symbol = "SPY"
  expiration_date = "20240930"

  url = f"http://localhost:8000/{contract_type}/{underlying_symbol}/{expiration_date}"
  params = {
    "data_type": "TRADES" | "BID" | "ASK",
    "right": "C" | "P",
    "strike": 570.0,
    "bar_size": 5, # in minutes
    "order": "asc",
    "limit": 100
  }

  bars = requests.get(url, params=params) 
```

## Optimisation

For optimal performance on a server, this setup works well with the containerized IB Gateway. However, if you're running the project on a local machine, you can comment out the IB Gateway in the docker-compose.yml file and use the native TWS app. Update the .env file as follows:
```bash
IB_GATEWAY_IP=host.docker.internal
IB_GATEWAY_PORT=4002
```

This allows you to monitor client creation more easily and, if needed, observe live trade executions in your trading system.

## Future Enhancements

Currently, for options contracts, only zero-day-to-expiration (0DTE) data is collected. Future improvements could involve gathering additional historical data, especially for contracts with weekly expirations. Another potential area for enhancement is the generation of technical indicators from the collected data, which could be used to trigger automated buy/sell actions. The possibilities for further development are endless.