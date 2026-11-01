import os
import asyncio
import requests
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Render Port Binding Dummy Server
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! अपनी कहानी का प्रॉम्प्ट या नाम भेजिए, कार्टून वीडियो बन जाएगा।")

async def generate_cartoon_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("कहानी और आवाज़ तैयार की जा रही है...")

    try:
        # 1. हिंदी आवाज़ (Edge-TTS)
        tts = edge_tts.Communicate(user_prompt, "hi-IN-MadhurNeural")
        audio_path = "voice.mp3"
        await tts.save(audio_path)

        # 2. कार्टून इमेज बनाना
        encoded_prompt = urllib.parse.quote(f"2D cartoon style, {user_prompt}")
        img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=720&height=1280&nologo=true"
        img_response = requests.get(img_url)
        img_path = "scene.jpg"
        with open(img_path, "wb") as f:
            f.write(img_response.content)

        # 3. वीडियो कंपोज़िशन
        audio_clip = AudioFileClip(audio_path)
        video_clip = ImageClip(img_path).set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        output_video = "cartoon_output.mp4"
        video_clip.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac")

        # 4. वीडियो भेजना
        with open(output_video, "rb") as v:
            await update.message.reply_video(video=v, caption="यह रहा आपका कार्टून वीडियो!")

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"त्रुटि: {e}")

if __name__ == "__main__":
    # वेब सर्वर बैकग्राउंड में शुरू करना
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # टेलीग्राम बॉट शुरू करना
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_cartoon_video))
    print("बॉट शुरू हो गया है...")
    app.run_polling()
