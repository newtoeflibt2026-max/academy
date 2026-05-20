& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -c "
import os
BASE = r'C:\yamen_academy'

def update_db():
    import sqlite3
    conn = sqlite3.connect(os.path.join(BASE, 'data', 'academy.db'))
    cur = conn.cursor()
    for col in ['image_file_id TEXT DEFAULT \"\"', 'image_url TEXT DEFAULT \"\"', 'audio_file_id TEXT DEFAULT \"\"', 'audio_url TEXT DEFAULT \"\"', 'video_file_id TEXT DEFAULT \"\"', 'video_url TEXT DEFAULT \"\"']:
        try: cur.execute(f'ALTER TABLE lessons ADD COLUMN {col}')
        except: pass
    conn.commit(); conn.close()
    print('DB updated')

update_db()

# Fix the buggy _safe_exec line in admin.py
path = os.path.join(BASE, 'handlers', 'admin.py')
with open(path, 'r', encoding='utf-8') as f: content = f.read()

old = '''_safe_exec(\"\"\"UPDATE lessons SET 
        image_file_id=?, image_url=?, audio_file_id=?, audio_url=?, video_file_id=?, video_url=? 
        WHERE id=?\"\"\",
        (d.get('image_file_id',''), d.get('image_url',''),
         d.get('audio_file_id',''), d.get('audio_url',''),
         d.get('video_file_id',''), d.get('video_url',''),
         lid-1))'''

new = '''_safe_exec(
    \"UPDATE lessons SET image_file_id=?, image_url=?, audio_file_id=?, audio_url=?, video_file_id=?, video_url=? WHERE id=?\",
    (d.get('image_file_id',''), d.get('image_url',''), d.get('audio_file_id',''), d.get('audio_url',''), d.get('video_file_id',''), d.get('video_url',''), lid-1)
)'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    print('admin.py fixed')
else:
    print('Pattern not found - checking for alternatives...')
    # Try simpler replacement
    if '_safe_exec(\"\"\"UPDATE lessons SET' in content:
        content = content.replace('_safe_exec(\"\"\"UPDATE lessons SET', '_safe_exec(\"UPDATE lessons SET')
        content = content.replace('WHERE id=?\"\"\",', 'WHERE id=?\",')
        with open(path, 'w', encoding='utf-8') as f: f.write(content)
        print('admin.py fixed (alt method)')
    else:
        print('Could not find the buggy line. Manual fix needed.')
"
