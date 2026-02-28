from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.config import get_settings

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _database
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    _database = _client[settings.mongo_db_name]

    try:
        await _client.admin.command("ping")
    except PyMongoError:
        # Keep the app booting so developers can still run in partial/offline mode.
        _client = None
        _database = None


async def disconnect_mongo() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI and run MongoDB.")
    return _database


def to_jsonable(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    if "_id" in document:
        document["_id"] = str(document["_id"])
    return document
