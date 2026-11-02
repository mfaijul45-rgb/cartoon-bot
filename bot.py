import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from pydub import AudioSegment
from pydub.generators import Sine
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ELEVENLABS_API_KEY = "sk_bede3c8f043c1cac00645ed4e2a6746366ff288f3bd20174"

# अलग-अलग किरदारों की ElevenLabs Voice IDs
VOICE_MAP = {
    "narrator": "pNInz6obpgDQGcFmaJgB",  # Adam - गंभीर नैरेटर आवाज़
    "boy": "ErXwobaYiN019PkySvjV",       # Antoni - नौजवान/लड़का आवाज़
    "ghost": "VR6AewLTigWG4xSOukaG",     # Arnold - भारी, डरावनी आवाज़
}

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Multi-Character Horror Bot is Live!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def generate_horror_bgm(duration_ms):
    sine_wave = Sine(65).to_audio_segment(duration=duration_ms)
    return sine_wave - 20  # धीमा डरावना बैकग्राउंड

def synthesize_clip(text, voice_id, filename):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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
            "similarity_boost": 0.80
        }
    }
    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 200:
        with open(filename, "wb") as f:
            f.write(res.content)
        return True
    return False

def parse_story(text):
    """
    नैरेटर, रोहन/लड़का और भूत के डायलॉग अलग करता है।
    """
    segments = []
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        lower_line = line.lower()
        if any(lower_line.startswith(k) for k in ["नैरेटर:", "narrator:", "कहानीकार:"]):
            content = re.sub(r"^(नैरेटर|narrator|कहानीकार)\s*[:：\-]\s*", "", line, flags=re.IGNORECASE)
            segments.append(("narrator", content))
        elif any(lower_line.startswith(k) for k in ["रोहन:", "लड़का:", "boy:", "rohan:"]):
            content = re.sub(r"^(रोहन|लड़का|boy|rohan)\s*[:：\-]\s*", "", line, flags=re.IGNORECASE)
            segments.append(("boy", content))
        elif any(lower_line.startswith(k) for k in ["भूत:", "चुड़ैल:", "ghost:", "आत्मा:"]):
            content = re.sub(r"^(भूत|चुड़ैल|ghost|आत्मा)\s*[:：\-]\s*", "", line, flags=re.IGNORECASE)
            segments.append(("ghost", content))
        else:
            segments.append(("narrator", line))
    return segments

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "भूतिया वॉइस बॉट तैयार है!\n\n"
        "आप इस तरह कहानी भेज सकते हैं:\n"
        "नैरेटर: रात का घना अँधेरा था।\n"
        "रोहन: यहाँ कोई है क्या?\n"
        "भूत: कोई नहीं बचेगा..."
    )
    await update.message.reply_text(welcome_text)

async def handle_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    story_text = update.message.text
    msg = await update.message.reply_text("किरदारों की अलग-अलग आवाज़ और BGM तैयार किया जा रहा है...")

    segments = parse_story(story_text)
    temp_files = []
    combined_audio = AudioSegment.empty()

    try:
        for idx, (role, dialogue) in enumerate(segments):
            if not dialogue.strip():
                continue
            voice_id = VOICE_MAP.get(role, VOICE_MAP["narrator"])
            clip_path = f"temp_{idx}.mp3"
            
            ok = synthesize_clip(dialogue, voice_id, clip_path)
            if ok:
                temp_files.append(clip_path)
                clip_audio = AudioSegment.from_file(clip_path)
                combined_audio += clip_audio + AudioSegment.silent(duration=350)
            else:
                await msg.edit_text("वॉइस जनरेट करने में कोई समस्या आई।")
                return

        total_duration = len(combined_audio)
        bgm = generate_horror_bgm(total_duration)
        final_audio = combined_audio.overlay(bgm)

        output_file = "final_horror_story.mp3"
        final_audio.export(output_file, format="mp3")
        temp_files.append(output_file)

        await msg.delete()
        await update.message.reply_audio(
            audio=open(output_file, "rb"),
            caption="ये रहा आपका मल्टी-कैरेक्टर हॉरर ऑडियो!"
        )

    except Exception as e:
        await msg.edit_text(f"एरर आ गया: {e}")
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

def main():
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_story))
    app.run_polling()

if __name__ == "__main__":
    main()
