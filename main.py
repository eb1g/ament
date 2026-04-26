import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from captcha.image import ImageCaptcha
import random
import string
from datetime import timedelta
import json
import requests
from bs4 import BeautifulSoup
import urllib.parse

# --- Data Management ---
DATA_FILE = "/home/ubuntu/data/guild_settings.json"

def load_settings():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# --- Global State ---
current_strong_password = "NotSetYet"

# --- Verification View ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="認証を開始する", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global current_strong_password
        await interaction.response.send_message("DMで認証を開始しました。確認してください。", ephemeral=True)

        image = ImageCaptcha(width=280, height=90)
        captcha_text = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        image_path = f"captcha_{interaction.user.id}.png"
        image.write(captcha_text, image_path)

        try:
            await interaction.user.send("【ステップ1: 画像認証】\n以下の画像に表示されている文字を入力してください。")
            await interaction.user.send(file=discord.File(image_path))

            def check(m):
                return m.author == interaction.user and m.channel == interaction.user.dm_channel

            try:
                user_response = await bot.wait_for("message", check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await interaction.user.send("時間切れです。もう一度ボタンを押してやり直してください。")
                return

            if user_response.content.upper() != captcha_text:
                await interaction.user.send("画像認証に失敗しました。もう一度ボタンを押してやり直してください。")
                return

            await interaction.user.send("【ステップ2: パスワード認証】\nサーバーで生成された最新の「最強パスワード」を入力してください。")
            
            try:
                pass_response = await bot.wait_for("message", check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await interaction.user.send("時間切れです。もう一度ボタンを押してやり直してください。")
                return

            if pass_response.content == current_strong_password:
                settings = load_settings()
                guild_id = str(interaction.guild_id)
                role_id = settings.get(guild_id, {}).get("role_id")
                
                if role_id:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        await interaction.user.add_roles(role)
                        await interaction.user.send(f"🎉 認証に成功しました！ {role.name} ロールが付与されました。")
                    else:
                        await interaction.user.send("❌ 設定されたロールが見つかりませんでした。管理者に連絡してください。")
                else:
                    await interaction.user.send("❌ このサーバーでは認証ロールが設定されていません。")
            else:
                await interaction.user.send("❌ パスワードが正しくありません。最新のパスワードを確認してください。")

        except discord.errors.Forbidden:
            pass
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

# --- Bot Setup ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.moderation = True
        super().__init__(command_prefix='/', intents=intents)

    async def update_status(self):
        guild_count = len(self.guilds)
        await self.change_presence(activity=discord.Game(name=f"{guild_count}個のサーバーで稼働中"))

    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.update_status()

@bot.event
async def on_guild_join(guild):
    await bot.update_status()

@bot.event
async def on_guild_remove(guild):
    await bot.update_status()

# --- Management Commands (Admin Only) ---

@bot.tree.command(name="kick", description="メンバーをキックします(管理者のみ)。")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member="キックするメンバー", reason="理由")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "理由なし"):
    await interaction.response.defer()
    try:
        await member.kick(reason=reason)
        await interaction.followup.send(f"{member.mention} をキックしました。理由: {reason}")
    except discord.Forbidden:
        await interaction.followup.send("権限が不足しているか、対象のロール順位がBotより高いため操作できません。")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}")

@bot.tree.command(name="ban", description="メンバーをBANします(管理者のみ)。")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member="BANするメンバー", reason="理由")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "理由なし"):
    await interaction.response.defer()
    try:
        await member.ban(reason=reason)
        await interaction.followup.send(f"{member.mention} をBANしました。理由: {reason}")
    except discord.Forbidden:
        await interaction.followup.send("権限が不足しているか、対象のロール順位がBotより高いため操作できません。")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}")

@bot.tree.command(name="timeout", description="メンバーをタイムアウトさせます(管理者のみ)。")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member="対象メンバー", minutes="時間（分）", reason="理由")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "理由なし"):
    await interaction.response.defer()
    try:
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.followup.send(f"{member.mention} を {minutes} 分間タイムアウトさせました。理由: {reason}")
    except discord.Forbidden:
        await interaction.followup.send("権限が不足しているか、対象のロール順位がBotより高いため操作できません。")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}")

@bot.tree.command(name="unmute", description="メンバーのタイムアウトを解除します(管理者のみ)。")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member="対象メンバー")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()
    try:
        await member.timeout(None)
        await interaction.followup.send(f"{member.mention} のタイムアウトを解除しました。")
    except discord.Forbidden:
        await interaction.followup.send("権限が不足しているか、対象のロール順位がBotより高いため操作できません。")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}")

@bot.tree.command(name="clear", description="メッセージを一括削除します(管理者のみ)。")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(amount="削除するメッセージ数")
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"{len(deleted)} 件のメッセージを削除しました。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)

# --- Search Commands ---

