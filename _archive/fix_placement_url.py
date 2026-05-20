"""SURGICAL FIX: Change /placement/submit to /api/placement/submit in placement.html"""
with open("templates/placement.html", "r", encoding="utf-8") as f:
    html = f.read()

old = '/placement/submit"'
new = '/api/placement/submit"'

if old in html:
    html = html.replace(old, new)
    with open("templates/placement.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] Changed /placement/submit -> /api/placement/submit")
else:
    print("[WARN] /placement/submit not found - searching...")
    # Check what's actually there
    idx = html.find("/placement/submit")
    if idx == -1:
        idx = html.find('placement/submit')
    if idx != -1:
        sni

ppet = html[idx-20:idx+60]
        print("Found at {}: ...{}...".format(idx, snippet))
    else:
        print("Could not find placement/submit anywhere")

# Verify
print()
print("=== VERIFICATION ===")
print("/api/placement/submit found: {}".format("/api/placement/submit" in html))
print("/placement/submit found: {}".format('"/placement/submit"' in html))
