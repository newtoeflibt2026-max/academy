# -*- coding: utf-8 -*-
"""
إصلاح شامل ونهائي:
1. API endpoints للموافقة/الرفض/الحذف
2. إصلاح جدول payments
3. إصلاح لوحة الأدمن - جميع الأزرار
4. إصلاح handlers/subscriptions.py
"""
import sqlite3, re

DB = "academy.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# ============================================================
# 1. إصلاح جدول payments - أضف أعمدة ناقصة
# ============================================================
print("1. Fixing payments table...")
cols = [r[1] for r in conn.execute("PRAGMA table_info(payments)").fetchall()]
needed = [
    ("plan_key",   "TEXT DEFAULT ''"),
    ("user_name",  "TEXT DEFAULT ''"),
    ("full_name",  "TEXT DEFAULT ''"),
    ("proof_file", "TEXT DEFAULT ''"),
    ("verified_at","TEXT DEFAULT ''"),
    ("notes",      "TEXT DEFAULT ''"),
]
for col, typ in needed:
    if col not in cols:
        conn.execute(f"ALTER TABLE payments ADD COLUMN {col} {typ}")
        print(f"   Added column: {col}")

# sync telegram_id → user_id
conn.execute("""
    UPDATE payments SET user_id = CAST(telegram_id AS INTEGER)
    WHERE telegram_id IS NOT NULL AND telegram_id != ''
    AND (user_id IS NULL OR user_id = 0)
""")
conn.commit()
print("   payments fixed")

# ============================================================
# 2. إصلاح app.py - إضافة endpoints الموافقة/الرفض/الحذف
# ============================================================
print("\n2. Fixing app.py endpoints...")

