import os

BASE = r"C:\yamen_academy"
FILES = {}

# ═══ ai/__init__.py ═══
FILES[r"ai\__init__.py"] = ""

# ═══ services/__init__.py ═══
FILES[r"services\__init__.py"] = ""

# ═══ services/key_rotator.py ═══
FILES[r"services\key_rotator.py"] = """import random, time, threading
from config import settings

class KeyRotator:
    def __init__(self, keys: list[str], rpm: int = 15):
        self.keys = keys
        self.rpm = rpm
        self.usage = {k: {"count": 0, "reset_at": time.time() + 60} for k in keys}
        self.lock = threading.Lock()

    def get_key(self) -> str:
        with self.lock:
            now = time.time()
            for k in self.keys:
                if self.usage[k]["reset_at"] <= now:
                    self.usage[k] = {"count": 0, "reset_at": now + 60}
                if self.usage[k]["count"] < self.rpm:
                    self.usage[k]["count"] += 1
                    return k
            # كل المفاتيح مستنفذة — نستنى
            time.sleep(1)
            return self.get_key()

writing_keys = KeyRotator(settings.GEMINI_WRITING_KEYS) if settings.GEMINI_WRITING_KEYS else None
speaking_keys = KeyRotator(settings.GEMINI_SPEAKING_KEYS) if settings.GEMINI_SPEAKING_KEYS else None
"""

# ═══ ai/gemini_client.py ═══
FILES[r"ai\gemini_client.py"] = """import google.generativeai as genai
from services.key_rotator import writing_keys, speaking_keys

WRITING_PROMPT = '''You are an IELTS writing examiner (British Council standard).
Analyze this essay and return a JSON only (no markdown, no backticks):
{
  "band_score": number (0-9, 0.5 increments),
  "task_response": {"score": number, "comment": "Arabic"},
  "coherence_cohesion": {"score": number, "comment": "Arabic"},
  "lexical_resource": {"score": number, "comment": "Arabic"},
  "grammar": {"score": number, "comment": "Arabic"},
  "corrected_essay": "the full corrected essay",
  "suggestions": ["3 specific improvement tips in Arabic"],
  "academic_vocab": ["5 suggested academic words with Arabic translation"]
}
Essay: '''

SPEAKING_PROMPT = '''You are an IELTS speaking examiner.
Evaluate this transcript and return JSON only (no markdown):
{
  "band_score": number (0-9, 0.5 increments),
  "fluency": {"score": number, "comment": "Arabic"},
  "pronunciation": {"score": number, "comment": "Arabic"},
  "grammar": {"score": number, "comment": "Arabic"},
  "vocabulary": {"score": number, "comment": "Arabic"},
  "hesitation_analysis": {"count": number, "comment": "Arabic"},
  "shadowing_text": "correct version to repeat",
  "tips": ["3 tips in Arabic"]
}
Transcript: '''

def _call_gemini(prompt: str, api_key: str) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content(prompt)
    return resp.text.strip()

def evaluate_writing(essay: str) -> dict:
    import json
    key = writing_keys.get_key() if writing_keys else settings.GEMINI_API_KEY
    raw = _call_gemini(WRITING_PROMPT + essay, key)
    # تنظيف الـ JSON لو رجع معاه backticks
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)

def evaluate_speaking(transcript: str) -> dict:
    import json
    key = speaking_keys.get_key() if speaking_keys else settings.GEMINI_API_KEY
    raw = _call_gemini(SPEAKING_PROMPT + transcript, key)
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
"""

