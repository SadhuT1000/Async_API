import json
import uuid

import pytest
import pytest_asyncio
from elasticsearch.helpers import async_bulk
from tests.functional.settings import TestSettings

with open("resources/genre_index.json", "r") as f:
    index_mapping = json.load(f)

test_settings = TestSettings(es_index="genres", es_index_mapping=index_mapping)


@pytest_asyncio.fixture(name="es_data")
async def es_data():
    es_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "Drama",
            "description": "some desc",
        }
        for _ in range(60)
    ]

    bulk_query = []
    for row in es_data:
        bulk_query.append(
            {
                "_op_type": "index",
                "_index": test_settings.es_index,
                "_id": row["id"],
                "_source": row,
            }
        )
    return bulk_query


@pytest_asyncio.fixture(name="es_write_data", scope="module")
async def es_write_data(es_client):
    async def inner(data: list[dict]):
        if await es_client.indices.exists(index=test_settings.es_index):
            await es_client.indices.delete(index=test_settings.es_index)
        await es_client.indices.create(
            index=test_settings.es_index, **test_settings.es_index_mapping
        )
        updated, errors = await async_bulk(client=es_client, actions=data)
        await es_client.indices.refresh(index=test_settings.es_index)

        if errors:
            raise Exception("Ошибка записи данных в Elasticsearch")

    return inner


@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        ({}, {"status": 200, "length": 50}),
        ({"page_size": 40, "page_number": 1}, {"status": 200, "length": 40}),
        ({"page_size": 40, "page_number": 2}, {"status": 200, "length": 20}),
    ],
)
@pytest.mark.asyncio
async def test_genres_list(
    get_redis_cache,
    make_get_request,
    es_write_data,
    es_data,
    query_data,
    expected_answer,
):
    await es_write_data(es_data)
    response = await make_get_request("api/v1/genres/", query_data)

    cache_key = "genres:list"

    page_size = query_data.get("page_size", "50")
    cache_key += ":" + str(page_size)

    page_number = query_data.get("page_number", "1")
    cache_key += ":" + str(page_number)

    cache = await get_redis_cache(cache_key)
    cache_ids = set([obj["id"] for obj in cache])
    response_ids = set([obj["uuid"] for obj in response["body"]])

    # Проверка кэша
    assert cache_ids == response_ids
    # Статус код
    assert response["status"] == expected_answer["status"]
    # Количетсво объектов
    assert len(response["body"]) == expected_answer["length"]


@pytest.mark.asyncio
async def test_genres_detail_200(
    get_redis_cache, make_get_request, es_write_data, es_data
):
    await es_write_data(es_data)
    response = await make_get_request("api/v1/genres/", {})
    obj = response["body"][0]
    obj_uuid = obj["uuid"]

    response_2 = await make_get_request(f"api/v1/genres/{obj_uuid}", {})
    assert response_2["status"] == 200
    print(response_2["body"])
