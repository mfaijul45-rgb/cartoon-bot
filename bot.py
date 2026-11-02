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
        self.wfile.write(b"Horror Audio Bot Running!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def generate_horror_track(duration_ms):
    # गहरा डरावना बेस टोन (Dark Sub-Bass)
    low_drone = Sine(45).to_audio_segment(duration=duration_ms).low_pass_filter(90) - 8
    # सस्पेंस भरी गूँज (Eerie Resonance)
    mid_eerie = Sine(110).to_audio_segment(duration=duration_ms).low_pass_filter(180) - 16
    # हवा जैसी खौफ़नाक सरसराहट (Dark Hum)
    high_wind = Sine(220).to_audio_segment(duration=duration_ms).low_pass_filter(280) - 22
    
    horror_bgm = low_drone.overlay(mid_eerie).overlay(high_wind)
    return horror_bgm

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! अपनी कहानी भेजिए, मैं सस्पेंस भरी धीमी आवाज़ और हॉरर बैकग्राउंड के साथ पूरा ऑडियो तैयार कर दूँगा।")

async def generate_horror_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    status = await update.message.reply_text("डायलॉग्स और सस्पेंस भरी आवाज़ें तैयार हो रही हैं...")

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    temp_files = []
    combined_dialogs = AudioSegment.empty()

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

            # आवाज़ का चुनाव
            if any(k in char_name for k in ["भूत", "चुड़ैल", "राक्षस", "आत्मा"]):
                voice = "hi-IN-SwaraNeural"
                rate = "-18%"   # डरावनी धीमी गति
                pitch = "-4Hz"
            elif any(k in char_name for k in ["लड़की", "औरत", "महिला", "माँ"]):
                voice = "hi-IN-SwaraNeural"
                rate = "-12%"
                pitch = "+0Hz"
            elif any(k in char_name for k in ["लड़का", "रोहन", "आदमी", "रामू"]):
                voice = "hi-IN-MadhurNeural"
                rate = "-12%"
                pitch = "+0Hz"
            else:
                # नैरेटर: एकदम धीमी, गंभीर और सस्पेंस वाली गति
                voice = "hi-IN-MadhurNeural"
                rate = "-15%"
                pitch = "-2Hz"

            temp_path = f"part_{idx}.mp3"
            temp_files.append(temp_path)

            tts = edge_tts.Communicate(dialog, voice=voice, pitch=pitch, rate=rate)
            await tts.save(temp_path)

            segment = AudioSegment.from_file(temp_path)
            # हर डायलॉग के बाद 1.2 सेकंड का सन्नाटा ताकि सस्पेंस बने
            combined_dialogs += segment + AudioSegment.silent(duration=1200)

        await status.edit_text("डरावना बैकग्राउंड माहौल जोड़ा जा रहा है...")

        dialog_duration = len(combined_dialogs)
        
        # 100% पक्का हॉरर ट्रैक जनरेट करना
        horror_bgm = generate_horror_track(dialog_duration)

        # दोनों को आपस में मिक्स करना
        final_audio = combined_dialogs.overlay(horror_bgm)
        
        output_file = "final_suspense_horror.mp3"
        temp_files.append(output_file)
        final_audio.export(output_file, format="mp3", bitrate="192k")

        with open(output_file, "rb") as audio:
            await update.message.reply_audio(
                audio=audio, 
                title="Slow Suspense Horror Story", 
                caption="धीमी सस्पेंस भरी आवाज़ और हॉरर बैकग्राउंड वाला ऑडियो तैयार है!"
            )

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
