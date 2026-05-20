with open("handlers/start.py", "r", encoding="utf-8") as f:
    text = f.read()

# إزالة تمرير today للدالة
import re
text = re.sub(r'get_daily_missions\(today\)', 'get_daily_missions()', text)
text = re.sub(r'get_daily_missions\(date[^)]*\)', 'get_daily_missions()', text)

with open("handlers/start.py", "w", encoding="utf-8") as f:
    f.write(text)
print("handlers/start.py fixed")