NEW_ENDPOINTS = '''
# ═══════════════════════════════════════════════════════════
# Payment Approval / Rejection endpoints
# ═══════════════════════════════════════════════════════════

@app.route("/api/admin/payments/<int:pid>/approve", methods=["POST"])
def api_approve_payment(pid):
    from datetime import datetime
    conn = get_db()
    try:
        pay = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not pay:
            return jsonify({"error": "Payment not found"}), 404
        pay = dict(pay)
        uid = pay.get("user_id") or pay.get("telegram_id")
        plan_id = pay.get("plan_id", 1)

        # تفعيل الطالب
        conn.execute("""
            UPDATE students SET is_paid=1, is_active=1,
            subscription_type='paid',
            last_activity=?
            WHERE user_id=? OR telegram_id=?
        """, (datetime.now().isoformat(), uid, str(uid)))

        # تحديث حالة الدفع
        conn.execute("""
            UPDATE payments SET status='approved', verified_at=?
            WHERE id=?
        """, (datetime.now().isoformat(), pid))

        conn.commit()

        # إشعار الطالب عبر البوت
        try:
            import asyncio, os
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            token = os.environ.get("BOT_TOKEN", "")
            if token and uid:
                async def notify():
                    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    await bot.send_message(
                        chat_id=int(uid),
                        text="✅ <b>تم تفعيل اشتراكك!</b>\\n\\nمرحباً بك في أكاديمية يامن للتوفل 🎓\\nابدأ رحلتك التعليمية الآن!"
                    )
                    await bot.session.close()
                asyncio.run(notify())
        except Exception as e:
            print(f"Bot notify error: {e}")

        return jsonify({"ok": True, "message": "تم تفعيل الطالب"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/payments/<int:pid>/reject", methods=["POST"])
def api_reject_payment(pid):
    conn = get_db()
    try:
        pay = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not pay:
            return jsonify({"error": "Payment not found"}), 404
        pay = dict(pay)
        uid = pay.get("user_id") or pay.get("telegram_id")

        conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (pid,))
        conn.commit()

        # إشعار الطالب
        try:
            import asyncio, os
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            token = os.environ.get("BOT_TOKEN", "")
            if token and uid:
                async def notify():
                    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    await bot.send_message(
                        chat_id=int(uid),
                        text="❌ <b>تم رفض طلب الاشتراك</b>\\n\\nيرجى التواصل مع الأدمن للمزيد من المعلومات."
                    )
                    await bot.session.close()
                asyncio.run(notify())
        except Exception as e:
            print(f"Bot notify error: {e}")

        return jsonify({"ok": True, "message": "تم رفض الطلب"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/students/<int:uid>/delete", methods=["DELETE"])
def api_delete_student(uid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM students WHERE user_id=? OR telegram_id=?", (uid, str(uid)))
        conn.execute("DELETE FROM payments WHERE user_id=? OR telegram_id=?", (uid, str(uid)))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/students/<int:uid>/send-message", methods=["POST"])
def api_send_message_to_student(uid):
    d = request.json or {}
    text = d.get("text", "").strip()
    if not text:
        return jsonify({"error": "النص مطلوب"}), 400
    try:
        import asyncio, os
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        token = os.environ.get("BOT_TOKEN", "")
        if not token:
            return jsonify({"error": "BOT_TOKEN غير مضبوط"}), 500
        async def send():
            bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await bot.send_message(chat_id=uid, text=text)
            await bot.session.close()
        asyncio.run(send())
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

with open("app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

added = []
if "api_approve_payment" not in app_content:
    marker = 'if __name__ == "__main__":'
    if marker in app_content:
        app_content = app_content.replace(marker, NEW_ENDPOINTS + "\n" + marker)
    else:
        app_content += NEW_ENDPOINTS
    added.append("approve/reject/delete/send-message endpoints")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_content)

print(f"   Added: {', '.join(added) if added else 'already exists'}")

# ============================================================
# 3. إصلاح لوحة الأدمن - أزرار الموافقة والحذف
# ============================================================
print("\n3. Fixing admin_dashboard.html...")

with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# أضف دوال JavaScript للموافقة والرفض والحذف
JS_FUNCTIONS = """
<script>
// ═══ Payment Actions ═══
async function approvePayment(pid) {
    if (!confirm('تأكيد الموافقة على الدفع وتفعيل الطالب؟')) return;
    const r = await fetch('/api/admin/payments/' + pid + '/approve', {method:'POST'});
    const d = await r.json();
    if (d.ok) { showToast('✅ تم تفعيل الطالب'); loadPayments(); loadStudents(); }
    else showToast('❌ ' + (d.error || 'خطأ'));
}

async function rejectPayment(pid) {
    if (!confirm('تأكيد رفض طلب الدفع؟')) return;
    const r = await fetch('/api/admin/payments/' + pid + '/reject', {method:'POST'});
    const d = await r.json();
    if (d.ok) { showToast('تم الرفض'); loadPayments(); }
    else showToast('❌ ' + (d.error || 'خطأ'));
}

// ═══ Student Actions ═══
async function deleteStudent(uid) {
    if (!confirm('حذف الطالب نهائياً؟ لا يمكن التراجع!')) return;
    const r = await fetch('/api/admin/students/' + uid + '/delete', {method:'DELETE'});
    const d = await r.json();
    if (d.ok) { showToast('تم الحذف'); loadStudents(); }
    else showToast('❌ ' + (d.error || 'خطأ'));
}

async function activateStudent(uid) {
    const r = await fetch('/api/admin/students/' + uid + '/activate-paid', {method:'POST'});
    const d = await r.json();
    if (d.ok) { showToast('✅ تم التفعيل'); loadStudents(); }
    else showToast('❌ ' + (d.error||'خطأ'));
}

async function deactivateStudent(uid) {
    const r = await fetch('/api/admin/students/' + uid + '/deactivate-paid', {method:'POST'});
    const d = await r.json();
    if (d.ok) { showToast('تم إلغاء التفعيل'); loadStudents(); }
    else showToast('❌ ' + (d.error||'خطأ'));
}

async function sendMsgToStudent(uid) {
    const txt = prompt('أدخل الرسالة للطالب:');
    if (!txt) return;
    const r = await fetch('/api/admin/students/' + uid + '/send-message', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({text: txt})
    });
    const d = await r.json();
    if (d.ok) showToast('✅ تم الإرسال');
    else showToast('❌ ' + (d.error||'خطأ'));
}
</script>
"""

if "approvePayment" not in html:
    html = html.replace("</body>", JS_FUNCTIONS + "\n</body>")
    print("   JS functions added")
else:
    print("   JS functions already exist")

# إصلاح جدول الطلاب - إضافة أزرار فعالة
OLD_STUDENT_ROW = "async function loadStudents"
if OLD_STUDENT_ROW in html:
    # ابحث عن دالة loadStudents وأضف أزرار الحذف والإرسال
    html = re.sub(
        r'(btn-sm["\'][^>]*>)(✅|تفعيل)',
        r'\1✅ تفعيل',
        html
    )
    print("   Student buttons updated")

# إصلاح جدول المدفوعات - إضافة أزرار موافقة ورفض
if "approvePayment" not in html:
    # إصلاح دالة loadPayments
    html = re.sub(
        r'(loadPayments[^}]+tbody[^}]+forEach[^}]+\{)',
        r'\1',
        html, flags=re.DOTALL
    )

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print("   admin_dashboard.html saved")

# ============================================================
# 4. تحديث loadPayments في HTML لإضافة أزرار موافقة/رفض
# ============================================================
print("\n4. Injecting payment action buttons in loadPayments...")

with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# ابحث عن دالة loadPayments
pay_func_match = re.search(r'async function loadPayments\(\)[^{]*\{', html)
if pay_func_match:
    # استبدل كامل دالة loadPayments
    NEW_LOAD_PAYMENTS = """async function loadPayments() {
  const d = await API('/api/admin/payments');
  const tb = document.querySelector('#tbl-payments tbody');
  if (!tb) return;
  tb.innerHTML = '';
  (d.payments || []).forEach(p => {
    const st = p.status || 'pending';
    const stClass = st==='approved'?'bg-success':st==='rejected'?'bg-danger':'bg-warning';
    const stAr = st==='approved'?'مفعّل':st==='rejected'?'مرفوض':'انتظار';
    const actions = st==='pending' ? `
      <button class="btn btn-g btn-sm" onclick="approvePayment(${p.id})">✅ موافقة</button>
      <button class="btn btn-d btn-sm" onclick="rejectPayment(${p.id})">❌ رفض</button>
    ` : `<span class="bg ${stClass}">${stAr}</span>`;
    tb.innerHTML += `<tr>
      <td>${p.id}</td>
      <td>${p.full_name||p.user_id||p.telegram_id||'-'}</td>
      <td>${p.plan_name||p.plan_id||'-'}</td>
      <td>${(p.amount||0).toLocaleString()} ${p.currency||'JOD'}</td>
      <td>${actions}</td>
      <td>${(p.created_at||'').slice(0,16)}</td>
    </tr>`;
  });
}"""

    # استبدل الدالة القديمة
    html = re.sub(
        r'async function loadPayments\(\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}',
        NEW_LOAD_PAYMENTS,
        html, count=1, flags=re.DOTALL
    )
    print("   loadPayments function replaced")
else:
    print("   loadPayments not found - adding...")
    html = html.replace("</body>", f"<script>{NEW_LOAD_PAYMENTS}</script>\n</body>")

# إصلاح loadStudents - إضافة أزرار حذف وإرسال
NEW_LOAD_STUDENTS = """async function loadStudents(q='') {
  const d = await API('/api/admin/students' + (q ? '?q=' + encodeURIComponent(q) : ''));
  const tb = document.querySelector('#tbl-students tbody');
  if (!tb) return;
  tb.innerHTML = '';
  (d.students || []).forEach(s => {
    const paid = s.is_paid ? '✅ مفعّل' : '⏳ غير مفعّل';
    const paidClass = s.is_paid ? 'bg-success' : 'bg-warning';
    const uid = s.user_id || s.telegram_id;
    tb.innerHTML += `<tr>
      <td>${uid}</td>
      <td>${s.full_name || s.name || '-'}</td>
      <td>${s.username ? '@'+s.username : '-'}</td>
      <td>${s.level || 'beginner'}</td>
      <td><span class="bg ${paidClass}">${paid}</span></td>
      <td>${s.xp || 0}</td>
      <td style="display:flex;gap:4px;flex-wrap:wrap">
        ${s.is_paid
          ? `<button class="btn btn-d btn-sm" onclick="deactivateStudent(${uid})">🚫 إلغاء</button>`
          : `<button class="btn btn-g btn-sm" onclick="activateStudent(${uid})">✅ تفعيل</button>`
        }
        <button class="btn btn-gh btn-sm" onclick="sendMsgToStudent(${uid})">💬 رسالة</button>
        <button class="btn btn-d btn-sm" onclick="deleteStudent(${uid})">🗑️ حذف</button>
      </td>
    </tr>`;
  });
}"""

html = re.sub(
    r'async function loadStudents\(q[^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}',
    NEW_LOAD_STUDENTS,
    html, count=1, flags=re.DOTALL
)
print("   loadStudents function replaced")

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print("   admin_dashboard.html final save done")

conn.close()
print("\n✅ ALL DONE - Restart the server")
