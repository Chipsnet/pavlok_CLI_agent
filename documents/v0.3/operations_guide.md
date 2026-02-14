# Oni System v0.3 運用手順書

## 1. デプロイ手順

### 1.1 前提条件

- Python 3.12
- SQLite 3
- 環境変数設定済み（`.env`ファイル）

### 1.2 初回デプロイ

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd pavlok_CLI_agent

# 2. 仮想環境作成
python -m venv .venv
source .venv/bin/activate

# 3. 依存関係インストール
pip install -e ".[dev]"

# 4. データベース初期化
python -c "from backend.models import Base, create_engine; engine = create_engine('sqlite:///app.db'); Base.metadata.create_all(engine)"

# 5. 初期設定値を投入
python scripts/init_config.py
```

### 1.3 アップデート

```bash
# 1. コードをプル
git pull origin main

# 2. 依存関係を更新
pip install -e ".[dev]"

# 3. マイグレーション実行（必要な場合）
alembic upgrade head

# 4. サービス再起動
systemctl restart oni-api
systemctl restart oni-worker
```

---

## 2. サービス管理

### 2.1 systemdサービス定義

**/etc/systemd/system/oni-api.service**
```ini
[Unit]
Description=Oni System API
After=network.target

[Service]
Type=simple
User=oni
WorkingDirectory=/opt/oni
Environment="PATH=/opt/oni/.venv/bin"
ExecStart=/opt/oni/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**/etc/systemd/system/oni-worker.service**
```ini
[Unit]
Description=Oni System Worker
After=network.target

[Service]
Type=simple
User=oni
WorkingDirectory=/opt/oni
Environment="PATH=/opt/oni/.venv/bin"
ExecStart=/opt/oni/.venv/bin/python -m backend.worker.worker
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2.2 サービス操作コマンド

```bash
# ステータス確認
systemctl status oni-api
systemctl status oni-worker

# 起動
systemctl start oni-api
systemctl start oni-worker

# 停止
systemctl stop oni-api
systemctl stop oni-worker

# 再起動
systemctl restart oni-api
systemctl restart oni-worker

# ログ確認
journalctl -u oni-api -f
journalctl -u oni-worker -f
```

---

## 3. バックアップと復元

### 3.1 データベースバックアップ

```bash
# 手動バックアップ
sqlite3 app.db ".backup 'backup/app.db.$(date +%Y%m%d_%H%M%S)'"

# cronで毎日バックアップ
# crontab -e
0 3 * * * sqlite3 /opt/oni/app.db ".backup '/opt/oni/backup/app.db.$(date +\%Y\%m\%d_\%H\%M\%S)'"
```

### 3.2 復元手順

```bash
# サービス停止
systemctl stop oni-api oni-worker

# バックアップから復元
cp /opt/oni/backup/app.db.20260214_030000 /opt/oni/app.db

# サービス再開
systemctl start oni-api oni-worker
```

---

## 4. 監視

### 4.1 ヘルスチェック

```bash
# APIヘルスチェック
curl http://localhost:8000/health

# 期待されるレスポンス
{"status": "healthy"}
```

### 4.2 ログ監視

重要なログパターン：

| パターン | 重要度 | 対応 |
|---------|-------|------|
| `Error processing schedule` | ERROR | スケジュール処理エラーを調査 |
| `Script execution failed` | ERROR | スクリプト実行エラーを調査 |
| `Slack signature verification failed` | WARN | セキュリティ警告 |
| `Daily zap limit reached` | INFO | 日次上限到達（正常） |

### 4.3 メトリクス

監視すべきメトリクス：

- API レスポンスタイム
- Worker 処理数/分
- データベースサイズ
- 罰実行回数/日

---

## 5. トラブルシューティング

### 5.1 APIが起動しない

```bash
# ポート使用状況確認
lsof -i :8000

# 環境変数確認
env | grep -E "(SLACK|PAVLOK|DATABASE)"

# ログ確認
journalctl -u oni-api -n 100
```

### 5.2 Workerが動作しない

```bash
# プロセス確認
ps aux | grep worker

# データベース接続確認
sqlite3 app.db "SELECT COUNT(*) FROM schedules WHERE state='pending'"

# ログ確認
journalctl -u oni-worker -n 100
```

### 5.3 Slack連携エラー

1. Slack Appの設定を確認
2. OAuthトークンが有効か確認
3. Webhook URLが正しいか確認
4. 署名検証が正しく設定されているか確認

### 5.4 Pavlok連携エラー

1. APIキーが有効か確認
2. デバイスがオンラインか確認
3. APIレート制限に達していないか確認

---

## 6. セキュリティ運用

### 6.1 定期確認事項

- [ ] アクセスログの異常がないか
- [ ] 設定変更監査ログの確認
- [ ] 認可ユーザーリストの更新
- [ ] APIキーのローテーション

### 6.2 インシデント対応

1. 異常を検知したら即座にサービスを停止
2. ログを保全
3. 原因を調査
4. 必要に応じて認証情報をローテーション
5. 修正後にサービス再開

---

## 7. 考慮ポイント

### 7.1 スケーラビリティ

- 現在の設計は1ユーザー・1サーバー前提
- 将来的なマルチユーザー対応はDBスキーマで準備済み

### 7.2 可用性

- APIとWorkerは独立して動作可能
- Workerが停止してもAPIは機能する（ただし処理は滞留）
- APIが停止してもWorkerは1分間隔で処理を継続

### 7.3 パフォーマンス

- 設定値は60秒キャッシュされる
- DBはSQLiteのため、大量データには注意
- Slack APIのレート制限に注意

---

## 8. 連絡先

技術的な問題については、開発チームまでお問い合わせください。
