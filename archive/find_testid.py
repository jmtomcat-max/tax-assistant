content = open(r".\.venv\Lib\site-packages\streamlit\static\static\js\index.ByR4Z2EF.js", encoding="utf-8", errors="ignore").read()
import re
matches = set(re.findall(r'data-testid["\']?\s*[:=]\s*[`"\']([^`"\']+)', content))
for m in sorted(matches):
    if "sidebar" in m.lower():
        print("Sidebar testid:", m)
