import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

if os.path.exists("local.tests.env"):
    load_dotenv("local.tests.env")
else:
    load_dotenv("tests.env")


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Environment variable {name} is not set")

    return value


class TestSettings(BaseSettings):
    es_host: str = get_required_env("ES_URL")

    redis_host: str = get_required_env("REDIS_HOST")
    redis_port: str = get_required_env("REDIS_PORT")

    service_url: str = get_required_env("API_URL")

    es_index: str
    es_index_mapping: dict


# Экземпляр, который содержит настройки по умолчанию. Для фикстур в conftest.py
default_settings = TestSettings(es_index="", es_index_mapping={})
