#!/bin/bash
set -e
poetry install
cd tests/functional
poetry run utils/wait_for_es.py
poetry run utils/wait_for_redis.py
poetry run pytest src