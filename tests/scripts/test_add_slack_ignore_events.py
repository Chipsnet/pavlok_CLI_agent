import json
from datetime import datetime, timedelta

from db import models
import scripts.add_slack_ignore_events as add_ignore


def test_add_event_creates_new_record_if_none_exists(db_session, monkeypatch):
    monkeypatch.setenv("TIMEZONE", "JST")
    
    total = add_ignore.add_event("1700000000.0001")
    assert total == 1
    
    punishments = db_session.query(models.DailyPunishment).all()
    assert len(punishments) == 1
    assert punishments[0].ignore_count == 1
    assert punishments[0].state == "pending"


def test_add_event_increments_latest_pending(db_session, monkeypatch):
    monkeypatch.setenv("TIMEZONE", "JST")
    
    # First event
    add_ignore.add_event("1700000000.0001")
    
    # Second event
    total = add_ignore.add_event("1700000000.0002")
    assert total == 2
    
    punishments = db_session.query(models.DailyPunishment).all()
    assert len(punishments) == 1
    assert punishments[0].ignore_count == 2


def test_add_event_increments_latest_pending_across_dates(db_session, monkeypatch):
    monkeypatch.setenv("TIMEZONE", "JST")
    
    # Create a record "yesterday" (conceptually, though date column is gone)
    p = models.DailyPunishment(
        ignore_count=1,
        punishment_count=1,
        state="pending"
    )
    db_session.add(p)
    db_session.commit()
    
    # Add event "today"
    # We pass a specific detected_at to simulate different event time, though logic shouldn't care
    future_date = models.now_jst() + timedelta(days=1)
    add_ignore.add_event("1700000000.0001", detected_at=future_date)
    
    db_session.expire_all()
    punishments = db_session.query(models.DailyPunishment).all()
    assert len(punishments) == 1
    assert punishments[0].ignore_count == 2


def test_add_event_creates_new_if_latest_is_done(db_session, monkeypatch):
    monkeypatch.setenv("TIMEZONE", "JST")
    
    # Old done record
    p = models.DailyPunishment(
        ignore_count=5,
        punishment_count=5,
        executed_count=5,
        state="done"
    )
    db_session.add(p)
    db_session.commit()
    
    # New event
    total = add_ignore.add_event("1700000000.0001")
    assert total == 1
    
    punishments = db_session.query(models.DailyPunishment).order_by(models.DailyPunishment.id).all()
    assert len(punishments) == 2
    assert punishments[0].state == "done"
    assert punishments[1].state == "pending"
    assert punishments[1].ignore_count == 1


def test_main_increments(db_session, capsys, monkeypatch):
    monkeypatch.setenv("TIMEZONE", "JST")

    add_ignore.add_event("1700000000.0001")
    add_ignore.add_event("1700000000.0002")

    add_ignore.main(argv=["1700000000.0003"])

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["remaining_total"] == 3
