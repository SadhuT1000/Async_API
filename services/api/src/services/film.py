import json
from functools import lru_cache
from typing import Annotated, Any, Dict, Iterable, List, Optional

from db.elastic import get_elastic
from db.redis import get_redis
from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from models.film import Film
from redis.asyncio import Redis

from .cache import CacheServiceProtocol, RedisCacheService

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5
FILM_LIST_CACHE_EXPIRE_IN_SECONDS = 60


class FilmService:
    INDEX = "movies"

    def __init__(self, cache: CacheServiceProtocol, elastic: AsyncElasticsearch):
        self.cache = cache
        self.elastic = elastic

    async def get_by_id(self, film_id: str) -> Optional[Film]:
        cache_key = self._get_film_cache_key(film_id)
        cached_film = await self.cache.get(cache_key)
        if cached_film:
            return Film.model_validate_json(cached_film)

        try:
            response = await self.elastic.get(index=self.INDEX, id=film_id)
        except NotFoundError:
            return None

        film = Film(**response["_source"])
        await self.cache.set(
            cache_key,
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
        cache_key = self._get_films_search_cache_key(query, page_size, page_number)
        cached_films = await self._get_films_from_cache(cache_key)
        if cached_films:
            return cached_films

        films = await self._get_films_from_elastic(
            {
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
            page_size=page_size,
            page_number=page_number,
        )
        await self._save_films_to_cache(cache_key, films)
        return films

    async def list_films(
        self,
        page_size: int,
        page_number: int,
        genre_id: Optional[str] = None,
        sort: str = "imdb_rating",
    ) -> List[Film]:
        cache_key = self._get_films_list_cache_key(
            sort, genre_id, page_size, page_number
        )
        cached_films = await self._get_films_from_cache(cache_key)
        if cached_films:
            return cached_films

        films = await self._get_films_from_elastic(
            (
                {"match_all": {}}
                if genre_id is None
                else {
                    "nested": {
                        "path": "genres",
                        "query": {"term": {"genres.id": genre_id}},
                    }
                }
            ),
            page_size=page_size,
            page_number=page_number,
            sort=sort,
        )
        await self._save_films_to_cache(cache_key, films)
        return films

    async def get_films_with_person(
        self,
        person_id: str,
        sort: str = "imdb_rating",
    ) -> List[Film]:
        cache_key = self._get_person_films_cache_key(person_id)
        cached_films = await self._get_films_from_cache(cache_key)
        if cached_films:
            return cached_films

        films = await self._get_films_from_elastic(
            {
                "bool": {
                    "should": [
                        {
                            "nested": {
                                "path": "actors",
                                "query": {"term": {"actors.id": person_id}},
                            }
                        },
                        {
                            "nested": {
                                "path": "directors",
                                "query": {"term": {"directors.id": person_id}},
                            }
                        },
                        {
                            "nested": {
                                "path": "writers",
                                "query": {"term": {"writers.id": person_id}},
                            }
                        },
                    ]
                }
            },
            sort=sort,
        )
        await self._save_films_to_cache(cache_key, films)
        return films

    async def _get_films_from_elastic(
        self,
        query: Dict[str, Any],
        page_size: Optional[int] = None,
        page_number: Optional[int] = None,
        sort: Optional[str] = None,
    ) -> List[Film]:
        body: dict[str, Any] = {
            "query": query,
        }

        if page_size:
            body["size"] = page_size

        if page_number and page_size:
            body["from"] = (page_number - 1) * page_size

        if sort is not None:
            sort_field = sort.lstrip("-")
            order = "desc" if sort.startswith("-") else "asc"
            body["sort"] = [{sort_field: {"order": order}}]

        response = await self.elastic.search(index=self.INDEX, body=body)

        return [Film(**hit["_source"]) for hit in response["hits"]["hits"]]

    def _get_film_cache_key(self, film_id: str) -> str:
        return f"film:{film_id}"

    def _get_films_search_cache_key(
        self, query: str, page_size: int, page_number: int
    ) -> str:
        return f"film:search:{query}:{page_size}:{page_number}"

    def _get_films_list_cache_key(
        self, sort: str, genre_id: Optional[str], page_size: int, page_number: int
    ) -> str:
        return f"films:list:{sort}:{genre_id}:{page_size}:{page_number}"

    def _get_person_films_cache_key(self, person_id: str) -> str:
        return f"person:{person_id}:roles"

    async def _save_films_to_cache(self, cache_key: str, films: Iterable[Film]) -> None:
        await self.cache.set(
            cache_key,
            json.dumps([f.model_dump(mode="json") for f in films]),
            FILM_LIST_CACHE_EXPIRE_IN_SECONDS,
        )

    async def _get_films_from_cache(self, cache_key: str) -> Optional[List[Film]]:
        cached_films = await self.cache.get(cache_key)
        if cached_films:
            return [Film.model_validate(item) for item in json.loads(cached_films)]

        return None


@lru_cache()
def get_film_service(
    redis: Annotated[Redis, Depends(get_redis)],
    elastic: Annotated[AsyncElasticsearch, Depends(get_elastic)],
) -> FilmService:
    cache = RedisCacheService(redis)
    return FilmService(cache, elastic)
