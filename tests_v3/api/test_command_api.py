# v0.3 Slack Command API Tests
import pytest
from unittest.mock import MagicMock
from fastapi import Request, HTTPException, status
from backend.api.command import (
    process_base_commit,
    process_stop,
    process_restart,
    process_config
)
from backend.models import Schedule


@pytest.mark.asyncio
class TestCommandApi:

    async def test_base_commit_command(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()
        request = MagicMock(spec=Request)
        request.state = "base_commit"

        result = await process_base_commit(request)
        assert result["status"] == "success"
        assert "blocks" in result

    @pytest.mark.asyncio
    async def test_stop_command(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()

        request = MagicMock(spec=Request)
        request.state = "stop"
        result = await process_stop(request)
        assert result["status"] == "success"
        assert "blocks" in result

    @pytest.mark.asyncio
    async def test_restart_command(self, v3_db_session, v3_test_data_factory):
        schedule = v3_test_data_factory.create_schedule()

        request = MagicMock(spec=Request)
        request.state = "restart"
        result = await process_restart(request)
        assert result["status"] == "success"
        assert "blocks" in result

    @pytest.mark.asyncio
    async def test_config_get_command(self, v3_db_session):
        request = MagicMock(spec=Request)
        request.method = "GET"

        result = await process_config(request)
        assert result["status"] == "success"
        assert "configurations" in result["data"]

    @pytest.mark.asyncio
    async def test_config_post_command(self, v3_db_session):
        config_data = {
            "PAVLOK_TYPE_PUNISH": "vibe",
            "PAVLOK_VALUE_PUNISH": "100"
        }

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.state = "config"
        result = await process_config(request, config_data)

        assert result["status"] == "success"
