import sys,re
sys.path.insert(0,'tools')
from i18n_common import *
f=sys.argv[1]
src=strip_js_comments(open(f,encoding='utf-8').read())
seen=set()
for m in JS_RUN.finditer(src):
    s=m.group(0).strip(" ,;:()=+?|&")
    if s and VI.search(s) and s not in seen:
        seen.add(s); print(s)
