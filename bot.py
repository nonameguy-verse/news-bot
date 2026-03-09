import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
from git import Repo

# ===== CONFIG =====
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
NEWS_REPO = "https://github.com/nonameguy-verse/news-storage"
POSTED_DB = "./posted.json"

# Ensure news folder exists
if not os.path.exists(NEWS_REPO):
    fallback = "./news"
    if os.path.exists(fallback):
        NEWS_REPO = fallback
    else:
        os.makedirs(NEWS_REPO)

intents = discord.Intents.default()
intents.message_content = True  # Still useful for reading messages if needed
bot = commands.Bot(command_prefix="!", intents=intents)  # Prefix not used, but required

# ===== POSTED NEWS TRACKING =====
def load_posted():
    if os.path.exists(POSTED_DB):
        with open(POSTED_DB, "r") as f:
            return json.load(f)
    return {}

def save_posted(posted):
    with open(POSTED_DB, "w") as f:
        json.dump(posted, f, indent=2)

posted_news = load_posted()

# ===== UTILITY FUNCTIONS =====
def load_news():
    news_list = []
    for filename in os.listdir(NEWS_REPO):
        if filename.endswith(".json"):
            with open(os.path.join(NEWS_REPO, filename), "r") as f:
                news_list.append(json.load(f))
    return news_list

def get_random_news(category=None):
    today = datetime.utcnow()
    eligible = []
    for news in load_news():
        news_id = news["id"]
        last_posted = posted_news.get(news_id)
        if last_posted:
            last_posted_dt = datetime.fromisoformat(last_posted)
            if (today - last_posted_dt).days < 7:
                continue
        if category and news.get("category") != category:
            continue
        eligible.append(news)
    if not eligible:
        return None
    chosen = random.choice(eligible)
    posted_news[chosen["id"]] = today.isoformat()
    save_posted(posted_news)
    return chosen

def is_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator
    
async def post_news(channel, news):
    message = f"""
📰 **Daily Emerald News**

**Headline:** {news['headline']}

**Summary:** {news['summary']}

*Source: {news['source']}*
"""
    await channel.send(message)

    video_path = news.get("video")
    if video_path and os.path.exists(video_path):
        await channel.send(file=discord.File(video_path))

# ===== CONFIGURATION STORAGE =====
configured_channels = {}  # guild_id: channel_id

# ===== SLASH COMMANDS =====
@app_commands.command(name="publish", description="Create a news entry")
@app_commands.check(is_admin)
async def publish(interaction: discord.Interaction, title: str, description: str):

    news_id = f"news-{random.randint(1000,9999)}"

    news_data = {
        "title": title,
        "description": description,
        "author": str(interaction.user),
        "date": datetime.utcnow().isoformat()
    }

    path = f"{NEWS_REPO}/{news_id}.json"

    with open(path, "w") as f:
        json.dump(news_data, f, indent=4)

    await interaction.response.send_message(f"News saved as {news_id}")

@app_commands.command(name="syncnews", description="Push news repo to remote")
@app_commands.check(is_admin)
async def syncnews(interaction: discord.Interaction):

    os.system(f"cd {NEWS_REPO} && git add .")
    os.system(f"cd {NEWS_REPO} && git commit -m 'news update'")
    os.system(f"cd {NEWS_REPO} && git push")

    await interaction.response.send_message("News repo synced.")
@app_commands.command(name="pullnews", description="Pull latest news repo")

@app_commands.check(is_admin)
async def pullnews(interaction: discord.Interaction):

    os.system(f"cd {NEWS_REPO} && git pull")

    await interaction.response.send_message("News repo updated.")

@bot.tree.command(name="setup", description="Configure news channel or start daily news")
@app_commands.describe(option="Choose 'channel' to set this channel, or 'daily' to start auto-posting")
async def setup(interaction: discord.Interaction, option: str):
    guild_id = str(interaction.guild_id)
    if option.lower() == "channel":
        configured_channels[guild_id] = interaction.channel_id
        await interaction.response.send_message(f"Channel set for news: {interaction.channel.mention}")
    elif option.lower() == "daily":
        if not daily_news.is_running():
            daily_news.start()
            await interaction.response.send_message("Daily news posting started!")
        else:
            await interaction.response.send_message("Daily news is already running.")
    else:
        await interaction.response.send_message("Invalid option. Use `channel` or `daily`.")

