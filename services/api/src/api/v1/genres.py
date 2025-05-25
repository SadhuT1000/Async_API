from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from models.genre import Genre
from pydantic import BaseModel
from services.genre import GenreService, get_genre_service

router = APIRouter()


class GenreResponse(BaseModel):
    uuid: UUID
    name: str

    @classmethod
    def from_model(cls, genre: Genre) -> "GenreResponse":
        return cls(uuid=genre.id, name=genre.name)


@router.get(
    "/",
    response_model=list[GenreResponse],
    summary="Genres list",
    description="Returns a list of genres.",
    tags=["genres"],
)
async def genres_list(
    genre_service: Annotated[GenreService, Depends(get_genre_service)],
    page_size: int = Query(50, ge=1, le=100),
    page_number: int = Query(1, ge=1),
) -> list[GenreResponse]:
    genres = await genre_service.list_genres(page_size, page_number)
    return [GenreResponse.from_model(genre) for genre in genres]


@router.get(
    "/{genre_id}",
    response_model=GenreResponse,
    summary="Genre details",
    tags=["genres"],
)
async def genre_details(
    genre_id: str,
    genre_service: Annotated[GenreService, Depends(get_genre_service)],
) -> GenreResponse:
    genre = await genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="genre not found")

    return GenreResponse.from_model(genre)
