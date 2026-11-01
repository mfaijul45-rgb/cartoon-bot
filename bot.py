import os
import asyncio
import requests
import urllib.parse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! अपनी 2D कार्टून कहानी का टाइटल या कहानी यहाँ लिखकर भेजिए, मैं वीडियो तैयार कर दूँगा।")

async def generate_cartoon_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("कहानी प्राप्त हुई! 2D कार्टून सीन और आवाज़ बनाई जा रही है, कृपया 1-2 मिनट इंतज़ार करें...")

    try:
        # 1. हिंदी आवाज़ (Edge-TTS - Free)
        audio_file = "voice.mp3"
        communicate = edge_tts.Communicate(user_prompt, "hi-IN-MadhurNeural")
        await communicate.save(audio_file)

        # 2. 2D कार्टून इमेज जनरेशन (Pollinations AI - Free)
        cartoon_prompt = f"Indian 2D cartoon animation style, clean outlines, flat colors, village story scene, {user_prompt}"
        encoded_prompt = urllib.parse.quote(cartoon_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true"

        img_data = requests.get(image_url).content
        img_file = "scene.jpg"
        with open(img_file, "wb") as handler:
            handler.write(img_data)

        # 3. वीडियो एडिटिंग (MoviePy)
        audio_clip = AudioFileClip(audio_file)
        video_clip = ImageClip(img_file).set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)

        output_video = "cartoon_story.mp4"
        video_clip.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac")

        # 4. टेलीग्राम पर वीडियो भेजना
        await status_msg.edit_text("वीडियो तैयार हो गया! अपलोड किया जा रहा है...")
        with open(output_video, "rb") as video:
            await update.message.reply_video(video=video, caption=f"आपकी 2D कार्टून कहानी तैयार है!\n\nकहानी: {user_prompt}")

        # टेम्परेरी फाइल्स डिलीट करना
        audio_clip.close()
        video_clip.close()
        for f in [audio_file, img_file, output_video]:
            if os.path.exists(f):
                os.remove(f)

    except Exception as e:
        await update.message.reply_text(f"त्रुटि आई: {str(e)}")

def main():
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN नहीं मिला!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_cartoon_video))

    print("बॉट शुरू हो गया है...")
    app.run_polling()

if __name__ == "__main__":
    main()
