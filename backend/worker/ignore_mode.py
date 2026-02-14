"""Ignore Mode Detection Module"""
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session


def calculate_ignore_punishment(ignore_time: int) -> Dict[str, Any]:
    """
    ignore回数から罰を計算する

    Args:
        ignore_time: ignore回数（IGNORE_INTERVAL単位）

    Returns:
        {"mode": PunishmentMode, "count": int}
    """
    from backend.models import PunishmentMode

    if ignore_time == 1:
        # 初回はIGNORE:100
        return {"mode": PunishmentMode.IGNORE, "count": 100}
    else:
        # 2回目以降はzap: min(35 + 10 * (ignore_time - 2), 100)
        zap_value = min(35 + 10 * (ignore_time - 2), 100)
        return {"mode": PunishmentMode.ZAP, "count": zap_value}


def detect_ignore_mode(session: Session, schedule) -> Dict[str, Any]:
    """
    ignore_modeを検知する

    Args:
        session: DBセッション
        schedule: 対象スケジュール

    Returns:
        {"detected": bool, "ignore_time": int}
    """
    from backend.models import Punishment, PunishmentMode

    # Get IGNORE_INTERVAL (default 900 seconds = 15 minutes)
    now = datetime.now()
    if isinstance(schedule.run_at, datetime):
        ignore_interval = int((now - schedule.run_at).total_seconds())
    else:
        ignore_interval = int(now.timestamp() - schedule.run_at)

    from backend.worker.config_cache import get_config
    config_interval = get_config("IGNORE_INTERVAL", 900)

    # Check if IGNORE_INTERVAL has passed
    if ignore_interval < config_interval:
        return {"detected": False, "ignore_time": 0}

    # Calculate ignore_time
    ignore_time = ignore_interval // config_interval

    # Check if punishment already exists (check all, not just exact match)
    existing = session.query(Punishment).filter_by(schedule_id=schedule.id).all()

    # Determine if we need to create a new punishment
    needs_new_punishment = True
    for existing_pun in existing:
        if existing_pun.mode == PunishmentMode.IGNORE and existing_pun.count == ignore_time:
            # Exact match exists, don't create new one
            needs_new_punishment = False
            break

    if not needs_new_punishment:
        return {"detected": True, "ignore_time": ignore_time}

    # Create new punishment
    punishment_data = calculate_ignore_punishment(ignore_time)

    punishment = Punishment(
        schedule_id=schedule.id,
        mode=punishment_data["mode"],
        count=punishment_data["count"]
    )
    session.add(punishment)
    session.commit()

    return {"detected": True, "ignore_time": ignore_time}
