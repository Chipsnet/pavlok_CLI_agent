"""Interactive API Handlers"""
from typing import Dict, Any

MAX_COMMITMENT_ROWS = 10


def _current_commitments_from_view(view: Dict[str, Any]) -> list[dict[str, str]]:
    """Extract current modal input values from Slack view payload."""
    blocks = view.get("blocks", [])
    state_values = view.get("state", {}).get("values", {})

    row_count = sum(
        1
        for block in blocks
        if str(block.get("block_id", "")).startswith("commitment_")
    )
    row_count = max(3, row_count)

    commitments: list[dict[str, str]] = []
    for idx in range(1, row_count + 1):
        task = ""
        selected_time = ""

        task_block = state_values.get(f"commitment_{idx}", {})
        task_input = task_block.get(f"task_{idx}", {})
        if isinstance(task_input, dict):
            task = task_input.get("value", "") or ""

        time_block = state_values.get(f"time_{idx}", {})
        time_input = time_block.get(f"time_{idx}", {})
        if isinstance(time_input, dict):
            selected_time = time_input.get("selected_time", "") or ""

        commitments.append({"task": task, "time": selected_time})

    return commitments


async def process_commitment_add_row(payload_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle "+ 追加" in base_commit modal by returning response_action=update.
    """
    from backend.slack_ui import base_commit_modal

    view = payload_data.get("view", {})
    commitments = _current_commitments_from_view(view)
    if len(commitments) < MAX_COMMITMENT_ROWS:
        commitments.append({"task": "", "time": ""})

    updated_view = base_commit_modal(commitments)

    # Keep metadata flags that may be set by previous view state.
    for key in ("private_metadata", "clear_on_close", "notify_on_close", "external_id"):
        if key in view:
            updated_view[key] = view[key]

    return {
        "response_action": "update",
        "view": updated_view,
    }


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
