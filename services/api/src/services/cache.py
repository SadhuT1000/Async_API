from typing import Optional, Protocol

from redis.asyncio import Redis


class CacheServiceProtocol(Protocol):
    async def get(self, key: str) -> Optional[str]: ...
    async def set(self, key: str, value: str, expire: int) -> None: ...


class RedisCacheService(CacheServiceProtocol):
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: int) -> None:
        await self.redis.set(key, value, expire)
