from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import get_settings
from app.schemas import ChatHistoryMessage, PredictionRequest, RecommendationRequest, SurveyRequest
from app.services.activity_service import log_activity
from app.services.dashboard_service import (
    fetch_dashboard_charts,
    fetch_dashboard_summary,
    fetch_recent_activities,
)
from app.services.knowledge_service import build_knowledge_context, find_relevant_knowledge
from app.services.model_service import model_service

ACRE_PER_HECTARE = 2.47105
QUINTAL_PER_TON = 10.0

DEFAULT_PREDICTION_INPUT: dict[str, Any] = {
    "crop": "rice",
    "state": "tamil nadu",
    "district": "thanjavur",
    "year": 2026,
    "area_hectares": 1.0,
    "rainfall_mm": 900.0,
    "temperature_c": 25.0,
    "humidity_pct": 65.0,
    "nitrogen": 70.0,
    "phosphorus": 40.0,
    "potassium": 40.0,
    "soil_ph": 6.5,
    "pesticides_tonnes": 0.03,
    "previous_yield_ton_hectare": 3.0,
}
CROP_KEYWORDS = ["rice", "wheat", "maize", "soybean", "cotton", "sugarcane", "barley", "sorghum"]
STATE_KEYWORDS = [
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "tamilnadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
]


@dataclass
class ChatAgentResult:
    reply: str
    used_tools: list[str] = field(default_factory=list)
    tool_summaries: list[str] = field(default_factory=list)


def _assistant_prompt(user_name: str, knowledge_context: str = "") -> str:
    prompt = (
        "You are AgroAI Copilot for Tamil Nadu farmers. "
        f"Current user: {user_name}. "
        "Keep language simple, practical, and respectful. "
        "Focus on Tamil Nadu crop, weather, irrigation, and regional farming conditions. "
        "Use India-friendly units: q/acre, q/ha, acres, quintals. "
        "If the user writes in Tamil, answer in Tamil. Otherwise answer in English."
    )
    if knowledge_context:
        prompt += "\n\n" + knowledge_context
    return prompt


def _normalize_limit(limit_value: Any, default: int = 10) -> int:
    try:
        limit = int(limit_value)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, 20))


