import json
from typing import Any, Optional

from utils.storages.base_storage import BaseStorage


class State:
    """Класс для работы с состояниями."""

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    def set_state(self, key: str, value: Any) -> None:
        """Установить состояние для определённого ключа."""
        self.storage.set(key, value)

    def get_state(self, key: str) -> Any:
        """Получить состояние по определённому ключу."""
        state = self.storage.get(key)
        return state

    def get_state_json(self, key: str) -> Optional[Any]:
        """Получить состояние в формате JSON."""
        state_json = self.get_state(key)
        if state_json is None:
            return None
        return json.loads(state_json)

    def set_state_json(self, key: str, value: Any) -> None:
        """Установить состояние в формате JSON."""
        state_json = json.dumps(value)
        self.set_state(key, state_json)
