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

RUN  poetry install --only main

COPY . .

RUN chmod +x entrypoint.sh &&  \
    chmod +x tests/functional/entrypoint.sh && \
    chmod +x tests/functional/utils/wait_for_es.py && \
    chmod +x tests/functional/utils/wait_for_redis.py



EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]