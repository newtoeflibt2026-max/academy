import py_compile
import sys

try:
    py_compile.compile("app.py", doraise=True)
    print("app.py syntax is perfect!")
except Exception as e:
    print(f"app.py syntax error: {e}")
    sys.exit(1)
