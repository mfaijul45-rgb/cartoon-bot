import os
import asyncio
import requests
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! अपनी कहानी भेजिए, मैं उसका कार्टून वीडियो तैयार कर दूँगा।")

async def generate_cartoon_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_story = update.message.text
    status_msg = await update.message.reply_text("कहानी मिल गई है! वीडियो पर काम शुरू हो रहा है...")

    raw_scenes = [s.strip() for s in user_story.replace("\n", "।").split("।") if len(s.strip()) > 5]
    if not raw_scenes:
        raw_scenes = [user_story]

    video_clips = []
    temp_files = []

    try:
        total = len(raw_scenes)
        for idx, scene_text in enumerate(raw_scenes):
            await status_msg.edit_text(f"सीन {idx+1}/{total} तैयार हो रहा है...")

            audio_path = f"voice_{idx}.mp3"
            temp_files.append(audio_path)
            tts = edge_tts.Communicate(scene_text, "hi-IN-MadhurNeural")
            await tts.save(audio_path)

            img_path = f"scene_{idx}.jpg"
            temp_files.append(img_path)
            encoded_prompt = urllib.parse.quote(f"2D cartoon illustration, indian village story, {scene_text[:50]}")
            img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=854&height=480&nologo=true"

            success = False
            try:
                resp = requests.get(img_url, timeout=25)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    with open(img_path, "wb") as f:
                        f.write(resp.content)
                    with Image.open(img_path) as im:
                        im.convert("RGB").resize((854, 480)).save(img_path, "JPEG", quality=80)
                    success = True
            except Exception:
                success = False

            if not success:
                fallback_img = Image.new("RGB", (854, 480), color=(60, 130, 210))
                draw = ImageDraw.Draw(fallback_img)
                fallback_img.save(img_path, "JPEG")

            audio_clip = AudioFileClip(audio_path)
            clip = ImageClip(img_path).set_duration(audio_clip.duration).set_audio(audio_clip)
            video_clips.append(clip)

        await status_msg.edit_text("सारे सीन्स जोड़े जा रहे हैं, वीडियो बन रहा है...")
        final_video = concatenate_videoclips(video_clips, method="compose")
        output_file = "full_cartoon_story.mp4"
        temp_files.append(output_file)

        # कम मेमोरी (RAM) खपत के साथ तेज़ रेंडरिंग
        final_video.write_videofile(
            output_file,
            fps=12,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=1
        )

        with open(output_file, "rb") as v:
            await update.message.reply_video(video=v, caption="यह रहा आपका कार्टून वीडियो!")

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"त्रुटि: {e}")

    finally:
        for clip in video_clips:
            try:
                clip.close()
            except Exception:
                pass
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_cartoon_video))
    print("बॉट शुरू हो गया है...")
    app.run_polling()
