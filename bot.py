import os
import asyncio
import threading
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import edge_tts
from pydub import AudioSegment

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 100% रॉयल्टी-फ़्री असली हॉरर बैकग्राउंड म्यूज़िक
HORROR_BGM_URL = "https://raw.githubusercontent.com/md-workspace/audio-assets/main/horror_drone_safe.mp3"
FALLBACK_BGM_URL = "https://ia800903.us.archive.org/24/items/horror-ambience-loop/horror_loop_ambience.mp3"
BGM_FILE = "horror_bgm.mp3"

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Horror Bot Running Smoothly!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def ensure_bgm():
    if not os.path.exists(BGM_FILE) or os.path.getsize(BGM_FILE) < 10000:
        req = urllib.request.Request(
            FALLBACK_BGM_URL, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp, open(BGM_FILE, 'wb') as out:
                out.write(resp.read())
        except Exception:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! हॉरर कहानी भेजिए, मैं सस्पेंस भरी आवाज़ और असली डरावने म्यूज़िक के साथ पूरा ऑडियो तैयार कर दूँगा।")

async def generate_horror_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    status = await update.message.reply_text("डायलॉग्स और डरावनी आवाज़ें तैयार हो रही हैं...")

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    temp_files = []
    combined_dialogs = AudioSegment.empty()

    try:
        ensure_bgm()

        for idx, line in enumerate(lines):
            if ":" in line:
                char_name, dialog = line.split(":", 1)
            elif "ः" in line:
                char_name, dialog = line.split("ः", 1)
            else:
                char_name, dialog = "नैरेटर", line

            char_name = char_name.strip()
            dialog = dialog.strip()

            # किरदारों के हिसाब से आवाज़ और सस्पेंस
            if any(k in char_name for k in ["भूत", "चुड़ैल", "राक्षस", "आत्मा"]):
                voice = "hi-IN-SwaraNeural"
                pitch = "-12Hz"
                rate = "-8%"
            elif any(k in char_name for k in ["लड़का", "रोहन", "आदमी", "रामू"]):
                voice = "hi-IN-MadhurNeural"
                pitch = "+0Hz"
                rate = "+0%"
            elif any(k in char_name for k in ["लड़की", "औरत", "महिला", "माँ"]):
                voice = "hi-IN-SwaraNeural"
                pitch = "+0Hz"
                rate = "+0%"
            else:
                # कथावाचक (नैरेटर): गहरा बेस और धीमी सस्पेंस वाली गति (बिना रोबोटिक बने)
                voice = "hi-IN-MadhurNeural"
                pitch = "-6Hz"
                rate = "-8%"

            temp_path = f"part_{idx}.mp3"
            temp_files.append(temp_path)

            tts = edge_tts.Communicate(dialog, voice=voice, pitch=pitch, rate=rate)
            await tts.save(temp_path)

            segment = AudioSegment.from_file(temp_path)
            # डायलॉग्स के बीच में 600ms का ठहराव ताकि हॉरर म्यूज़िक का डर महसूस हो
            combined_dialogs += segment + AudioSegment.silent(duration=600)

        await status.edit_text("डरावना बैकग्राउंड म्यूज़िक मिक्स किया जा रहा है...")

        dialog_duration = len(combined_dialogs)

        if os.path.exists(BGM_FILE) and os.path.getsize(BGM_FILE) > 5000:
            bgm = AudioSegment.from_file(BGM_FILE)
            while len(bgm) < dialog_duration:
                bgm += bgm
            bgm = bgm[:dialog_duration]
            # बैकग्राउंड म्यूज़िक को सही बैलेंस पर रखना
            bgm = bgm - 18
            final_audio = combined_dialogs.overlay(bgm)
        else:
            final_audio = combined_dialogs

        output_file = "final_suspense_horror.mp3"
        temp_files.append(output_file)
        final_audio.export(output_file, format="mp3")

        with open(output_file, "rb") as audio:
            await update.message.reply_audio(audio=audio, title="Suspense Horror Audio", caption="यह रहा आपका सस्पेंस आवाज़ और हॉरर म्यूज़िक वाला ऑडियो!")

        await status.delete()

    except Exception as e:
        await status.edit_text(f"त्रुटि: {e}")

    finally:
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
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_horror_audio))
    print("हॉरर ऑडियो बॉट चालू है...")
    app.run_polling()
