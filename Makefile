lint:
	ruff format && ruff check --fix --unsafe-fixes && mypy .

ruff:
	ruff check

mypy:
	mypy .

test:
	pytest -W ignore::DeprecationWarning

run:
	docker-compose -f deploy/docker-compose.yaml up --build
