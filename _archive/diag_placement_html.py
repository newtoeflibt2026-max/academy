with open("templates/placement.html", "r", encoding="utf-8") as f:
    html = f.read()

print("=== SIZE ===")
print(len(html), "bytes")
print()

# Find fetch/axios/XMLHttpRequest URLs
keywords = ["fetch(", "axios(", "XMLHttpRequest", ".open(", "POST", "/api/", "/placement", "submit"]
for kw in keywords:
    if kw in html:
        idx = html.find(kw)
        snippet = html[max(0, idx-30):idx+80].replace("\n", " ").replace("\r", "")
        print("FOUND '{}' at {}: ...{}...".format(kw, idx, snippet))
    else:
        print("NOT FOUND: {}".format(kw))

# Find <script> tags
import re
scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
print()
print("=== EXTERNAL SCRIPTS ===")
for s in scripts:
    print("  " + s)

# Find inline scripts
inline = re.findall(r'<script[^>]*>([\s\S]*?)</script>', html)
print()
print("=== INLINE SCRIPTS ({}) ===".format(len(inline)))
for i, s in enumerate(inline):
    s_clean = s.strip()[:200].replace("\n", " ")
    print("  #{}: {}".format(i+1, s_clean[:150]))
