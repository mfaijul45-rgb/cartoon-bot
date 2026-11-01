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
from PIL import Image

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
    await update.message.reply_text("नमस्ते! अपनी पूरी 10-12 मिनट की कहानी भेजिए। मैं उसके सारे सीन और आवाज़ जोड़कर पूरा लंबा वीडियो तैयार कर दूँगा।")

async def generate_cartoon_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_story = update.message.text
    status_msg = await update.message.reply_text("पूरी कहानी मिल गई है! दृश्यों (Scenes) और आवाज़ पर काम शुरू हो रहा है, कृपया इंतज़ार करें...")

    # कहानी को वाक्यों/सीन्स में बाँटना
    raw_scenes = [s.strip() for s in user_story.replace("\n", "।").split("।") if len(s.strip()) > 5]
    if not raw_scenes:
        raw_scenes = [user_story]

    video_clips = []
    temp_files = []

    try:
        total = len(raw_scenes)
        for idx, scene_text in enumerate(raw_scenes):
            await status_msg.edit_text(f"सीन {idx+1}/{total} तैयार हो रहा है...")

            # 1. सीन की हिंदी आवाज़
            audio_path = f"voice_{idx}.mp3"
            temp_files.append(audio_path)
            tts = edge_tts.Communicate(scene_text, "hi-IN-MadhurNeural")
            await tts.save(audio_path)

            # 2. सीन की कार्टून इमेज
            encoded_prompt = urllib.parse.quote(f"2D clean indian cartoon style, highly detailed animation, {scene_text[:100]}")
            img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true"
            img_path = f"scene_{idx}.jpg"
            temp_files.append(img_path)

            resp = requests.get(img_url)
            with open(img_path, "wb") as f:
                f.write(resp.content)

            # इमेज को पक्का JPG फॉर्मैट में सुरक्षित करना
            with Image.open(img_path) as im:
                im.convert("RGB").save(img_path, "JPEG")

            # 3. क्लिप बनाना
            audio_clip = AudioFileClip(audio_path)
            clip = ImageClip(img_path).set_duration(audio_clip.duration).set_audio(audio_clip)
            video_clips.append(clip)

        # 4. सारे सीन्स को एक साथ जोड़ना
        await status_msg.edit_text("सारे सीन्स को जोड़कर पूरी फ़िल्म रेंडर हो रही है...")
        final_video = concatenate_videoclips(video_clips, method="compose")
        output_file = "full_cartoon_story.mp4"
        temp_files.append(output_file)

        final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")

        # 5. वीडियो भेजना
        with open(output_file, "rb") as v:
            await update.message.reply_video(video=v, caption="यह रहा आपका पूरा कार्टून वीडियो!")

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"त्रुटि: {e}")

    finally:
        # Temp Files हटाना
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
