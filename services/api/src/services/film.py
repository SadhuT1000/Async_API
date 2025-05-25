import json
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Optional

from db.elastic import get_elastic
from db.redis import get_redis
from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from models.film import Film
from redis.asyncio import Redis

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5
FILM_LIST_CACHE_EXPIRE_IN_SECONDS = 1


class FilmService:
    INDEX = "movies"

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, film_id: str) -> Optional[Film]:
        redis_key = f"film:{film_id}"

        cached_film = await self.redis.get(redis_key)
        if cached_film:
            return Film.model_validate_json(cached_film)

        try:
            film_doc = await self.elastic.get(index=self.INDEX, id=film_id)
        except NotFoundError:
            return None

        film = Film(**film_doc["_source"])

        await self.redis.set(
            redis_key,
            film.model_dump_json(),
            FILM_CACHE_EXPIRE_IN_SECONDS,
        )

        return film

    async def search_films(
        self,
        query: str,
        page_size: int,
        page_number: int,
    ) -> List[Film]:
        redis_key = f"film:search:{query}:{page_size}:{page_number}"

        cached_films = await self._get_films_from_cache(redis_key)
        if cached_films:
            return cached_films

        films = await self._get_films_from_elastic(
            {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^3",
                            "description",
                            "genres_names",
                            "actors_names",
                            "directors_names",
                            "writers_names",
                        ],
                        "fuzziness": "AUTO",
                    },
                },
                "from": (page_number - 1) * page_size,
                "size": page_size,
            },
        )

        await self._save_films_to_cache(redis_key, films)

        return films

    async def list_films(
        self,
        sort: str = "imdb_rating",
        genre_id: Optional[str] = None,
        page_size: int = 50,
        page_number: int = 1,
    ) -> List[Film]:
        redis_key = f"films:list:{sort}:{genre_id}:{page_size}:{page_number}"

        cached_films = await self._get_films_from_cache(redis_key)
        if cached_films:
            return cached_films

        sort_field = sort.lstrip("-")
        order = "desc" if sort.startswith("-") else "asc"

        films = await self._get_films_from_elastic(
            {
                "query": (
                    {"match_all": {}}
                    if genre_id is None
                    else {
                        "nested": {
                            "path": "genres",
                            "query": {"term": {"genres.id": genre_id}},
                        }
                    }
                ),
                "sort": [{sort_field: {"order": order}}],
                "from": (page_number - 1) * page_size,
                "size": page_size,
            },
        )

        await self._save_films_to_cache(redis_key, films)

        return films

    async def _get_films_from_elastic(self, body: Dict[str, Any]) -> List[Film]:
        docs = await self.elastic.search(index=self.INDEX, body=body)
        return [Film(**hit["_source"]) for hit in docs["hits"]["hits"]]

    async def _save_films_to_cache(self, redis_key: str, films: List[Film]) -> None:
        await self.redis.set(
            redis_key,
            json.dumps([f.model_dump(mode="json") for f in films]),
            FILM_LIST_CACHE_EXPIRE_IN_SECONDS,
        )

    async def _get_films_from_cache(self, redis_key: str) -> Optional[List[Film]]:
        cached_films = await self.redis.get(redis_key)
        if cached_films:
            return [Film.model_validate(item) for item in json.loads(cached_films)]
        return None


@lru_cache()
def get_film_service(
    redis: Annotated[Redis, Depends(get_redis)],
    elastic: Annotated[AsyncElasticsearch, Depends(get_elastic)],
) -> FilmService:
    return FilmService(redis, elastic)
