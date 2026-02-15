"""Punishment Worker Package"""
from .config_cache import get_config, invalidate_config_cache
from .ignore_mode import detect_ignore_mode, calculate_ignore_punishment
from .no_mode import detect_no_mode, calculate_no_punishment

__all__ = [
    "get_config",
    "invalidate_config_cache",
    "detect_ignore_mode",
    "calculate_ignore_punishment",
    "detect_no_mode",
    "calculate_no_punishment",
    "PunishmentWorker",
    "main",
]


def __getattr__(name: str):
    if name in {"PunishmentWorker", "main"}:
        from .worker import PunishmentWorker, main
        return {"PunishmentWorker": PunishmentWorker, "main": main}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