# ═══ handlers/writing.py ═══
FILES[r"handlers\writing.py"] = """from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ai.gemini_client import evaluate_writing
from database import get_student
import json

router = Router()

class WritingState(StatesGroup):
    waiting_essay = State()

@router.message(F.text == "✍️ تصحيح كتابة")
async def ask_essay(message: types.Message, state: FSMContext):
    student = get_student(message.from_user.id)
    if not student or not student["placement_done"]:
        await message.answer("⚠️ أجرِ اختبار المستوى أولاً.")
        return
    await state.set_state(WritingState.waiting_essay)
    await message.answer("📝 أرسل مقالك بالإنجليزية (250 كلمة على الأقل):")

@router.message(WritingState.waiting_essay)
async def correct_essay(message: types.Message, state: FSMContext):
    if len(message.text.split()) < 50:
        await message.answer("⚠️ المقال قصير جداً. أرسل 250 كلمة على الأقل.")
        return

    await message.answer("🔍 جارٍ تصحيح مقالك... (قد يستغرق 10-20 ثانية)")
    try:
        result = evaluate_writing(message.text)
    except Exception as e:
        await message.answer(f"❌ خطأ في التصحيح. حاول مرة أخرى.\n{str(e)[:200]}")
        await state.clear()
        return

    resp = (
        f"📊 <b>نتيجة تقييم IELTS للكتابة</b>\\n\\n"
        f"🎯 <b>الدرجة الكلية: {result['band_score']}/9</b>\\n\\n"
        f"📋 <b>المهمة:</b> {result['task_response']['score']}/9\\n"
        f"└ {result['task_response']['comment']}\\n\\n"
        f"🔗 <b>الترابط:</b> {result['coherence_cohesion']['score']}/9\\n"
        f"└ {result['coherence_cohesion']['comment']}\\n\\n"
        f"📚 <b>المفردات:</b> {result['lexical_resource']['score']}/9\\n"
        f"└ {result['lexical_resource']['comment']}\\n\\n"
        f"✏️ <b>القواعد:</b> {result['grammar']['score']}/9\\n"
        f"└ {result['grammar']['comment']}\\n\\n"
        f"💡 <b>نصائح:</b>\\n" +
        "\\n".join(f"• {s}" for s in result['suggestions']) + "\\n\\n" +
        f"📖 <b>مفردات أكاديمية مقترحة:</b>\\n" +
        "\\n".join(f"• {v}" for v in result['academic_vocab'])
    )

    if len(resp) > 4000:
        await message.answer(resp[:4000] + "\\n\\n...(النص طويل جداً)")
        await message.answer(f"✏️ <b>النص المصحح:</b>\\n{result['corrected_essay'][:4000]}")
    else:
        await message.answer(resp)

    await state.clear()
"""

