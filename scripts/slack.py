"""Slack helper utilities for worker scripts."""
from __future__ import annotations

import os
from typing import Any

import requests


def require_bot_token() -> str:
    """Get bot token from environment or raise an error."""
    token = os.getenv("SLACK_BOT_USER_OAUTH_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SLACK_BOT_USER_OAUTH_TOKEN is not configured")
    return token


def require_channel() -> str:
    """Resolve destination channel for worker notifications."""
    for key in ("SLACK_CHANNEL", "SLACK_CHANNEL_ID", "CHANNEL_ID"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise RuntimeError(
        "Slack channel is not configured. Set SLACK_CHANNEL or SLACK_CHANNEL_ID."
    )


def post_message(
    blocks: list[dict[str, Any]],
    channel: str,
    token: str,
    text: str = "notification",
):
    """Post a Block Kit message to Slack and validate response."""
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={
            "channel": channel,
            "text": text,
            "blocks": blocks,
            "unfurl_links": False,
            "unfurl_media": False,
        },
        timeout=5,
    )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"chat.postMessage returned non-JSON response: {response.status_code}"
        ) from exc

    if not payload.get("ok"):
        raise RuntimeError(f"chat.postMessage failed: {payload.get('error')}")

    return response
