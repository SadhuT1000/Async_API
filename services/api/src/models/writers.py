from typing import List

from pydantic import BaseModel


class Writers(BaseModel):

    id: int
    full_name: str
    films: List[int] = []
