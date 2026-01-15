import os
import requests
import instaloader
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ===============================
# ENV VARIABLES (Railway se aayengi)
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID missing in environment variables")

# ===============================
# CLEAR WEBHOOK (IMPORTANT FIX)
# ===============================
async def clear_webhook():
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)

asyncio.run(clear_webhook())

# ===============================
# DOWNLOAD FOLDER
# ===============================
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ===============================
# INSTALOADER SETUP
# ===============================
loader = instaloader.Instaloader(
    download_videos=False,
    save_metadata=False,
    compress_json=False,
    post_metadata_txt_pattern=""
)

# ===============================
# REEL DOWNLOAD FUNCTION
# ===============================
def download_reel(insta_url: str):
    shortcode = insta_url.rstrip("/").split("/")[-1]

    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    video_path = os.path.join(DOWNLOAD_DIR, f"{shortcode}.mp4")

    loader.download_pic(
        filename=video_path.replace(".mp4", ""),
        url=post.video_url,
        mtime=post.date
    )

    # instaloader quirk fix
    jpg_path = video_path.replace(".mp4", "") + ".jpg"
    if not os.path.exists(video_path) and os.path.exists(jpg_path):
        os.rename(jpg_path, video_path)

    caption = post.caption or ""

    final_caption = f"""{caption}

━━━━━━━━━━━━━━
🎥 Credit: @{post.owner_username}
🔁 Reposted via Telegram Bot
━━━━━━━━━━━━━━
"""

    return video_path, final_caption

# ===============================
# TELEGRAM UPLOAD FUNCTION
# ===============================
def upload_to_telegram(video_path: str, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

    with open(video_path, "rb") as video:
        data = {
            "chat_id": CHAT_ID,
            "caption": caption
        }
        files = {
            "video": video
        }
        r = requests.post(url, data=data, files=files)

    if r.status_code != 200:
        raise RuntimeError(f"Telegram upload failed: {r.text}")

# ===============================
# MESSAGE HANDLER
# ===============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        await update.message.reply_text(
            "❌ Please send a valid *Instagram Reel URL*",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏬ Reel downloading, please wait...")

    try:
        video_path, caption = download_reel(text)
        upload_to_telegram(video_path, caption)

        await update.message.reply_text("✅ Reel uploaded here with caption")

        # cleanup (Railway disk save)
        if os.path.exists(video_path):
            os.remove(video_path)

    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n`{e}`", parse_mode="Markdown")

# ===============================
# BOT START
# ===============================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
