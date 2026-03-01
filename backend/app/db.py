from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings
from app.local_store import LocalDatabase

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | LocalDatabase | None = None


def _resolve_local_store_path(configured_path: str) -> Path:
    configured = Path(configured_path)
    if configured.is_absolute():
        return configured

    backend_root = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / configured,
        backend_root / configured,
        Path.cwd() / configured,
        backend_root / "data" / "local_store.json",
    ]
    return candidates[0]


def _activate_local_store() -> None:
    global _database, _client
    settings = get_settings()
    _client = None
    _database = LocalDatabase(_resolve_local_store_path(settings.local_db_path))


async def connect_to_mongo() -> None:
    global _client, _database
    settings = get_settings()
    mongo_uri = settings.mongo_uri.strip()

    if not mongo_uri:
        if settings.local_db_fallback:
            _activate_local_store()
            return
        _client = None
        _database = None
        return

    _client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=4000)
    _database = _client[settings.mongo_db_name]

    try:
        await _client.admin.command("ping")
    except Exception:
        if _client is not None:
            _client.close()
        if settings.local_db_fallback:
            _activate_local_store()
            return
        _client = None
        _database = None


async def disconnect_mongo() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase | LocalDatabase:
    if _database is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI and run MongoDB.")
    return _database


def to_jsonable(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    if "_id" in document:
        document["_id"] = str(document["_id"])
    return document
