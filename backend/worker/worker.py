"""Punishment Worker Main Module"""
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


logger = logging.getLogger(__name__)

# Load local .env if present (without overriding real environment variables).
load_dotenv()


class PunishmentWorker:
    """鬼コーチPunishment Worker"""

    def __init__(self, session: Session):
        """
        初期化

        Args:
            session: DBセッション
        """
        self.session = session

    def _resolve_bootstrap_user_id(self) -> Optional[str]:
        """
        Resolve user_id for initial plan bootstrap.
        Rule:
        - Only users who have active commitments are eligible.
        """
        from backend.models import Commitment

        commitment_row = (
            self.session.query(Commitment.user_id)
            .filter(Commitment.active.is_(True))
            .order_by(Commitment.updated_at.desc())
            .first()
        )
        if commitment_row and commitment_row[0]:
            return str(commitment_row[0])

        return None

    async def ensure_initial_plan_schedule(self) -> Optional[str]:
        """
        Bootstrap first plan schedule if no pending/processing records exist.

        Returns:
            Created schedule id if inserted, otherwise None.
        """
        from backend.models import Schedule, ScheduleState, EventType

        in_flight_count = (
            self.session.query(Schedule)
            .filter(Schedule.state.in_([ScheduleState.PENDING, ScheduleState.PROCESSING]))
            .count()
        )
        if in_flight_count > 0:
            logger.info(
                "Bootstrap skipped: pending+processing schedules exist (%s)",
                in_flight_count,
            )
            return None

        user_id = self._resolve_bootstrap_user_id()
        if not user_id:
            logger.warning(
                "Bootstrap skipped: no active commitments found. "
                "Run /base_commit to create active commitments first."
            )
            return None

        now = datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        existing_today = (
            self.session.query(Schedule.id)
            .filter(
                Schedule.user_id == user_id,
                Schedule.event_type == EventType.PLAN,
                Schedule.run_at >= day_start,
                Schedule.run_at < day_end,
            )
            .first()
        )
        if existing_today:
            logger.info(
                "Bootstrap skipped: today's plan already exists for user_id=%s schedule_id=%s",
                user_id,
                existing_today[0],
            )
            return None

        schedule = Schedule(
            user_id=user_id,
            event_type=EventType.PLAN,
            run_at=now,
            state=ScheduleState.PENDING,
            retry_count=0,
        )
        self.session.add(schedule)
        self.session.commit()
        logger.info(
            "Bootstrap inserted initial plan schedule: schedule_id=%s user_id=%s",
            schedule.id,
            user_id,
        )
        return str(schedule.id)

    async def fetch_pending_schedules(self) -> List:
        """
        処理待ちスケジュールを取得する

        Returns:
            pendingかつrun_at <= nowのスケジュールリスト
        """
        from backend.models import Schedule, ScheduleState

        now = datetime.now()
        schedules = self.session.query(Schedule).filter(
            Schedule.state == ScheduleState.PENDING,
            Schedule.run_at <= now
        ).all()

        return schedules

    async def execute_script(self, script_name: str, schedule) -> None:
        """
        スクリプトを実行する

        Args:
            script_name: スクリプト名（plan.py, remind.py）
            schedule: 対象スケジュール
        """
        import subprocess

        repo_root = Path(__file__).resolve().parents[2]
        script_path = repo_root / "scripts" / script_name

        env = os.environ.copy()
        env["SCHEDULE_ID"] = str(schedule.id)

        if not script_path.is_file():
            raise Exception(f"Script file not found: {script_path}")

        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"Script execution failed: {result.stderr}")

    async def process_schedule(self, schedule) -> None:
        """
        スケジュールを処理する

        Args:
            schedule: 対象スケジュール
        """
        from backend.models import ScheduleState, EventType
        from backend.worker.ignore_mode import detect_ignore_mode
        from backend.worker.no_mode import detect_no_mode

        try:
            # Mark as processing while script is running / waiting for user response.
            schedule.state = ScheduleState.PROCESSING
            self.session.commit()

            # Execute script based on event_type
            if schedule.event_type == EventType.PLAN:
                await self.execute_script("plan.py", schedule)
            elif schedule.event_type == EventType.REMIND:
                await self.execute_script("remind.py", schedule)

            # Check for ignore_mode
            ignore_result = detect_ignore_mode(self.session, schedule)
            if ignore_result["detected"]:
                logger.info(f"ignore_mode detected: {ignore_result['ignore_time']}")

            # Check for no_mode
            no_result = detect_no_mode(self.session, schedule)
            if no_result["detected"]:
                logger.info(f"no_mode detected: {no_result['no_time']}")

            # For plan, keep processing until user submits response.
            # For remind, keep current behavior and mark done after notification.
            if schedule.event_type == EventType.REMIND:
                schedule.state = ScheduleState.DONE
            self.session.commit()

        except Exception as e:
            logger.error(f"Error processing schedule {schedule.id}: {e}")
            schedule.state = ScheduleState.FAILED
            schedule.retry_count += 1

            # Retry if under limit
            max_retry = 3
            if schedule.retry_count < max_retry:
                from datetime import timedelta
                from backend.worker.config_cache import get_config
                retry_delay = get_config("RETRY_DELAY", 5, session=self.session)
                schedule.run_at = datetime.now() + timedelta(minutes=retry_delay)
                schedule.state = ScheduleState.PENDING
            self.session.commit()

    async def run_once(self) -> None:
        """
        1回分の処理を実行する
        """
        try:
            await self.ensure_initial_plan_schedule()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Bootstrap error: {e}")

        schedules = await self.fetch_pending_schedules()
        logger.info(f"Processing {len(schedules)} schedules")

        for schedule in schedules:
            await self.process_schedule(schedule)

    async def run(self) -> None:
        """
        無限ループで処理を実行する
        """
        while True:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"Worker error: {e}")
            # Wait 1 minute
            await asyncio.sleep(60)


async def main() -> None:
    """
        メインエントリーポイント
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create database session
    database_url = os.getenv("DATABASE_URL", "sqlite:///oni.db")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        worker = PunishmentWorker(session)
        await worker.run()
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
