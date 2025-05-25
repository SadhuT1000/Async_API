from typing import Any, Set
from uuid import UUID

from pydantic import BaseModel


class Person(BaseModel):
    id: UUID  # noqa: VNE003, A003
    name: str

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: Any) -> bool:
        return self.id == other.id

    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }


class GenreBaseInfo(BaseModel):
    id: UUID  # noqa: VNE003, A003
    name: str

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: Any) -> bool:
        return self.id == other.id

    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }


class ESMovieDocument(BaseModel):
    id: UUID  # noqa: VNE003, A003
    title: str
    description: str | None
    imdb_rating: float | None

    genres: Set[GenreBaseInfo]
    genres_names: Set[str]

    actors: Set[Person]
    actors_names: Set[str]

    directors: Set[Person]
    directors_names: Set[str]

    writers: Set[Person]
    writers_names: Set[str]

    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }


class Genre(GenreBaseInfo):
    description: str | None
