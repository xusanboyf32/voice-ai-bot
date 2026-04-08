# Voice AI Bot 🎤

Ovozli xabar yuboring — bot avtomatik tarjima qilib, o'zbek tilida javob beradi.

## Qanday ishlaydi

1. Ovozli xabar yuborasiz (istalgan tilda)
2. Whisper ovozni matnga o'giradi + tilni aniqlaydi
3. O'zbek bo'lsa — tarjima yo'q, to'g'ridan audio
4. Boshqa til bo'lsa — LLaMA o'zbek tiliga tarjima qiladi
5. gTTS tarjimani o'zbek tilida ovozga o'giradi

## Tillar

| Til | Matn | Tarjima | Audio |
|-----|------|---------|-------|
| O'zbek 🇺🇿 | ✅ | — | ✅ O'zbek |
| Rus 🇷🇺 | ✅ | ✅ O'zbek | ✅ O'zbek |
| Ingliz 🇬🇧 | ✅ | ✅ O'zbek | ✅ O'zbek |
| Boshqa 🌐 | ✅ | ✅ O'zbek | ✅ O'zbek |

## Stack

- Python 3.11 + aiogram 3
- Groq API — Whisper Large v3 (STT) + LLaMA 3.3 70b (tarjima)
- gTTS + ffmpeg (TTS + audio konvertatsiya)
- Docker + DigitalOcean

## Ishlatish

1. `.env` faylga yoz:
