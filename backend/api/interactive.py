"""Interactive API Handlers"""
from fastapi import Request, HTTPException, status
from typing import Dict, Any


async def process_plan_submit(payload_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    プラン登録処理（インタラクティブ）

    Args:
        payload_data: Slackペイロードデータ

    Returns:
        Dict[str, Any]: 処理結果
    """
    # TODO: Implement actual plan registration with database
    return {
        "status": "success",
        "detail": "予定を登録しました"
    }


async def process_remind_response(payload_data: Dict[str, Any], action: str = "YES") -> Dict[str, Any]:
    """
    リマインド応答処理（YES/NO）

    Args:
        payload_data: Slackペイロードデータ
        action: "YES" or "NO"

    Returns:
        Dict[str, Any]: 処理結果
    """
    # TODO: Implement actual remind response processing with database
    if action == "YES":
        return {
            "status": "success",
            "detail": "やりました！"
        }
    else:
        return {
            "status": "success",
            "detail": "できませんでした..."
        }


async def process_ignore_response(payload_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    無視応答処理（今やりました/やっぱり）

    Args:
        payload_data: Slackペイロードデータ

    Returns:
        Dict[str, Any]: 処理結果
    """
    # TODO: Implement actual ignore response processing with database
    actions = payload_data.get("actions", [])
    if actions:
        action_value = actions[0].get("value", "")
        try:
            import json
            value_data = json.loads(action_value)
            action_type = "yes" if "yes" in actions[0].get("action_id", "") else "no"
        except (json.JSONDecodeError, TypeError):
            action_type = "yes"
    else:
        action_type = "yes"

    if action_type == "yes":
        return {
            "status": "success",
            "detail": "今やりました"
        }
    else:
        return {
            "status": "success",
            "detail": "やっぱり..."
        }
