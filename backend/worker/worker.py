"""Punishment Worker Main Module"""
import asyncio
import os
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)


class PunishmentWorker:
    """鬼コーチPunishment Worker"""

    def __init__(self, session: Session):
        """
        初期化

        Args:
            session: DBセッション
        """
        self.session = session

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
        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        script_path = os.path.join(scripts_dir, script_name)

        env = os.environ.copy()
        env["SCHEDULE_ID"] = str(schedule.id)

        result = subprocess.run(
            ["python", script_path],
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

            # Mark as done
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
