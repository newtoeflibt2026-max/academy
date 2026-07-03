import io, os
os.makedirs("templates/toefl_writing", exist_ok=True)
html = """<!DOCTYPE html>
<html lang=\"ar\" dir=\"rtl\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>راجع أخطائي</title>
<style>
body{font-family:'Segoe UI',Tahoma,sans-serif;background:#f5f7fb;margin:0;padding:20px;color:#1a202c}
.wrap{max-width:760px;margin:0 auto}
.head{text-align:center;margin-bottom:20px}
.head h1{color:#1e3a5f;margin:0 0 6px}
.count{color:#64748b;font-size:14px}
.back{display:inline-block;margin-bottom:14px;color:#3b82f6;text-decoration:none;font-weight:600}
.card{background:#fff;border-radius:14px;padding:16px 18px;margin-bottom:14px;box-shadow:0 2px 10px rgba(0,0,0,.06);border-right:4px solid #ef4444}
.q{font-weight:700;margin-bottom:10px;color:#0f172a}
.line{margin:6px 0;font-size:15px}
.lbl{color:#64748b;font-weight:600;margin-left:6px}
.wrong{color:#dc2626;text-decoration:line-through}
.right{color:#059669;font-weight:700}
.note{background:#f8fafc;border-radius:8px;padding:8px 10px;margin-top:8px;font-size:14px;color:#334155}
.empty{text-align:center;background:#fff;border-radius:14px;padding:40px 20px;color:#64748b}
.en{direction:ltr;text-align:left;font-family:'Segoe UI',sans-serif}
</style>
</head>
<body>
<div class=\"wrap\">
  <a class=\"back\" href=\"/writing?user_id={{ user_id }}\">← العودة للمسار</a>
  <div class=\"head\">
    <h1>📝 راجع أخطائي</h1>
    <div class=\"count\">عدد الأخطاء المسجلة: {{ total }}</div>
  </div>
  {% if mistakes %}
    {% for m in mistakes %}
    <div class=\"card\">
      {% if m.question_ar %}<div class=\"q\">{{ m.question_ar }}</div>{% endif %}
      {% if m.user_answer %}<div class=\"line\"><span class=\"lbl\">إجابتك:</span> <span class=\"wrong en\">{{ m.user_answer }}</span></div>{% endif %}
      <div class=\"line\"><span class=\"lbl\">الصحيح:</span> <span class=\"right en\">✓ {{ m.correct_answer }}</span></div>
      {% if m.arabic_translation %}<div class=\"line\">🌍 <span class=\"lbl\">الترجمة:</span> {{ m.arabic_translation }}</div>{% endif %}
      {% if m.rule_applied %}<div class=\"note\">📐 <b>القاعدة:</b> {{ m.rule_applied }}</div>{% endif %}
      {% if m.strategy_ar %}<div class=\"note\">🎯 <b>الاستراتيجية:</b> {{ m.strategy_ar }}</div>{% endif %}
      {% if m.explanation_ar %}<div class=\"note\">💡 <b>الشرح:</b> {{ m.explanation_ar }}</div>{% endif %}
      {% if m.common_error_ar %}<div class=\"note\">⚠️ <b>خطأ شائع:</b> {{ m.common_error_ar }}</div>{% endif %}
    </div>
    {% endfor %}
  {% else %}
    <div class=\"empty\">🎉 لا توجد أخطاء مسجلة بعد!<br>حلّ بعض الدروس والامتحانات وستظهر أخطاؤك هنا لمراجعتها.</div>
  {% endif %}
</div>
</body>
</html>
"""
io.open("templates/toefl_writing/my_mistakes.html", "w", encoding="utf-8").write(html)
print("TEMPLATE CREATED")
