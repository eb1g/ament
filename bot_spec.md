# Discord Bot 実装仕様書

## 1. 概要
ユーザーの要望に基づき、以下の機能を備えた Discord Bot を `discord.py` を用いて開発する。

## 2. 機能詳細

### 2.1 読み上げ機能 (TTS)
- **ライブラリ**: `gTTS` (Google Text-to-Speech) または `VOICEVOX` (API経由)
- **動作**: ユーザーがボイスチャンネルに接続している状態でコマンドを打つと、テキストを音声に変換して再生する。
- **コマンド**: `/join`, `/leave`, `/speak [text]`

### 2.2 音楽再生機能
- **ライブラリ**: `yt-dlp`, `PyNaCl`, `FFmpeg`
- **ソース**: YouTube (SpotifyはYouTube検索経由で対応)
- **動作**: YouTubeのURLまたはキーワードから音声を抽出して再生する。
- **コマンド**: `/play [url/keyword]`, `/stop`, `/skip`

### 2.3 天気予報機能
- **API**: `OpenWeatherMap API`
- **動作**: 指定された都市、または全国の主要都市の天気を表示する。
- **コマンド**: `/weather [city]`

### 2.4 認証機能 (Captcha)
- **ライブラリ**: `captcha` (Python library)
- **動作**: 新規参加者、またはコマンド実行者に対して画像認証を表示。正解すると指定のロールを付与する。
- **コマンド**: `/verify`

### 2.5 ヘルプ機能
- **動作**: 利用可能なコマンド一覧と説明を Embed 形式で表示する。
- **コマンド**: `/help`

## 3. 技術スタック
- **言語**: Python 3.11
- **主要ライブラリ**:
    - `discord.py` (Botフレームワーク)
    - `yt-dlp` (YouTube動画情報取得)
    - `gTTS` (音声合成)
    - `captcha` (画像認証生成)
    - `requests` (天気API呼び出し)

## 4. 必要な環境変数
- `DISCORD_BOT_TOKEN`
- `OPENWEATHER_API_KEY`
- `VERIFIED_ROLE_ID`
