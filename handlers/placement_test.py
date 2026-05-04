from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_student, set_student_level, set_placement_done, get_placement_questions

router = Router()
TOTAL_PER_LEVEL = {0: (0,3,"A1"), 1:(4,6,"A2"), 2:(7,8,"B1"), 3:(9,9,"B2"), 4:(10,10,"C1")}

def get_pathway(score):
    if score <= 3:   return "A1", "مبتدئ 🔸"
    elif score <= 6:  return "A2", "تحت المتوسط 🟠"
    elif score <= 8:  return "B1", "متوسط 🟡"
    elif score <= 9:  return "B2", "فوق المتوسط 🟢"
    return "C1", "متقدم 🔴"

class PlaceState(StatesGroup):
    q = State()

@router.callback_query(F.data == "placement_test")
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    student = get_student(callback.from_user.id)
    if student and student["placement_done"]:
        await callback.message.edit_text(
            "✅ *لقد أتممت اختبار تحديد المستوى مسبقاً* ✅\n\n"
            "تم تحديد مستواك بالفعل، يمكنك الآن:\n"
            "📚 تصفح *دوراتي* للبدء بالتعلم\n"
            "🎯 المشاركة في *تحدي الـ60 ثانية*\n\n"
            "بالتوفيق في رحلتك التعليمية! 🌟",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    questions = get_placement_questions(10)
    if len(questions) < 10:
        await callback.message.edit_text("⚠️ لم يتم إعداد أسئلة كافية بعد. يرجى التواصل مع الأدمن.")
        await callback.answer()
        return
    await state.update_data(score=0, idx=0, questions=questions)
    await state.set_state(PlaceState.q)
    await send_q(callback.message, state, 0)

async def send_q(msg, state, idx):
    data = await state.get_data()
    questions = data.get("questions", [])
    if idx >= len(questions):
        await finish_test(msg, state)
        return
    q = questions[idx]
    opts = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
    btns = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{chr(0x2460+i)} {o}", callback_data=f"pq_{idx}_{i}")]
        for i, o in enumerate(opts)
    ])
    await msg.edit_text(
        f"📝 *سؤال {idx+1} من {len(questions)}*\n\n_{q['question']}_",
        reply_markup=btns, parse_mode="Markdown"
    )

@router.callback_query(PlaceState.q, F.data.startswith("pq_"))
async def handle_place(callback: types.CallbackQuery, state: FSMContext):
    _, idx_s, choice_s = callback.data.split("_")
    idx, choice = int(idx_s), int(choice_s)
    data = await state.get_data()
    questions = data["questions"]
    correct = questions[idx]["correct_option"]
    score = data.get("score", 0)
    if choice == correct:
        score += 1
    await state.update_data(score=score)
    await send_q(callback.message, state, idx + 1)
    await callback.answer()

async def finish_test(msg, state):
    data = await state.get_data()
    score = data.get("score", 0)
    total = len(data.get("questions", []))
    level, label = get_pathway(score)
    uid = msg.chat.id
    set_student_level(uid, level)
    set_placement_done(uid)
    await msg.edit_text(
        f"🎉 *اكتمل اختبار تحديد المستوى!*\n\n"
        f"📊 نتيجتك: *{score}/{total}*\n"
        f"🎯 مستواك: *{label} ({level})*\n\n"
        f"📚 تفضل بزيارة *دوراتي* للبدء بالدروس!\n"
        f"⚡ جرّب *تحدي الـ60 ثانية* لاختبار سرعتك!",
        parse_mode="Markdown"
    )
