import pytest

from backend.main import route_interactive_payload


@pytest.mark.asyncio
async def test_route_interactive_payload_plan_open_modal(monkeypatch):
    payload_data = {
        "type": "block_actions",
        "user": {"id": "U03JBULT484"},
        "actions": [{"action_id": "plan_open_modal"}],
    }
    called = {}

    async def _fake_process_plan_open_modal(received_payload):
        called["payload"] = received_payload
        return {"status": "success"}

    monkeypatch.setattr(
        "backend.main.process_plan_open_modal",
        _fake_process_plan_open_modal,
    )

    result = await route_interactive_payload(payload_data)

    assert result == {"status": "success"}
    assert called["payload"] == payload_data


@pytest.mark.asyncio
async def test_route_interactive_payload_plan_submit(monkeypatch):
    payload_data = {
        "type": "view_submission",
        "user": {"id": "U03JBULT484"},
        "view": {"callback_id": "plan_submit", "state": {"values": {}}},
    }
    called = {}

    async def _fake_process_plan_modal_submit(received_payload):
        called["payload"] = received_payload
        return {"response_action": "clear"}

    monkeypatch.setattr(
        "backend.main.process_plan_modal_submit",
        _fake_process_plan_modal_submit,
    )

    result = await route_interactive_payload(payload_data)

    assert result == {"response_action": "clear"}
    assert called["payload"] == payload_data
