# -*- coding: utf-8 -*-
import os, sqlite3, sys, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates", "reading", "exam_screen.html")
RES = os.path.join(ROOT, "templates", "reading", "result.html")
DB  = "C:/app/data/academy.db" if os.path.exists("C:/app/data/academy.db") else os.path.join(ROOT, "data", "academy.db")
errors = []
def check(cond, msg):
    if cond: print("  PASS:", msg)
    else: print("  FAIL:", msg); errors.append(msg)
print("[T1] exam_screen.html")
html = open(TPL, encoding="utf-8").read()
check(".q-text-ar.revealed" in html, "CSS .q-text-ar.revealed exists")
check("opacity: 0" in html, "default opacity: 0")
check("visibility: hidden" in html, "default visibility: hidden")
check("updateArabicTranslation" in html, "updateArabicTranslation function")
check("IS_FRESH_ATTEMPT" in html, "IS_FRESH_ATTEMPT flag")
m = re.search(r"<div class=\"q-text-ar\"[^>]*id=\"qTextAr\"", html)
if m: check("revealed" not in m.group(0), "no revealed class in initial HTML")
print("[T2] result.html")
res = open(RES, encoding="utf-8").read()
check("raw_score" in res, "raw_score variable")
check("correct_count" in res, "correct_count variable")
print("[T3] DB integrity")
if os.path.exists(DB):
    c = sqlite3.connect(DB)
    bad = c.execute("SELECT COUNT(*) FROM reading_attempts WHERE status=? AND score > total", ("completed",)).fetchone()[0]
    check(bad == 0, "no score > total in completed (found: %d)" % bad)
    subm = c.execute("SELECT COUNT(*) FROM reading_attempts WHERE status=?", ("submitted",)).fetchone()[0]
    check(subm == 0, "no status=submitted (found: %d)" % subm)
    c.close()
print("=" * 50)
if errors: print("FAIL: %d tests failed" % len(errors)); sys.exit(1)
else: print("ALL TESTS PASSED"); sys.exit(0)

