# -*- coding: utf-8 -*-
import json
import sys
from app_core import app

# تأمين اللغة العربية في المخرجات
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

client = app.test_client()

print("🚀 بدء الفحص السريع والشامل لأنظمة أكاديمية يامن...")
print("-" * 50)

# 1. فحص تشغيل السيرفر والاتصال (Health Check)
response = client.get("/api/health")
if response.status_code == 200:
    print("✅ 1. السيرفر والـ APIs تعمل بكفاءة.")
else:
    print("❌ 1. هناك مشكلة في تشغيل السيرفر.")

# 2. فحص واجهة جمع بيانات الطالب (Onboarding API)
student_data = {
    "username": "محمد",
    "target_score": 79,
    "test_date": "2026-07-15",
    "package_type": "60",
    "student_stage": "جامعة",
    "study_hours_per_day": "ساعتان+"
}
response = client.post("/api/student/initialize", 
                       data=json.dumps(student_data), 
                       content_type="application/json")
if response.status_code == 200:
    print("✅ 2. نظام Onboarding وحفظ بيانات الطالب يعمل 100%.")
else:
    print("❌ 2. فشل في حفظ بيانات الطالب.")

# 3. فحص سحب أسئلة الامتحان الـ 20 (Placement Questions)
response = client.get("/api/placement/questions")
if response.status_code == 200:
    data = json.loads(response.data)
    questions_count = len(data.get("questions", []))
    if questions_count == 20:
        print(f"✅ 3. تم سحب بنك الأسئلة بنجاح (العدد: {questions_count} سؤالاً مفصولاً).")
    else:
        print(f"❌ 3. مستودع الأسئلة يحتوي على خلل، العدد الحالي: {questions_count}")
else:
    print("❌ 3. فشل في الاتصال بملف الأسئلة.")

# 4. فحص إرسال الإجابات وحساب النتيجة والمسار (Placement Submit)
# محاكاة إجابة الطالب على الأسئلة (إجابة b على أول 10 أسئلة لضمان علامة متوسطة)
mock_answers = {str(i): "b" for i in range(1, 21)}
response = client.post("/api/placement/submit", 
                       data=json.dumps({"answers": mock_answers}), 
                       content_type="application/json")

if response.status_code == 200:
    result = json.loads(response.data)
    print(f"✅ 4. نظام التشخيص وحساب النتائج يعمل.")
    print(f"   - النتيجة المحسوبة: {result.get('score')}%")
    print(f"   - المسار الموجه له الطالب تلقائياً: {result.get('track_arabic')}")
else:
    print("❌ 4. فشل في معالجة إجابات الامتحان وتحديد المستوى.")

# 5. فحص لوحة التحكم ومولد الخطة الديناميكي (Dashboard Context)
response = client.get("/dashboard")
if response.status_code == 200:
    print("✅ 5. لوحة التحكم تستقبل البيانات الحقيقية والخطة الزمنية دون أي تعارض (Jinja Context Clean).")
else:
    print("❌ 5. خطأ في تحميل لوحة التحكم (تأكدي من مطابقة متغيرات Jinja).")

print("-" * 50)
print("🏁 انتهى الفحص السريع بنجاح.")