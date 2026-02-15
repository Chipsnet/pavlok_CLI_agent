"""Command API Handlers"""
import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict
from collections.abc import Mapping

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Commitment

MAX_COMMITMENT_ROWS = 10

_SESSION_FACTORY = None
_SESSION_DB_URL = None


def _get_session():
    """Create DB session using current DATABASE_URL."""
    global _SESSION_FACTORY, _SESSION_DB_URL
    database_url = os.getenv("DATABASE_URL", "sqlite:///./oni.db")

    if _SESSION_FACTORY is None or _SESSION_DB_URL != database_url:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )
        _SESSION_FACTORY = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
        _SESSION_DB_URL = database_url

    return _SESSION_FACTORY()


def _load_existing_commitments(user_id: str) -> list[dict[str, str]]:
    """Load existing active commitments for modal prefill."""
    if not user_id:
        return []

    session = _get_session()
    try:
        rows = (
            session.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.active.is_(True),
            )
            .order_by(Commitment.time.asc(), Commitment.created_at.asc())
            .limit(MAX_COMMITMENT_ROWS)
            .all()
        )
        return [{"task": row.task, "time": row.time} for row in rows]
    except Exception as exc:
        print(f"[{datetime.now()}] failed to load commitments for modal: {exc}")
        return []
    finally:
        session.close()


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
        error = payload.get("error", "views.open failed")
        details = payload.get("response_metadata", {}).get("messages", [])
        if details:
            return False, f"{error} ({'; '.join(details)})"
        return False, error

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

    request_map = request if isinstance(request, Mapping) else {}
    user_id = request_map.get("user_id", "")
    channel_id = request_map.get("channel_id", "")
    response_url = request_map.get("response_url", "")
    trigger_id = request_map.get("trigger_id", "")

    if not isinstance(user_id, str):
        user_id = ""
    if not isinstance(channel_id, str):
        channel_id = ""
    if not isinstance(response_url, str):
        response_url = ""
    if not isinstance(trigger_id, str):
        trigger_id = ""

    existing_commitments: list[dict[str, str]] = []
    if user_id:
        existing_commitments = _load_existing_commitments(user_id)
    modal_data = base_commit_modal(existing_commitments)
    private_metadata: dict[str, str] = {}
    if channel_id:
        private_metadata["channel_id"] = channel_id
    if user_id:
        private_metadata["user_id"] = user_id
    if response_url:
        private_metadata["response_url"] = response_url
    if private_metadata:
        modal_data["private_metadata"] = json.dumps(private_metadata, ensure_ascii=False)

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
