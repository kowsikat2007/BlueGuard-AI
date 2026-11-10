import re

with open("Frontend/script.js", "r", encoding="utf-8") as f:
    js = f.read()

with open("Frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

ids_in_js = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', js))
ids_in_html = set(re.findall(r'id=["\']([^"\']+)["\']', html))

missing = ids_in_js - ids_in_html
print("Total IDs queried in script.js:", len(ids_in_js))
print("IDs in HTML:", len(ids_in_html))
print("Missing IDs (in script.js but not in index.html):", missing)
