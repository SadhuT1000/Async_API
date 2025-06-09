import asyncio
import json

import aiohttp
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis
from tests.functional.settings import default_settings


@pytest_asyncio.fixture(scope="session")
def _function_event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(name="redis_client", scope="function")
async def redis_client():
    redis_client = Redis(
        host=default_settings.redis_host, port=default_settings.redis_port
    )
    yield redis_client
    await redis_client.flushdb()
    await redis_client.close()


@pytest_asyncio.fixture(name="es_client", scope="session")
async def es_client():
    es_client = AsyncElasticsearch(hosts=default_settings.es_host, verify_certs=False)
    yield es_client
    await es_client.close()


@pytest_asyncio.fixture(name="client_http_session", scope="session")
async def client_http_session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest_asyncio.fixture(name="make_get_request")
async def make_get_request(client_http_session):
    async def inner(url, query_data):
        full_url = default_settings.service_url + "/" + url

        async with client_http_session.get(full_url, params=query_data) as response:
            response_dict = {"body": await response.json(), "status": response.status}
        return response_dict

    return inner


@pytest_asyncio.fixture(name="get_redis_cache")
async def get_redis_cache(redis_client):
    async def inner(cache_key):
        data = await redis_client.get(cache_key)
        return json.loads(data)

    return inner
