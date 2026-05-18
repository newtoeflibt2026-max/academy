import base64, aiohttp
from config import settings

async def voice_to_text(audio_bytes, mime_type="audio/ogg"):
    key = settings.GEMINI_KEY
    if not key:
        return ""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    audio_b64 = base64.b64encode(audio_bytes).decode()
    payload = {"contents": [{"parts": [
        {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
        {"text": "Transcribe this audio to text exactly as spoken. Return only the transcript."}
    ]}]}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload) as r:
            if r.status == 200:
                d = await r.json()
                try:
                    return d["candidates"][0]["content"]["parts"][0]["text"].strip()
                except:
                    return ""
    return ""
