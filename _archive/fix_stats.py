# fix_stats.py
p = r'C:\yamen_academy\database.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old = '''def get_stats():
    total = _safe_fetchone("SELECT COUNT(*) as cnt FROM students")
    active = _safe_fetchone("SELECT COUNT(*) as cnt FROM students WHERE is_active=1")
    paying = _safe_fetchone("SELECT COUNT(*) as cnt FROM payments WHERE status=pending")
    return {
        "total_students": total["cnt"] if total else 0,
        "active_students": active["cnt"] if active else 0,
        "pending_payments": paying["cnt"] if paying else 0,
    }'''

new = '''def get_stats():
    conn = get_conn()
    total = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    active = conn.execute('SELECT COUNT(*) FROM students WHERE is_active=1').fetchone()[0]
    try:
        paying = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    except:
        paying = 0
    return {
        "total_students": total,
        "active_students": active,
        "pending_payments": paying,
    }'''

if old in c:
    c = c.replace(old, new)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('FIXED')
else:
    print('NOT FOUND - trying line-by-line')
    lines = c.split('\n')
    for i, line in enumerate(lines):
        if 'def get_stats():' in line:
            # replace lines i to i+7 with new code
            new_lines = [
                'def get_stats():',
                '    conn = get_conn()',
                "    total = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]",
                "    active = conn.execute('SELECT COUNT(*) FROM students WHERE is_active=1').fetchone()[0]",
                '    try:',
                "        paying = conn.execute(\"SELECT COUNT(*) FROM payments WHERE status='pending'\").fetchone()[0]",
                '    except:',
                '        paying = 0',
                '    return {',
                '        "total_students": total,',
                '        "active_students": active,',
                '        "pending_payments": paying,',
                '    }',
            ]
            lines[i:i+8] = new_lines
            break
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('FIXED line-by-line')
