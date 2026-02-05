import argparse
import json
import os
import time

import requests
from dotenv import load_dotenv

from scripts import add_slack_ignore_events as add_ignore

load_dotenv()

SLACK_API_BASE = "https://slack.com/api"


def require_bot_token() -> str:
    token = os.getenv("SLACK_BOT_USER_OAUTH_TOKEN")
    if not token:
        raise SystemExit(
            "SLACK_BOT_USER_OAUTH_TOKEN is not set. Add it to .env or the environment."
        )
    return token


def get_reply_token(bot_token: str) -> str:
    return os.getenv("SLACK_USER_OAUTH_TOKEN") or bot_token


def normalize_channel(channel: str) -> str:
    channel = channel.strip()
    if channel.startswith("#"):
        return channel
    if channel and channel[0] in {"C", "G", "D", "W"} and channel.isalnum():
        return channel
    return f"#{channel}"


def require_channel(override: str | None = None) -> str:
    channel = override or os.getenv("SLACK_CHANNEL")
    if not channel:
        raise SystemExit(
            "SLACK_CHANNEL is not set. Add it to .env or the environment."
        )
    return channel


def build_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_int_env(name: str, default: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        if default is None:
            raise SystemExit(f"{name} is not set. Add it to .env or the environment.")
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer.") from exc


def parse_response(response: requests.Response) -> dict:
    try:
        return response.json()
    except ValueError as exc:
        raise SystemExit(f"Slack API error: {response.text}") from exc


def unescape_cli_text(text: str) -> str:
    return text.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t")


def post_question(
    question: str, token: str, add_reply_hint: bool, channel: str
) -> tuple:
    url = f"{SLACK_API_BASE}/chat.postMessage"
    text = question
    if add_reply_hint:
        text = f"{question}\n\nReply in thread."
    payload = {"channel": normalize_channel(channel), "text": text}

    response = requests.post(
        url, data=payload, headers=build_headers(token), timeout=10
    )
    data = parse_response(response)
    if not data.get("ok"):
        raise SystemExit(f"Slack API error: {data.get('error', 'unknown_error')}")
    return data["channel"], data["ts"]


def post_reply(text: str, thread_ts: str, token: str, channel: str) -> str:
    url = f"{SLACK_API_BASE}/chat.postMessage"
    payload = {
        "channel": normalize_channel(channel),
        "text": text,
        "thread_ts": thread_ts,
    }

    response = requests.post(
        url, data=payload, headers=build_headers(token), timeout=10
    )
    data = parse_response(response)
    if not data.get("ok"):
        raise SystemExit(f"Slack API error: {data.get('error', 'unknown_error')}")
    return data["ts"]


def fetch_replies(channel: str, thread_ts: str, token: str) -> list:
    url = f"{SLACK_API_BASE}/conversations.replies"
    params = {
        "channel": channel,
        "ts": thread_ts,
        "inclusive": True,
        "limit": 100,
    }

    response = requests.get(url, params=params, headers=build_headers(token), timeout=10)
    data = parse_response(response)
    if not data.get("ok"):
        if data.get("error") == "missing_scope":
            raise SystemExit(
                "Slack API error: missing_scope. Add history scopes to the bot token "
                "(channels:history, groups:history, im:history, mpim:history) and "
                "reinstall the app."
            )
        raise SystemExit(f"Slack API error: {data.get('error', 'unknown_error')}")
    return data.get("messages", [])


def is_bot_message(message: dict) -> bool:
    if message.get("subtype") == "bot_message":
        return True
    if message.get("bot_id"):
        return True
    if message.get("bot_profile"):
        return True
    return False


def find_user_reply(messages: list, thread_ts: str) -> str | None:
    for message in messages:
        if message.get("ts") == thread_ts:
            continue
        if is_bot_message(message):
            continue
        if message.get("subtype"):
            continue
        if "user" not in message:
            continue
        return message.get("text", "")
    return None


def wait_for_reply(
    channel: str,
    thread_ts: str,
    read_token: str,
    post_token: str,
    poll_interval_sec: float,
    follow_up_message: str | None = None,
) -> str | None:
    ignore_span = get_int_env("IGNORE_SPAN", default=0)
    ignore_limit = get_int_env("REPLY_COUNT_LIMIT", default=0)
    if ignore_span <= 0 or ignore_limit <= 0:
        ignore_span = 0
        ignore_limit = 0

    start_time = time.monotonic()
    timeout_deadline = start_time + (ignore_span * ignore_limit)
    next_ignore_at = start_time + ignore_span if ignore_span else None
    ignore_ct = 0

    while time.monotonic() <= timeout_deadline:
        reply = find_user_reply(fetch_replies(channel, thread_ts, read_token), thread_ts)
        if reply is not None:
            return reply

        now = time.monotonic()
        if next_ignore_at is not None and now >= next_ignore_at:
            ignore_ct += 1

            try:
                add_ignore.add_event(f"{thread_ts}_{ignore_ct}")
            except Exception as exc:
                raise SystemExit(
                    f"Failed to record slack ignore event: {exc}"
                ) from exc

            post_reply(f"==無視{ignore_ct}回目==\n{follow_up_message}", thread_ts, post_token, channel)

            if ignore_limit and ignore_ct >= ignore_limit:
                break
            if ignore_span:
                next_ignore_at += ignore_span

        if poll_interval_sec > 0:
            time.sleep(poll_interval_sec)
    return None


def build_result(
    question: str,
    answer: str | None,
    is_answer: bool,
    thread_ts: str,
    message_ts: str,
) -> dict:
    return {
        "assistant_question": question,
        "user_answer": answer,
        "is_answer": is_answer,
        "thread_ts": thread_ts,
        "message_ts": message_ts,
    }


def print_result(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def run_ask(
    question: str,
    follow_up_message: str | None,
    interval: float,
    no_reply_hint: bool,
    channel_override: str | None,
) -> None:
    bot_token = require_bot_token()
    channel = require_channel(channel_override)
    reply_token = get_reply_token(bot_token)
    channel_id, thread_ts = post_question(
        question, bot_token, not no_reply_hint, channel
    )
    reply = wait_for_reply(
        channel_id,
        thread_ts,
        reply_token,
        bot_token,
        interval,
        follow_up_message,
    )
    if reply is None:
        payload = build_result(question, None, False, thread_ts, thread_ts)
    else:
        payload = build_result(question, reply, True, thread_ts, thread_ts)
    print_result(payload)


def run_reply(question: str, thread_ts: str, channel_override: str | None) -> None:
    bot_token = require_bot_token()
    channel = require_channel(channel_override)
    message_ts = post_reply(question, thread_ts, bot_token, channel)
    payload = build_result(question, None, False, thread_ts, message_ts)
    print_result(payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post a question to Slack and wait for a reply.",
    )
    parser.add_argument(
        "question", help="Message text (question in ask mode, reply in reply mode)."
    )
    parser.add_argument(
        "--mode",
        choices=("ask", "reply"),
        default="ask",
        help="ask: post a question and wait; reply: post to a thread.",
    )
    parser.add_argument(
        "--thread-ts",
        help="Thread timestamp to reply to (required in reply mode).",
    )
    parser.add_argument(
        "--channel",
        help="Slack channel name or ID (defaults to SLACK_CHANNEL).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2,
        help="Polling interval in seconds.",
    )
    parser.add_argument(
        "--no-reply-hint",
        action="store_true",
        help="Do not append a reply hint line.",
    )
    parser.add_argument(
        "--follow-up-message",
        help="Message to post when a reply is not received in time (required in ask mode).",
    )
    args = parser.parse_args()

    if args.mode == "ask" and args.follow_up_message is None:
        raise SystemExit("--follow-up-message is required in ask mode.")

    question = unescape_cli_text(args.question)
    follow_up_message = (
        unescape_cli_text(args.follow_up_message)
        if args.follow_up_message is not None
        else None
    )
    time.sleep(2) # codex CLIが1000msくらいでTIMEOUTすることが多いので対策

    if args.mode == "ask":
        run_ask(
            question=question,
            follow_up_message=follow_up_message,
            interval=args.interval,
            no_reply_hint=args.no_reply_hint,
            channel_override=args.channel,
        )
    else:
        if not args.thread_ts:
            raise SystemExit("--thread-ts is required in reply mode.")
        run_reply(question, args.thread_ts, args.channel)


if __name__ == "__main__":
    main()
