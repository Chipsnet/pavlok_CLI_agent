"""Command API Handlers"""
import asyncio
import os
from datetime import datetime
from typing import Any, Dict

import requests


def _open_slack_modal(trigger_id: str, view: Dict[str, Any]) -> tuple[bool, str]:
    """
    Open a modal using Slack views.open API.
    Returns (ok, reason).
    """
    bot_token = os.getenv("SLACK_BOT_USER_OAUTH_TOKEN")
    if not bot_token:
        return False, "SLACK_BOT_USER_OAUTH_TOKEN is not configured"

    try:
        response = requests.post(
            "https://slack.com/api/views.open",
            headers={
                "Authorization": f"Bearer {bot_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "trigger_id": trigger_id,
                "view": view,
            },
            timeout=2.5,
        )
    except requests.RequestException as exc:
        return False, f"views.open request failed: {exc}"

    try:
        payload = response.json()
    except ValueError:
        return False, f"views.open non-JSON response: status={response.status_code}"

    if not payload.get("ok"):
        return False, payload.get("error", "views.open failed")

    return True, "ok"


async def process_base_commit(request) -> Dict[str, Any]:
    """
    ベースコミットコマンド処理

    Args:
        request: FastAPIリクエスト

    Returns:
        Dict[str, Any]: 処理結果
    """
    from backend.slack_ui import base_commit_modal

    modal_data = base_commit_modal([])
    trigger_id = request.get("trigger_id") if hasattr(request, "get") else None

    if trigger_id:
        ok, reason = await asyncio.to_thread(_open_slack_modal, trigger_id, modal_data)
        if ok:
            print(f"[{datetime.now()}] views.open succeeded")
            # Slash command response must be a valid command response.
            return {
                "status": "success",
                "response_type": "ephemeral",
                "text": "コミットメント管理モーダルを開きました。",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "📋 コミットメント管理モーダルを開きました。",
                        },
                    }
                ],
            }
        return {
            "status": "success",
            "response_type": "ephemeral",
            "text": f"モーダルを開けませんでした: {reason}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":warning: モーダルを開けませんでした: {reason}",
                    },
                }
            ],
        }
        
    print(f"[{datetime.now()}] views.open skipped: missing trigger_id")

    return {
        "status": "success",
        "response_type": "ephemeral",
        "text": "trigger_id が取得できないためモーダルを開けませんでした。再実行してください。",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":warning: trigger_id が取得できないためモーダルを開けませんでした。再実行してください。",
                },
            }
        ],
    }


async def process_stop(request) -> Dict[str, Any]:
    """
    停止コマンド処理

    Args:
        request: FastAPIリクエスト

    Returns:
        Dict[str, Any]: 処理結果
    """
    from backend.slack_ui import stop_notification

    blocks = stop_notification()
    return {
        "status": "success",
        "response_type": "ephemeral",
        "text": "鬼コーチを停止しました",
        "blocks": blocks,
    }


async def process_restart(request) -> Dict[str, Any]:
    """
    再開コマンド処理

    Args:
        request: FastAPIリクエスト

    Returns:
        Dict[str, Any]: 処理結果
    """
    from backend.slack_ui import restart_notification

    blocks = restart_notification()
    return {
        "status": "success",
        "response_type": "ephemeral",
        "text": "鬼コーチを再開しました",
        "blocks": blocks,
    }


async def process_config(request, config_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    設定コマンド処理

    Args:
        request: FastAPIリクエスト
        config_data: 設定データ

    Returns:
        Dict[str, Any]: 処理結果
    """
    # TODO: Implement actual config processing with database
    method = getattr(request, "method", "GET")
    if method == "GET":
        return {
            "status": "success",
            "response_type": "ephemeral",
            "text": "現在の設定を表示します。",
            "data": {"configurations": {}}
        }
    elif method == "POST" and config_data:
        return {
            "status": "success",
            "response_type": "ephemeral",
            "text": "設定を更新しました",
            "data": config_data
        }
    return {
        "status": "success",
        "response_type": "ephemeral",
        "text": "設定処理完了"
    }
