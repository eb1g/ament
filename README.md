# Discord Bot

このDiscord Botは、以下の機能を備えています。

- **読み上げ機能**: テキストを音声に変換してボイスチャンネルで読み上げます。
- **音楽再生機能**: YouTubeの動画を検索・再生します。
- **天気予報機能**: 指定した都市の天気情報を表示します。
- **認証機能**: 画像認証により、新規ユーザーに特定のロールを付与します。
- **ヘルプ機能**: 利用可能なコマンド一覧を表示します。

## セットアップ方法

### 1. 必要なソフトウェアのインストール

- **Python 3.8以上**: [Python公式サイト](https://www.python.org/downloads/) からダウンロードしてインストールしてください。
- **FFmpeg**: 音楽再生機能に必要です。お使いのOSに合わせてインストールしてください。
  - Windows: [FFmpeg公式サイト](https://ffmpeg.org/download.html) からダウンロードし、環境変数PATHにFFmpegの`bin`ディレクトリを追加してください。
  - macOS: `brew install ffmpeg`
  - Linux (Ubuntu/Debian): `sudo apt-get update && sudo apt-get install -y ffmpeg`

### 2. Discord Botの作成とトークンの取得

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセスし、新しいアプリケーションを作成します。
2. 「Bot」タブに移動し、「Add Bot」をクリックしてBotを作成します。
3. 「TOKEN」セクションの「Reset Token」をクリックし、表示されたトークンをコピーします。このトークンは後で必要になります。
4. 「Privileged Gateway Intents」セクションで、「PRESENCE INTENT」と「MESSAGE CONTENT INTENT」を有効にします。

### 3. Botをサーバーに招待

1. 「OAuth2」タブの「URL Generator」に移動します。
2. 「SCOPES」で `bot` と `applications.commands` を選択します。
3. 「BOT PERMISSIONS」で以下の権限を選択します。
   - `Read Messages/View Channels`
   - `Send Messages`
   - `Manage Roles` (認証機能用)
   - `Connect` (ボイスチャンネル接続用)
   - `Speak` (読み上げ・音楽再生用)
4. 生成されたURLをコピーし、ブラウザで開いてBotをあなたのサーバーに招待します。

### 4. OpenWeatherMap APIキーの取得

1. [OpenWeatherMap公式サイト](https://openweathermap.org/api) にアクセスし、アカウントを作成します。
2. ログイン後、「API keys」タブからAPIキーを生成し、コピーします。このキーは後で必要になります。

### 5. 認証用ロールの準備

Discordサーバーで、認証が成功したユーザーに付与するロールを作成し、そのロールIDを控えておきます。

### 6. プロジェクトファイルの準備

1. 提供された `main.py` と `config.py` ファイルを任意のディレクトリに保存します。
2. ターミナルまたはコマンドプロンプトを開き、これらのファイルを保存したディレクトリに移動します。

### 7. 依存関係のインストール

以下のコマンドを実行して、必要なPythonライブラリをインストールします。

```bash
pip install discord.py gTTS yt-dlp requests captcha PyNaCl
```

### 8. 環境変数の設定

`config.py` ファイルを編集するか、環境変数として以下の値を設定します。

- `DISCORD_BOT_TOKEN`: Discord Developer Portalで取得したBotトークン
- `OPENWEATHER_API_KEY`: OpenWeatherMapで取得したAPIキー
- `VERIFIED_ROLE_ID`: 認証成功時に付与するロールのID

例: `config.py` の編集

```python
import os

DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"
VERIFIED_ROLE_ID = "YOUR_VERIFIED_ROLE_ID" # ロールIDは文字列として設定
```

### 9. Botの実行

以下のコマンドを実行してBotを起動します。

```bash
python main.py
```

Botがオンラインになり、Discordサーバーで利用可能になります。

## コマンド一覧

- `/join`: Botをボイスチャンネルに接続します。
- `/leave`: Botをボイスチャンネルから切断します。
- `/speak [テキスト]`: 指定されたテキストを読み上げます。
- `/play [URLまたはキーワード]`: YouTubeのURLまたはキーワードから音楽を再生します。
- `/stop`: 音楽の再生を停止します。
- `/skip`: 現在の曲をスキップします。
- `/weather [都市名]`: 指定された都市の天気情報を表示します。
- `/verify`: 画像認証を行い、成功するとロールが付与されます。
- `/help`: このヘルプメッセージを表示します。
