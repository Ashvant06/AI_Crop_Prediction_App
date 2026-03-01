from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

COLLECTION_NAMES = ("users", "predictions", "recommendations", "surveys", "activities", "chat_logs")
DATETIME_TAG = "__local_datetime__"


def _normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _value_matches(actual: Any, expected: Any) -> bool:
    if actual == expected:
        return True
    return str(_normalize(actual)) == str(_normalize(expected))


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        if not _value_matches(document.get(key), expected):
            return False
    return True


def _nested_value(document: dict[str, Any], path: str) -> Any:
    value: Any = document
    for segment in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(segment)
    return value


def _sortable(value: Any) -> tuple[int, Any]:
    if value is None:
        return (1, "")
    if isinstance(value, datetime):
        return (0, value.timestamp())
    if isinstance(value, (int, float)):
        return (0, value)
    return (0, str(value))


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return {DATETIME_TAG: value.isoformat()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _deserialize(value: Any) -> Any:
    if isinstance(value, list):
        return [_deserialize(item) for item in value]
    if isinstance(value, dict):
        if DATETIME_TAG in value and isinstance(value[DATETIME_TAG], str):
            return datetime.fromisoformat(value[DATETIME_TAG])
        return {key: _deserialize(item) for key, item in value.items()}
    return value


class LocalInsertOneResult:
    def __init__(self, inserted_id: str) -> None:
        self.inserted_id = inserted_id


class LocalCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def sort(self, key: str, direction: int) -> LocalCursor:
        reverse = direction < 0
        self._rows.sort(key=lambda row: _sortable(_nested_value(row, key)), reverse=reverse)
        return self

    def limit(self, count: int) -> LocalCursor:
        if count >= 0:
            self._rows = self._rows[:count]
        return self

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        if length is None or length < 0:
            return deepcopy(self._rows)
        return deepcopy(self._rows[:length])


class LocalCollection:
    def __init__(self, database: LocalDatabase, name: str) -> None:
        self._database = database
        self._name = name

    async def insert_one(self, document: dict[str, Any]) -> LocalInsertOneResult:
        row = deepcopy(document)
        row.setdefault("_id", uuid4().hex)
        self._database._rows(self._name).append(row)
        self._database._persist()
        return LocalInsertOneResult(inserted_id=str(row["_id"]))

    async def count_documents(self, query: dict[str, Any]) -> int:
        return sum(1 for row in self._database._rows(self._name) if _matches(row, query))

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for row in self._database._rows(self._name):
            if _matches(row, query):
                return deepcopy(row)
        return None

    async def find_one_and_update(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        *,
        upsert: bool = False,
        return_document: Any = None,
    ) -> dict[str, Any] | None:
        del return_document
        rows = self._database._rows(self._name)
        update_set = deepcopy(update.get("$set", {}))
        update_set_on_insert = deepcopy(update.get("$setOnInsert", {}))

        for index, row in enumerate(rows):
            if not _matches(row, query):
                continue
            rows[index] = {**row, **update_set}
            self._database._persist()
            return deepcopy(rows[index])

        if not upsert:
            return None

        inserted = {**deepcopy(query), **update_set_on_insert, **update_set}
        inserted.setdefault("_id", uuid4().hex)
        rows.append(inserted)
        self._database._persist()
        return deepcopy(inserted)

    def find(self, query: dict[str, Any]) -> LocalCursor:
        rows = [deepcopy(row) for row in self._database._rows(self._name) if _matches(row, query)]
        return LocalCursor(rows)


class LocalDatabase:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._lock = Lock()
        self._data: dict[str, list[dict[str, Any]]] = self._load()

        for name in COLLECTION_NAMES:
            setattr(self, name, LocalCollection(self, name))

    def _rows(self, name: str) -> list[dict[str, Any]]:
        return self._data[name]

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        base: dict[str, list[dict[str, Any]]] = {name: [] for name in COLLECTION_NAMES}
        if not self._storage_path.exists():
            return base

        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return base

        if not isinstance(raw, dict):
            return base

        for name in COLLECTION_NAMES:
            source = raw.get(name, [])
            if isinstance(source, list):
                base[name] = _deserialize(source)
        return base

    def _persist(self) -> None:
        payload = {name: _serialize(rows) for name, rows in self._data.items()}
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
