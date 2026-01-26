---
name: repentance
description: Execute pending daily punishments by sending Pavlok stimuli via scripts/repentance.py. Use when you need to run the punishment cycle.
---

# Repentance

Use `scripts/repentance.py` to execute pending punishments and update `daily_punishments`.

## Run

```bash
uv run scripts/repentance.py
```

## Inputs

This script takes no CLI arguments.

## Environment

- `PAVLOK_TYPE_PUNISH` is required (e.g., `zap`, `vibe`, `beep`).
- `PAVLOK_VALUE_PUNISH` is required (integer).
- `PUNISH_INTERVAL_SEC` is optional (integer, default `1`).
- `PAVLOK_API_KEY` is required by `scripts/pavlok.py`.
- If using `zap`, `LIMIT_DAY_PAVLOK_COUNTS` and `LIMIT_PAVLOK_ZAP_VALUE` are required.

## Outputs

Prints a single line of JSON:

```
{"executed": 2}
```

## Notes

- Processes `daily_punishments` rows in `pending` or `failed` state.
- Marks rows `running` while executing, updates `executed_count`, and sets `failed` on errors or rate limits.
- Always creates a new pending `daily_punishments` row after processing.
- Database URL comes from `DATABASE_URL` (default: `sqlite:///./app.db`).
