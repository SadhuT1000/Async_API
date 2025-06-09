import json
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Optional

from db.elastic import get_elastic
from db.redis import get_redis
from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from models.genre import Genre
from redis.asyncio import Redis

from .cache import CacheServiceProtocol, RedisCacheService

GENRE_CACHE_EXPIRE_IN_SECONDS = 60 * 5
GENRE_LIST_CACHE_EXPIRE_IN_SECONDS = 60


class GenreService:
    INDEX = "genres"

    def __init__(self, cache: CacheServiceProtocol, elastic: AsyncElasticsearch):
        self.cache = cache
        self.elastic = elastic

    async def get_by_id(self, genre_id: str) -> Optional[Genre]:
        cache_key = self._get_genre_cache_key(genre_id)
        cached_genre = await self.cache.get(cache_key)
        if cached_genre:
            return Genre.model_validate_json(cached_genre)

        try:
            response = await self.elastic.get(index=self.INDEX, id=genre_id)
        except NotFoundError:
            return None

        genre = Genre(**response["_source"])
        await self.cache.set(
            cache_key,
            genre.model_dump_json(),
            GENRE_CACHE_EXPIRE_IN_SECONDS,
        )

        return genre

    async def list_genres(
        self,
        page_size: int,
        page_number: int,
    ) -> List[Genre]:
        cache_key = self._get_genres_list_cache_key(page_size, page_number)
        cached_genres = await self._get_genres_from_cache(cache_key)
        if cached_genres:
            return cached_genres

        genres = await self._get_genres_from_elastic(
            {
                "query": {"match_all": {}},
                "from": (page_number - 1) * page_size,
                "size": page_size,
            },
        )

        await self._save_genres_to_cache(cache_key, genres)

        return genres

    async def _get_genres_from_elastic(self, body: Dict[str, Any]) -> List[Genre]:
        response = await self.elastic.search(index=self.INDEX, body=body)

        return [Genre(**hit["_source"]) for hit in response["hits"]["hits"]]

    def _get_genre_cache_key(self, genre_id: str) -> str:
        return f"genre:{genre_id}"

    def _get_genres_list_cache_key(self, page_size: int, page_number: int) -> str:
        return f"genres:list:{page_size}:{page_number}"

    async def _save_genres_to_cache(self, cache_key: str, genres: List[Genre]) -> None:
        await self.cache.set(
            cache_key,
            json.dumps([f.model_dump(mode="json") for f in genres]),
            GENRE_LIST_CACHE_EXPIRE_IN_SECONDS,
        )

    async def _get_genres_from_cache(self, cache_key: str) -> Optional[List[Genre]]:
        cached_genres = await self.cache.get(cache_key)
        if cached_genres:
            return [Genre.model_validate(item) for item in json.loads(cached_genres)]

        return None


@lru_cache()
def get_genre_service(
    redis: Annotated[Redis, Depends(get_redis)],
    elastic: Annotated[AsyncElasticsearch, Depends(get_elastic)],
) -> GenreService:
    cache = RedisCacheService(redis)
    return GenreService(cache, elastic)
