import os
import requests
import instaloader
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ===============================
# ENV VARIABLES
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID missing")

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
# REEL DOWNLOAD
# ===============================
def download_reel(insta_url):
    shortcode = insta_url.rstrip("/").split("/")[-1]
    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    video_path = os.path.join(DOWNLOAD_DIR, f"{shortcode}.mp4")

    loader.download_pic(
        filename=video_path.replace(".mp4", ""),
        url=post.video_url,
        mtime=post.date
    )

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
# TELEGRAM UPLOAD
# ===============================
def upload_to_telegram(video_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

    with open(video_path, "rb") as video:
        r = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"video": video},
            timeout=120
        )

    if r.status_code != 200:
        raise RuntimeError(r.text)

# ===============================
# MESSAGE HANDLER
# ===============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        await update.message.reply_text("❌ Instagram Reel URL bhejo")
        return

    await update.message.reply_text("⏬ Reel download ho rahi hai...")

    try:
        video_path, caption = download_reel(text)
        upload_to_telegram(video_path, caption)

        await update.message.reply_text("✅ Reel yahin upload kar di gayi")

        if os.path.exists(video_path):
            os.remove(video_path)

    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n{e}")

# ===============================
# BOT START (SAFE WAY)
# ===============================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
