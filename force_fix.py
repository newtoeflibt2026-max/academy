import re, shutil, datetime, sys
sys.stdout.reconfigure(encoding="utf-8")

TPL = r"C:\Users\nelt2\yamen_academy\templates\toefl_writing\discussion_exam.html"
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(TPL, TPL + ".bak_force_" + ts)

with open(TPL, "r", encoding="utf-8") as f:
    html = f.read()
print("Original size:", len(html))

NEW_FUNC = (
    'function submitResponse() {\n'
    '  const text = textarea.value.trim();\n'
    '  const words = text.split(/[\\s]+/).filter(w => w.length > 0).length;\n'
    '  if (words < MIN_WORDS) {\n'
    '    showConfirm("You wrote " + words + " words. Minimum is " + MIN_WORDS + ". Submit anyway?", function() { doSubmitFinal(); });\n'
    '    return;\n'
    '  }\n'
    '  doSubmitFinal();\n'
    '}\n'
    'function doSubmitFinal() {\n'
    '  showModal("Success", "Response saved successfully!");\n'
    '}'
)

pattern = r"function submitResponse\(\)\s*\{.*?\n\}"
new_html, n = re.subn(pattern, lambda m: NEW_FUNC, html, count=1, flags=re.DOTALL)

print("Replacements made:", n)

with open(TPL, "w", encoding="utf-8", newline="\n") as f:
    f.write(new_html)

print("New size:", len(new_html))
print("showConfirm present:", "showConfirm(" in new_html)
print("doSubmitFinal present:", "doSubmitFinal" in new_html)
print("Old !confirm gone:", "!confirm(" not in new_html)
print("DONE")