def _merge_prediction_defaults(arguments: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    merged = {**DEFAULT_PREDICTION_INPUT}
    context_prediction = context.get("prediction_defaults", {})
    if isinstance(context_prediction, dict):
        merged.update({k: v for k, v in context_prediction.items() if v is not None})
    merged.update({k: v for k, v in arguments.items() if v is not None})
    return merged


async def _tool_predict_yield(database, user: dict, arguments: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = PredictionRequest(**_merge_prediction_defaults(arguments, context))
    output = model_service.predict(payload)

    area_hectares = payload.area_hectares
    area_acres = area_hectares * ACRE_PER_HECTARE
    yield_ton_hectare = output.yield_ton_hectare
    yield_quintal_hectare = yield_ton_hectare * QUINTAL_PER_TON
    yield_quintal_acre = yield_quintal_hectare / ACRE_PER_HECTARE
    total_tons = yield_ton_hectare * area_hectares
    total_quintals = total_tons * QUINTAL_PER_TON

    await database.predictions.insert_one(
        {
            "user_id": user["_id"],
            "input": payload.model_dump(),
            "predicted_yield_ton_hectare": yield_ton_hectare,
            "predicted_yield_quintal_hectare": yield_quintal_hectare,
            "predicted_yield_quintal_acre": yield_quintal_acre,
            "predicted_total_tons": total_tons,
            "predicted_total_quintals": total_quintals,
            "area_hectares": area_hectares,
            "area_acres": area_acres,
            "model_used": output.model_used,
            "created_at": output.created_at,
        }
    )
    await log_activity(
        user["_id"],
        "prediction",
        (
            f"{payload.crop.title()} in {payload.state.title()}: "
            f"{yield_quintal_acre:.2f} q/acre ({yield_quintal_hectare:.2f} q/ha)"
        ),
    )

    return {
        "crop": payload.crop,
        "state": payload.state,
        "predicted_yield_quintal_acre": round(yield_quintal_acre, 3),
        "predicted_yield_quintal_hectare": round(yield_quintal_hectare, 3),
        "predicted_total_quintals": round(total_quintals, 3),
        "area_acres": round(area_acres, 3),
        "model_used": output.model_used,
        "created_at": output.created_at.isoformat(),
    }


async def _tool_recommend_crops(database, user: dict, arguments: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    args = _merge_prediction_defaults(arguments, context)
    top_n = _normalize_limit(arguments.get("top_n"), default=5)
    payload = RecommendationRequest(**{**args, "top_n": top_n})
    prediction_request = PredictionRequest(**payload.model_dump())
    recommendations, model_used = model_service.recommend(prediction_request, top_n=payload.top_n)
    now = datetime.now(UTC)

    await database.recommendations.insert_one(
        {
            "user_id": user["_id"],
            "input": payload.model_dump(),
            "recommendations": [item.model_dump() for item in recommendations],
            "model_used": model_used,
            "created_at": now,
        }
    )
    crops = ", ".join([item.crop for item in recommendations[:3]])
    await log_activity(user["_id"], "recommendation", f"Top crops suggested: {crops}")

    return {
        "model_used": model_used,
        "top_recommendations": [
            {
                "crop": item.crop,
                "yield_q_acre": round(item.predicted_yield_quintal_acre, 3),
                "yield_q_ha": round(item.predicted_yield_quintal_hectare, 3),
            }
            for item in recommendations
        ],
        "created_at": now.isoformat(),
    }


async def _tool_submit_survey(database, user: dict, arguments: dict[str, Any]) -> dict[str, Any]:
    payload_data = {
        "preferred_crops": arguments.get("preferred_crops", []),
        "irrigation_method": arguments.get("irrigation_method"),
        "risk_appetite": arguments.get("risk_appetite"),
        "satisfaction_score": arguments.get("satisfaction_score", 4),
        "notes": arguments.get("notes"),
        "user_latitude": arguments.get("user_latitude"),
        "user_longitude": arguments.get("user_longitude"),
        "user_locality": arguments.get("user_locality"),
    }
    payload = SurveyRequest(**payload_data)
    now = datetime.now(UTC)

    await database.surveys.insert_one(
        {
            "user_id": user["_id"],
            **payload.model_dump(),
            "created_at": now,
        }
    )
    await log_activity(user["_id"], "survey", f"Survey submitted (satisfaction: {payload.satisfaction_score}/5)")

    return {
        "status": "saved",
        "satisfaction_score": payload.satisfaction_score,
        "created_at": now.isoformat(),
    }


async def _tool_get_recent_predictions(database, user: dict, arguments: dict[str, Any]) -> dict[str, Any]:
    limit = _normalize_limit(arguments.get("limit"), default=5)
    rows = (
        await database.predictions.find({"user_id": user["_id"]})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    predictions = []
    for row in rows:
        q_acre = row.get("predicted_yield_quintal_acre")
        if q_acre is None:
            q_acre = (float(row.get("predicted_yield_ton_hectare", 0.0)) * QUINTAL_PER_TON) / ACRE_PER_HECTARE
        predictions.append(
            {
                "crop": row.get("input", {}).get("crop", "unknown"),
                "state": row.get("input", {}).get("state", "unknown"),
                "yield_q_acre": round(float(q_acre), 3),
                "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
            }
        )
    return {"count": len(predictions), "items": predictions}


async def _tool_get_recent_recommendations(database, user: dict, arguments: dict[str, Any]) -> dict[str, Any]:
    limit = _normalize_limit(arguments.get("limit"), default=3)
    rows = (
        await database.recommendations.find({"user_id": user["_id"]})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    summaries: list[dict[str, Any]] = []
    for row in rows:
        top = row.get("recommendations", [])[:3]
        summaries.append(
            {
                "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
                "model_used": row.get("model_used", ""),
                "top_crops": [
                    {
                        "crop": item.get("crop", ""),
                        "yield_q_acre": round(float(item.get("predicted_yield_quintal_acre", 0.0)), 3),
                    }
                    for item in top
                ],
            }
        )
    return {"count": len(summaries), "items": summaries}


def _tool_summary(name: str, result: dict[str, Any]) -> str:
    if name == "predict_yield":
        return (
            f"Prediction saved: {result.get('crop', 'crop')} -> "
            f"{result.get('predicted_yield_quintal_acre', 'n/a')} q/acre"
        )
    if name == "recommend_crops":
        top_items = result.get("top_recommendations", [])[:3]
        crops = ", ".join([item.get("crop", "") for item in top_items]) or "none"
        return f"Recommendations saved: {crops}"
    if name == "submit_survey":
        return f"Survey saved with satisfaction {result.get('satisfaction_score', 'n/a')}/5"
    if name == "get_dashboard_summary":
        return "Loaded dashboard summary."
    if name == "get_dashboard_charts":
        return "Loaded chart analytics."
    if name == "get_recent_activities":
        return f"Loaded {result.get('count', 0)} activities."
    if name == "get_recent_predictions":
        return f"Loaded {result.get('count', 0)} predictions."
    if name == "get_recent_recommendations":
        return f"Loaded {result.get('count', 0)} recommendations."
    return f"Executed {name}"


async def _execute_tool(
    database,
    user: dict,
    tool_name: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    if tool_name == "predict_yield":
        return await _tool_predict_yield(database, user, arguments, context)
    if tool_name == "recommend_crops":
        return await _tool_recommend_crops(database, user, arguments, context)
    if tool_name == "submit_survey":
        return await _tool_submit_survey(database, user, arguments)
    if tool_name == "get_dashboard_summary":
        return (await fetch_dashboard_summary(database, user["_id"])).model_dump()
    if tool_name == "get_dashboard_charts":
        return (await fetch_dashboard_charts(database, user["_id"])).model_dump()
    if tool_name == "get_recent_activities":
        limit = _normalize_limit(arguments.get("limit"), default=10)
        activities = await fetch_recent_activities(database, user["_id"], limit=limit)
        return {"count": len(activities), "items": [item.model_dump() for item in activities]}
    if tool_name == "get_recent_predictions":
        return await _tool_get_recent_predictions(database, user, arguments)
    if tool_name == "get_recent_recommendations":
        return await _tool_get_recent_recommendations(database, user, arguments)
    raise ValueError(f"Unsupported tool: {tool_name}")


def _safe_json_loads(payload: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _command_mode_help() -> str:
    return (
        "Use app actions via commands:\n"
        "/predict {json}\n"
        "/recommend {json}\n"
        "/survey {json}\n"
        "/summary\n"
        "/charts\n"
        "/activities {\"limit\":10}\n"
        "/predictions {\"limit\":5}\n"
        "/recommendations {\"limit\":3}"
    )


def _extract_inline_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text)
    if not match:
        return {}
    return _safe_json_loads(match.group(0))


def _extract_first_int(text: str, default: int) -> int:
    match = re.search(r"\b(\d{1,2})\b", text)
    if not match:
        return default
    try:
        return int(match.group(1))
    except ValueError:
        return default


def _infer_tool_from_text(text: str) -> tuple[str, dict[str, Any]] | None:
    normalized = text.strip().lower()
    inline_args = _extract_inline_json(text)

    if "summary" in normalized or "dashboard" in normalized:
        return "get_dashboard_summary", inline_args
    if "chart" in normalized or "trend" in normalized or "analytics" in normalized:
        return "get_dashboard_charts", inline_args
    if "activities" in normalized or "activity" in normalized:
        limit = _extract_first_int(normalized, 10)
        return "get_recent_activities", {**inline_args, "limit": limit}
    if "recent prediction" in normalized or "past prediction" in normalized:
        limit = _extract_first_int(normalized, 5)
        return "get_recent_predictions", {**inline_args, "limit": limit}
    if "recent recommendation" in normalized or "past recommendation" in normalized:
        limit = _extract_first_int(normalized, 3)
        return "get_recent_recommendations", {**inline_args, "limit": limit}

    if "survey" in normalized:
        satisfaction = _extract_first_int(normalized, 4)
        if satisfaction < 1 or satisfaction > 5:
            satisfaction = 4
        return "submit_survey", {**inline_args, "satisfaction_score": inline_args.get("satisfaction_score", satisfaction)}

    if "recommend" in normalized:
        args = dict(inline_args)
        for crop in CROP_KEYWORDS:
            if crop in normalized:
                args.setdefault("crop", crop)
                break
        for state in STATE_KEYWORDS:
            if state in normalized:
                args.setdefault("state", state)
                break
        if "top" in normalized:
            args.setdefault("top_n", _extract_first_int(normalized, 5))
        return "recommend_crops", args

    if "predict" in normalized or ("yield" in normalized and ("estimate" in normalized or "forecast" in normalized)):
        args = dict(inline_args)
        for crop in CROP_KEYWORDS:
            if crop in normalized:
                args.setdefault("crop", crop)
                break
        for state in STATE_KEYWORDS:
            if state in normalized:
                args.setdefault("state", state)
                break
        return "predict_yield", args

    return None


async def _command_mode_response(
    database,
    user: dict,
    message: str,
    context: dict[str, Any],
) -> ChatAgentResult:
    text = message.strip()
    if not text.startswith("/"):
        inferred = _infer_tool_from_text(text)
        if inferred is not None:
            tool_name, arguments = inferred
            result = await _execute_tool(database, user, tool_name, arguments, context)
            summary = _tool_summary(tool_name, result)
            return ChatAgentResult(
                reply=f"{summary}\n\nData: {json.dumps(result, default=str)}",
                used_tools=[tool_name],
                tool_summaries=[summary],
            )
        return ChatAgentResult(
            reply=_general_guidance_reply(text),
            used_tools=[],
            tool_summaries=[],
        )

    command, _, arg_text = text.partition(" ")
    command_map = {
        "/predict": "predict_yield",
        "/recommend": "recommend_crops",
        "/survey": "submit_survey",
        "/summary": "get_dashboard_summary",
        "/charts": "get_dashboard_charts",
        "/activities": "get_recent_activities",
        "/predictions": "get_recent_predictions",
        "/recommendations": "get_recent_recommendations",
        "/help": "help",
    }
    tool_name = command_map.get(command.lower())
    if tool_name is None:
        return ChatAgentResult(reply=f"Unknown command `{command}`.\n{_command_mode_help()}")
    if tool_name == "help":
        return ChatAgentResult(reply=_command_mode_help())

    arguments = _safe_json_loads(arg_text.strip())
    result = await _execute_tool(database, user, tool_name, arguments, context)
    summary = _tool_summary(tool_name, result)
    return ChatAgentResult(
        reply=f"{summary}\n\nData: {json.dumps(result, default=str)}",
        used_tools=[tool_name],
        tool_summaries=[summary],
    )


async def _gemini_chat_reply(
    *,
    api_key: str,
    model: str,
    user: dict,
    message: str,
    history: list[ChatHistoryMessage],
    knowledge_context: str,
) -> str | None:
    contents: list[dict[str, Any]] = []
    for turn in history[-6:]:
        role = "model" if turn.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": turn.content}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    payload = {
        "systemInstruction": {"parts": [{"text": _assistant_prompt(user.get("name", "Farmer"), knowledge_context)}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 500},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        reply = "\n".join([part.strip() for part in text_parts if part.strip()])
        return reply or None
    except Exception:
        return None


def _general_guidance_reply(user_text: str) -> str:
    snippets = find_relevant_knowledge(user_text, top_k=4)
    if not snippets:
        return (
            "I can run app actions for you. Ask: show dashboard summary, predict yield, "
            "recommend crops, show activities, or use /help for command format."
        )

    lines = [
        "General farming guidance from the knowledge dataset:",
    ]
    for item in snippets:
        lines.append(f"- {item['title']}: {item['content']}")
    lines.append("")
    lines.append("You can also ask commands like /predict, /recommend, /summary.")
    return "\n".join(lines)


async def get_chat_reply(
    *,
    database,
    user: dict,
    message: str,
    history: list[ChatHistoryMessage] | None = None,
    context: dict[str, Any] | None = None,
) -> ChatAgentResult:
    settings = get_settings()
    turns = history or []
    context_data = context or {}
    trimmed = message.strip()
    knowledge_context = build_knowledge_context(trimmed)

    inferred = None if trimmed.startswith("/") else _infer_tool_from_text(trimmed)
    if trimmed.startswith("/") or inferred is not None:
        return await _command_mode_response(database, user, message, context_data)

    if settings.gemini_api_key:
        gemini_reply = await _gemini_chat_reply(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            user=user,
            message=message,
            history=turns,
            knowledge_context=knowledge_context,
        )
        if gemini_reply:
            return ChatAgentResult(reply=gemini_reply)

    return await _command_mode_response(database, user, message, context_data)
