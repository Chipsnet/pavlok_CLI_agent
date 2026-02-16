"""
v0.3 Slack BlockKit Builder

BlockKit JSON生成モジュール
https://api.slack.com/reference/block-kit/blocks
"""
from typing import Any
import json


class BlockKitBuilder:
    """Slack BlockKit JSON生成クラス"""

    # ============================================================================
    # Plan Event Blocks
    # ============================================================================

    @staticmethod
    def plan_open_notification(schedule_id: str) -> list[dict[str, Any]]:
        """planイベント開始通知（パブリック）"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📅 今日の予定を登録しましょう"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "おはようございます！今日の計画を立てましょう。\n以下のボタンをクリックして予定を登録してください。"
                }
            },
            {
                "type": "actions",
                "block_id": "plan_trigger",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📝 予定を登録"
                        },
                        "style": "primary",
                        "action_id": "plan_open_modal",
                        "value": json.dumps({"schedule_id": schedule_id}, ensure_ascii=False)
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⏰ 応答がない場合、15分後に催促が始まります"
                    }
                ]
            }
        ]

    @staticmethod
    def plan_submit_confirmation(
        scheduled_tasks: list[dict[str, str]],
        next_plan: dict[str, str]
    ) -> list[dict[str, Any]]:
        """plan送信完了通知（パブリックメッセージ）"""
        # Build task list text
        task_lines = []
        for task in scheduled_tasks:
            task_lines.append(f"*{task['task']}*\n🕐 {task['date']} {task['time']}")

        task_list_text = "\n\n".join(task_lines)

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📅 本日の予定を登録しました"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": task_list_text
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔁 次回計画: {next_plan['date']} {next_plan['time']}*"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 各時刻にリマインドされます"
                    }
                ]
            }
        ]

    # ============================================================================
    # Remind Event Blocks
    # ============================================================================

    @staticmethod
    def remind_notification(
        schedule_id: str,
        task_name: str,
        task_time: str,
        description: str
    ) -> list[dict[str, Any]]:
        """remindイベント通知（パブリック）"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔔 リマインド"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{task_name}*\n🕐 {task_time}\n\n{description}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "block_id": "remind_response",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✓ やりました！"
                        },
                        "style": "primary",
                        "action_id": "remind_yes",
                        "value": json.dumps(
                            {"schedule_id": schedule_id, "event_type": "remind"},
                            ensure_ascii=False
                        )
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✕ やれません"
                        },
                        "style": "danger",
                        "action_id": "remind_no",
                        "value": json.dumps(
                            {"schedule_id": schedule_id, "event_type": "remind"},
                            ensure_ascii=False
                        )
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚠️ 応答がない場合、15分ごとにPavlokが動作します"
                    }
                ]
            }
        ]

    @staticmethod
    def yes_response(task_name: str, comment: str) -> list[dict[str, Any]]:
        """YES応答（スレッド返信）"""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🎉 *{task_name}*\n✓ 完了しました！\n\n良い一日のスタートです！\n> {comment}"
                }
            }
        ]

    @staticmethod
    def no_response(
        task_name: str,
        no_count: int,
        punishment_mode: str,
        punishment_value: int,
        comment: str
    ) -> list[dict[str, Any]]:
        """NO応答（スレッド返信 + Pavlok実行）"""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"😢 *{task_name}*\n✕ できませんでした...\n\n今回のNO回数: {no_count}回\n"
                            f"罰: {punishment_mode} {punishment_value}%\n\n> {comment}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚡ Pavlokから刺激を送信しました"
                    }
                ]
            }
        ]

    # ============================================================================
    # Ignore Notification Blocks
    # ============================================================================

    @staticmethod
    def ignore_notification(
        schedule_id: str,
        task_name: str,
        task_time: str,
        ignore_time: int,
        ignore_count: int,
        stimulation_type: str,
        stimulation_value: int
    ) -> list[dict[str, Any]]:
        """ignore検知通知（パブリック）"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ 応答待ち"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{task_name}*\n🕐 {task_time}\n\n応答を待っています...\n\n"
                            f"無視時間: {ignore_time}分経過\ngentle reminder: {stimulation_type} {stimulation_value}%"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "block_id": "ignore_response",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✓ 今やりました！"
                        },
                        "style": "primary",
                        "action_id": "ignore_yes",
                        "value": json.dumps(
                            {"schedule_id": schedule_id, "event_type": "ignore"},
                            ensure_ascii=False
                        )
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✕ やれません"
                        },
                        "style": "danger",
                        "action_id": "ignore_no",
                        "value": json.dumps(
                            {"schedule_id": schedule_id, "event_type": "ignore"},
                            ensure_ascii=False
                        )
                    }
                ]
            }
        ]

    @staticmethod
    def auto_canceled_notification(
        task_name: str,
        task_time: str,
        final_punishment_mode: str,
        final_punishment_value: int
    ) -> list[dict[str, Any]]:
        """最大無視到達時（キャンセル通知）"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "❌ 自動キャンセル"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{task_name}*\n🕐 {task_time}\n\n長時間無視が続いたため、"
                            f"このタスクは自動的にキャンセルされました。\n\n"
                            f"最終罰: {final_punishment_mode} {final_punishment_value}%\n\n"
                            f"> 次は一緒に頑張りましょう。"
                }
            }
        ]

    # ============================================================================
    # Command Notification Blocks
    # ============================================================================

    @staticmethod
    def stop_notification() -> list[dict[str, Any]]:
        """/stop コマンド完了通知（エフェメラル）"""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "⏸️ *鬼コーチを停止しました*\n\n再開するには `/restart` を実行してください。"
                }
            }
        ]

    @staticmethod
    def restart_notification() -> list[dict[str, Any]]:
        """/restart コマンド完了通知（エフェメラル）"""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "▶️ *鬼コーチを再開しました*"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "次回のWorkerサイクルから通常運用が再開されます"
                    }
                ]
            }
        ]

    # ============================================================================
    # Modal Blocks
    # ============================================================================

    @staticmethod
    def base_commit_modal(commitments: list[dict[str, str]]) -> dict[str, Any]:
        """コミットメント管理モーダル"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "毎日実行するコミットメントを設定します。入力内容はplan_APIに送信されます。"
                }
            },
            {
                "type": "divider"
            }
        ]

        # Add commitment rows (minimum 3 rows)
        for i in range(max(3, len(commitments))):
            idx = i + 1
            commitment = commitments[i] if i < len(commitments) else {}

            blocks.append({
                "type": "input",
                "block_id": f"commitment_{idx}",
                "label": {
                    "type": "plain_text",
                    "text": f"コミットメント {idx}"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": f"task_{idx}",
                    "initial_value": commitment.get("task", ""),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "タスク名"
                    },
                    "max_length": 100
                },
                "dispatch_action": True
            })
            blocks.append({
                "type": "input",
                "block_id": f"time_{idx}",
                "label": {
                    "type": "plain_text",
                    "text": f"時刻 {idx}"
                },
                "element": {
                    "type": "timepicker",
                    "action_id": f"time_{idx}",
                    "initial_time": commitment.get("time", "07:00"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "時間を選択"
                    }
                },
                "optional": True
            })
            blocks.append({"type": "divider"})

        # Remove last divider
        blocks.pop()

        # Add action buttons
        blocks.extend([
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "+ 追加"
                        },
                        "style": "primary",
                        "action_id": "commitment_add_row"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 コミットメントは毎日指定時刻にplanイベントとして登録されます"
                    }
                ]
            }
        ])

        return {
            "type": "modal",
            "callback_id": "base_commit_submit",
            "title": {
                "type": "plain_text",
                "text": "📋 コミットメント管理"
            },
            "submit": {
                "type": "plain_text",
                "text": "送信"
            },
            "blocks": blocks
        }

    @staticmethod
    def config_modal(config_values: dict[str, str]) -> dict[str, Any]:
        """設定管理モーダル"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔴 罰設定"
                }
            },
            {
                "type": "input",
                "block_id": "PAVLOK_TYPE_PUNISH",
                "label": {
                    "type": "plain_text",
                    "text": "デフォルト罰スタイル"
                },
                "element": {
                    "type": "static_select",
                    "action_id": "PAVLOK_TYPE_PUNISH_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "⚡ zap (電気ショック)"},
                        "value": "zap"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "⚡ zap (電気ショック)"}, "value": "zap"},
                        {"text": {"type": "plain_text", "text": "📳 vibe (振動)"}, "value": "vibe"},
                        {"text": {"type": "plain_text", "text": "🔊 beep (音)"}, "value": "beep"}
                    ]
                }
            },
            {
                "type": "input",
                "block_id": "PAVLOK_VALUE_PUNISH",
                "label": {
                    "type": "plain_text",
                    "text": "デフォルト罰強度 (0-100)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "PAVLOK_VALUE_PUNISH_input",
                    "initial_value": config_values.get("PAVLOK_VALUE_PUNISH", "35"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "0-100の数値"
                    },
                    "min_length": 1,
                    "max_length": 3
                },
                "hint": {
                    "type": "plain_text",
                    "text": ":warning: 80以上は非常に強力です。十分に注意してください。"
                }
            },
            {
                "type": "input",
                "block_id": "LIMIT_DAY_PAVLOK_COUNTS",
                "label": {
                    "type": "plain_text",
                    "text": "1日の最大ZAP回数"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "LIMIT_DAY_PAVLOK_COUNTS_input",
                    "initial_value": config_values.get("LIMIT_DAY_PAVLOK_COUNTS", "100"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "例: 100"
                    },
                    "min_length": 1,
                    "max_length": 4
                }
            },
            {
                "type": "input",
                "block_id": "LIMIT_PAVLOK_ZAP_VALUE",
                "label": {
                    "type": "plain_text",
                    "text": "最大ZAP強度 (安全リミット)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "LIMIT_PAVLOK_ZAP_VALUE_input",
                    "initial_value": config_values.get("LIMIT_PAVLOK_ZAP_VALUE", "100"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "0-100の数値"
                    },
                    "min_length": 1,
                    "max_length": 3
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚡ Ignoreモード設定"
                }
            },
            {
                "type": "input",
                "block_id": "IGNORE_INTERVAL",
                "label": {
                    "type": "plain_text",
                    "text": "検知間隔 (秒)"
                },
                "element": {
                    "type": "static_select",
                    "action_id": "IGNORE_INTERVAL_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "15分 (900秒)"},
                        "value": config_values.get("IGNORE_INTERVAL", "900")
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "5分 (300秒)"}, "value": "300"},
                        {"text": {"type": "plain_text", "text": "10分 (600秒)"}, "value": "600"},
                        {"text": {"type": "plain_text", "text": "15分 (900秒)"}, "value": "900"},
                        {"text": {"type": "plain_text", "text": "30分 (1800秒)"}, "value": "1800"}
                    ]
                }
            },
            {
                "type": "input",
                "block_id": "IGNORE_JUDGE_TIME",
                "label": {
                    "type": "plain_text",
                    "text": "判定時間 (秒)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "IGNORE_JUDGE_TIME_input",
                    "initial_value": config_values.get("IGNORE_JUDGE_TIME", "3"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "例: 3"
                    },
                    "min_length": 1,
                    "max_length": 3
                }
            },
            {
                "type": "input",
                "block_id": "IGNORE_MAX_RETRY",
                "label": {
                    "type": "plain_text",
                    "text": "最大再試行回数"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "IGNORE_MAX_RETRY_input",
                    "initial_value": config_values.get("IGNORE_MAX_RETRY", "5"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "例: 5"
                    },
                    "min_length": 1,
                    "max_length": 2
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⏱️ タイムアウト設定"
                }
            },
            {
                "type": "input",
                "block_id": "TIMEOUT_REMIND",
                "label": {
                    "type": "plain_text",
                    "text": "リマインドタイムアウト (秒)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "TIMEOUT_REMIND_input",
                    "initial_value": config_values.get("TIMEOUT_REMIND", "600"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "例: 600"
                    },
                    "min_length": 1,
                    "max_length": 5
                }
            },
            {
                "type": "input",
                "block_id": "TIMEOUT_REVIEW",
                "label": {
                    "type": "plain_text",
                    "text": "振り返りタイムアウト (秒)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "TIMEOUT_REVIEW_input",
                    "initial_value": config_values.get("TIMEOUT_REVIEW", "600"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "例: 600"
                    },
                    "min_length": 1,
                    "max_length": 5
                }
            },
            {
                "type": "input",
                "block_id": "RETRY_DELAY",
                "label": {
                    "type": "plain_text",
                    "text": "リトライ遅延 (分)"
                },
                "element": {
                    "type": "static_select",
                    "action_id": "RETRY_DELAY_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "5分"},
                        "value": config_values.get("RETRY_DELAY", "5")
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "1分"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "3分"}, "value": "3"},
                        {"text": {"type": "plain_text", "text": "5分"}, "value": "5"},
                        {"text": {"type": "plain_text", "text": "10分"}, "value": "10"},
                        {"text": {"type": "plain_text", "text": "15分"}, "value": "15"}
                    ]
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "💬 コーチ口調設定"
                }
            },
            {
                "type": "input",
                "block_id": "COACH_CHARACTOR",
                "label": {
                    "type": "plain_text",
                    "text": "キャラクター"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "COACH_CHARACTOR_input",
                    "initial_value": config_values.get("COACH_CHARACTOR", "うる星やつらのラムちゃん"),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "例: うる星やつらのラムちゃん"
                    },
                    "min_length": 1,
                    "max_length": 100
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔄 全リセット"
                        },
                        "style": "danger",
                        "action_id": "config_reset_all",
                        "confirm": {
                            "title": {
                                "type": "plain_text",
                                "text": "確認"
                            },
                            "text": {
                                "type": "plain_text",
                                "text": "全ての設定をデフォルト値にリセットします。よろしいですか？"
                            },
                            "confirm": {
                                "type": "plain_text",
                                "text": "リセット"
                            },
                            "deny": {
                                "type": "plain_text",
                                "text": "キャンセル"
                            }
                        }
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📋 変更履歴"
                        },
                        "action_id": "config_history"
                    }
                ]
            }
        ]

        return {
            "type": "modal",
            "callback_id": "config_submit",
            "title": {
                "type": "plain_text",
                "text": "⚙️ Oni System 設定"
            },
            "submit": {
                "type": "plain_text",
                "text": "保存"
            },
            "blocks": blocks
        }

    # ============================================================================
    # Error & Status Notification Blocks
    # ============================================================================

    @staticmethod
    def error_notification(error_message: str) -> list[dict[str, Any]]:
        """エラー通知"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "❌ エラーが発生しました"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{error_message}\n\n```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "再試行"
                        },
                        "action_id": "retry_config"
                    }
                ]
            }
        ]

    @staticmethod
    def daily_limit_reached(limit_count: int) -> list[dict[str, Any]]:
        """日次最大ZAP到達通知"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🛑 本日の罰上限に到達"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"本日のZAP回数が *{limit_count}回* に達しました。\n\n"
                            f"安全のため、これ以上の罰は実行されません。\n明日はリセットされます。"
                }
            }
        ]
