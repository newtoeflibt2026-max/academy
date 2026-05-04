path = r'C:\yamen_academy\build_ai_engines.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all nested f-string patterns inside the triple-quoted strings
# These are inside SPEAKING_CODE = f'''...''' where {essay} or {prompt} appear
# The real problem: f-strings containing {{ }} that look like nested f-strings

# Fix line 675 and similar: replace nested f-string patterns
fixes = [
    # speaking inline_data dict - remove the f-string entirely, use concatenation
    ('f"""', '"""'),  # This might be too broad...
]

# Better: find the SPEAKING_CODE = f''' block and make it a regular string
# The variables are GEMINI_SPEAKING_KEYS and GEMINI_MODEL, they're at the top

# Actually the issue is: SPEAKING_CODE = f'''... contains {"inline_data": {...}}
# which Python tries to parse as f-string expressions

# Solution: change the outer f''' to just ''' and use .format() or % formatting
# Or escape the inner braces that aren't meant to be expressions

# Count lines with issues
import re
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if i >= 670 and i <= 680:
        print(f'Line {i}: {repr(line[:150])}')
