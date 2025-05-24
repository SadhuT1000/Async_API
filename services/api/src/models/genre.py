from pydantic import BaseModel


class Genre(BaseModel):

    id: int
    name: str
    description: str
