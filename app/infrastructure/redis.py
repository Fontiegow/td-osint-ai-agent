import redis.asyncio as aioredis

from app.core.config import settings
from app.core.exceptions import ExternalServiceError


class RedisClient:
    def __init__(self) -> None:
        self.client: aioredis.Redis | None = None

    async def connect(self, url: str | None = None) -> None:
        target_url = url or settings.REDIS_URL
        self.client = aioredis.from_url(
            target_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )

    async def close(self) -> None:
        if self.client:
            await self.client.close()

    async def ping(self) -> bool:
        if not self.client:
            return False
        try:
            return bool(await self.client.ping())
        except (aioredis.RedisError, ConnectionError, OSError) as e:
            raise ExternalServiceError(str(e), service_name="Redis") from e


redis_client = RedisClient()