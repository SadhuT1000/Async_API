from http import HTTPStatus
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from models.film import Film
from models.genre import Genre
from models.person import Person
from pydantic import BaseModel
from services.film import FilmService, get_film_service

router = APIRouter()


class FilmItemResponse(BaseModel):
    uuid: UUID
    title: str
    imdb_rating: float | None

    @classmethod
    def from_model(cls, film: Film) -> "FilmItemResponse":
        return cls(uuid=film.id, title=film.title, imdb_rating=film.imdb_rating)


class FilmDetailGenreResponse(BaseModel):
    id: UUID
    name: str

    @classmethod
    def from_model(cls, genre: Genre) -> "FilmDetailGenreResponse":
        return cls(id=genre.id, name=genre.name)


class FilmDetailResponse(BaseModel):
    uuid: UUID
    title: str
    imdb_rating: float | None
    description: str | None
    genre: List[FilmDetailGenreResponse]
    actors: List[Person]
    writers: List[Person]
    directors: List[Person]

    @classmethod
    def from_model(cls, film: Film) -> "FilmDetailResponse":
        return cls(
            uuid=film.id,
            title=film.title,
            imdb_rating=film.imdb_rating,
            description=film.description,
            genre=[FilmDetailGenreResponse.from_model(genre) for genre in film.genres],
            actors=film.actors,
            writers=film.writers,
            directors=film.directors,
        )


@router.get(
    "/",
    response_model=list[FilmItemResponse],
    summary="Films list",
    description="Returns a list of films with their names and IMDb ratings. "
    "You can sort by IMDb rating or filter by genre",
    response_description="Film name and IMDb rating",
    tags=["films"],
)
async def films_list(
    film_service: Annotated[FilmService, Depends(get_film_service)],
    sort: str = Query(
        "-imdb_rating",
        examples=["-imdb_rating", "imdb_rating"],
        description="Name to sort by with '-' for DESC).",
    ),
    genre: Optional[str] = Query(
        None,
        description="filter by genre id",
    ),
    page_size: int = Query(50, ge=1, le=100),
    page_number: int = Query(1, ge=1),
) -> list[FilmItemResponse]:
    films = await film_service.list_films(sort, genre, page_size, page_number)
    return [FilmItemResponse.from_model(f) for f in films]


@router.get(
    "/search",
    response_model=list[FilmItemResponse],
    summary="Full-text search",
    description="Returns a list of films matching the search query. "
    "You can search by title, genres, description, actors, directors, and writers.",
    response_description="Film name and IMDb rating",
    tags=["films"],
)
async def films_search(
    film_service: Annotated[FilmService, Depends(get_film_service)],
    query: str = Query(..., min_length=1, description="Search query"),
    page_size: int = Query(50, ge=1, le=100),
    page_number: int = Query(1, ge=1),
) -> list[FilmItemResponse]:
    films = await film_service.search_films(query, page_size, page_number)
    return [FilmItemResponse.from_model(f) for f in films]


@router.get(
    "/{film_id}",
    response_model=FilmDetailResponse,
    summary="Film details",
    description="Returns detailed information about a film by its ID.",
    response_description="Detailed information about the film",
    tags=["films"],
)
async def film_details(
    film_id: str,
    film_service: Annotated[FilmService, Depends(get_film_service)],
) -> FilmDetailResponse:
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")

    return FilmDetailResponse.from_model(film)
