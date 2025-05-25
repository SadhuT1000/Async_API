from datetime import datetime
from typing import Dict, List, Tuple

import psycopg
from psycopg import ClientCursor, Cursor
from psycopg.rows import dict_row
from schemas.elasticsearch import ESMovieDocument, Genre, GenreBaseInfo, Person
from utils.backoff import backoff
from utils.logging_settings import logger
from utils.state import State


class PostgresProducer:
    def __init__(self, connect_data: dict, state: State):
        self.state = state
        self.connect_data = connect_data

    def _get_modified_ids(
        self, table_name: str, cursor: Cursor, state_prefix: str = ""
    ) -> List[str]:
        state_key = f"{state_prefix}_{table_name}_state"
        state = self.state.get_state_json(state_key)

        proceed_timestamp, proceed_id = (
            state
            if state
            else (datetime.min.isoformat(), "00000000-0000-0000-0000-000000000000")
        )

        query = f"""
                    SELECT id, modified
                    FROM content.{table_name}
                    WHERE modified > %s OR (modified = %s AND id > %s)
                    ORDER BY modified, id
                    LIMIT 100;
                """  # noqa: E702, E231, E241

        cursor.execute(query, (proceed_timestamp, proceed_timestamp, proceed_id))
        data: Tuple[dict] = cursor.fetchall()  # type: ignore

        if len(data) == 0:
            return []

        last_processed_timestamp = data[-1]["modified"].isoformat()
        last_processed_id = str(data[-1]["id"])

        logger.info(
            f"{table_name}: last_processed_timestamp: {last_processed_timestamp}, last_processed_id: {last_processed_id}"
        )

        self.state.set_state_json(
            state_key, [last_processed_timestamp, last_processed_id]
        )

        return [str(item["id"]) for item in data]

    def _get_films_with_modified_persons(
        self, modified_persons: list, cursor: Cursor
    ) -> List[str]:
        query = """
                    SELECT fw.id, fw.modified
                    FROM content.film_work fw
                    LEFT JOIN content.person_film_work pfw ON pfw.film_work_id = fw.id
                    WHERE pfw.person_id = ANY(%s)
                    ORDER BY fw.modified
                    ;
                """
        cursor.execute(query, (modified_persons,))
        data: Tuple[dict] = cursor.fetchall()  # type: ignore
        return [str(item["id"]) for item in data]

    def _get_films_by_ids(
        self, films_with_modified_persons: List[str], cursor: Cursor
    ) -> List[dict]:
        query = """
                    SELECT
                        fw.id as fw_id,
                        fw.title as fw_title,
                        fw.description as fw_description,
                        fw.rating as fw_rating,
                        fw.created as fw_created,
                        fw.modified as fw_modified,
                        pfw.role as pfw_role,
                        p.id as p_id,
                        p.full_name as p_full_name,
                        g.id as g_id,
                        g.name as g_name
                    FROM content.film_work fw
                    LEFT JOIN content.person_film_work pfw ON pfw.film_work_id = fw.id
                    LEFT JOIN content.person p ON p.id = pfw.person_id
                    LEFT JOIN content.genre_film_work gfw ON gfw.film_work_id = fw.id
                    LEFT JOIN content.genre g ON g.id = gfw.genre_id
                    WHERE fw.id = ANY(%s);
                """

        cursor.execute(query, (films_with_modified_persons,))
        data = cursor.fetchall()
        return data  # type: ignore

    def _merge_data_to_models(  # noqa: CCR001
        self, data: List[dict]
    ) -> Dict[str, ESMovieDocument]:
        docs: Dict[str, ESMovieDocument] = {}
        for row in data:
            doc = docs.get(row["fw_id"])
            if not doc:
                doc = ESMovieDocument(
                    id=row["fw_id"],
                    title=row["fw_title"],
                    description=row["fw_description"],
                    imdb_rating=row["fw_rating"],
                    genres=set(),
                    genres_names=set(),
                    actors=set(),
                    actors_names=set(),
                    directors=set(),
                    directors_names=set(),
                    writers=set(),
                    writers_names=set(),
                )
                docs[row["fw_id"]] = doc

            if row.get("g_id"):
                genre = GenreBaseInfo(id=row.get("g_id"), name=row.get("g_name"))
                doc.genres.add(genre)
                doc.genres_names.add(genre.name)

            if row.get("p_id"):
                person = Person(id=row["p_id"], name=row["p_full_name"])
                role = row.get("pfw_role")
                if role == "actor":
                    doc.actors.add(person)
                    doc.actors_names.add(person.name)
                elif role == "writer":
                    doc.writers.add(person)
                    doc.writers_names.add(person.name)
                elif role == "director":
                    doc.directors.add(person)
                    doc.directors_names.add(person.name)
        return docs

    def get_films_with_modified_genres(
        self, genres_ids: List[str], cursor: Cursor
    ) -> List[str]:
        query = """
                    SELECT fw.id, fw.modified
                    FROM content.film_work fw
                    LEFT JOIN content.genre_film_work gfw ON gfw.film_work_id = fw.id
                    WHERE gfw.genre_id = ANY(%s)
                    ORDER BY fw.modified;
                """
        cursor.execute(query, (genres_ids,))
        data = cursor.fetchall()
        return [str(item["id"]) for item in data]  # type: ignore

    @backoff()
    def get_film_works_by_modified_persons(  # noqa: CCR001
        self,
    ) -> Dict[str, ESMovieDocument]:

        with psycopg.connect(
            **self.connect_data, row_factory=dict_row, cursor_factory=ClientCursor
        ) as pg_conn:
            cursor = pg_conn.cursor()
            modified_persons_ids = self._get_modified_ids("person", cursor)
            films_ids = self._get_films_with_modified_persons(
                modified_persons_ids, cursor
            )
            film_data = self._get_films_by_ids(films_ids, cursor)
            merged_objects = self._merge_data_to_models(film_data)
            return merged_objects

    @backoff()
    def get_films_by_modified_self(self) -> Dict[str, ESMovieDocument]:  # noqa: CCR001
        with psycopg.connect(
            **self.connect_data, row_factory=dict_row, cursor_factory=ClientCursor
        ) as pg_conn:
            cursor = pg_conn.cursor()
            films_ids = self._get_modified_ids("film_work", cursor)
            films_data = self._get_films_by_ids(films_ids, cursor)
            merged_objects = self._merge_data_to_models(films_data)
            return merged_objects

    @backoff()
    def get_film_works_by_modified_genres(
        self,
    ) -> Dict[str, ESMovieDocument]:  # noqa: CCR001
        with psycopg.connect(
            **self.connect_data, row_factory=dict_row, cursor_factory=ClientCursor
        ) as pg_conn:
            cursor = pg_conn.cursor()
            genres_ids = self._get_modified_ids("genre", cursor)
            films_ids = self.get_films_with_modified_genres(genres_ids, cursor)
            films_data = self._get_films_by_ids(films_ids, cursor)
            merged_objects = self._merge_data_to_models(films_data)
            return merged_objects

    @backoff()
    def _get_genres_by_ids(self, genres_ids: List[str], cursor) -> List[dict]:
        query = """
                SELECT g.id, g.name, g.description
                FROM content.genre g
                WHERE g.id = ANY(%s)
                """
        cursor.execute(query, (genres_ids,))
        data = cursor.fetchall()
        return data

    def _merge_genres_to_models(self, genres_data: List[dict]) -> Dict[str, Genre]:
        docs = {}
        for genre in genres_data:
            doc = Genre(**genre)
            docs[doc.id] = doc
        return docs

    @backoff()
    def get_modified_genres(self) -> Dict[str, Genre]:
        with psycopg.connect(
            **self.connect_data, row_factory=dict_row, cursor_factory=ClientCursor
        ) as pg_conn:
            cursor = pg_conn.cursor()
            genres_ids = self._get_modified_ids(
                "genre", cursor, state_prefix="genres_index"
            )
            genres_data = self._get_genres_by_ids(genres_ids, cursor)
            model_objects = self._merge_genres_to_models(genres_data)
            return model_objects
