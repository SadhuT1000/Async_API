import uuid

import aiohttp
import pytest
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from tests.functional.settings import test_settings

@pytest.mark.asyncio
async def test_search():
    # 1. Генерируем данные для ES
    es_data = [{
        "id": str(uuid.uuid4()),
        "imdb_rating": 8.5,
        "title": "The Star",
        "description": "New World",
        "genres_names": ["Fantasy", "Fantastic"],
        "directors_names": ["Stan"],
        "actors_names": ["Ann", "Bob"],
        "writers_names": ["Ben", "Howard"],
        "genres": [
            {"id": "ef86b8ff-3c82-4d31-ad8e-72b69f5E3f95", "name": "Fantasy"},
            {"id": "fb111f22-121e-44a7-b78f-b19191810fbf", "name": "Fantastic"}
        ],
        "directors": [
            {"id": "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f85", "name": "Stan"},
        ],
        "actors": [
            {"id": "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f95", "name": "Ann"},
            {"id": "fb111f22-121e-44a7-b78f-b19191810fbf", "name": "Bob"}
        ],
        "writers": [
            {"id": "caf76c67-c0fe-477e-8766-3ab3ff2574b5", "name": "Ben"},
            {"id": "b45bd7bc-2e16-46d5-b125-983d356768c6", "name": "Howard"}
        ],
    } for _ in range(60)]

    bulk_query = []
    for row in es_data:
        bulk_query.append({
            "_op_type": "index",
            "_index": test_settings.es_index,
            "_id": row["id"],
            "_source": row
        })

        # 2. Загружаем данные в ES
    es_client = AsyncElasticsearch(hosts=test_settings.es_host,
                                   verify_certs=False)
    if await es_client.indices.exists(index=test_settings.es_index):
        await es_client.indices.delete(index=test_settings.es_index)
    await es_client.indices.create(index=test_settings.es_index,
                                   **test_settings.es_index_mapping)

    updated, errors = await async_bulk(client=es_client, actions=bulk_query)
    await es_client.indices.refresh(index=test_settings.es_index)
    await es_client.close()

    if errors:
        raise Exception("Ошибка записи данных в Elasticsearch")

    # 3. Запрашиваем данные из ES по API

    session = aiohttp.ClientSession()
    url = test_settings.service_url + "/api/v1/films/search"
    query_data = {"query": "The Star"}
    async with session.get(url, params=query_data) as response:
        body = await response.json()
        headers = response.headers
        status = response.status
    await session.close()

    # 4. Проверяем ответ

    assert status == 200
    assert len(body) == 50