@bot.tree.command(name="search", description="ウェブ検索を行います。")
@app_commands.describe(query="検索キーワード")
async def search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        for g in soup.find_all('div', class_='tF2Cxc'):
            title = g.find('h3').text if g.find('h3') else "No Title"
            link = g.find('a')['href'] if g.find('a') else "No Link"
            if title and link:
                results.append(f"**[{title}]({link})**")
            if len(results) >= 5: break
            
        if not results:
            await interaction.followup.send("検索結果が見つかりませんでした。")
        else:
            embed = discord.Embed(title=f"🔍 「{query}」の検索結果", description="\n\n".join(results), color=discord.Color.blue())
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"検索中にエラーが発生しました: {e}")

@bot.tree.command(name="image_search", description="画像検索を行います。")
@app_commands.describe(query="検索キーワード")
async def image_search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        # DuckDuckGoの画像検索を利用（簡易版）
        search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}&iax=images&ia=images"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers)
        # 実際にはAPIやより複雑なスクレイピングが必要ですが、ここでは簡易的なリンク提供を行います
        await interaction.followup.send(f"🖼️ 「{query}」の画像検索結果はこちら:\nhttps://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch")
    except Exception as e:
        await interaction.followup.send(f"画像検索中にエラーが発生しました: {e}")

@bot.tree.command(name="lyrics", description="歌詞を検索します。")
@app_commands.describe(query="曲名・アーティスト名")
async def lyrics(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query + ' 歌詞')}"
        await interaction.followup.send(f"🎵 「{query}」の歌詞検索結果はこちら:\n{search_url}")
    except Exception as e:
        await interaction.followup.send(f"歌詞検索中にエラーが発生しました: {e}")

# --- Password & Verification Commands ---

@bot.tree.command(name="password", description="認証の時に使います(隠し)。")
async def password(interaction: discord.Interaction):
    global current_strong_password
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    current_strong_password = "".join(random.choices(characters, k=12))
    
    embed = discord.Embed(
        title="🔑 サーバー認証用パスワード",
        description=f"新しい認証パスワードが生成されました：\n`{current_strong_password}`\n\nこのパスワードは認証の際に必要になります。",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="genpass", description="アカウント作成用の最強パスワードを生成します(隠し)。")
@app_commands.describe(length="パスワードの長さ (8-32)", include_symbols="記号を含めるか")
async def genpass(interaction: discord.Interaction, length: int = 16, include_symbols: bool = True):
    if length < 8 or length > 32:
        return await interaction.response.send_message("長さは8文字から32文字の間で指定してください。", ephemeral=True)
    
    chars = string.ascii_letters + string.digits
    if include_symbols:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    new_pass = "".join(random.choices(chars, k=length))
    
    embed = discord.Embed(
        title="🛡️ アカウント作成用 最強パスワード",
        description=f"あなた専用の強力なパスワードを生成しました：\n\n`{new_pass}`\n\n**注意:** このメッセージはあなたにしか見えません。安全な場所に保管してください。",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="verify", description="認証パネルを設置し、ロールを設定します(管理者のみ)。")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(role="認証後に付与するロール")
async def verify(interaction: discord.Interaction, role: discord.Role):
    settings = load_settings()
    settings[str(interaction.guild_id)] = {"role_id": str(role.id)}
    save_settings(settings)
    
    embed = discord.Embed(
        title="✅ サーバー認証",
        description=f"このサーバーに参加するには認証が必要です。\n下のボタンを押して認証を開始してください。\n\n付与されるロール: {role.mention}",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message("認証パネルを設置しました。", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

# --- Help Command ---

@bot.tree.command(name="help", description="コマンド一覧を表示します。")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ サーバー管理Bot コマンド一覧",
        description="スラッシュコマンド（/）を入力して使用してください。",
        color=discord.Color.red()
    )
    embed.add_field(name="🛠️ 管理コマンド (管理者のみ)", value=(
        "`/verify role:[ロール]` - 認証パネルを設置します。\n"
        "`/kick [メンバー] [理由]` - メンバーをキックします。\n"
        "`/ban [メンバー] [理由]` - メンバーをBANします。\n"
        "`/timeout [メンバー] [分] [理由]` - メンバーをタイムアウトさせます。\n"
        "`/unmute [メンバー]` - タイムアウトを解除します。\n"
        "`/clear [数]` - メッセージを一括削除します。"
    ), inline=False)
    embed.add_field(name="🔍 検索機能", value=(
        "`/search [キーワード]` - ウェブ検索を行います。\n"
        "`/image_search [キーワード]` - 画像検索を行います。\n"
        "`/lyrics [曲名]` - 歌詞を検索します。"
    ), inline=False)
    embed.add_field(name="🔐 セキュリティ・認証", value=(
        "`/password` - 認証の時に使います(隠し)。\n"
        "`/genpass [長さ] [記号]` - アカウント作成用の最強パスワードを生成します(隠し)。"
    ), inline=False)
    embed.add_field(name="ℹ️ その他", value=(
        "`/help` - このメッセージを表示します。"
    ), inline=False)
    await interaction.response.send_message(embed=embed)



if __name__ == '__main__':
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