@bot.tree.command(name="curious", description="Get a random curious news article")
async def curious(interaction: discord.Interaction):
    news = get_random_news(category="curious")
    if not news:
        await interaction.response.send_message("No news to show in 'curious'.")
    else:
        await interaction.response.defer()  # In case posting takes time
        await post_news(interaction.channel, news)

@bot.tree.command(name="law", description="Get a random law-related news article")
async def law(interaction: discord.Interaction):
    news = get_random_news(category="law")
    if not news:
        await interaction.response.send_message("No law-related news to show.")
    else:
        await interaction.response.defer()
        await post_news(interaction.channel, news)

@bot.tree.command(name="current", description="Show a news article by ID")
@app_commands.describe(news_id="ID of the news to display")
async def current(interaction: discord.Interaction, news_id: str):
    # Pull latest from the remote repo
    try:
        repo = Repo(NEWS_REPO)
        origin = repo.remote(name='origin')
        origin.pull()
    except Exception as e:
        print(f"Failed to pull news repo: {e}")

    # Path to the news JSON
    filepath = os.path.join(NEWS_REPO, f"{news_id}.json")
    
    if not os.path.exists(filepath):
        await interaction.response.send_message(f"News {news_id} not found.", ephemeral=True)
        return
    
    # Load the news JSON
    with open(filepath, "r") as f:
        news = json.load(f)
    
    msg = f"**{news.get('headline', news.get('title', 'No title'))}**\n" \
          f"{news.get('summary', news.get('description', 'No description'))}\n" \
          f"By {news.get('owner', news.get('author', 'Unknown'))} at {news.get('date', 'Unknown')}"
    
    await interaction.response.send_message(msg)

@bot.tree.command(name="createnews", description="Create a new news article (optionally with video/image)")
@app_commands.describe(
    headline="Headline of the news",
    summary="Short summary",
    category="Category (e.g., curious, law, general)",
    owner="Optional owner name (defaults to your username)",
    attachment="Optional video/image file"
)
async def createnews(
    interaction: discord.Interaction,
    headline: str,
    summary: str,
    category: str,
    owner: str = None,
    attachment: discord.Attachment = None
):
    if owner is None:
        owner = interaction.user.name

    # Generate a unique ID
    news_id = f"news-{random.randint(1000,9999)}"

    # Prepare news dictionary
    news_item = {
        "id": news_id,
        "headline": headline,
        "summary": summary,
        "category": category,
        "owner": owner,
        "source": f"Created by {owner}",
    }

    # Handle file attachment if provided
    video_path = None
    if attachment:
        # Define allowed file types (images/videos)
        allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.avi')
        if any(attachment.filename.lower().endswith(ext) for ext in allowed_extensions):
            # Save the file locally
            video_path = os.path.join(NEWS_REPO, f"{news_id}_{attachment.filename}")
            await attachment.save(video_path)
            news_item["video"] = video_path
        else:
            await interaction.response.send_message("Invalid file type. Please upload an image or video.", ephemeral=True)
            return

    # Save news JSON
    filepath = os.path.join(NEWS_REPO, f"{news_id}.json")
    with open(filepath, "w") as f:
        json.dump(news_item, f, indent=2)

    # Respond with confirmation
    message = f"""
📰 **News Created**

**Headline:** {headline}

**Summary:** {summary}

*Category: {category}*
*Source: Created by {owner}*
*ID: `{news_id}`*
"""
    await interaction.response.send_message(message)

    # If there was an attachment, also post it in the channel
    if video_path:
        await interaction.channel.send(file=discord.File(video_path))

