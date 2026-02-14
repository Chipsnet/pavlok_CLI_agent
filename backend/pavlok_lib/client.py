"""
v0.3 Pavlok API Client

Pavlokデバイス刺激APIクライアント
https://pavlok-eu.readme.io/docs/api_reference.html
"""
import os
from typing import Any
import requests


class PavlokClient:
    """Pavlok APIクライアントクラス"""

    PAVLOK_API_BASE = "https://app.pavlok-the-api.com/api/v5"

    VALID_STIMULUS_TYPES = ("zap", "beep", "vibe")

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        http_client: Any = None
    ):
        """
        Args:
            api_key: Pavlok APIキー。省略時は環境変数PAVLOK_API_KEYを使用
            api_base: APIベースURL（テスト用）
            http_client: HTTPクライアント（テスト用モック注入）
        """
        self.api_key = api_key or os.getenv("PAVLOK_API_KEY")
        self.api_base = api_base or self.PAVLOK_API_BASE
        self.http_client = http_client or requests

        if not self.api_key:
            raise ValueError(
                "PAVLOK_API_KEY is not set. "
                "Provide api_key parameter or set environment variable."
            )

    def _get_headers(self) -> dict[str, str]:
        """APIリクエストヘッダーを生成"""
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }

    def _post(self, url: str, payload: dict) -> requests.Response:
        """API POSTリクエストを実行"""
        return self.http_client.post(
            url,
            json=payload,
            headers=self._get_headers(),
            timeout=10
        )

    def _get(self, url: str) -> requests.Response:
        """API GETリクエストを実行"""
        return self.http_client.get(
            url,
            headers=self._get_headers(),
            timeout=10
        )

    def _validate_stimulus_type(self, stimulus_type: str) -> None:
        """刺激タイプのバリデーション"""
        if stimulus_type not in self.VALID_STIMULUS_TYPES:
            raise ValueError(
                f"Invalid stimulus type: {stimulus_type}. "
                f"Valid types are: {', '.join(self.VALID_STIMULUS_TYPES)}"
            )

    def _validate_value(self, value: int) -> None:
        """刺激値のバリデーション (0-100)"""
        if not 0 <= value <= 100:
            raise ValueError(f"Value must be between 0 and 100, got: {value}")

    def stimulate(
        self,
        stimulus_type: str,
        value: int = 50,
        **kwargs
    ) -> dict[str, Any]:
        """
        刺激を送信

        Args:
            stimulus_type: 刺激タイプ ("zap", "beep", "vibe")
            value: 刺激強度 (0-100), デフォルト50
            **kwargs: 追加パラメータ

        Returns:
            dict: APIレスポンス {"success": bool, "type": str, "value": int, ...}
        """
        self._validate_stimulus_type(stimulus_type)
        self._validate_value(value)

        url = f"{self.api_base}/stimulus/send"
        payload = {
            "stimulus": {
                "stimulusType": stimulus_type,
                "stimulusValue": value
            }
        }

        try:
            response = self._post(url, payload)
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "type": stimulus_type,
                "value": value,
                "raw": data
            }
        except Exception as e:
            return {
                "success": False,
                "type": stimulus_type,
                "value": value,
                "error": str(e)
            }

    def zap(self, value: int = 50, **kwargs) -> dict[str, Any]:
        """ZAP刺激を送信（ショートカット）"""
        return self.stimulate(stimulus_type="zap", value=value, **kwargs)

    def vibe(self, value: int = 100, **kwargs) -> dict[str, Any]:
        """VIBE刺激を送信（振動）"""
        return self.stimulate(stimulus_type="vibe", value=value, **kwargs)

    def beep(self, value: int = 100, **kwargs) -> dict[str, Any]:
        """BEEP刺激を送信（音）"""
        return self.stimulate(stimulus_type="beep", value=value, **kwargs)

    def get_status(self, **kwargs) -> dict[str, Any]:
        """
        デバイス状態を取得

        Returns:
            dict: デバイス状態情報 {"success": bool, "battery": int, ...}
        """
        url = f"{self.api_base}/me"
        try:
            response = self._get(url)
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "battery": data.get("battery", 0),
                "is_charging": data.get("isCharging", False),
                "raw": data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
