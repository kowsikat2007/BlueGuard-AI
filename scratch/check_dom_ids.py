import re
from pathlib import Path

html = Path('frontend/index.html').read_text(encoding='utf-8')
js = Path('frontend/script.js').read_text(encoding='utf-8')

ids_in_js = set(re.findall(r'getElementById\([\'"]([^\'"]+)[\'"]\)', js))
print(f"Total getElementById calls in script.js: {len(ids_in_js)}")

missing = [i for i in ids_in_js if f'id="{i}"' not in html and f"id='{i}'" not in html]
print(f"Missing IDs in index.html: {len(missing)}")
if missing:
    print("Missing list:", missing)
else:
    print("100% of DOM IDs accessed by script.js exist in index.html!")
