#!/usr/bin/env python3
"""
v0.3 Agent Call Script

Use prompts/add_comment.md + `codex exec` to populate remind comments.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Configuration, EventType, Schedule

DEFAULT_COACH_CHARACTOR = "うる星やつらのラムちゃん"
COACH_CHARACTOR_KEY = "COACH_CHARACTOR"
PROMPT_PATH = ROOT / "prompts" / "add_comment.md"
CODEX_TIMEOUT_SEC = int(os.getenv("CODEX_EXEC_TIMEOUT_SEC", "180"))


def parse_schedule_ids(raw: str) -> list[str]:
    """Parse target schedule ids from JSON array text."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Invalid SCHEDULE_IDS_JSON")

    if not isinstance(parsed, list):
        raise ValueError("SCHEDULE_IDS_JSON must be a JSON array")

    return [str(v) for v in parsed if str(v)]


def build_fallback_comments(task_name: str, charactor: str) -> tuple[str, str, str]:
    """Create deterministic fallback comments when codex execution fails."""
    task = task_name or "タスク"
    style_suffix = "っちゃ" if "ラム" in charactor else ""
    comment = f"{task} を予定どおり実行する{style_suffix}。"
    yes_comment = f"{task} 完了、良い流れだ{style_suffix}。"
    no_comment = f"{task} 未達。次の行動を今すぐ決める{style_suffix}。"
    return comment, yes_comment, no_comment


def load_target_rows(session, schedule_ids: list[str]) -> list[Schedule]:
    """Load remind schedules for target ids."""
    return (
        session.query(Schedule)
        .filter(
            Schedule.id.in_(schedule_ids),
            Schedule.event_type == EventType.REMIND,
        )
        .all()
    )


def load_coach_charactor(session, user_id: str) -> str:
    """Load coach character from configurations table."""
    if not user_id:
        return DEFAULT_COACH_CHARACTOR

    row = (
        session.query(Configuration)
        .filter(
            Configuration.user_id == user_id,
            Configuration.key == COACH_CHARACTOR_KEY,
        )
        .first()
    )
    if not row or not row.value:
        return DEFAULT_COACH_CHARACTOR
    return str(row.value)


def render_prompt(schedule_ids: list[str], charactor: str) -> str:
    """Render prompt template for codex exec."""
    if not PROMPT_PATH.is_file():
        raise FileNotFoundError(f"Prompt template not found: {PROMPT_PATH}")

    template = PROMPT_PATH.read_text(encoding="utf-8")
    schedule_ids_text = json.dumps(schedule_ids, ensure_ascii=False)
    prompt = template.replace("{{charactor}}", charactor)
    prompt = prompt.replace("{{schedule_ids}}", schedule_ids_text)
    # Keep compatibility with typo-ed placeholder in current template.
    prompt = prompt.replace("{schedule_ids}", schedule_ids_text)
    return prompt


def run_codex_exec(prompt: str) -> tuple[bool, str]:
    """Execute codex CLI with prompt via stdin."""
    codex_bin = os.getenv("CODEX_BIN", "codex")
    if shutil.which(codex_bin) is None:
        return False, f"{codex_bin} command not found"

    try:
        result = subprocess.run(
            [codex_bin, "exec"],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=CODEX_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return False, f"codex exec timeout({CODEX_TIMEOUT_SEC}s)"
    except OSError as exc:
        return False, f"codex exec failed: {exc}"

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    detail = stderr or stdout or f"exit={result.returncode}"
    return result.returncode == 0, detail


def ensure_comments_with_fallback(session, rows: list[Schedule], charactor: str) -> int:
    """
    Fill missing comments when codex path fails or returns incomplete updates.
    Returns number of schedules modified by fallback.
    """
    updated = 0
    for row in rows:
        if row.comment and row.yes_comment and row.no_comment:
            continue

        task_name = row.comment or "タスク"
        fallback_comment, fallback_yes, fallback_no = build_fallback_comments(
            task_name,
            charactor,
        )
        row.comment = fallback_comment
        row.yes_comment = fallback_yes
        row.no_comment = fallback_no
        updated += 1
    return updated


def main() -> None:
    raw = os.getenv("SCHEDULE_IDS_JSON", "[]")
    try:
        schedule_ids = parse_schedule_ids(raw)
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)

    if not schedule_ids:
        print("No target schedules")
        return

    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///oni.db"))
    Session = sessionmaker(bind=engine)

    session = Session()
    try:
        rows = load_target_rows(session, schedule_ids)
        if not rows:
            print("No matching REMIND schedules")
            return

        user_id = rows[0].user_id
        charactor = load_coach_charactor(session, user_id)
    finally:
        session.close()

    prompt = render_prompt(schedule_ids, charactor)
    codex_ok, codex_detail = run_codex_exec(prompt)

    session = Session()
    try:
        rows = load_target_rows(session, schedule_ids)
        filled_count = sum(
            1
            for row in rows
            if row.comment and row.yes_comment and row.no_comment
        )

        fallback_updated = 0
        if filled_count < len(rows):
            fallback_updated = ensure_comments_with_fallback(session, rows, charactor)
            if fallback_updated > 0:
                session.commit()

        print(
            "agent_call completed: "
            f"targets={len(rows)} filled={filled_count} "
            f"fallback_updated={fallback_updated} codex_ok={codex_ok}"
        )
        if not codex_ok:
            print(f"agent_call codex detail: {codex_detail}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
