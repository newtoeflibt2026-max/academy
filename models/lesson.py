<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Elite Veterinary Clinic | رعاية بيطرية متميزة</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700&family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Tajawal', sans-serif; }
        .en-font { font-family: 'Poppins', sans-serif; }
        .glass-effect { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }
    </style>
</head>
<body class="bg-slate-50 text-slate-800">

    <nav class="fixed w-full z-50 glass-effect border-b border-slate-200">
        <div class="container mx-auto px-6 py-4 flex justify-between items-center">
            <div class="text-2xl font-bold text-cyan-900">EliteVet <span class="en-font text-sm text-cyan-600 block">Clinic</span></div>
            <div class="flex gap-6 items-center">
                <a href="#services" class="hover:text-cyan-600 transition">الخدمات</a>
                <a href="#about" class="hover:text-cyan-600 transition">عن العيادة</a>
                <a href="tel:0000000" class="bg-cyan-900 text-white px-6 py-2 rounded-full hover:bg-cyan-800 transition">احجز الآن</a>
            </div>
        </div>
    </nav>

    <section class="pt-32 pb-20 px-6 container mx-auto text-center">
        <h1 class="text-5xl md:text-7xl font-bold text-slate-900 mb-6">رعاية طبية تخصصية لحيوانك الأليف</h1>
        <p class="text-xl text-slate-600 mb-10 max-w-2xl mx-auto">نحن ندمج بين التكنولوجيا الحديثة والخصوصية العالية لتقديم تجربة علاجية لا مثيل لها.</p>
        <div class="flex justify-center gap-4">
            <button class="bg-cyan-600 text-white px-8 py-4 rounded-lg font-bold shadow-lg hover:bg-cyan-700">طلب فريق الإنقاذ (توصيل مجاني)</button>
        </div>
    </section>

    <section id="services" class="py-20 bg-white">
        <div class="container mx-auto px-6">
            <h2 class="text-4xl font-bold text-center mb-16">لماذا عيادتنا؟</h2>
            <div class="grid md:grid-cols-3 gap-10">
                <div class="p-8 bg-slate-50 rounded-2xl border border-slate-100 hover:shadow-xl transition">
                    <div class="text-4xl mb-4">🏥</div>
                    <h3 class="text-2xl font-bold mb-2">بيئة معقمة كلياً</h3>
                    <p>بروتوكولات تعقيم صارمة تضمن سلامة أليفك في غرف العمليات.</p>
                </div>
                <div class="p-8 bg-slate-50 rounded-2xl border border-slate-100 hover:shadow-xl transition">
                    <div class="text-4xl mb-4">🤫</div>
                    <h3 class="text-2xl font-bold mb-2">خصوصية تامة</h3>
                    <p>نظام خاص يضمن الهدوء التام للحيوان بعيداً عن صخب العيادات العامة.</p>
                </div>
                <div class="p-8 bg-slate-50 rounded-2xl border border-slate-100 hover:shadow-xl transition">
                    <div class="text-4xl mb-4">🚚</div>
                    <h3 class="text-2xl font-bold mb-2">توصيل مجاني للإنقاذ</h3>
                    <p>فريقنا يصل إليك فوراً لنقل الحالة بسلامة إلى العيادة.</p>
                </div>
            </div>
        </div>
    </section>

    <section class="py-20 bg-cyan-900 text-white">
        <div class="container mx-auto px-6 text-center">
            <h2 class="text-3xl font-bold mb-6">جاهز للبدء؟</h2>
            <p class="mb-10 text-cyan-100">نحن هنا للحالات الطارئة والاستشارات التخصصية.</p>
            <a href="#" class="bg-white text-cyan-900 px-10 py-4 rounded-lg font-bold hover:bg-slate-100">تواصل مع الفريق الطبي</a>
        </div>
    </section>

    <footer class="py-10 text-center text-slate-500">
        © 2026 Elite Veterinary Clinic. جميع الحقوق محفوظة.
    </footer>

</body>
</html>