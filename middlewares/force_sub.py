# -*- coding: utf-8 -*-
"""
Force Subscribe Middleware — أكاديمية يامن
يمنع استخدام البوت إذا لم يكن الطالب مشتركاً في القناة
"""
from __future__ import annotations
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import settings


# ── قائمة القنوات/المجموعات المطلوبة ────────────────────────────
# أضفها في .env كـ FORCE_SUB_CHANNELS=@channel1,@channel2
import os
_raw = os.environ.get("FORCE_SUB_CHANNELS", settings.GROUP_LINK)
REQUIRED_CHANNELS: list[str] = [
    c.strip() for c in _raw.split(",") if c.strip()
] if _raw else []


def build_force_sub_kb() -> InlineKeyboardMarkup:
    """لوحة مفاتيح الاشتراك الإجباري"""
    kb = InlineKeyboardBuilder()
    for ch in REQUIRED_CHANNELS:
        name = ch.replace("https://t.me/", "@").replace("http://t.me/", "@")
        kb.button(text=f"📢 اشترك في {name}", url=ch if ch.startswith("http") else f"https://t.me/{ch.lstrip('@')}")
    kb.button(text="✅ تحققت من الاشتراك", callback_data="force_sub_check")
    kb.adjust(1)
    return kb.as_markup()


async def is_member(bot, user_id: int, channel: str) -> bool:
    """التحقق من اشتراك المستخدم في قناة معينة"""
    try:
        # تحويل الرابط إلى username
        if channel.startswith("http"):
            # https://t.me/yamen_academy → @yamen_academy
            ch_id = "@" + channel.rstrip("/").split("/")[-1]
        elif not channel.startswith("@") and not channel.startswith("-"):
            ch_id = "@" + channel
        else:
            ch_id = channel

        member = await bot.get_chat_member(ch_id, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        # إذا فشل التحقق (القناة خاصة أو خطأ في الصلاحيات) → اسمح بالمرور
        return True


async def check_all_channels(bot, user_id: int) -> bool:
    """التحقق من الاشتراك في جميع القنوات المطلوبة"""
    if not REQUIRED_CHANNELS:
        return True
    for ch in REQUIRED_CHANNELS:
        if not await is_member(bot, user_id, ch):
            return False
    return True


FORCE_SUB_TEXT = (
    "⛔ <b>الاشتراك مطلوب!</b>\n\n"
    "للوصول إلى أكاديمية يامن، يجب الاشتراك في قناتنا أولاً:\n\n"
    "اضغط على الزر أدناه للاشتراك، ثم اضغط <b>«تحققت من الاشتراك»</b>."
)


class ForceSub(BaseMiddleware):
    """Middleware يتحقق من الاشتراك في القناة قبل كل طلب"""

    # الأوامر المستثناة (تعمل بدون اشتراك)
    EXEMPT_COMMANDS = {"/start", "/help", "/subscribe"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # لا نطبق على غير Message و CallbackQuery
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        # استخراج البيانات الأساسية
        bot      = data.get("bot")
        user     = event.from_user
        if not bot or not user:
            return await handler(event, data)

        # تجاهل الـ Force Sub إذا لا توجد قنوات مضبوطة
        if not REQUIRED_CHANNELS:
            return await handler(event, data)

        # استثناء الأوامر المعفاة
        if isinstance(event, Message) and event.text:
            cmd = event.text.split()[0].lower() if event.text else ""
            if cmd in self.EXEMPT_COMMANDS:
                return await handler(event, data)

        # استثناء callback التحقق نفسه
        if isinstance(event, CallbackQuery) and event.data == "force_sub_check":
            return await handler(event, data)

        # التحقق من الاشتراك
        subscribed = await check_all_channels(bot, user.id)
        if subscribed:
            return await handler(event, data)

        # المستخدم غير مشترك → أرسل رسالة الاشتراك الإجباري
        kb = build_force_sub_kb()
        if isinstance(event, Message):
            await event.answer(FORCE_SUB_TEXT, reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(FORCE_SUB_TEXT, reply_markup=kb)
            except Exception:
                await event.message.answer(FORCE_SUB_TEXT, reply_markup=kb)
            await event.answer("⛔ يجب الاشتراك أولاً!", show_alert=True)

        # لا نكمل معالجة الحدث
        return None
