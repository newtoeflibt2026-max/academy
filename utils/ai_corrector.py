import aiohttp
from config import settings

async def _gemini(prompt):
    key = settings.GEMINI_KEY
    if not key:
        return "مفتاح Gemini غير مضبوط"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload) as r:
            if r.status == 200:
                d = await r.json()
                try:
                    return d["candidates"][0]["content"]["parts"][0]["text"]
                except:
                    return "لم يتم الحصول على رد"
            return f"خطأ {r.status}"

async def correct_writing(text, task_type="Writing Task 2"):
    prompt = f"You are an IELTS examiner. Evaluate this essay in Arabic. Give band scores and tips.\nTask: {task_type}\nEssay: {text}"
    return await _gemini(prompt)

async def correct_speaking(transcript, part="Part 1", question=""):
    prompt = f"You are an IELTS examiner. Evaluate this speaking transcript in Arabic. Give band scores and tips.\nQuestion: {question}\nPart: {part}\nTranscript: {transcript}"
    return await _gemini(prompt)
