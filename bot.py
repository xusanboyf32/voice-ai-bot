import asyncio
import io
import subprocess
import httpx
from gtts import gTTS
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)



from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")



FFMPEG = "ffmpeg"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LANGUAGE_NAMES = {
    "uzbek": "O'zbek 🇺🇿",
    "russian": "Rus 🇷🇺",
    "english": "Ingliz 🇬🇧",
    "arabic": "Arab 🇸🇦",
    "turkish": "Turk 🇹🇷",
    "kazakh": "Qozoq 🇰🇿",
}


async def transcribe(audio_bytes: bytes) -> tuple[str, str]:
    log.info("Whisper: ovoz tahlil qilinmoqda, hajmi: %d bytes", len(audio_bytes))
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": ("voice.ogg", audio_bytes, "audio/ogg")},
            data={
                "model": "whisper-large-v3",
                "response_format": "verbose_json",
            }
        )
        data = response.json()

    text = data.get("text", "").strip()
    language = data.get("language", "unknown").lower()
    language_label = LANGUAGE_NAMES.get(language, f"{language} 🌐")
    log.info("Whisper: tayyor. Til: %s | Matn: %s", language_label, text)
    return text, language_label


async def ask_llama(text: str, language: str) -> str:
    log.info("LLaMA: tarjima boshlanmoqda → %s", text)

    if "O'zbek" in language:
        return text  # O'zbek bo'lsa tarjima shart emas, o'zini qaytaradi

    system_prompt = (
        "Sen faqat tarjimonsan. "
        "Berilgan matnni o'zbek tiliga tarjima qil. "
        "Hech qanday izoh, qo'shimcha gap yozma. "
        "Faqat tarjimani yoz."
    )

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.3
            }
        )
        data = response.json()

    answer = data["choices"][0]["message"]["content"].strip()
    log.info("LLaMA: tarjima tayyor → %s", answer)
    return answer




async def text_to_ogg(text: str) -> bytes:
    log.info("TTS boshlandi. Matn: %s", text)

    tts = gTTS(text=text, slow=False)
    mp3_buf = io.BytesIO()
    tts.write_to_fp(mp3_buf)
    mp3_bytes = mp3_buf.getvalue()
    log.info("MP3 tayyor, hajmi: %d bytes", len(mp3_bytes))

    log.info("MP3 → OGG convert qilinmoqda...")
    process = subprocess.run(
        [FFMPEG, "-i", "pipe:0", "-c:a", "libvorbis", "-f", "ogg", "pipe:1"],
        input=mp3_bytes,
        capture_output=True
    )

    if process.returncode != 0:
        raise Exception(f"ffmpeg xatosi: {process.stderr.decode()}")

    ogg_bytes = process.stdout
    log.info("OGG tayyor, hajmi: %d bytes", len(ogg_bytes))
    return ogg_bytes


@dp.message(Command("start"))
async def handle_start(message: Message):
    log.info("Foydalanuvchi /start bosdi: %s", message.from_user.id)
    await message.answer(
        "👋 Salom! Men AI ovozli assistantman.\n\n"
        "🎤 Menga ovozli xabar yuboring — savol bering!\n\n"
        "📝 Matnni ko'rasiz\n"
        "🤖 AI javob beradi\n"
        "🔊 Ovozli javob ham keladi"
    )




@dp.message(F.voice)
async def handle_voice(message: Message):
    user_id = message.from_user.id
    log.info("=== Yangi ovoz. Foydalanuvchi: %s ===", user_id)

    status = await message.answer("⏳ Ovoz tahlil qilinmoqda...")

    try:
        # 1. Ovozni yuklab olish
        log.info("Ovoz yuklab olinmoqda...")
        file = await bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with httpx.AsyncClient(timeout=30) as client:
            audio_bytes = (await client.get(file_url)).content
        log.info("Ovoz yuklandi: %d bytes", len(audio_bytes))

        # 2. Ovoz → Matn (Whisper)
        text, language = await transcribe(audio_bytes)
        if not text:
            await status.edit_text("❌ Matn ajratib bo'lmadi, qayta urinib ko'ring.")
            return

        await status.edit_text(
            f"🎤 *Ovoz qabul qilindi*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 Til: {language}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 AI o'ylayapti..."
        )

        # 3. Matn → LLaMA javob
        answer = await ask_llama(text, language)

        # 4. Javobni formatlash
        is_uzbek = "O'zbek" in language

        if is_uzbek:
            result_text = (
                f"╔════════════════════╗\n"
                f"   🎤 Siz aytdingiz\n"
                f"╚════════════════════╝\n"
                f"{text}\n\n"
                f"╔════════════════════╗\n"
                f"   🤖 AI javob\n"
                f"╚════════════════════╝\n"
                f"{answer}"
            )
        else:
            result_text = (
                f"╔════════════════════╗\n"
                f"   🎤 Siz ({language})\n"
                f"╚════════════════════╝\n"
                f"{text}\n\n"
                f"╔════════════════════╗\n"
                f"   🌐 O'zbek tarjimasi\n"
                f"╚════════════════════╝\n"
                f"{answer}"
            )

        await status.edit_text(result_text)
        log.info("Matnli javob yuborildi")

        # 5. Javobni ovozga o'girish
        log.info("Javob ovozga o'girilmoqda...")
        ogg_bytes = await text_to_ogg(answer)

        await message.answer_voice(
            voice=BufferedInputFile(ogg_bytes, filename="voice.ogg"),
            caption="🔊 AI ovozli javob"
        )
        log.info("=== Jarayon tugadi ===")

    except httpx.TimeoutException:
        log.error("Timeout xatosi")
        await status.edit_text("⏱ Vaqt tugadi, qayta urinib ko'ring.")
    except Exception as e:
        log.error("Xatolik: %s", str(e), exc_info=True)
        await status.edit_text(f"❌ Xatolik: {str(e)}")



@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    await message.answer("🎤 Iltimos, ovozli xabar yuboring.")


async def main():
    log.info("✅ Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())