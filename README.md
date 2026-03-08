# 📰 News Bot

A Discord bot that generates **news-style cards and newsletters automatically** using images.

Users can create news posts and the bot converts them into **visual news cards**.

---

## ✨ Features

- 📰 Generate news cards
- 🖼️ Automatic image generation
- 🧾 Newsletter-style layout
- 🏷️ Categories for news
- 👤 Owner / author display
- ⚡ Slash command support

---

## 📸 Example

The bot generates a news card like this:

[ Headline ] | Image  
Summary  
Category • Author

---

## ⚙️ Commands

### /bignews
Create a large news card.

Parameters:

- **headline** – News headline
- **summary** – Description of the news
- **category** – News category
- **owner** – Author (optional)
- **image** – Image URL (optional)

Example:

```
/bignews headline:Robbery downtown summary:Police are investigating... category:Crime
```

---

## 🛠️ Installation

Clone the repository:

```
git clone https://github.com/YOURNAME/news-bot.git
cd news-bot
```

Create virtual environment:

```
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```
pip install -r requirements.txt
```

---

## 🔑 Setup

Create a `.env` file:

```
DISCORD_TOKEN=your_bot_token
```

Run the bot:

```
python bot.py
```

---

## 📦 Requirements

- Python 3.10+
- discord.py
- Pillow (PIL)

---

## 🚀 Future Plans

- News database
- Multiple templates
- Auto-generated images
- Top.gg integration
- Website dashboard

---

## 📜 License

MIT License