path = r'C:\yamen_academy\build_ai_engines.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The problem: SPEAKING_CODE = f'''... contains double braces like {{ and }}
# inside dict literals that Python misinterprets as nested f-string expressions.
# 
# Fix: replace f''' with ''' and inject variables differently.
# GEMINI_SPEAKING_KEYS and GEMINI_MODEL are the only vars used in SPEAKING_CODE

# 1. Change SPEAKING_CODE = f''' to SPEAKING_CODE = '''
content = content.replace(
    "SPEAKING_CODE = f'''",
    "SPEAKING_CODE = '''"
)

# 2. Replace {GEMINI_SPEAKING_KEYS} and {GEMINI_MODEL} with placeholder markers
content = content.replace("{GEMINI_SPEAKING_KEYS}", "SPEAKING_KEYS_PLACEHOLDER")
content = content.replace("{GEMINI_MODEL}", "MODEL_PLACEHOLDER")

# 3. Now inject the actual values using .replace after the string definition
# Find the end of SPEAKING_CODE (the closing ''')
end_marker = "print(\"✅ handlers/speaking.py — AI Speaking Coach ready\")"
injection = '''
# Inject dynamic values into speaking code
SPEAKING_CODE = SPEAKING_CODE.replace("SPEAKING_KEYS_PLACEHOLDER", str(GEMINI_SPEAKING_KEYS))
SPEAKING_CODE = SPEAKING_CODE.replace("MODEL_PLACEHOLDER", GEMINI_MODEL)
'''
content = content.replace(end_marker, injection + end_marker)

# Now fix WRITING_CODE as well - same issue
content = content.replace(
    "WRITING_CODE = f'''",
    "WRITING_CODE = '''"
)
content = content.replace("{GEMINI_WRITING_KEYS}", "WRITING_KEYS_PLACEHOLDER")
content = content.replace("{GEMINI_MODEL}", "MODEL_W_PLACEHOLDER")  # separate placeholder

writing_end = "print(\"✅ handlers/writing.py — AI Writing Engine ready\")"
injection_w = '''
# Inject dynamic values into writing code
WRITING_CODE = WRITING_CODE.replace("WRITING_KEYS_PLACEHOLDER", str(GEMINI_WRITING_KEYS))
WRITING_CODE = WRITING_CODE.replace("MODEL_W_PLACEHOLDER", GEMINI_MODEL)
'''
content = content.replace(writing_end, injection_w + writing_end)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed all nested f-string issues')
