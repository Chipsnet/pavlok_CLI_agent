#!/usr/bin/env python3
"""
v0.3 Remind Event Script

remindイベント実行：激励メッセージ + YES/NOボタンを投稿
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.slack_lib.blockkit import BlockKitBuilder
from scripts import slack


def main():
    """remindイベントメイン処理"""
    schedule_id = os.getenv("SCHEDULE_ID")
    if not schedule_id:
        print("Error: SCHEDULE_ID environment variable not set")
        sys.exit(1)

    # Get schedule from database
    from backend.models import Schedule, Commitment
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///oni.db"))
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        schedule = session.query(Schedule).filter_by(id=schedule_id).first()
        if not schedule:
            print(f"Error: Schedule {schedule_id} not found")
            sys.exit(1)

        # Get associated commitment
        commitment = session.query(Commitment).filter_by(
            user_id=schedule.user_id,
            active=True
        ).first()

        if not commitment:
            task_name = "タスク"
            task_time = "--:--"
            description = "予定がありません"
        else:
            task_name = commitment.task
            task_time = commitment.time
            description = schedule.yes_comment or "やってるか？"

        # Get channel
        channel = scripts.require_channel()

        # Post remind notification
        token = scripts.require_bot_token()
        blocks = BlockKitBuilder.remind_notification(
            schedule_id=schedule_id,
            task_name=task_name,
            task_time=task_time,
            description=description
        )

        response = scripts.post_message(blocks, channel, token)

        # Save thread_ts for later updates
        thread_ts = response.json().get("message", {}).get("ts")
        print(f"Remind notification sent. thread_ts: {thread_ts}")

        # Update schedule with thread_ts
        schedule.thread_ts = thread_ts
        session.commit()

    finally:
        session.close()


if __name__ == "__main__":
    main()
