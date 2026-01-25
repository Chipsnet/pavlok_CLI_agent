このプロジェクトの常駐サーバーを作成しました。
`ssh oni_coach_motoya`で接続可能です。
dockerは使用せず、サーバーに直接実行環境を作成してください。(Dockerfileの内容が参考になると思います)

1. 以下のソース類をサーバー上にコピーする
  - .codex
  - db
  - prompts
  - scripts
  - tests
  - root直下のファイル全て
2. 実行環境をインストールする
3. `~/.codex/auth.json`,`~/.codex/config.toml`をサーバー環境の適切な位置にコピーする
4. `uv run pytest -q`が正常終了することを確認
5. `codex exec こんにちわ`で正常応答することを確認
6. ここまでのデプロイ手順を第三者ができるように、具体的なコマンドを含め`## 環境構築手順`に記載する

## 環境構築手順
以下はローカル端末から実行する前提の手順です。（サーバーは `ssh oni_coach_motoya` で接続できる想定）

### 1) ソースをクローン & `.env`を反映
```bash
git clone https://github.com/motoya0118/pavlok_CLI_agent.git
scp /Users/motoya/pavlok_CLI_agent/.env oni_coach_motoya:~/pavlok_CLI_agent/.env

# もしDBデータ引き継ぎたければ
scp /Users/motoya/pavlok_CLI_agent/app.db oni_coach_motoya:~/pavlok_CLI_agent/app.db
```

### 2) サーバーに接続して実行環境を作成
```bash
ssh oni_coach_motoya
```

```bash
# 以降はサーバー上で実行
cd ~/pavlok_CLI_agent

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  git curl nodejs npm \
  python3.12 python3.12-venv python3.12-dev

# uv をインストール（Astral公式）
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.profile

# Codex CLI をインストール
sudo npm i -g @openai/codex
```

### 3) Codex認証情報を配置
```bash
mkdir -p ~/.codex
exit
```

```bash
# ローカルで実行: 認証情報をサーバーへコピー
scp ~/.codex/auth.json oni_coach_motoya:~/.codex/auth.json
scp ~/.codex/config.toml oni_coach_motoya:~/.codex/config.toml
```

```bash
# サーバーへ再接続
ssh oni_coach_motoya
cd ~/pavlok_CLI_agent
```

### 4) 依存関係を同期
```bash
uv sync --frozen
```

### 5) 動作確認
```bash
uv run pytest -q
```

```bash
codex exec こんにちわ
```

### 6) OniCoachの起動
```bash
nohup uv run python main.py > app.log 2>&1 &
```