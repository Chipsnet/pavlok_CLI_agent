## 対象
scripts/repentance.py

## 問題点
daily_punishment.dateを起点に罰回数を管理しているが、日付起因にすると
`repentance`実行後に`scripts/add_slack_ignore_events`が発生した時に`daily_punishment.state = done`に1加算されてしまい
罪が正しく記録されない。

## 対応方針
- daily_punishmentレコードの考え方を日付からid起点に変更する（つまり、`repentance`から`repentance`までの区間が1レコード）
  - `daily_punishments.date` をドロップし、ユニーク制約も削除する
  - 「最新レコードに加算 / repentance 実行ごとに新規レコード生成」という運用に変更する
    - add_slack_ignore_events は **日付で検索せず**「最新レコード」に対して `ignore_count` / `punishment_count` を加算する
    - レコードが存在しない場合は新規作成してから加算する
  - repentance は「全 pending/failed を処理 → 実行の最後に必ず新規レコードを生成」に変更する

## 変更点（具体）
- DBスキーマ
  - `daily_punishments.date` を削除
  - 代わりに「サイクル開始時刻」を持たせるなら `cycle_started_at` を追加（任意）
- scripts/add_slack_ignore_events.py
  - `event_date` の扱いは `SlackIgnoreEvent` に残す
  - `DailyPunishment` は日付ではなく「最新レコード」を取得するよう修正
- scripts/repentance.py
  - 対象レコード取得は state in pending/failed の全件を処理する
  - 実行の最後に次サイクル用レコードを必ず作成する

## 期待される効果
- repentance 実行後に新しい ignore が発生しても **最新レコード** に計上されるため、`done` レコードが増えない
- 日付起因の競合がなくなり、罰回数のカウントが時系列で一貫する

## 移行方針（最小）
- 既存 `daily_punishments` は `date` を削除するマイグレーションを追加
- 初回起動時にレコードが存在しない場合は add_slack_ignore_events が新規生成する

## 実装タスク
- [ ] **DBモデル修正** (前提)
  - [ ] `db/models.py`: `DailyPunishment` モデルから `date` カラム定義を削除する
  - [ ] マイグレーション: `daily_punishments` テーブルから `date` カラムとユニーク制約を削除する Alembic リビジョンを作成する
- [ ] **TDD: add_slack_ignore_events.py**
  - [ ] **テスト修正**: `tests/scripts/test_add_slack_ignore_events.py`
    - [ ] `DailyPunishment` の作成時に `date` を指定しないように修正
    - [ ] ケース追加: 日付が異なるタイミングで実行しても、既存の最新レコード (state=pending/failed) があればそれに加算されることを検証するテスト
    - [ ] ケース追加: レコードが存在しない場合、新規作成されることを検証するテスト
  - [ ] **実装修正**: `scripts/add_slack_ignore_events.py`
    - [ ] テストが通るように、日付検索 (`filter_by(date=...)`) をID降順 (`order_by(DailyPunishment.id.desc())`) に変更し、新規作成ロジックを修正する
- [ ] **TDD: repentance.py**
  - [ ] **テスト修正**: `tests/scripts/test_repentance.py`
    - [ ] `DailyPunishment` の作成時に `date` を指定しないように修正
    - [ ] ケース追加: `executed_count` 完了後に、次サイクル用の新規レコード (state='pending', count=0) が作成されていることを検証するアサーションを追加
  - [ ] **実装修正**: `scripts/repentance.py`
    - [ ] ログ出力の `date` 依存を排除
    - [ ] 処理終了後に次サイクル用レコード作成処理を追加し、テストを通過させる

