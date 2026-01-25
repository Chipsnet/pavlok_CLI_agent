import json

from db import models
import scripts.repentance as repentance


def test_repentance_executes_and_updates(db_session, monkeypatch, capsys):
    punishment = models.DailyPunishment(
        ignore_count=2,
        punishment_count=2,
        executed_count=0,
        state="pending",
    )
    db_session.add(punishment)
    db_session.commit()

    calls = []

    def fake_call(stimulus_type, stimulus_value, reason):
        calls.append((stimulus_type, stimulus_value, reason))
        return {"ok": True}

    monkeypatch.setattr(repentance.pavlok, "call", fake_call)
    monkeypatch.setenv("PAVLOK_TYPE_PUNISH", "zap")
    monkeypatch.setenv("PAVLOK_VALUE_PUNISH", "50")
    monkeypatch.setenv("PUNISH_INTERVAL_SEC", "0")

    repentance.main(argv=[])

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["executed"] == 2
    assert len(calls) == 2

    db_session.expire_all()
    refreshed = db_session.get(models.DailyPunishment, punishment.id)
    assert refreshed.state == "done"
    assert refreshed.executed_count == 2


def test_repentance_limit_failure(db_session, monkeypatch, capsys):
    punishment = models.DailyPunishment(
        ignore_count=1,
        punishment_count=1,
        executed_count=0,
        state="pending",
    )
    db_session.add(punishment)
    db_session.commit()

    def fake_call(stimulus_type, stimulus_value, reason):
        return {"skipped": True, "reason": "limit_reached"}

    monkeypatch.setattr(repentance.pavlok, "call", fake_call)
    monkeypatch.setenv("PAVLOK_TYPE_PUNISH", "zap")
    monkeypatch.setenv("PAVLOK_VALUE_PUNISH", "50")
    monkeypatch.setenv("PUNISH_INTERVAL_SEC", "0")

    repentance.main(argv=[])

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["executed"] == 0

    db_session.expire_all()
    refreshed = db_session.get(models.DailyPunishment, punishment.id)
    assert refreshed.state == "failed"
    assert refreshed.executed_count == 0


def test_repentance_creates_next_cycle_record(db_session, monkeypatch, capsys):
    # Case: Existing pending task gets done, and a new empty pending task is created
    punishment = models.DailyPunishment(
        ignore_count=1,
        punishment_count=1,
        executed_count=0,
        state="pending",
    )
    db_session.add(punishment)
    db_session.commit()

    def fake_call(stimulus_type, stimulus_value, reason):
        return {"ok": True}

    monkeypatch.setattr(repentance.pavlok, "call", fake_call)
    monkeypatch.setenv("PAVLOK_TYPE_PUNISH", "zap")
    monkeypatch.setenv("PAVLOK_VALUE_PUNISH", "50")
    monkeypatch.setenv("PUNISH_INTERVAL_SEC", "0")

    repentance.main(argv=[])

    db_session.expire_all()
    
    # Verify old record is done
    refreshed = db_session.get(models.DailyPunishment, punishment.id)
    assert refreshed.state == "done"

    # Verify new record created
    all_records = db_session.query(models.DailyPunishment).order_by(models.DailyPunishment.id).all()
    assert len(all_records) == 2
    new_record = all_records[1]
    assert new_record.state == "pending"
    assert new_record.punishment_count == 0
    assert new_record.ignore_count == 0


def test_repentance_creates_next_cycle_record_even_if_no_pending(db_session, monkeypatch, capsys):
    # Case: No pending tasks initially. Should still ensure a pending record exists?
    # Actually per requirement: "repentance is ... execute all pending/failed -> at the end generate new record"
    # If there are no pending tasks, it runs 0 punishments, then should create a new record if strictly following "always create".
    # However, if there is ALREADY a clean pending record (count=0), creating another might be redundant but the requirement says "always create at the end".
    # Let's interpret "run repentance" as "closing the current cycle and starting a new one".
    # But usually repentance is run by scheduler. 
    # If we always create a new one, and repentance runs every 10 mins, we will spam records.
    # The requirement says: "repentance から repentance までの区間が1レコード"
    # So yes, every execution of repentance defines a cycle.
    
    monkeypatch.setenv("PAVLOK_TYPE_PUNISH", "zap")
    monkeypatch.setenv("PAVLOK_VALUE_PUNISH", "50")
    monkeypatch.setenv("PUNISH_INTERVAL_SEC", "0")

    repentance.main(argv=[])
    
    db_session.expire_all()
    all_records = db_session.query(models.DailyPunishment).all()
    assert len(all_records) == 1
    assert all_records[0].state == "pending"
    assert all_records[0].punishment_count == 0
