import os

base = r'C:\yamen_academy'
handlers = os.path.join(base, 'handlers')

# List all .py files with their size
files_to_check = [
    os.path.join(base, 'api_server.py'),
    os.path.join(handlers, '__init__.py'),
    os.path.join(handlers, 'start.py'),
    os.path.join(handlers, 'writing.py'),
    os.path.join(handlers, 'speaking.py'),
]

for f in files_to_check:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f'{f} — {size} bytes')
    else:
        print(f'{f} — MISSING')
