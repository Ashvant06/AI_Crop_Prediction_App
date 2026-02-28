from datetime import UTC, datetime

from app.db import get_database


async def log_activity(user_id: str, activity_type: str, detail: str) -> None:
    database = get_database()
    await database.activities.insert_one(
        {
            "user_id": user_id,
            "activity_type": activity_type,
            "detail": detail,
            "created_at": datetime.now(UTC),
        }
    )
