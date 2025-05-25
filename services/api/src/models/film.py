from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from .genre import Genre
from .person import Person


class Film(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    imdb_rating: Optional[float]

    genres: list[Genre]
    genre_names: list[str] = []

    actors: list[Person]
    actors_names: list[str] = []

    directors: list[Person]
    directors_names: list[str] = []

    writers: list[Person]
    writers_names: list[str] = []
