FROM python:3.11.9

WORKDIR /app

RUN pip install poetry==1.8.3

COPY ./pyproject.toml ./pyproject.toml
COPY ./poetry.lock ./poetry.lock

RUN poetry install --no-root --only main

COPY . /app
