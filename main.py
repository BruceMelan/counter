from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import requests

# === SETUP ===
YOUTUBE_API_KEY = 'AIzaSyC3URfkGlm72SYyxX02yR2HO7V8mOzptl4'
PLAYLIST_ID = 'PLKrq5Qcx0-tiI06GCeQhXoH8kIeLiyQnc'
TELEGRAM_TOKEN = '8167723720:AAHbKr42Gts55ARUz2guzJQL4jH7YCARb4I'

# Store quiz answers temporarily
quiz_data = {}

# === YOUTUBE VIDEO DATA ===
def get_all_video_data():
    video_ids = []
    url = 'https://www.googleapis.com/youtube/v3/playlistItems'
    params = {
        'part': 'contentDetails',
        'playlistId': PLAYLIST_ID,
        'maxResults': 50,
        'key': YOUTUBE_API_KEY
    }

    while True:
        response = requests.get(url, params=params).json()
        for item in response['items']:
            video_ids.append(item['contentDetails']['videoId'])
        if 'nextPageToken' in response:
            params['pageToken'] = response['nextPageToken']
        else:
            break

    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        stats_url = 'https://www.googleapis.com/youtube/v3/videos'
        stats_params = {
            'part': 'snippet,statistics',
            'id': ','.join(batch),
            'key': YOUTUBE_API_KEY
        }
        stats_response = requests.get(stats_url, params=stats_params).json()
        for item in stats_response['items']:
            title = item['snippet']['title']
            video_id = item['id']
            views = int(item['statistics'].get('viewCount', 0))
            videos.append({'title': title, 'id': video_id, 'views': views})
    return videos

# === COMMANDS ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the YouTube Playlist Bot!\n\n"
        "Available commands:\n"
        "/views – Total views of your playlist\n"
        "/top5 – Most viewed videos\n"
        "/newest – 10 latest uploaded videos\n"
        "/random – Get a random video\n"
        "/quiz – Guess the view count (interactive)\n"
        "/feedback – Send feedback\n"
        "/quotes – Get a random quote 💬"
    )

async def views_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = get_all_video_data()
    total = sum(video['views'] for video in videos)
    await update.message.reply_text(f"📊 Total views: {total:,}")

async def top5_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = get_all_video_data()
    top = sorted(videos, key=lambda x: x['views'], reverse=True)[:5]
    msg = "🏆 Top 5 Videos:\n\n"
    for i, v in enumerate(top, start=1):
        link = f"https://youtu.be/{v['id']}"
        msg += f"{i}. [{v['title']}]({link}) — {v['views']:,} views\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def newest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = get_all_video_data()
    latest = videos[-10:][::-1]
    msg = "🆕 Newest 10 Videos:\n\n"
    for v in latest:
        link = f"https://youtu.be/{v['id']}"
        msg += f"- [{v['title']}]({link}) — {v['views']:,} views\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = get_all_video_data()
    v = random.choice(videos)
    url = f"https://youtu.be/{v['id']}"
    await update.message.reply_text(f"🎲 Random Pick:\n[{v['title']}]({url}) — {v['views']:,} views", parse_mode="Markdown")

# === QUIZ ===

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = get_all_video_data()
    v = random.choice(videos)
    correct_views = v['views']
    options = sorted(set([
        correct_views,
        correct_views + random.randint(1000, 5000),
        max(0, correct_views - random.randint(1000, 5000)),
        correct_views + random.randint(6000, 10000)
    ]))
    random.shuffle(options)

    keyboard = [[InlineKeyboardButton(f"{i+1}. {opt:,}", callback_data=str(opt))] for i, opt in enumerate(options)]
    reply_markup = InlineKeyboardMarkup(keyboard)

    quiz_data[update.effective_user.id] = {
        'correct': correct_views,
        'video_title': v['title'],
        'video_id': v['id']
    }

    await update.message.reply_text(
        f"❓ How many views does this video have?\n[{v['title']}](https://youtu.be/{v['id']})",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_quiz_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in quiz_data:
        await query.edit_message_text("❌ Quiz expired. Try again with /quiz.")
        return

    selected = int(query.data)
    correct = quiz_data[user_id]['correct']
    title = quiz_data[user_id]['video_title']
    video_id = quiz_data[user_id]['video_id']
    del quiz_data[user_id]

    if selected == correct:
        result = "✅ Correct!"
    else:
        result = "❌ Not quite."

    await query.edit_message_text(
        f"{result}\n[{title}](https://youtu.be/{video_id}) has *{correct:,}* views.",
        parse_mode="Markdown"
    )

# === FEEDBACK & QUOTES ===

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feedback = ' '.join(context.args)
    if not feedback:
        await update.message.reply_text("✏️ Please send your message after the command.\nExample:\n/feedback This bot is great!")
        return
    print(f"📝 Feedback from {update.effective_user.first_name}: {feedback}")
    await update.message.reply_text("✅ Thanks for your feedback!")

async def quotes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quotes = [
        "🎯 Consistency beats talent when talent doesn't show up.",
        "💡 Tip: Pin your best video to the top of your channel!",
        "📈 Growth = Patience + Action.",
        "🔥 Keep uploading. Keep improving. Keep going.",
        "🎵 Your next video could be the one that blows up."
    ]
    await update.message.reply_text(random.choice(quotes))

# === INIT BOT ===

print("✅ Bot is running...")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("views", views_command))
app.add_handler(CommandHandler("top5", top5_command))
app.add_handler(CommandHandler("newest", newest_command))
app.add_handler(CommandHandler("random", random_command))
app.add_handler(CommandHandler("quiz", quiz_command))
app.add_handler(CallbackQueryHandler(handle_quiz_response))
app.add_handler(CommandHandler("feedback", feedback_command))
app.add_handler(CommandHandler("quotes", quotes_command))

app.run_polling()
