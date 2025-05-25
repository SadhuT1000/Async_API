from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Genre(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
