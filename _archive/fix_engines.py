# Fix speaking.py — replace placeholder with real keys
path = r'C:\yamen_academy\handlers\speaking.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('SPEAKING_KEYS_PLACEHOLDER', '["AIzaSyCBFNExYp5-9yFjHFrnaqUS-yZn_YqigSY","AIzaSyAXGja3hvzIo2SyTTQcuKBNa-yHZghHu8M","AIzaSyBWj39r49ORhKEpoDLhk6bpPiJLGrmohW0"]')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Fix writing.py — replace placeholder with real keys
path = r'C:\yamen_academy\handlers\writing.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('WRITING_KEYS_PLACEHOLDER', '["AIzaSyDkAuMCa9rBQGiFkqxIauUCL7eXQyP2aHw","AIzaSyDGRbeskDR64jlDFkC5UzSdfleMp_sUwKc","AIzaSyDFU5MAO20Hssq6SWS-F0TGGint3IZHcTU"]')
content = content.replace('MODEL_W_PLACEHOLDER', '"gemini-2.5-flash"')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed speaking.py + writing.py')
