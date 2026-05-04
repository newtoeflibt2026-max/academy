from aiogram.utils.keyboard import InlineKeyboardBuilder

def start_test_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 ابدأ اختبار تحديد المستوى", callback_data="start_test")
    kb.button(text="💎 الاشتراكات", callback_data="menu_subscribe")
    kb.button(text="🏆 لوحة الشرف", callback_data="menu_leaderboard")
    kb.button(text="ℹ️ عن الأكاديمية", callback_data="about")
    kb.adjust(1)
    return kb

def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 اختبار تحديد المستوى", callback_data="start_test")
    kb.button(text="📚 دوراتي", callback_data="my_courses")
    kb.button(text="💎 الاشتراكات", callback_data="menu_subscribe")
    kb.button(text="⚡ تحدي 60 ثانية", callback_data="daily_challenge")
    kb.button(text="🏆 لوحة الشرف", callback_data="menu_leaderboard")
    kb.button(text="📊 تقدمي", callback_data="my_progress")
    kb.button(text="ℹ️ عن الأكاديمية", callback_data="about")
    kb.adjust(1, 2, 2, 2)
    return kb

def back_kb(target: str = "main_menu"):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 رجوع", callback_data=target)
    return kb
