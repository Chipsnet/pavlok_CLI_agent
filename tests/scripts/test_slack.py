import types

import scripts.slack as slack


def test_unescape_cli_text_newlines():
    assert slack.unescape_cli_text("line1\\nline2") == "line1\nline2"


def test_unescape_cli_text_tabs_and_returns():
    assert slack.unescape_cli_text("a\\tb\\r\\n") == "a\tb\r\n"


def test_unescape_cli_text_passes_through_real_newlines():
    text = "line1\nline2"
    assert slack.unescape_cli_text(text) == text


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self.now += seconds


def setup_wait_for_reply(
    monkeypatch,
    *,
    ignore_span: int,
    ignore_limit: int,
    poll_interval: float,
    reply_on_call: int | None,
):
    clock = FakeClock()
    monkeypatch.setattr(slack.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(slack.time, "sleep", clock.sleep)

    monkeypatch.setenv("IGNORE_SPAN", str(ignore_span))
    monkeypatch.setenv("REPLY_COUNT_LIMIT", str(ignore_limit))

    calls = {"fetch": 0, "add_event": 0, "post_reply": 0}

    def fake_fetch_replies(channel: str, thread_ts: str, token: str) -> list:
        calls["fetch"] += 1
        if reply_on_call is not None and calls["fetch"] == reply_on_call:
            return [{"ts": "123.456", "user": "U1", "text": "reply"}]
        return []

    def fake_post_reply(text: str, thread_ts: str, token: str, channel: str) -> str:
        calls["post_reply"] += 1
        return "post_ts"

    def fake_add_event(thread_ts: str) -> None:
        calls["add_event"] += 1

    fake_module = types.SimpleNamespace(add_event=fake_add_event)
    monkeypatch.setattr(slack, "add_ignore", fake_module, raising=True)
    monkeypatch.setattr(slack, "fetch_replies", fake_fetch_replies)
    monkeypatch.setattr(slack, "post_reply", fake_post_reply)

    return calls, clock


def test_wait_for_reply_stops_after_3_ignores(monkeypatch):
    calls, _ = setup_wait_for_reply(
        monkeypatch,
        ignore_span=1,
        ignore_limit=3,
        poll_interval=0.6,
        reply_on_call=None,
    )

    result = slack.wait_for_reply(
        "C123",
        "1700000000.0001",
        "read-token",
        "post-token",
        0.6,
        "follow-up",
    )

    assert result is None
    assert calls["add_event"] == 3
    assert calls["post_reply"] == 3


def test_wait_for_reply_stops_on_user_reply(monkeypatch):
    calls, _ = setup_wait_for_reply(
        monkeypatch,
        ignore_span=1,
        ignore_limit=5,
        poll_interval=0.6,
        reply_on_call=4,
    )

    result = slack.wait_for_reply(
        "C123",
        "1700000000.0002",
        "read-token",
        "post-token",
        0.6,
        "follow-up",
    )

    assert result == "reply"
    assert calls["add_event"] == 1
    assert calls["post_reply"] == 1


def test_wait_for_reply_stops_after_5_ignores(monkeypatch):
    calls, _ = setup_wait_for_reply(
        monkeypatch,
        ignore_span=1,
        ignore_limit=5,
        poll_interval=1.0,
        reply_on_call=None,
    )

    result = slack.wait_for_reply(
        "C123",
        "1700000000.0003",
        "read-token",
        "post-token",
        1.0,
        "follow-up",
    )

    assert result is None
    assert calls["add_event"] == 5
    assert calls["post_reply"] == 5
