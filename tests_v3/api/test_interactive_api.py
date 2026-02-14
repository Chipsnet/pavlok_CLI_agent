# v0.3 Interactive API Tests
import pytest
from unittest.mock import MagicMock
from fastapi import Request, HTTPException, status
from backend.api.interactive import (
    process_plan_submit,
    process_remind_response,
    process_ignore_response
)
from backend.models import Schedule, ActionLog, ActionResult


@pytest.mark.asyncio
class TestInteractiveApi:

    @pytest.mark.asyncio
    async def test_plan_submit(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()

        payload_data = {
            "type": "view_submission",
            "user": {"id": "U03JBULT484"},
            "view": {
                "callback_id": "commitment_submit",
                "state": {
                    "values": {
                        "task_1": {"task": "朝の瞑想", "time": "07:00"},
                        "task_2": {"task": "メールチェック", "time": "09:00"},
                        "task_3": {"task": "振り返り", "time": "22:00"},
                        "next_plan": {"date": "tomorrow", "time": "07:00"}
                    }
                }
            }
        }

        result = await process_plan_submit(payload_data)
        assert result["status"] == "success"
        assert result.get("detail") == "予定を登録しました"

    @pytest.mark.asyncio
    async def test_remind_response_yes(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()

        action_log = ActionLog(
            schedule_id=schedule.id,
            result=ActionResult.YES
        )
        v3_db_session.add(action_log)
        v3_db_session.commit()

        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "remind_yes", "value": f'{{"schedule_id": "{schedule.id}"}}'}]
        }

        result = await process_remind_response(payload_data, "YES")
        assert result["status"] == "success"
        assert result.get("detail") == "やりました！"

    @pytest.mark.asyncio
    async def test_remind_response_no(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()

        action_log = ActionLog(
            schedule_id=schedule.id,
            result=ActionResult.NO
        )
        v3_db_session.add(action_log)
        v3_db_session.commit()

        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "remind_no", "value": f'{{"schedule_id": "{schedule.id}"}}'}]
        }

        result = await process_remind_response(payload_data, "NO")
        assert result["status"] == "success"
        assert result.get("detail") == "できませんでした..."

    @pytest.mark.asyncio
    async def test_ignore_response_yes(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()

        action_log = ActionLog(
            schedule_id=schedule.id,
            result=ActionResult.YES
        )
        v3_db_session.add(action_log)
        v3_db_session.commit()

        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "ignore_yes", "value": f'{{"schedule_id": "{schedule.id}"}}'}]
        }

        result = await process_ignore_response(payload_data)
        assert result["status"] == "success"
        assert result.get("detail") == "今やりました"

    @pytest.mark.asyncio
    async def test_ignore_response_no(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()

        action_log = ActionLog(
            schedule_id=schedule.id,
            result=ActionResult.NO
        )
        v3_db_session.add(action_log)
        v3_db_session.commit()

        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "ignore_no", "value": f'{{"schedule_id": "{schedule.id}"}}'}]
        }

        result = await process_ignore_response(payload_data)
        assert result["status"] == "success"
        assert result.get("detail") == "やっぱり..."
