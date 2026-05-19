import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("8615393496:AAGtjfoPfIm5PDh1Oc7wB9gpi2w13fXGm34", "")

# ── helpers ──────────────────────────────────────────────────────────────────

def get_formats(url: str):
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info, info.get("formats", [])

def build_keyboard(url, formats):
    buttons = []
    buttons.append([InlineKeyboardButton(
        "🏆 Best Video + Audio (Auto)", callback_data=f"dl|{url}|best|video")])
    seen, res_map = set(), {}
    for f in reversed(formats):
        h, ext, fid = f.get("height"), f.get("ext","?"), f.get("format_id")
        if f.get("vcodec","none") != "none" and h and fid not in seen:
            seen.add(fid)
            lbl = f"🎬 {h}p  ({ext.upper()})"
            if lbl not in res_map:
                res_map[lbl] = [InlineKeyboardButton(lbl, callback_data=f"dl|{url}|{fid}|video")]
    for row in list(res_map.values())[:6]:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🎵 Audio – MP3  (320kbps)", callback_data=f"dl|{url}|bestaudio|mp3")])
    buttons.append([InlineKeyboardButton("🎵 Audio – M4A  (best)",    callback_data=f"dl|{url}|bestaudio|m4a")])
    buttons.append([InlineKeyboardButton("🎵 Audio – OPUS (best)",    callback_data=f"dl|{url}|bestaudio|opus")])
    return InlineKeyboardMarkup(buttons)

async def download_send(update, context, url, fmt_id, mode):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_message(chat_id, "⏳ Downloading… please wait")
    out = f"/tmp/tgbot_{chat_id}"
    os.makedirs(out, exist_ok=True)
    try:
        if mode in ("mp3","m4a","opus"):
            opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{out}/%(title)s.%(ext)s",
                "postprocessors": [{"key":"FFmpegExtractAudio","preferredcodec":mode,
                                    "preferredquality":"320" if mode=="mp3" else "0"}],
                "quiet": True,
            }
        else:
            fmt = "bestvideo+bestaudio/best" if fmt_id == "best" else f"{fmt_id}+bestaudio/{fmt_id}"
            opts = {"format":fmt,"outtmpl":f"{out}/%(title)s.%(ext)s",
                    "merge_output_format":"mp4","quiet":True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        files = os.listdir(out)
        if not files:
            await msg.edit_text("❌ Download failed."); return
        fp = os.path.join(out, files[0])
        mb = os.path.getsize(fp) / 1024 / 1024
        await msg.edit_text(f"📤 Uploading ({mb:.1f} MB)…")
        if mode in ("mp3","m4a","opus"):
            await context.bot.send_audio(chat_id, audio=open(fp,"rb"), caption="🎵 @YourBot")
        else:
            await context.bot.send_video(chat_id, video=open(fp,"rb"),
                                         supports_streaming=True, caption="🎬 @YourBot")
        await msg.delete()
        for f in os.listdir(out): os.remove(os.path.join(out,f))
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:300]}")

# ── handlers ─────────────────────────────────────────────────────────────────

async def start(update, context):
    await update.message.reply_text(
        "👋 *Welcome!* Send me a YouTube or Instagram link\n"
        "and I'll show you all download options 🎉",
        parse_mode="Markdown")

async def handle_url(update, context):
    url = update.message.text.strip()
    msg = await update.message.reply_text("🔍 Fetching formats…")
    try:
        info, fmts = get_formats(url)
        title = info.get("title","Video")
        dur   = info.get("duration",0)
        m,s   = divmod(dur,60)
        kbd   = build_keyboard(url, fmts)
        await msg.edit_text(f"📹 *{title}*\n⏱ {m}m {s}s\n\nChoose format:",
                            reply_markup=kbd, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Could not read link.\n{str(e)[:200]}")

async def button_cb(update, context):
    q = update.callback_query
    await q.answer("Starting…")
    try:
        _, url, fmt_id, mode = q.data.split("|",3)
    except:
        await q.edit_message_text("❌ Bad selection."); return
    await q.edit_message_text(f"⬇️ Downloading in format: {fmt_id}")
    await download_send(update, context, url, fmt_id, mode)

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_cb))
    print("🤖 Bot running…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
