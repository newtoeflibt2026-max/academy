# -*- coding: utf-8 -*-
"""
handlers/admin.py — لوحة تحكم الأدمن من البوت
- /admin  : رابط لوحة التحكم
- /stats  : إحصائيات سريعة
- /students : إدارة الطلاب بالأزرار (تفعيل قسم / حذف)
"""
import sqlite3
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from config import settings
NL = chr(10)

router = Router(name="admin")

# خريطة الأقسام: (الكود, الاسم المعروض, مدة بالأيام)
SECTIONS = [
    ("writing",    "✍️ الكتابة",    45),
    ("reading",    "📖 القراءة",    45),
    ("listening",  "🎧 الاستماع",   45),
    ("speaking",   "🗣️ المحادثة",   45),
    ("foundation", "🏗️ التأسيس",    45),
    ("mock",       "📝 التجريبية",  15),
    ("full",       "👑 الشاملة",    90),
    ("free",       "🆓 المجانية",   15),
]


def _is_admin(uid):
    return uid in settings.ADMIN_IDS


# ══ /admin ════════════════════════════════════
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ هذا الأمر متاح للأدمن فقط.")
        return
    panel_url = settings.WEBHOOK_HOST.rstrip("/") + "/"
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 فتح لوحة التحكم", url=panel_url)
    kb.button(text="👥 إدارة الطلاب (بالبوت)", callback_data="adm_students:0")
    kb.adjust(1)
    await message.answer(
        f"👑 <b>لوحة تحكم الأدمن</b>\n\n"
        f"مرحباً {message.from_user.full_name} 👋\n\n"
        f"اكتب /students لإدارة الطلاب مباشرة من البوت.",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )


# ══ /stats ════════════════════════════════════
@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not _is_admin(message.from_user.id):
        return
    try:
        conn = sqlite3.connect(settings.DB_PATH); cur = conn.cursor()
        s_total = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        s_paid  = cur.execute("SELECT COUNT(*) FROM students WHERE is_paid=1").fetchone()[0]
        p_pend  = cur.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
        conn.close()
    except Exception as e:
        await message.answer(f"❌ خطأ: {e}"); return
    await message.answer(
        f"📊 <b>إحصائيات</b>\n\n"
        f"👥 الطلاب: <b>{s_total}</b>\n"
        f"💰 المدفوعين: <b>{s_paid}</b>\n"
        f"⏳ بانتظار: <b>{p_pend}</b>",
        parse_mode="HTML"
    )


# ══ /students : قائمة الطلاب ══════════════════
@router.message(Command("students"))
async def cmd_students(message: types.Message):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ للأدمن فقط.")
        return
    await _show_students(message, 0)


@router.callback_query(F.data.startswith("adm_students:"))
async def cb_students(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    await cb.answer()
    page = int(cb.data.split(":")[1])
    await _show_students(cb.message, page, edit=True)


async def _show_students(target, page, edit=False):
    conn = sqlite3.connect(settings.DB_PATH); conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT telegram_id, full_name, name, username, subscription_type, subscription_section, is_paid "
        "FROM students ORDER BY rowid DESC").fetchall()
    conn.close()

    per = 6
    total = len(rows)
    start = page * per
    chunk = rows[start:start + per]

    text = f"👥 <b>إدارة الطلاب</b> ({total})\n\n"
    kb = InlineKeyboardBuilder()
    if not chunk:
        text += "لا يوجد طلاب."
    for r in chunk:
        tid  = r["telegram_id"]
        name = (r["full_name"] or r["username"] or (r["name"] if r["name"] not in (None,"","طالب") else None) or f"👤 {r['telegram_id']}")
        sec  = r["subscription_section"] or "—"
        paid = "✅" if r["is_paid"] else "⏳"
        text += f"{paid} <b>{name}</b>\n   🆔 <code>{tid}</code> | قسم: {sec}\n\n"
        btn_label = (r["full_name"] or r["username"] or (r["name"] if r["name"] not in (None,"","طالب") else None) or str(tid)); kb.button(text=f"⚙️ {btn_label[:20]}", callback_data=f"adm_pick:{tid}")
    kb.adjust(1)

    # أزرار التنقل
    nav = []
    if start > 0:
        nav.append(("◀️ السابق", f"adm_students:{page-1}"))
    if start + per < total:
        nav.append(("التالي ▶️", f"adm_students:{page+1}"))
    for t, d in nav:
        kb.button(text=t, callback_data=d)
    if nav:
        kb.adjust(1, len(nav))

    markup = kb.as_markup()
    if edit:
        try:
            await target.edit_text(text, reply_markup=markup, parse_mode="HTML")
            return
        except Exception:
            pass
    await target.answer(text, reply_markup=markup, parse_mode="HTML")


