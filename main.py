import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import string
import asyncio
import json
import requests
from captcha.image import ImageCaptcha
import io
import base64
import time
from flask import Flask
from threading import Thread

# Flaskアプリの初期化
app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is running!", 200

def run_flask():
    app.run(host='0.0.0.0', port=os.getenv('PORT', 8080))

# Discord Botの初期化
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# サーバーごとの設定を保存するファイル
SETTINGS_FILE = 'server_settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

server_settings = load_settings()

# 認証用のパスワードを一時的に保存する辞書
# Renderで複数インスタンスが立ち上がる可能性を考慮し、永続化はしない
current_verify_password = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name=f'{len(bot.guilds)}個のサーバーで稼働中'))
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    
    # Flaskサーバーを別スレッドで起動
    Thread(target=run_flask).start()

@bot.event
async def on_guild_join(guild):
    await bot.change_presence(activity=discord.Game(name=f'{len(bot.guilds)}個のサーバーで稼働中'))

@bot.event
async def on_guild_remove(guild):
    await bot.change_presence(activity=discord.Game(name=f'{len(bot.guilds)}個のサーバーで稼働中'))

# 管理者権限チェックデコレーター
def is_admin():
    async def predicate(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("このコマンドは管理者のみが実行できます。", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# ヘルプコマンド
@bot.tree.command(name="help", description="Botのコマンド一覧を表示します。")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Botコマンド一覧", description="Botの機能と使い方です。", color=discord.Color.blue())
    embed.add_field(name="__管理コマンド (管理者のみ)__", value=(
        "`/verify role:[ロール]` - 認証パネルを設置します。\n"
        "`/kick [メンバー] [理由]` - メンバーをキックします。\n"
        "`/ban [メンバー] [理由]` - メンバーをBANします。\n"
        "`/timeout [メンバー] [時間(分)] [理由]` - メンバーを一時的にミュートします。\n"
        "`/unmute [メンバー]` - メンバーのタイムアウトを解除します。\n"
        "`/clear [数]` - 指定した数のメッセージを削除します。"
    ), inline=False)
    embed.add_field(name="__セキュリティ__", value=(
        "`/password` - 認証の時に使います(隠し)。\n"
        "`/genpass [長さ] [記号を含めるか]` - アカウント作成用の強力なパスワードを生成します(隠し)。"
    ), inline=False)
    embed.add_field(name="__検索__", value=(
        "`/search [キーワード]` - ウェブ検索を行います。\n"
        "`/image_search [キーワード]` - 画像検索を行います。\n"
        "`/lyrics [曲名・アーティスト]` - 歌詞を検索します。"
    ), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# キックコマンド
@bot.tree.command(name="kick", description="メンバーをキックします。")
@app_commands.describe(member="キックするメンバー", reason="キックする理由")
@is_admin()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "理由なし"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.kick(reason=reason)
        await interaction.followup.send(f'{member.display_name} をキックしました。理由: {reason}', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("Botにメンバーをキックする権限がありません。または、Botのロールが対象メンバーより下位にあります。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)

# BANコマンド
@bot.tree.command(name="ban", description="メンバーをBANします。")
@app_commands.describe(member="BANするメンバー", reason="BANする理由")
@is_admin()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "理由なし"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.ban(reason=reason)
        await interaction.followup.send(f'{member.display_name} をBANしました。理由: {reason}', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("BotにメンバーをBANする権限がありません。または、Botのロールが対象メンバーより下位にあります。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)

# タイムアウトコマンド
@bot.tree.command(name="timeout", description="メンバーを一時的にミュートします。")
@app_commands.describe(member="タイムアウトするメンバー", minutes="タイムアウトする時間(分)", reason="タイムアウトする理由")
@is_admin()
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "理由なし"):
    await interaction.response.defer(ephemeral=True)
    try:
        duration = discord.utils.utcnow() + discord.Timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.followup.send(f'{member.display_name} を {minutes} 分間タイムアウトしました。理由: {reason}', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("Botにメンバーをタイムアウトする権限がありません。または、Botのロールが対象メンバーより下位にあります。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)

# タイムアウト解除コマンド
@bot.tree.command(name="unmute", description="メンバーのタイムアウトを解除します。")
@app_commands.describe(member="タイムアウトを解除するメンバー")
@is_admin()
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.timeout(None)
        await interaction.followup.send(f'{member.display_name} のタイムアウトを解除しました。', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("Botにメンバーのタイムアウトを解除する権限がありません。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)

# メッセージクリアコマンド
@bot.tree.command(name="clear", description="指定した数のメッセージを削除します。")
@app_commands.describe(count="削除するメッセージの数")
@is_admin()
async def clear(interaction: discord.Interaction, count: int):
    await interaction.response.defer(ephemeral=True)
    try:
        await interaction.channel.purge(limit=count)
        await interaction.followup.send(f'{count} 件のメッセージを削除しました。', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("Botにメッセージを管理する権限がありません。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)

# パスワード生成コマンド
@bot.tree.command(name="password", description="認証の時に使うパスワードを生成します。")
async def password(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    characters = string.ascii_letters + string.digits + string.punctuation
    generated_password = ''.join(random.choice(characters) for i in range(12))
    current_verify_password[interaction.guild_id] = generated_password
    await interaction.followup.send(f"認証用パスワードを生成しました: `{generated_password}`\nこのパスワードは認証時に使用します。", ephemeral=True)

# アカウント作成用パスワード生成コマンド
@bot.tree.command(name="genpass", description="アカウント作成用の強力なパスワードを生成します。")
@app_commands.describe(length="パスワードの長さ (8-32)", include_symbols="記号を含めるか")
async def genpass(interaction: discord.Interaction, length: app_commands.Range[int, 8, 32] = 16, include_symbols: bool = True):
    await interaction.response.defer(ephemeral=True)
    characters = string.ascii_letters + string.digits
    if include_symbols:
        characters += string.punctuation
    generated_password = ''.join(random.choice(characters) for i in range(length))
    await interaction.followup.send(f"生成されたパスワード: `{generated_password}`", ephemeral=True)

# 認証パネル設置コマンド
@bot.tree.command(name="verify", description="認証パネルを設置します。")
@app_commands.describe(role="認証後に付与するロール")
@is_admin()
async def verify_setup(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    settings = load_settings()
    settings[str(interaction.guild_id)] = {
        'verified_role_id': role.id,
        'channel_id': interaction.channel_id
    }
    save_settings(settings)

    embed = discord.Embed(title="認証が必要です", description="このサーバーに参加するには認証を完了してください。", color=discord.Color.green())
    embed.add_field(name="認証方法", value="下のボタンを押して、DMで送られてくる指示に従ってください。", inline=False)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="認証を開始する", custom_id="start_verification", style=discord.ButtonStyle.success))

    await interaction.followup.send("認証パネルを設置しました。", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data['custom_id'] == "start_verification":
            await interaction.response.defer(ephemeral=True, thinking=True)
            settings = load_settings()
            guild_settings = settings.get(str(interaction.guild_id))

            if not guild_settings:
                await interaction.followup.send("このサーバーでは認証が設定されていません。管理者に連絡してください。", ephemeral=True)
                return

            # キャプチャ生成
            captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            image_captcha = ImageCaptcha(width=200, height=75)
            image_data = image_captcha.generate(captcha_text)
            image_file = discord.File(io.BytesIO(image_data.read()), filename="captcha.png")

            # ユーザーにDMでキャプチャを送信
            try:
                await interaction.user.send("以下の画像に表示されている文字を入力してください。", file=image_file)
                await interaction.user.send("パスワード認証に進むには、このDMでキャプチャの文字を返信してください。")
            except discord.Forbidden:
                await interaction.followup.send("DMを送信できませんでした。プライバシー設定を確認し、BotからのDMを許可してください。", ephemeral=True)
                return

            # キャプチャの正解を一時的に保存
            # ユーザーIDをキーとして、キャプチャテキストとパスワード認証フラグを保存
            server_settings[str(interaction.user.id)] = {
                'captcha_text': captcha_text,
                'awaiting_password': False, # パスワード認証待ちかどうか
                'guild_id': interaction.guild_id
            }
            save_settings(server_settings)

            await interaction.followup.send("DMを送信しました。DMを確認して認証を完了してください。", ephemeral=True)

    await bot.process_commands(interaction)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: # Bot自身のメッセージは無視
        return

    # DMでの認証処理
    if isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        user_data = server_settings.get(user_id)

        if user_data and user_data.get('guild_id'):
            guild_id = user_data['guild_id']
            guild = bot.get_guild(guild_id)
            if not guild:
                await message.channel.send("認証元のサーバーが見つかりません。再度認証を開始してください。")
                del server_settings[user_id]
                save_settings(server_settings)
                return

            member = guild.get_member(message.author.id)
            if not member:
                await message.channel.send("認証元のサーバーにあなたが見つかりません。再度認証を開始してください。")
                del server_settings[user_id]
                save_settings(server_settings)
                return

            guild_settings = load_settings().get(str(guild_id))
            if not guild_settings:
                await message.channel.send("このサーバーでは認証が設定されていません。管理者に連絡してください。")
                del server_settings[user_id]
                save_settings(server_settings)
                return

            verified_role_id = guild_settings.get('verified_role_id')
            if not verified_role_id:
                await message.channel.send("認証ロールが設定されていません。管理者に連絡してください。")
                del server_settings[user_id]
                save_settings(server_settings)
                return

            if not user_data.get('awaiting_password'): # キャプチャ認証待ち
                if message.content.upper() == user_data['captcha_text'].upper():
                    user_data['awaiting_password'] = True
                    server_settings[user_id] = user_data
                    save_settings(server_settings)
                    await message.channel.send("キャプチャ認証に成功しました！\n次に、管理者が `/password` コマンドで生成したパスワードを入力してください。")
                else:
                    await message.channel.send("キャプチャ認証に失敗しました。もう一度 `/verify` コマンドからやり直してください。")
                    del server_settings[user_id]
                    save_settings(server_settings)
            else: # パスワード認証待ち
                if message.content == current_verify_password.get(guild_id):
                    role = guild.get_role(verified_role_id)
                    if role:
                        try:
                            await member.add_roles(role)
                            await message.channel.send(f"認証に成功しました！ {role.name} ロールが付与されました。")
                            del server_settings[user_id]
                            save_settings(server_settings)
                            # パスワード認証成功後、パスワードをクリア
                            if guild_id in current_verify_password:
                                del current_verify_password[guild_id]
                        except discord.Forbidden:
                            await message.channel.send("Botにロールを付与する権限がありません。Botのロールが対象ロールより上位にあるか確認してください。")
                            del server_settings[user_id]
                            save_settings(server_settings)
                        except Exception as e:
                            await message.channel.send(f"ロール付与中にエラーが発生しました: {e}")
                            del server_settings[user_id]
                            save_settings(server_settings)
                    else:
                        await message.channel.send("設定された認証ロールが見つかりません。管理者に連絡してください。")
                        del server_settings[user_id]
                        save_settings(server_settings)
                else:
                    await message.channel.send("パスワードが間違っています。もう一度 `/verify` コマンドからやり直してください。")
                    del server_settings[user_id]
                    save_settings(server_settings)

    await bot.process_commands(message)

# ウェブ検索コマンド
@bot.tree.command(name="search", description="ウェブ検索を行います。")
@app_commands.describe(query="検索キーワード")
async def search_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=False)
    try:
        # Google Custom Search APIを使用する代わりに、DuckDuckGoのLite版をスクレイピング
        # より堅牢な実装にはAPIキーが必要
        url = f"https://lite.duckduckgo.com/lite/?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる

        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('a', class_='result-link', limit=5)

        if not results:
            await interaction.followup.send("検索結果が見つかりませんでした。", ephemeral=False)
            return

        embed = discord.Embed(title=f"'{query}' の検索結果", color=discord.Color.blue())
        for i, result in enumerate(results):
            title = result.text.strip()
            link = result['href']
            embed.add_field(name=f"{i+1}. {title}", value=f"[リンク]({link})", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=False)

    except requests.exceptions.RequestException as e:
        await interaction.followup.send(f"ウェブ検索中にエラーが発生しました: {e}", ephemeral=False)
    except Exception as e:
        await interaction.followup.send(f"予期せぬエラーが発生しました: {e}", ephemeral=False)

# 画像検索コマンド
@bot.tree.command(name="image_search", description="画像検索を行います。")
@app_commands.describe(query="画像検索キーワード")
async def image_search_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=False)
    try:
        # Google画像検索への直接リンクを生成
        search_url = f"https://www.google.com/search?tbm=isch&q={query}"
        embed = discord.Embed(title=f"'{query}' の画像検索結果", url=search_url, color=discord.Color.blue())
        embed.set_footer(text="リンクをクリックして画像検索結果をご覧ください。")
        await interaction.followup.send(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.followup.send(f"画像検索中にエラーが発生しました: {e}", ephemeral=False)

# 歌詞検索コマンド
@bot.tree.command(name="lyrics", description="歌詞を検索します。")
@app_commands.describe(query="曲名またはアーティスト名")
async def lyrics_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=False)
    try:
        # 歌詞検索サイトへの直接リンクを生成 (例: Uta-Net)
        search_url = f"https://www.uta-net.com/search/?keyword={query}&commit=検索"
        embed = discord.Embed(title=f"'{query}' の歌詞検索結果", url=search_url, color=discord.Color.blue())
        embed.set_footer(text="リンクをクリックして歌詞検索結果をご覧ください。")
        await interaction.followup.send(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.followup.send(f"歌詞検索中にエラーが発生しました: {e}", ephemeral=False)

if __name__ == '__main__':
    # Flaskサーバーを別スレッドで起動
    Thread(target=run_flask).start()
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