@bot.tree.command(name="bignews", description="Create a visual news card")
@app_commands.describe(
    headline="Headline of the news",
    summary="Short summary",
    category="Category",
    owner="Optional owner name (defaults to your username)",
    photo="Optional photo (person, suspect, victim, etc.)"
)
async def bignews(
    interaction: discord.Interaction,
    headline: str,
    summary: str,
    category: str,
    owner: str = None,
    photo: discord.Attachment = None
):
    owner = owner or interaction.user.name

    news_id = f"news-{random.randint(1000,9999)}"
    news_item = {
        "id": news_id,
        "headline": headline,
        "summary": summary,
        "category": category,
        "owner": owner,
        "source": f"Created by {owner}"
    }

    # Save photo if provided
    image_path = None
    if photo:
        ext = os.path.splitext(photo.filename)[1]
        image_path = os.path.join(NEWS_REPO, f"{news_id}{ext}")
        await photo.save(image_path)
        news_item["photo"] = image_path

    # Save JSON
    filepath = os.path.join(NEWS_REPO, f"{news_id}.json")
    with open(filepath, "w") as f:
        json.dump(news_item, f, indent=2)

    # Generate card
    width, height = 900, 520
    photo_width = 260

    img = Image.new("RGB", (width, height), (35,35,35))
    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    headline_font = ImageFont.truetype(font_path, 40)
    summary_font = ImageFont.truetype(font_path, 24)
    footer_font = ImageFont.truetype(font_path, 22)

    # HEADLINE
    headline_lines = textwrap.wrap(headline, width=32)

    y = 20
    for line in headline_lines:
        draw.text((20,y), line, fill="white", font=headline_font)
        y += 45

    y += 10

    # SUMMARY
    summary_lines = textwrap.wrap(summary, width=45)

    for line in summary_lines:
        draw.text((20,y), line, fill="white", font=summary_font)
        y += 30
        if y > height - 120:
            break

    # PHOTO
    if image_path and os.path.exists(image_path):
        with Image.open(image_path) as p:
            p = p.convert("RGB")
            p = p.resize((photo_width,260))
            img.paste(p,(width-photo_width-20,120))

    # CATEGORY
    bbox = draw.textbbox((0,0), category, font=footer_font)
    cat_w = bbox[2]-bbox[0]
    cat_h = bbox[3]-bbox[1]

    draw.rectangle([20,height-70,30+cat_w,height-70+cat_h], fill=(200,70,70))
    draw.text((25,height-70), category, fill="white", font=footer_font)

    # OWNER
    owner_text = f"Owner: {owner}"
    bbox = draw.textbbox((0,0), owner_text, font=footer_font)
    owner_w = bbox[2]-bbox[0]

    draw.text((width-owner_w-20,height-70), owner_text, fill="white", font=footer_font)
    # Draw category
    bbox = draw.textbbox((0, 0), category, font=footer_font)
    cat_width = bbox[2] - bbox[0]
    cat_height = bbox[3] - bbox[1]
    draw.rectangle([20, y + 10, 30 + cat_width, y + 10 + cat_height], fill=(200,70,70))
    draw.text((25, y + 10), category, font=footer_font, fill="white")

    # Owner
    draw.text((20, height - 40), f"Owner: {owner}", font=footer_font, fill="white")

    card_filename = os.path.join(NEWS_REPO, f"{news_id}_card.png")
    img.save(card_filename)

    await interaction.response.send_message(file=discord.File(card_filename))

@bot.tree.command(name="help", description="Show all news bot commands")
async def help_cmd(interaction: discord.Interaction):
    help_text = """
📌 **News Bot Commands**

/setup <channel|daily> — Set this channel for news or start daily news  
/curious — Get a random curious news article  
/law — Get a random law-related news article  
/current <news_id> — Show news by ID  
/createnews — Create a new text-based news article  
/bignews — Create a news article with a newsletter image  
/help — Show this message
"""
    await interaction.response.send_message(help_text, ephemeral=True)

# ===== AUTOMATIC POSTING TASKS =====
@tasks.loop(hours=16)  # Adjust as needed
async def auto_news():
    for guild_id, channel_id in configured_channels.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        news = get_random_news()
        if news:
            await post_news(channel, news)
        else:
            await channel.send("No news to show today.")

@tasks.loop(hours=24)  # For daily news
async def daily_news():
    for guild_id, channel_id in configured_channels.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        news = get_random_news()
        if news:
            await post_news(channel, news)
        else:
            await channel.send("No news to show today.")

# ===== BOT EVENTS =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    if not auto_news.is_running():
        auto_news.start()


# ===== RUN BOT =====
if __name__ == "__main__":
    bot.run(TOKEN)
