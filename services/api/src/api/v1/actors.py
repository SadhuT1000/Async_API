from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Actors(BaseModel):

    id: int
    full_name: str
