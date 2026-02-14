"""Config Cache Module"""
import os
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta


# Cache storage: {key: (value, expire_time)}
_config_cache: Dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(seconds=60)  # 60秒キャッシュ


def _parse_value(value: str, value_type: str) -> Any:
    """
    設定値を型に応じてパースする

    Args:
        value: 設定値（文字列）
        value_type: 型（str, int, float, bool, json）

    Returns:
        パースされた値
    """
    if value_type == "int":
        return int(value)
    elif value_type == "float":
        return float(value)
    elif value_type == "bool":
        return value.lower() in ("true", "1", "yes")
    elif value_type == "json":
        return json.loads(value)
    else:
        return value


def get_config(key: str, default: Any = None, session=None) -> Any:
    """
    設定値を取得する（キャッシュ考慮）

    優先順位: DB > 環境変数 > デフォルト値

    Args:
        key: 設定キー
        default: デフォルト値
        session: DBセッション（オプション）

    Returns:
        設定値
    """
    now = datetime.now()

    # Check cache
    if key in _config_cache:
        value, expire_time = _config_cache[key]
        if now < expire_time:
            return value
        # Cache expired, remove
        del _config_cache[key]

    # Try to get from DB if session provided
    if session is not None:
        try:
            from backend.models import Configuration

            config = session.query(Configuration).filter_by(key=key).first()
            if config:
                value = _parse_value(config.value, config.value_type)
                # Cache with TTL
                _config_cache[key] = (value, now + CACHE_TTL)
                return value
        except Exception:
            # DB access failed, continue to env var
            pass

    # Try environment variable
    env_value = os.getenv(key)
    if env_value is not None:
        value = _parse_value(env_value, "str")
        # Cache with TTL
        _config_cache[key] = (value, now + CACHE_TTL)
        return value

    # Return default
    return default


def invalidate_config_cache(key: str = None) -> None:
    """
    設定キャッシュを無効化する

    Args:
        key: 無効化するキー（省略時は全て）
    """
    if key is None:
        _config_cache.clear()
    elif key in _config_cache:
        del _config_cache[key]