# ═══ handlers/speaking.py ═══
FILES[r"handlers\speaking.py"] = """from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ai.gemini_client import evaluate_speaking
from database import get_student
import os, subprocess, tempfile

router = Router()

class SpeakingState(StatesGroup):
    waiting_voice = State()

@router.message(F.text == "🎤 تقييم تحدث")
async def ask_voice(message: types.Message, state: FSMContext):
    student = get_student(message.from_user.id)
    if not student or not student["placement_done"]:
        await message.answer("⚠️ أجرِ اختبار المستوى أولاً.")
        return
    await state.set_state(SpeakingState.waiting_voice)
    await message.answer("🎙 أرسل تسجيلاً صوتياً بالإنجليزية (30 ثانية - دقيقتان):")

@router.message(SpeakingState.waiting_voice, F.voice)
async def evaluate_voice(message: types.Message, state: FSMContext, bot):
    voice = message.voice
    if voice.duration < 10:
        await message.answer("⚠️ التسجيل قصير جداً. تحدث 30 ثانية على الأقل.")
        return
    if voice.duration > 180:
        await message.answer("⚠️ التسجيل طويل جداً. أرسل دقيقتين كحد أقصى.")
        return

    await message.answer("🔍 جارٍ تحليل تسجيلك... (قد يستغرق 20-40 ثانية)")

    # تحميل الملف الصوتي
    file_path = tempfile.mktemp(suffix=".ogg")
    await bot.download(voice, destination=file_path)

    # محاولة تحويل الصوت لنص (نحتاج whisper أو بديل)
    transcript = "[Transcription not available - using Gemini multimodal]"

    try:
        # استخدام whisper محلي لو موجود
        result = subprocess.run(
            ["whisper", file_path, "--model", "tiny", "--language", "en", "--output_format", "txt"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            transcript = result.stdout.strip()
    except:
        pass

    if transcript == "[Transcription not available - using Gemini multimodal]":
        await message.answer("⚠️ لم نتمكن من تحويل الصوت لنص. يرجى تثبيت whisper:\\n`pip install openai-whisper`",
                           parse_mode="Markdown")
        os.remove(file_path)
        await state.clear()
        return

    try:
        result = evaluate_speaking(transcript)
    except Exception as e:
        await message.answer(f"❌ خطأ في التقييم:\\n{str(e)[:200]}")
        os.remove(file_path)
        await state.clear()
        return

    os.remove(file_path)

    resp = (
        f"🎙 <b>نتيجة تقييم IELTS للتحدث</b>\\n\\n"
        f"🎯 <b>الدرجة الكلية: {result['band_score']}/9</b>\\n\\n"
        f"💬 <b>الطلاقة:</b> {result['fluency']['score']}/9\\n"
        f"└ {result['fluency']['comment']}\\n\\n"
        f"🔊 <b>النطق:</b> {result['pronunciation']['score']}/9\\n"
        f"└ {result['pronunciation']['comment']}\\n\\n"
        f"✏️ <b>القواعد:</b> {result['grammar']['score']}/9\\n"
        f"└ {result['grammar']['comment']}\\n\\n"
        f"📚 <b>المفردات:</b> {result['vocabulary']['score']}/9\\n"
        f"└ {result['vocabulary']['comment']}\\n\\n"
        f"⏸ <b>تحليل التردد:</b> {result['hesitation_analysis']['count']} توقفات\\n"
        f"└ {result['hesitation_analysis']['comment']}\\n\\n"
        f"💡 <b>نصائح:</b>\\n" +
        "\\n".join(f"• {t}" for t in result['tips'])
    )

    await message.answer(resp[:4000])
    await message.answer(f"🗣 <b>نص Shadowing للتمرين:</b>\\n\\n{result['shadowing_text']}")
    await state.clear()
"""

# ═══ تحديث main.py ═══
FILES["main.py"] = """import asyncio, logging, sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from handlers import student, admin, placement_test, writing, speaking

async def main():
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), stream=sys.stdout)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(student.router, admin.router, placement_test.router, writing.router, speaking.router)
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
"""

# ═══ تحديث student.py لإضافة أزرار ✍️ و 🎤 ═══
FILES[r"handlers\student.py"] = """from aiogram import Router, F, types
from aiogram.filters import CommandStart
from keyboards.main_kb import start_test_kb
from database import upsert_student, get_student
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

router = Router()

def main_menu_kb():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="✍️ تصحيح كتابة"), KeyboardButton(text="🎤 تقييم تحدث"))
    b.row(KeyboardButton(text="📚 دروسي"), KeyboardButton(text="📊 تقاريري"))
    b.adjust(2)
    return b

@router.message(CommandStart())
async def welcome(message: types.Message):
    user = message.from_user
    is_new = upsert_student(user.id, user.full_name)
    student = get_student(user.id)

    if is_new or not student["placement_done"]:
        await message.answer(
            f"👋 أهلاً {user.full_name} في أكاديمية يامن الرقمية!\\n\\nقبل البدء، يجب إجراء اختبار مستوى سريع (10 أسئلة).",
            reply_markup=start_test_kb().as_markup())
    else:
        await message.answer(
            f"👋 مرحباً بعودتك {user.full_name}!\\nمستواك: {student['level']}",
            reply_markup=main_menu_kb().as_markup(resize_keyboard=True))
"""

# ═══ تحديث requirements.txt ═══
FILES["requirements.txt"] = """aiogram>=3.27.0
python-dotenv>=1.0.0
google-generativeai>=0.8.0
openai-whisper
"""

# ═══ BUILD ═══
print("🧠 بناء الوحدة الثانية: الذكاء الاصطناعي...")
for path, content in FILES.items():
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ {path}")
print("\n🎉 تم! شغّل pip install -r requirements.txt ثم python main.py")
