import json
import uuid

import pytest
import pytest_asyncio
from elasticsearch.helpers import async_bulk
from tests.functional.settings import TestSettings

with open("resources/movie_index.json", "r") as f:
    index_mapping = json.load(f)

test_settings = TestSettings(es_index="movies", es_index_mapping=index_mapping)


@pytest_asyncio.fixture(name="es_data")
async def es_data():
    es_data = [
        {
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
                {"id": "fb111f22-121e-44a7-b78f-b19191810fbf", "name": "Fantastic"},
            ],
            "directors": [
                {"id": "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f85", "name": "Stan"},
            ],
            "actors": [
                {"id": "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f95", "name": "Ann"},
                {"id": "fb111f22-121e-44a7-b78f-b19191810fbf", "name": "Bob"},
            ],
            "writers": [
                {"id": "caf76c67-c0fe-477e-8766-3ab3ff2574b5", "name": "Ben"},
                {"id": "b45bd7bc-2e16-46d5-b125-983d356768c6", "name": "Howard"},
            ],
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


@pytest_asyncio.fixture(name="es_write_data")
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
        ({"query": "The Star"}, {"status": 200, "length": 50}),
        ({"query": "Mashed Potato"}, {"status": 200, "length": 0}),
        ({"query": "The Star", "page_size": 30}, {"status": 200, "length": 30}),
        (
            {"query": "The Star", "page_size": 40, "page_number": 2},
            {"status": 200, "length": 20},
        ),
    ],
)
@pytest.mark.asyncio
async def test_search(
    get_redis_cache,
    make_get_request,
    es_write_data,
    es_data: list[dict],
    query_data,
    expected_answer,
):
    await es_write_data(es_data)

    response = await make_get_request("api/v1/films/search", query_data)
    cache = await get_redis_cache("film", "search", query_data)

    cache_ids = set([obj["id"] for obj in cache])
    response_ids = set([obj["uuid"] for obj in response["body"]])

    # Проверка кэша
    assert cache_ids == response_ids
    # Статус код
    assert response["status"] == expected_answer["status"]
    # Количетсво объектов
    assert len(response["body"]) == expected_answer["length"]
