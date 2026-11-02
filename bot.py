import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from pydub import AudioSegment
from pydub.generators import Sine
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# यहाँ आपकी ElevenLabs की कॉपी की हुई Key पेस्ट कर दी गई है:
ELEVENLABS_API_KEY = "sk_bede3c8f043c1cac00645ed4e2a6746366ff288f3bd20174"

# Render/Webserver के लिए डमी हैंडलर
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Horror Audio Bot is Running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def generate_horror_bgm(duration_ms):
    sine_wave = Sine(70).to_audio_segment(duration=duration_ms)
    bgm = sine_wave - 18
    return bgm

async def generate_voice_elevenlabs(text, output_file):
    url = "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("भूतिया आवाज़ बॉट में स्वागत है! अपनी हॉरर कहानी भेजिए, मैं डरावनी आवाज़ और BGM के साथ ऑडियो बना दूँगा।")

async def handle_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    story_text = update.message.text
    msg = await update.message.reply_text("डरावनी आवाज़ बनाई जा रही है... कृपया इंतज़ार करें।")

    temp_voice = "temp_voice.mp3"
    final_output = "horror_story.mp3"

    try:
        success = await generate_voice_elevenlabs(story_text, temp_voice)
        if not success:
            await msg.edit_text("वॉइस बनाने में समस्या आई, कृपया बाद में प्रयास करें।")
            return

        voice_audio = AudioSegment.from_file(temp_voice)
        duration = len(voice_audio)
        bgm_audio = generate_horror_bgm(duration)

        mixed_audio = voice_audio.overlay(bgm_audio)
        mixed_audio.export(final_output, format="mp3")

        await msg.delete()
        await update.message.reply_audio(audio=open(final_output, "rb"), caption="ये रही आपकी हॉरर कहानी!")

    except Exception as e:
        await msg.edit_text(f"एरर आ गया: {e}")
    finally:
        for file in [temp_voice, final_output]:
            if os.path.exists(file):
                os.remove(file)

def main():
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_story))
    app.run_polling()

if __name__ == "__main__":
    main()