# ══ اختيار طالب : عرض خياراته ═════════════════
@router.callback_query(F.data.startswith("adm_pick:"))
async def cb_pick(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    await cb.answer()
    tid = cb.data.split(":")[1]

    conn = sqlite3.connect(settings.DB_PATH); conn.row_factory = sqlite3.Row
    r = conn.execute(
        "SELECT telegram_id, full_name, name, username, subscription_type, subscription_section, is_paid, package_end "
        "FROM students WHERE telegram_id=?", (tid,)).fetchone()
    conn.close()
    if not r:
        await cb.message.answer("❌ الطالب غير موجود."); return

    name = (r["full_name"] or r["username"] or (r["name"] if r["name"] not in (None,"","طالب") else None) or f"👤 {r['telegram_id']}")
    text = (f"👤 <b>{name}</b>\n"
            f"🆔 <code>{tid}</code>\n"
            f"📦 النوع: {r['subscription_type'] or '—'}\n"
            f"🔑 القسم: {r['subscription_section'] or '—'}\n"
            f"💰 مدفوع: {'نعم' if r['is_paid'] else 'لا'}\n"
            f"📅 ينتهي: {r['package_end'] or '—'}\n\n"
            f"اختر إجراءً:")
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ تفعيل قسم", callback_data=f"adm_act:{tid}")
    kb.button(text="🚫 إيقاف", callback_data=f"adm_stop:{tid}")
    kb.button(text="🗑️ حذف نهائي", callback_data=f"adm_del:{tid}")
    kb.button(text="◀️ رجوع", callback_data="adm_students:0")
    kb.adjust(1)
    await cb.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# ══ تفعيل قسم : عرض الأقسام ════════════════════
@router.callback_query(F.data.startswith("adm_act:"))
async def cb_activate_menu(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    await cb.answer()
    tid = cb.data.split(":")[1]
    _MULTI_SEC.setdefault(tid, set())
    sel = _MULTI_SEC[tid]
    kb = InlineKeyboardBuilder()
    for code, label, days in SECTIONS:
        mark = "✅ " if code in sel else ""
        kb.button(text=f"{mark}{label}", callback_data=f"adm_multisec:{tid}:{code}")
    kb.button(text="🔓 Full", callback_data=f"adm_multisec:{tid}:__full__")
    kb.button(text="✔️ تأكيد", callback_data=f"adm_confirmsec:{tid}")
    kb.button(text="◀️ رجوع", callback_data=f"adm_pick:{tid}")
    kb.adjust(2, 2, 1, 1)
    chosen = "، ".join(sorted(sel)) if sel else "لا شيء"
    _t = "🔑 اختر الأقسام ثم تأكيد" + NL + "المختار: <b>" + chosen + "</b>"
    await cb.message.answer(_t, reply_markup=kb.as_markup(), parse_mode="HTML")


_MULTI_SEC = {}

@router.callback_query(F.data.startswith("adm_multisec:"))
async def cb_multisec(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    parts = cb.data.split(":")
    tid, code = parts[1], parts[2]
    sel = _MULTI_SEC.setdefault(tid, set())
    if code == "__full__":
        sel.clear(); sel.add("__full__")
    else:
        sel.discard("__full__")
        if code in sel: sel.discard(code)
        else: sel.add(code)
    await cb.answer()
    kb = InlineKeyboardBuilder()
    for c, label, days in SECTIONS:
        mark = "✅ " if c in sel else ""
        kb.button(text=f"{mark}{label}", callback_data=f"adm_multisec:{tid}:{c}")
    fullmark = "✅ " if "__full__" in sel else ""
    kb.button(text=f"{fullmark}🔓 Full", callback_data=f"adm_multisec:{tid}:__full__")
    kb.button(text="✔️ تأكيد", callback_data=f"adm_confirmsec:{tid}")
    kb.button(text="◀️ رجوع", callback_data=f"adm_pick:{tid}")
    kb.adjust(2, 2, 1, 1)
    chosen = "Full Access" if "__full__" in sel else ("، ".join(sorted(sel)) if sel else "لا شيء")
    _t = "🔑 اختر الأقسام ثم تأكيد" + NL + "المختار: <b>" + chosen + "</b>"
    try:
        await cb.message.edit_text(_t, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_confirmsec:"))
async def cb_confirmsec(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    tid = cb.data.split(":")[1]
    sel = _MULTI_SEC.get(tid, set())
    if not sel:
        await cb.answer("⚠️ اختر قسماً", show_alert=True); return
    if "__full__" in sel:
        section_value = "full"; label = "Full Access"
    else:
        section_value = ",".join(sorted(sel))
        labels = []
        for code in sorted(sel):
            for c, l, d in SECTIONS:
                if c == code: labels.append(l); break
        label = "، ".join(labels) if labels else section_value
    end_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(settings.DB_PATH)
    conn.execute(
        "UPDATE students SET is_paid=1, is_active=1, subscription_type=?, "
        "subscription_section=?, package_end=? WHERE telegram_id=?",
        (label, section_value, end_date, tid))
    conn.commit(); conn.close()
    _MULTI_SEC.pop(tid, None)
    notify = "تم إرسال إشعار ✅"
    try:
        _m = "🎉 <b>تم تفعيل اشتراكك!</b>" + NL + NL + "📦 الأقسام: <b>" + label + "</b>" + NL + "📅 ينتهي: <b>" + end_date + "</b>" + NL + NL + "✨ اكتب /start 🚀"
        await cb.bot.send_message(int(tid), _m, parse_mode="HTML")
    except Exception as e:
        notify = "⚠️ لم يصل الإشعار: " + str(e)
    from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
    _kb = _IKB()
    _kb.button(text="📚 وصول منتظم", callback_data=f"adm_mode:{tid}:sequential")
    _kb.button(text="🔓 وصول كامل", callback_data=f"adm_mode:{tid}:full")
    _kb.adjust(1)
    await cb.answer("✅ تم التفعيل", show_alert=True)
    _r = "✅ تم تفعيل <b>" + label + "</b> للطالب <code>" + tid + "</code>." + NL + notify + NL + NL + "⚙️ اختر نمط الوصول:"
    await cb.message.answer(_r, reply_markup=_kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_setsec:"))
async def cb_setsec(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    parts = cb.data.split(":")
    tid, code = parts[1], parts[2]
    label, days = code, 45
    for c, l, d in SECTIONS:
        if c == code:
            label, days = l, d; break
    end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    conn = sqlite3.connect(settings.DB_PATH)
    conn.execute(
        "UPDATE students SET is_paid=1, is_active=1, subscription_type=?, "
        "subscription_section=?, package_end=? WHERE telegram_id=?",
        (label, code, end_date, tid))
    conn.commit(); conn.close()
    notify_status = "تم إرسال إشعار للطالب ✅"
    try:
        await cb.bot.send_message(int(tid), f"🎉 <b>تم تفعيل اشتراكك!</b>\n\n📦 القسم: <b>{label}</b>\n📅 ينتهي في: <b>{end_date}</b>\n\n✨ اكتب /start وابدأ التعلم الآن! 🚀", parse_mode="HTML")
    except Exception as e:
        notify_status = f"⚠️ لم يصل الإشعار للطالب: {e}"
    from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
    _kb = _IKB()
    _kb.button(text="📚 وصول منتظم (بالترتيب)", callback_data=f"adm_mode:{tid}:sequential")
    _kb.button(text="🔓 وصول كامل (كل الدروس)", callback_data=f"adm_mode:{tid}:full")
    _kb.adjust(1)
    await cb.answer("✅ تم التفعيل", show_alert=True)
    await cb.message.answer(f"✅ تم تفعيل قسم <b>{label}</b> للطالب <code>{tid}</code>.\n{notify_status}\n\n⚙️ اختر نمط الوصول:", reply_markup=_kb.as_markup(), parse_mode="HTML")
    return
    await cb.message.answer(f"✅ تم تفعيل قسم <b>{label}</b> للطالب <code>{tid}</code> حتى {end_date}.\n{notify_status}", parse_mode="HTML")


# ══ إيقاف ═════════════════════════════════════
@router.callback_query(F.data.startswith("adm_stop:"))
async def cb_stop(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    tid = cb.data.split(":")[1]
    conn = sqlite3.connect(settings.DB_PATH)
    conn.execute("UPDATE students SET is_paid=0, is_active=0 WHERE telegram_id=?", (tid,))
    conn.commit(); conn.close()
    await cb.answer("🚫 تم الإيقاف", show_alert=True)
    await cb.message.answer(f"🚫 تم إيقاف الطالب <code>{tid}</code>.", parse_mode="HTML")


# ══ حذف نهائي : تأكيد ═════════════════════════
@router.callback_query(F.data.startswith("adm_del:"))
async def cb_del_confirm(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    await cb.answer()
    tid = cb.data.split(":")[1]
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ نعم، احذف نهائياً", callback_data=f"adm_delok:{tid}")
    kb.button(text="◀️ إلغاء", callback_data=f"adm_pick:{tid}")
    kb.adjust(1)
    await cb.message.answer(
        f"⚠️ هل تريد حذف الطالب <code>{tid}</code> نهائياً من كل الجداول؟\n"
        f"لا يمكن التراجع.", reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_delok:"))
async def cb_del_ok(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    tid = cb.data.split(":")[1]
    conn = sqlite3.connect(settings.DB_PATH)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    deleted = {}
    for t in tables:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
        for col in ("telegram_id", "user_id"):
            if col in cols:
                cur = conn.execute(f"DELETE FROM {t} WHERE {col}=?", (str(tid),))
                if cur.rowcount:
                    deleted[t] = deleted.get(t, 0) + cur.rowcount
    conn.commit(); conn.close()
    await cb.answer("🗑️ تم الحذف", show_alert=True)
    summary = "\n".join(f"• {k}: {v}" for k, v in deleted.items()) or "لا شيء"
    await cb.message.answer(
        f"🗑️ تم حذف الطالب <code>{tid}</code> نهائياً.\n\nمن الجداول:\n{summary}",
        parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_mode:"))
async def cb_setmode(cb: types.CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔", show_alert=True); return
    parts = cb.data.split(":")
    tid, mode = parts[1], parts[2]
    conn = sqlite3.connect(settings.DB_PATH)
    conn.execute("UPDATE students SET access_mode=? WHERE telegram_id=?", (mode, tid))
    conn.commit(); conn.close()
    if mode == "full":
        msg = "🔓 تم فتح جميع الدروس للطالب (وصول كامل)."
    else:
        msg = "📚 الطالب يمشي بالترتيب (وصول منتظم)."
    await cb.answer("✅ تم الحفظ", show_alert=True)
    await cb.message.answer(f"{msg}\n<code>{tid}</code>", parse_mode="HTML")


# ══ /promo : رسالة تسويقية لمن قدّم الاختبار ولم يشترك ═══════════
_PROMO_CACHE = {}

@router.message(Command("promo"))
async def cmd_promo(message: types.Message):
    if not _is_admin(message.from_user.id):
        await message.answer("\u26d4 \u0647\u0630\u0627 \u0627\u0644\u0623\u0645\u0631 \u0644\u0644\u0623\u062f\u0645\u0646 \u0641\u0642\u0637.")
        return
    text = message.text or ""
    body = text.partition(" ")[2].strip()
    if not body:
        await message.answer(
            "\U0001F4E2 <b>\u0631\u0633\u0627\u0644\u0629 \u062a\u0633\u0648\u064a\u0642\u064a\u0629</b>\n\n"
            "\u0627\u0643\u062a\u0628 \u0627\u0644\u0623\u0645\u0631 \u0647\u0643\u0630\u0627:\n"
            "<code>/promo \u0646\u0635 \u0631\u0633\u0627\u0644\u062a\u0643 \u0627\u0644\u062a\u0633\u0648\u064a\u0642\u064a\u0629 \u0647\u0646\u0627</code>\n\n"
            "\u0633\u062a\u0635\u0644 \u0644\u0643\u0644 \u0637\u0627\u0644\u0628 \u0623\u0646\u0647\u0649 \u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631 \u0648\u0644\u0645 \u064a\u0634\u062a\u0631\u0643.",
            parse_mode="HTML")
        return
    conn = sqlite3.connect(settings.DB_PATH, timeout=30.0)
    rows = conn.execute(
        "SELECT telegram_id FROM students WHERE placement_done=1 AND (is_paid=0 OR is_paid IS NULL) AND telegram_id IS NOT NULL AND telegram_id != ''"
    ).fetchall()
    conn.close()
    targets = [r[0] for r in rows if str(r[0]).strip().isdigit()]
    if not targets:
        await message.answer("\u2139\ufe0f \u0644\u0627 \u064a\u0648\u062c\u062f \u0637\u0644\u0627\u0628 \u064a\u0637\u0627\u0628\u0642\u0648\u0646 \u0627\u0644\u0634\u0631\u0637.")
        return
    _PROMO_CACHE[message.from_user.id] = {"body": body, "targets": targets}
    kb = InlineKeyboardBuilder()
    kb.button(text="\u2705 \u062a\u0623\u0643\u064a\u062f \u0627\u0644\u0625\u0631\u0633\u0627\u0644", callback_data="promo_send")
    kb.button(text="\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="promo_cancel")
    kb.adjust(1)
    preview = (
        "\U0001F4E2 <b>\u0645\u0639\u0627\u064a\u0646\u0629 \u0627\u0644\u0631\u0633\u0627\u0644\u0629</b>\n\n"
        "\U0001F465 \u0633\u062a\u0635\u0644 \u0644\u0640 <b>" + str(len(targets)) + "</b> \u0637\u0627\u0644\u0628\n\n"
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n" + body + "\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
    )
    await message.answer(preview, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "promo_cancel")
async def cb_promo_cancel(callback: types.CallbackQuery):
    _PROMO_CACHE.pop(callback.from_user.id, None)
    await callback.message.edit_text("\u274c \u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0625\u0631\u0633\u0627\u0644.")
    await callback.answer()


@router.callback_query(F.data == "promo_send")
async def cb_promo_send(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("\u26d4", show_alert=True); return
    job = _PROMO_CACHE.pop(callback.from_user.id, None)
    if not job:
        await callback.message.edit_text("\u26a0\ufe0f \u0627\u0646\u062a\u0647\u062a \u0635\u0644\u0627\u062d\u064a\u0629 \u0627\u0644\u0631\u0633\u0627\u0644\u0629. \u0623\u0639\u062f /promo.")
        await callback.answer(); return
    await callback.answer("\u062c\u0627\u0631\u064d \u0627\u0644\u0625\u0631\u0633\u0627\u0644...")
    plans_url = settings.WEBHOOK_HOST.rstrip("/") + "/miniapp/plans"
    sent = 0; failed = 0
    for tid in job["targets"]:
        try:
            kb = InlineKeyboardBuilder()
            kb.button(text="\U0001F4B3 \u0639\u0631\u0636 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0648\u0627\u0644\u0639\u0631\u0648\u0636", url=plans_url)
            await callback.bot.send_message(int(tid), job["body"], reply_markup=kb.as_markup())
            sent += 1
        except Exception:
            failed += 1
    await callback.message.edit_text(
        "\u2705 <b>\u0627\u0643\u062a\u0645\u0644 \u0627\u0644\u0625\u0631\u0633\u0627\u0644</b>\n\n"
        "\U0001F4E4 \u0648\u0635\u0644\u062a: <b>" + str(sent) + "</b>\n"
        "\u26a0\ufe0f \u0641\u0634\u0644\u062a (\u062d\u0638\u0631\u0648\u0627 \u0627\u0644\u0628\u0648\u062a): <b>" + str(failed) + "</b>",
        parse_mode="HTML")
