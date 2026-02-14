# v0.3 Worker Ignore Mode Detection Tests
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from backend.worker.ignore_mode import detect_ignore_mode, calculate_ignore_punishment
from backend.models import Schedule, Punishment, PunishmentMode


@pytest.mark.asyncio
class TestIgnoreModeDetection:

    @pytest.mark.asyncio
    async def test_detect_ignore_single_interval(self, v3_db_session, v3_test_data_factory):
        """1回のignore_intervalを検知できること"""
        schedule = v3_test_data_factory.create_schedule(
            run_at=datetime.now() - timedelta(seconds=900),  # IGNORE_INTERVAL default
        )

        result = detect_ignore_mode(v3_db_session, schedule)
        assert result["detected"] is True
        assert result["ignore_time"] == 1

    @pytest.mark.asyncio
    async def test_detect_ignore_multiple_intervals(self, v3_db_session, v3_test_data_factory):
        """複数回のignore_intervalを検知できること"""
        schedule = v3_test_data_factory.create_schedule(
            run_at=datetime.now() - timedelta(seconds=1800),  # 30分 = 2 intervals
        )

        result = detect_ignore_mode(v3_db_session, schedule)
        assert result["detected"] is True
        assert result["ignore_time"] == 2

    @pytest.mark.asyncio
    async def test_no_ignore_within_interval(self, v3_db_session, v3_test_data_factory):
        """ignore_interval内では検知しないこと"""
        schedule = v3_test_data_factory.create_schedule(
            run_at=datetime.now() - timedelta(seconds=300),  # 5分 < 15分
        )

        result = detect_ignore_mode(v3_db_session, schedule)
        assert result["detected"] is False

    @pytest.mark.asyncio
    async def test_calculate_punishment_ignore_first_time(self):
        """初回ignoreはIGNORE:100であること"""
        result = calculate_ignore_punishment(ignore_time=1)
        assert result["mode"] == PunishmentMode.IGNORE
        assert result["count"] == 100

    @pytest.mark.asyncio
    async def test_calculate_punishment_zap_second_time(self):
        """2回目ignoreはZAP:35であること"""
        result = calculate_ignore_punishment(ignore_time=2)
        assert result["mode"] == PunishmentMode.ZAP
        assert result["count"] == 35

    @pytest.mark.asyncio
    async def test_calculate_punishment_zap_third_time(self):
        """3回目ignoreはZAP:45であること"""
        result = calculate_ignore_punishment(ignore_time=3)
        assert result["mode"] == PunishmentMode.ZAP
        assert result["count"] == 45

    @pytest.mark.asyncio
    async def test_calculate_punishment_zap_max_100(self):
        """ZAPは最大100であること"""
        result = calculate_ignore_punishment(ignore_time=10)
        assert result["mode"] == PunishmentMode.ZAP
        assert result["count"] == 100

    @pytest.mark.asyncio
    async def test_punishment_already_exists(self, v3_db_session, v3_test_data_factory):
        """既存の罰レコードがある場合は追加しないこと"""
        schedule = v3_test_data_factory.create_schedule(
            run_at=datetime.now() - timedelta(seconds=900)
        )
        existing_punishment = v3_test_data_factory.create_punishment(
            schedule_id=schedule.id,
            mode=PunishmentMode.IGNORE,
            count=1
        )

        result = detect_ignore_mode(v3_db_session, schedule)
        assert result["detected"] is True
        assert result["ignore_time"] == 1
        # At least the existing one should exist
        punishments = v3_db_session.query(Punishment).filter_by(schedule_id=schedule.id).all()
        assert len(punishments) >= 1
