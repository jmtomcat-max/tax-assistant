import re
css_path = r".\.venv\Lib\site-packages\streamlit\static\static\css\index.DZDjBcCO.css"
content = open(css_path, "r", encoding="utf-8").read()
idx = content.find("/* FIX STREAMLIT SIDEBAR BUTTON ICON TEXT */")
if idx != -1:
    clean_content = content[:idx]
    open(css_path, "w", encoding="utf-8").write(clean_content)
    print("Successfully removed injected CSS from index.css")
else:
    print("Injected CSS not found in index.css")
