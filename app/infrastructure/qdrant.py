from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from app.core.config import settings
from app.core.exceptions import ExternalServiceError


class QdrantManager:
    def __init__(self) -> None:
        self.client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        self.client = AsyncQdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=5.0
        )

    async def close(self) -> None:
        if self.client:
            await self.client.close()

    async def ping(self) -> bool:
        if not self.client:
            return False
        try:
            await self.client.get_collections()
            return True
        except (ResponseHandlingException, ConnectionError, OSError) as e:
            raise ExternalServiceError(str(e), service_name="Qdrant") from e


qdrant_manager = QdrantManager()
