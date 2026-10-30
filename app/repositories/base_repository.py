from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.base import Base


class BaseRepository[TModel: Base]:
    """Shared data access for one entity type. Write methods commit, so each call is durable."""

    model: ClassVar[type[Any]]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: Any) -> TModel:
        entity: TModel | None = await self._session.get(self.model, entity_id)
        if entity is None:
            raise NotFoundError(
                f"{self.model.__name__} {entity_id} not found",
                details={"id": str(entity_id)},
            )
        return entity

    async def _save(self, entity: TModel) -> TModel:
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return entity
