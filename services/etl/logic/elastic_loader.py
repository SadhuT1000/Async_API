import json

import requests
from schemas.elasticsearch import ESMovieDocument, Genre
from utils.backoff import backoff
from utils.logging_settings import logger


class ElasticSearchLoader:

    def create_index(self, file_path: str, index_name: str):
        with open(file_path, "r") as f:
            index_data = json.load(f)

        request = requests.put(
            f"{self.base_url}/{index_name}",
            json=index_data,
            headers={"Content-Type": "application/json"},
        )
        status_code = request.status_code
        if status_code == 400:
            logger.warning("Elastic WARNING:\n" + str(request.json()))
        if status_code == 500:
            logger.error("Elastic ERROR:\n" + str(request.json()))

    @backoff()
    def create_indexes(self) -> None:
        self.create_index("resources/movie_index.json", "movies")
        self.create_index("resources/genre_index.json", "genres")

    def __init__(self, api_url: str):
        self.base_url = api_url  # noqa: E231

    @backoff()
    def load(self, docs: dict[str, ESMovieDocument | Genre], index_name: str) -> int:
        if len(docs) == 0:
            logger.info(f"Загрузка {index_name} не требуется")
            return 0

        logger.info(f"Загружаем {len(docs)} записей в {index_name}")
        request_body = ""
        for doc in docs.values():
            id_row = {"index": {"_index": index_name, "_id": str(doc.id)}}
            request_body += f"{json.dumps(id_row)}\n"  # Строка с id
            request_body += f"{doc.model_dump_json()}\n"  # Строка с объектом
        request_body += "\n"  # Необходим перенос строки в конце
        response = requests.post(
            f"{self.base_url}/_bulk",
            headers={"Content-Type": "application/x-ndjson"},
            data=request_body,
        )
        logger.info(response.status_code)

        return len(docs)
