import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import edge_tts
from pydub import AudioSegment
from pydub.generators import Sine

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Horror Audio Bot is Running!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! अपनी कहानी भेजिए, मैं अलग-अलग आवाज़ों और डरावने बैकग्राउंड म्यूज़िक के साथ पूरा ऑडियो तैयार कर दूँगा।")

async def generate_horror_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    status = await update.message.reply_text("डायलॉग्स और डरावनी आवाज़ें तैयार हो रही हैं...")

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    temp_files = []
    combined_audio = AudioSegment.empty()

    try:
        for idx, line in enumerate(lines):
            if ":" in line:
                char_name, dialog = line.split(":", 1)
            elif "ः" in line:
                char_name, dialog = line.split("ः", 1)
            else:
                char_name, dialog = "नैरेटर", line

            char_name = char_name.strip()
            dialog = dialog.strip()

            # कैरेक्टर के हिसाब से वॉयस और पिच
            if any(k in char_name for k in ["भूत", "चुड़ैल", "राक्षस", "आत्मा"]):
                voice = "hi-IN-SwaraNeural"
                pitch = "-30Hz"
                rate = "-15%"
            elif any(k in char_name for k in ["लड़का", "रामू", "आदमी", "रोहन"]):
                voice = "hi-IN-MadhurNeural"
                pitch = "+5Hz"
                rate = "+0%"
            elif any(k in char_name for k in ["लड़की", "औरत", "महिला", "माँ"]):
                voice = "hi-IN-SwaraNeural"
                pitch = "+5Hz"
                rate = "+0%"
            else:
                # नैरेटर
                voice = "hi-IN-MadhurNeural"
                pitch = "-15Hz"
                rate = "-10%"

            temp_path = f"part_{idx}.mp3"
            temp_files.append(temp_path)

            tts = edge_tts.Communicate(dialog, voice=voice, pitch=pitch, rate=rate)
            await tts.save(temp_path)

            segment = AudioSegment.from_file(temp_path)
            combined_audio += segment + AudioSegment.silent(duration=500)

        await status.edit_text("डरावना बैकग्राउंड म्यूज़िक जोड़ा जा रहा है...")

        duration_ms = len(combined_audio)
        bg_drone = Sine(55).to_audio_segment(duration=duration_ms).low_pass_filter(120)
        bg_drone = bg_drone - 24

        final_audio = combined_audio.overlay(bg_drone)
        output_file = "horror_story.mp3"
        temp_files.append(output_file)
        final_audio.export(output_file, format="mp3")

        with open(output_file, "rb") as audio:
            await update.message.reply_audio(audio=audio, title="Horror Story Audio", caption="यह रहा आपका हॉरर ऑडियो!")

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
