import io
p = "handlers/placement_inline.py"
s = io.open(p, encoding="utf-8").read()
old = "        \"• نتيجة 50 بالمئة فأكثر تعني TOEFL مباشرة\\n\\n\""
new = "        \"• ونرسم لك خطة دراسة تناسب مستواك تماماً\\n\\n\""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("FIXED last line")
elif "خطة دراسة تناسب مستواك" in s:
    print("ALREADY FIXED")
else:
    print("PATTERN NOT FOUND")
