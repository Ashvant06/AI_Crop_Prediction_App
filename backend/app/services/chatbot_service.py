from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas import ChatHistoryMessage, PredictionRequest, RecommendationRequest, SurveyRequest
from app.services.activity_service import log_activity
from app.services.dashboard_service import (
    fetch_dashboard_charts,
    fetch_dashboard_summary,
    fetch_recent_activities,
)
from app.services.model_service import model_service

ACRE_PER_HECTARE = 2.47105
QUINTAL_PER_TON = 10.0
MAX_TOOL_STEPS = 5

DEFAULT_PREDICTION_INPUT: dict[str, Any] = {
    "crop": "rice",
    "state": "karnataka",
    "district": "mysuru",
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


def _assistant_prompt(user_name: str) -> str:
    return (
        "You are AgroAI Copilot for an Indian farming app. "
        f"Current user: {user_name}. "
        "You can execute app tools for predictions, recommendations, surveys, dashboards, and activities. "
        "When data is requested, call tools instead of guessing. "
        "For prediction/recommendation tools, if the user misses fields, use practical defaults and explain assumptions. "
        "Use India-friendly units in replies: q/acre, q/ha, acres, quintals. "
        "Keep responses practical, concise, and action-oriented."
    )


def _tool_schemas() -> list[dict[str, Any]]:
    prediction_properties = {
        "crop": {"type": "string"},
        "state": {"type": "string"},
        "district": {"type": "string"},
        "year": {"type": "integer"},
        "area_hectares": {"type": "number"},
        "rainfall_mm": {"type": "number"},
        "temperature_c": {"type": "number"},
        "humidity_pct": {"type": "number"},
        "nitrogen": {"type": "number"},
        "phosphorus": {"type": "number"},
        "potassium": {"type": "number"},
        "soil_ph": {"type": "number"},
        "pesticides_tonnes": {"type": "number"},
        "previous_yield_ton_hectare": {"type": "number"},
    }
    return [
        {
            "type": "function",
            "function": {
                "name": "predict_yield",
                "description": "Run crop yield prediction and save it in user account.",
                "parameters": {"type": "object", "properties": prediction_properties},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "recommend_crops",
                "description": "Recommend top crops based on conditions and save recommendation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        **prediction_properties,
                        "top_n": {"type": "integer"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "submit_survey",
                "description": "Submit a farmer survey response for the current user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "preferred_crops": {"type": "array", "items": {"type": "string"}},
                        "irrigation_method": {"type": "string"},
                        "risk_appetite": {"type": "string"},
                        "satisfaction_score": {"type": "integer"},
                        "notes": {"type": "string"},
                    },
                    "required": ["satisfaction_score"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_dashboard_summary",
                "description": "Get user dashboard summary metrics.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_dashboard_charts",
                "description": "Get chart-ready analytics data for monthly yields and trends.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_recent_activities",
                "description": "Get recent user activities from app history.",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_recent_predictions",
                "description": "Fetch recent saved prediction results.",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_recent_recommendations",
                "description": "Fetch recent saved crop recommendation results.",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
            },
        },
    ]


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


def _build_messages(user: dict, message: str, history: list[ChatHistoryMessage]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": _assistant_prompt(user.get("name", "Farmer"))}]
    for turn in history[-10:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": message})
    return messages


def _safe_json_loads(payload: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _command_mode_help() -> str:
    return (
        "Generative mode is unavailable (OPENAI_API_KEY missing), but you can still use app actions via commands:\n"
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
            reply=(
                "I can operate all app features for you. Ask naturally like "
                "\"show dashboard summary\", \"predict wheat in punjab\", \"recommend crops\", "
                "\"show my activities\", or use /help for command format."
            ),
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
    return ChatAgentResult(reply=f"{summary}\n\nData: {json.dumps(result, default=str)}", used_tools=[tool_name], tool_summaries=[summary])


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

    if not settings.openai_api_key:
        return await _command_mode_response(database, user, message, context_data)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    messages = _build_messages(user, message, turns)
    used_tools: list[str] = []
    tool_summaries: list[str] = []
    tools = _tool_schemas()

    try:
        for _ in range(MAX_TOOL_STEPS):
            completion = await client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.2,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            assistant_message = completion.choices[0].message
            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                text = (assistant_message.content or "").strip()
                if text:
                    return ChatAgentResult(reply=text, used_tools=used_tools, tool_summaries=tool_summaries)
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in tool_calls
                    ],
                }
            )

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                arguments = _safe_json_loads(tool_call.function.arguments)
                try:
                    result = await _execute_tool(database, user, tool_name, arguments, context_data)
                    summary = _tool_summary(tool_name, result)
                except Exception as exc:
                    result = {"error": str(exc)}
                    summary = f"{tool_name} failed: {exc}"

                used_tools.append(tool_name)
                tool_summaries.append(summary)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        if tool_summaries:
            return ChatAgentResult(
                reply="Completed requested operations.\n" + "\n".join([f"- {item}" for item in tool_summaries]),
                used_tools=used_tools,
                tool_summaries=tool_summaries,
            )
        return ChatAgentResult(reply="I could not complete that request. Please rephrase with crop and location details.")
    except Exception:
        return await _command_mode_response(database, user, message, context_data)
