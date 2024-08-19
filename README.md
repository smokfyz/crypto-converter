# Crypto Converter

## Tested on
* macOS 14.6.1
* docker 27.0.3
* docker-compose 2.28.1
* python 3.11

## Description

Crypto Converter is a  web service that converts the amount of one cryptocurrency to another using the quotes consuming from the Binance HTTP API or the Binance WebSocket.

## API
### GET /convert
#### Query parameters:

* amount - amount of source currency. Default precision is 6 decimal places. If number of decimal places in amount is greater than 6 (can be configured using AMOUNT_PRECISION env variable), the service will round using round half to even algorithm.
* from - source currency (e.g. BTC)
* to - target currency (e.g. USDT)
* [Optional] timestamp - timestamp in seconds (default: current timestamp). If timestamp is provided, the service will use the quote for nearest timestamp that smaller or equal to provided with respect to NO_OLDER_THAN_SECONDS parameters.

#### Errors

* 404 - Quote not found / Quote is outdated
* 422 - Invalid/missing parameters

#### Example:

##### Request
```
curl --location 'http://127.0.0.1:8000/convert?amount=1&from=BTC&to=USDT'
```
##### Response:
```
{
    "amount":"58646.100000",
    "conversion_rate":"58646.100000000000"
}
```

## Configuration

You can configure the service using environment variables or `.env` file.

All available environment variables:

### Common
* LOG_LEVEL - log level (default: INFO)
* POSTGRES_HOST - host of the postgresql server (default: localhost)
* POSTGRES_PORT - port of the postgresql server (default: 5432)
* POSTGRES_USER - user of the postgresql server (default: postgres)
* POSTGRES_PASSWORD - password of the postgresql server (default: postgres)
* POSTGRES_DB - database name on the postgresql server (default: quotes)

### API service
* HOST - host of the service (default: localhost)
* SERVER_PORT - port of the service (default: 8000)
* ENABLE_HOT_RELOAD - enable hot reload (default: 0)
* NUM_WORKERS - number of workers (default: 2)
* AMOUNT_PRECISION - amount precision (default: 6)
* NO_OLDER_THAN_SECONDS - if all available quotes for timestamp older than this parameter than service will return error

### Consumer
* CONVERSION_RATE_PRECISION - conversion rate precision (default: 12)
* SAVE_PERIOD_SECONDS - quotes consume period in seconds (default: 30)
* CLEANUP_PERIOD_SECONDS - cleanup period in seconds (default: 600)
* CLEANUP_OLDER_THAN_SECONDS - cleanup older than seconds (default: 604800 (7 days))
* CONSUMER_SUBSCRIBTION_TYPE - consumer subscription type: http or ws (default: http)

## Run with docker-compose
1. Clone repository
2. Run docker-compose
```
make run
```
3. Send an example request
```
curl --location 'http://127.0.0.1:8000/convert?amount=1&from=BTC&to=USDT'
```

## Install dependencies
```
pip install poetry==1.8.3 && poetry install
```

## Run only api server
```
python run.py api
```

## Run only consumer
```
python run.py quotes-consumer
```

## Run tests
```
make test
```

## Run linter & formatter
```
make lint
```
