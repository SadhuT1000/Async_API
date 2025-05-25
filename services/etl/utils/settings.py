import os

from pydantic_settings import BaseSettings, SettingsConfigDict

local_dotenv_path = "local.env"
prod_dotenv_path = "../../.env"

dotenv_path = None

if os.path.exists(local_dotenv_path):
    dotenv_path = local_dotenv_path
elif os.path.exists(prod_dotenv_path):
    dotenv_path = prod_dotenv_path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: str
    es_url: str
    project_name: str
    redis_host: str
    redis_port: str


settings = Settings(_env_file=dotenv_path, _env_file_encoding="utf-8")  # type: ignore
