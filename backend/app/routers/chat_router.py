from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.db import get_database
from app.dependencies import get_current_user
from app.schemas import ChatRequest, ChatResponse
from app.services.activity_service import log_activity
from app.services.chatbot_service import get_chat_reply

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def chatbot_message(payload: ChatRequest, user: dict = Depends(get_current_user)) -> ChatResponse:
    now = datetime.now(UTC)
    try:
        database = get_database()
        agent_result = await get_chat_reply(
            database=database,
            user=user,
            message=payload.message,
            history=payload.history,
            context=payload.context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    try:
        await database.chat_logs.insert_one(
            {
                "user_id": user["_id"],
                "message": payload.message,
                "history": [item.model_dump() for item in payload.history],
                "context": payload.context,
                "reply": agent_result.reply,
                "used_tools": agent_result.used_tools,
                "tool_summaries": agent_result.tool_summaries,
                "created_at": now,
            }
        )
        tool_count = len(agent_result.used_tools)
        detail = "Asked agro-assistant for guidance" if tool_count == 0 else f"Assistant executed {tool_count} app action(s)"
        await log_activity(user["_id"], "chat", detail)
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save chat") from exc

    return ChatResponse(
        reply=agent_result.reply,
        created_at=now,
        used_tools=agent_result.used_tools,
        tool_summaries=agent_result.tool_summaries,
    )
