# v0.3 Interactive API Tests
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.interactive import (
    process_plan_submit,
    process_plan_modal_submit,
    process_remind_response,
    process_ignore_response,
    process_commitment_add_row,
    process_commitment_remove_row,
)
from backend.models import Base, Schedule, Commitment, ActionLog, ActionResult, EventType, ScheduleState
from backend.slack_ui import base_commit_modal


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
        assert result["response_action"] == "clear"

    @pytest.mark.asyncio
    async def test_plan_modal_submit_saves_schedules_and_returns_clear(self, monkeypatch, tmp_path):
        db_path = tmp_path / "plan_submit.sqlite3"
        database_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setattr("backend.api.interactive._SESSION_FACTORY", None)
        monkeypatch.setattr("backend.api.interactive._SESSION_DB_URL", None)

        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)

        session = Session()
        user_id = "U03JBULT484"
        opened_plan = Schedule(
            user_id=user_id,
            event_type=EventType.PLAN,
            run_at=datetime.now() - timedelta(minutes=1),
            state=ScheduleState.PROCESSING,
        )
        session.add(opened_plan)
        session.add_all(
            [
                Commitment(user_id=user_id, task="朝やる", time="06:00:00", active=True),
                Commitment(user_id=user_id, task="昼やる", time="12:00:00", active=True),
            ]
        )
        session.commit()
        opened_plan_id = opened_plan.id
        session.close()

        payload_data = {
            "type": "view_submission",
            "user": {"id": user_id},
            "view": {
                "callback_id": "plan_submit",
                "private_metadata": json.dumps(
                    {
                        "user_id": user_id,
                        "schedule_id": opened_plan_id,
                        "channel_id": "C123456",
                    }
                ),
                "state": {
                    "values": {
                        "task_1_date": {
                            "date": {
                                "selected_option": {
                                    "value": "today",
                                }
                            }
                        },
                        "task_1_time": {
                            "time": {
                                "selected_time": "06:00",
                            }
                        },
                        "task_1_skip": {
                            "skip": {
                                "selected_options": [],
                            }
                        },
                        "task_2_date": {
                            "date": {
                                "selected_option": {
                                    "value": "today",
                                }
                            }
                        },
                        "task_2_time": {
                            "time": {
                                "selected_time": "12:00",
                            }
                        },
                        "task_2_skip": {
                            "skip": {
                                "selected_options": [],
                            }
                        },
                        "next_plan_date": {
                            "date": {
                                "selected_option": {
                                    "value": "tomorrow",
                                }
                            }
                        },
                        "next_plan_time": {
                            "time": {
                                "selected_time": "07:00",
                            }
                        },
                    }
                },
            },
        }

        result = await process_plan_modal_submit(payload_data)
        assert result["response_action"] == "clear"

        session = Session()
        refreshed_opened_plan = session.get(Schedule, opened_plan_id)
        assert refreshed_opened_plan is not None
        assert refreshed_opened_plan.state == ScheduleState.DONE

        remind_schedules = (
            session.query(Schedule)
            .filter(
                Schedule.user_id == user_id,
                Schedule.event_type == EventType.REMIND,
            )
            .all()
        )
        assert len(remind_schedules) == 2
        assert len({r.run_at.date() for r in remind_schedules}) == 1
        assert sorted(r.run_at.strftime("%H:%M:%S") for r in remind_schedules) == [
            "06:00:00",
            "12:00:00",
        ]

        next_plan_schedules = (
            session.query(Schedule)
            .filter(
                Schedule.user_id == user_id,
                Schedule.event_type == EventType.PLAN,
            )
            .all()
        )
        assert len(next_plan_schedules) == 2
        session.close()

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

    @pytest.mark.asyncio
    async def test_commitment_add_row_updates_modal(self):
        modal = base_commit_modal([])
        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "commitment_add_row"}],
            "view": {
                **modal,
                "state": {
                    "values": {
                        "commitment_1": {"task_1": {"type": "plain_text_input", "value": "朝の瞑想"}},
                        "time_1": {"time_1": {"type": "timepicker", "selected_time": "07:00"}},
                        "commitment_2": {"task_2": {"type": "plain_text_input", "value": ""}},
                        "time_2": {"time_2": {"type": "timepicker", "selected_time": None}},
                        "commitment_3": {"task_3": {"type": "plain_text_input", "value": ""}},
                        "time_3": {"time_3": {"type": "timepicker", "selected_time": None}},
                    }
                },
            },
        }

        result = await process_commitment_add_row(payload_data)
        assert result["response_action"] == "update"
        updated_view = result["view"]
        task_blocks = [
            b for b in updated_view["blocks"]
            if b.get("block_id", "").startswith("commitment_")
        ]
        assert len(task_blocks) == 4

    @pytest.mark.asyncio
    async def test_commitment_add_row_stops_at_max(self):
        commitments = [{"task": f"task-{i}", "time": "07:00"} for i in range(1, 11)]
        modal = base_commit_modal(commitments)
        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "commitment_add_row"}],
            "view": {
                **modal,
                "state": {"values": {}},
            },
        }

        result = await process_commitment_add_row(payload_data)
        updated_view = result["view"]
        task_blocks = [
            b for b in updated_view["blocks"]
            if b.get("block_id", "").startswith("commitment_")
        ]
        assert len(task_blocks) == 10

    @pytest.mark.asyncio
    async def test_commitment_remove_row_updates_modal(self):
        commitments = [{"task": f"task-{i}", "time": "07:00"} for i in range(1, 5)]
        modal = base_commit_modal(commitments)
        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "commitment_remove_row"}],
            "view": {
                **modal,
                "state": {"values": {}},
            },
        }

        result = await process_commitment_remove_row(payload_data)
        assert result["response_action"] == "update"
        updated_view = result["view"]
        task_blocks = [
            b for b in updated_view["blocks"]
            if b.get("block_id", "").startswith("commitment_")
        ]
        assert len(task_blocks) == 3

    @pytest.mark.asyncio
    async def test_commitment_remove_row_keeps_min_rows(self):
        modal = base_commit_modal([])
        payload_data = {
            "type": "block_actions",
            "user": {"id": "U03JBULT484"},
            "actions": [{"action_id": "commitment_remove_row"}],
            "view": {
                **modal,
                "state": {"values": {}},
            },
        }

        result = await process_commitment_remove_row(payload_data)
        updated_view = result["view"]
        task_blocks = [
            b for b in updated_view["blocks"]
            if b.get("block_id", "").startswith("commitment_")
        ]
        assert len(task_blocks) == 3
