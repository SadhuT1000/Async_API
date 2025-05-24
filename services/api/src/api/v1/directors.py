from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Directors(BaseModel):

    id: int
    full_name: str
