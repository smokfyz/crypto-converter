lint:
	poetry run ruff format && poetry run ruff check --fix --unsafe-fixes && poetry run mypy .

ruff:
	poetry run ruff check

mypy:
	poetry run mypy .

test:
	poetry run pytest -W ignore::DeprecationWarning

run:
	docker-compose -f deploy/docker-compose.yaml up --build
