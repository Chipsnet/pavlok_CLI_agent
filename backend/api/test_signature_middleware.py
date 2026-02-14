# v0.3 Slack Signature Verification Middleware Tests
import pytest
import hmac
from unittest.mock import MagicMock
from fastapi import Request, HTTPException, status
from backend.api.signature import verify_slack_signature, SignatureVerificationError, verify_signature_middleware


@pytest.mark.asyncio
class TestSignatureMiddleware:

    async def test_valid_signature_verification(self):
        timestamp = "1531420620005"
        signing_secret = "test-secret"
        signature = "v0:" + hashlib.sha256((timestamp + "v0:" + signing_secret).encode()).hexdigest()

        request = MagicMock(spec=Request)
        request.headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature
        }
        request.body = None

        assert await verify_signature_middleware(request, MagicMock()) is None
        assert verify_slack_signature(timestamp, signature, None) is True

    @pytest.mark.asyncio
    async def test_invalid_signature_rejection(self):
        timestamp = "1531420620005"
        signing_secret = "test-secret"
        signature = "v0:invalid"

        request = MagicMock(spec=Request)
        request.headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature
        }
        request.body = None

        with pytest.raises(HTTPException) as exc_info:
            response = await verify_signature_middleware(request, MagicMock())
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_signature_rejection(self):
        signing_secret = "test-secret"
        timestamp = "1531420620005"

        request = MagicMock(spec=Request)
        request.headers = {
            "X-Slack-Request-Timestamp": timestamp,
            # No signature header
        }
        request.body = None

        with pytest.raises(HTTPException) as exc_info:
            response = await verify_signature_middleware(request, MagicMock())
            assert exc_info.value.status_code == 401
