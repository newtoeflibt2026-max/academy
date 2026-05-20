with open("templates/placement.html", "r", encoding="utf-8") as f:
    html = f.read()

check = "اختبار"
if check in html:
    print("OK: Arabic text is correct in file - no encoding issue")
else:
    print("PROBLEM: Arabic text garbled in file")

has_meta = '<meta charset' in html
print("Has charset meta: " + str(has_meta))

if not has_meta:
    html = html.replace("<head>", '<head>\n<meta charset="UTF-8">')
    with open("templates/placement.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Added UTF-8 meta tag")

print("DONE")
