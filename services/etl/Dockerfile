FROM python:3.11

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install poetry==2.1.2

WORKDIR /code

COPY poetry.lock pyproject.toml ./

RUN  poetry install

COPY . .

RUN chmod +x entrypoint.sh


RUN addgroup --system etl && adduser --system --group etl && \
    chown -R etl:etl /code

USER etl

ENTRYPOINT ["./entrypoint.sh"]
