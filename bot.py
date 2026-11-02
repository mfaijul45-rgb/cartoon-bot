import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import edge_tts
from pydub import AudioSegment
from pydub.generators import Sine

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# हर किरदार के लिए अलग फ़्री आवाज़ और टोन (Pitch / Rate)
VOICE_CONFIG = {
    "narrator": {"voice": "hi-IN-MadhurNeural", "rate": "+0%", "pitch": "-5Hz"},
    "boy": {"voice": "hi-IN-SwaraNeural", "rate": "+5%", "pitch": "+0Hz"},
    "ghost": {"voice": "hi-IN-MadhurNeural", "rate": "-25%", "pitch": "-25Hz"} # भारी और धीमी डरावनी आवाज़
}

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Multi-Character Edge-TTS Bot is Running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def generate_horror_bgm(duration_ms):
    sine_wave = Sine(65).to_audio_segment(duration=duration_ms)
    return sine_wave - 20

async def synthesize_clip(text, role, output_file):
    cfg = VOICE_CONFIG.get(role, VOICE_CONFIG["narrator"])
    communicate = edge_tts.Communicate(
        text=text, 
        voice=cfg["voice"], 
        rate=cfg["rate"], 
        pitch=cfg["pitch"]
    )
    await communicate.save(output_file)

def parse_story(text):
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
    msg = (
        "भूतिया मल्टी-कैरेक्टर बॉट तैयार है!\n\n"
        "आप इस तरह कहानी लिखकर भेजें:\n"
        "नैरेटर: रात का घना अंधेरा था।\n"
        "लड़का: मुझे बहुत डर लग रहा है!\n"
        "भूत: कोई ज़िंदा नहीं बचेगा..."
    )
    await update.message.reply_text(msg)

async def handle_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    story_text = update.message.text
    msg = await update.message.reply_text("सब कैरेक्टर की अलग-अलग आवाज़ और डरावना BGM तैयार हो रहा है...")

    segments = parse_story(story_text)
    temp_files = []
    combined_audio = AudioSegment.empty()

    try:
        for idx, (role, dialogue) in enumerate(segments):
            if not dialogue.strip():
                continue
            
            clip_path = f"temp_clip_{idx}.mp3"
            await synthesize_clip(dialogue, role, clip_path)
            temp_files.append(clip_path)

            clip_audio = AudioSegment.from_file(clip_path)
            combined_audio += clip_audio + AudioSegment.silent(duration=350)

        total_duration = len(combined_audio)
        bgm = generate_horror_bgm(total_duration)
        final_audio = combined_audio.overlay(bgm)

        final_output = "final_story.mp3"
        final_audio.export(final_output, format="mp3")
        temp_files.append(final_output)

        await msg.delete()
        await update.message.reply_audio(
            audio=open(final_output, "rb"),
            caption="ये रहा आपका तैयार मल्टी-कैरेक्टर हॉरर ऑडियो!"
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
