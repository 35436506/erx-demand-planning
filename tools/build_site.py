"""Build the bilingual Demand Planning module.

Input : src/pages/*.html            (Vietnamese source pages, relative links)
        i18n/html_en.json           (Vietnamese block/attribute → English)
        i18n/js/<name>.tsv          (Vietnamese fragment → English, per game script)
        site/assets, site/files, site/config.js   (shared by both languages)
Output: site/vi/*.html, site/en/*.html, site/index.html (language router), site/404.html,
        site/assets/js/games/en/*.js (English copies of the game scripts)

Usage:  python3 tools/build_site.py          (writes report to stdout, exit 1 on problems)
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from i18n_common import ATTRS, VI, leaf_blocks, norm, orphan_texts, replace_runs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "pages"
SITE = ROOT / "site"
GAMES = SITE / "assets" / "js" / "games"
LANGS = ("vi", "en")
SHARED = ("assets/", "files/", "config.js")
# letters that only Vietnamese uses (Greek letters, ×, ≤ … are not counted)
VI_STRICT = re.compile(r"[àáâãèéêìíòóôõùúýăđĩũơưÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯẠ-ỹ]")
# Vietnamese that may legitimately stay on English pages (names, places, product names, the word Tết)
ALLOWED = re.compile(r"Tết|Thư Nguyễn|Nguyễn|Phở|Phúc Lộc|An Khang|Xuân Sum Vầy|Đoàn Viên|Hưng Thịnh|Như Ý|Vạn Phúc|"
                     r"Tiếng Việt|ngôn ngữ|Ngôn ngữ")

problems = []


def frag(html):
    return BeautifulSoup(html, "html.parser")


def load_js_map(name):
    pairs, lits = {}, []
    p = ROOT / "i18n" / "js" / f"{name}.tsv"
    if not p.exists():
        return pairs, lits
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith("!\t"):
            _, a, b = line.split("\t", 2)
            lits.append((a, b))
        else:
            a, b = line.split("\t", 1)
            pairs[a] = b
    return pairs, lits


def build_games_en():
    out = GAMES / "en"
    out.mkdir(exist_ok=True)
    for js in sorted(GAMES.glob("*.js")):
        name = js.stem
        src = js.read_text(encoding="utf-8")
        pairs, lits = load_js_map(name)
        if name == "data":
            data = json.loads(src[src.index("{"): src.rindex("}") + 1])

            def tr(o):
                if isinstance(o, dict):
                    return {k: tr(v) for k, v in o.items()}
                if isinstance(o, list):
                    return [tr(v) for v in o]
                if isinstance(o, str) and VI.search(o):
                    if o not in pairs:
                        problems.append(f"data.js: missing translation for {o!r}")
                    return pairs.get(o, o)
                return o
            res = "window.GAME_DATA = " + json.dumps(tr(data), ensure_ascii=False) + ";\n"
        else:
            res = src
            for a, b in lits:
                if a not in res:
                    problems.append(f"{name}.js: literal not found {a!r}")
                res = res.replace(a, b)
            res = replace_runs(res, pairs)
        # leftovers outside comments
        body = re.sub(r"/\*.*?\*/", "", res, flags=re.S)
        body = re.sub(r"(?m)//.*$", "", body)
        for ln in body.splitlines():
            if VI_STRICT.search(ALLOWED.sub("", ln)):
                problems.append(f"{name}.js (en): Vietnamese left: {ln.strip()[:140]}")
        (out / js.name).write_text(res, encoding="utf-8")


def rewrite_paths(soup, lang):
    for el in soup.find_all(True):
        for a in ("href", "src"):
            v = el.get(a)
            if isinstance(v, str) and v.startswith(SHARED):
                if lang == "en" and a == "src" and v.startswith("assets/js/games/"):
                    v = v.replace("assets/js/games/", "assets/js/games/en/")
                el[a] = "../" + v


LANG_SWITCH = ('<div class="lang-switch" role="group" aria-label="{label}">'
               '<a href="../vi/{page}" hreflang="vi" lang="vi" data-lang-switch="vi"{cur_vi}>VI</a>'
               '<a href="../en/{page}" hreflang="en" lang="en" data-lang-switch="en"{cur_en}>EN</a></div>')


def add_chrome(soup, lang, page):
    soup.html["lang"] = lang
    head = soup.head
    for alt in LANGS:
        head.append(frag(f'<link rel="alternate" hreflang="{alt}" href="../{alt}/{page}">'))
    head.append(frag(f'<link rel="alternate" hreflang="x-default" href="../vi/{page}">'))
    bar = soup.select_one(".site-header .bar")
    if bar is not None:
        sw = frag(LANG_SWITCH.format(page=page, label="Ngôn ngữ / Language",
                                     cur_vi=' aria-current="true"' if lang == "vi" else "",
                                     cur_en=' aria-current="true"' if lang == "en" else ""))
        bar.append(sw)
    else:
        problems.append(f"{page}: no header bar for the language switch")
    if lang == "en":
        foot = soup.select_one(".site-footer .container")
        if foot is not None:
            foot.append(frag('<div class="lang-note small">English edition · slides, workbooks and lecture notes '
                             'are in Vietnamese; the Lab and the games are fully bilingual.</div>'))


def translate(soup, m, page):
    blocks = leaf_blocks(soup)
    orphans = orphan_texts(soup, blocks)
    for el, inner in blocks:
        k = norm(inner)
        if k not in m:
            problems.append(f"{page}: missing block {k[:90]!r}")
            continue
        el.clear()
        for node in list(frag(m[k]).contents):
            el.append(node)
    for t in orphans:
        k = norm(str(t))
        if k not in m:
            problems.append(f"{page}: missing text {k[:90]!r}")
            continue
        s = str(t)
        lead = s[: len(s) - len(s.lstrip())]
        trail = s[len(s.rstrip()):]
        new = frag(lead + m[k] + trail)
        t.replace_with(*list(new.contents))
    for el in soup.find_all(True):
        for a in ATTRS:
            v = el.get(a)
            if isinstance(v, str) and VI.search(v):
                k = "@" + norm(v)
                if k not in m:
                    problems.append(f"{page}: missing attribute {a}={v[:80]!r}")
                    continue
                el[a] = m[k][1:]
    # viewer titles in xem.html?t=… links are part of the translated blocks; inline game-list script:
    for sc in soup.find_all("script"):
        if sc.string and "Bạn đã chơi" in sc.string:
            sc.string = sc.string.replace('"Bạn đã chơi · kỷ lục ("', '"Played · best ("').replace('") cập nhật ngày "', '") · updated "')


# Vietnamese words without diacritics are not caught by the extractor — translated here (exact text node match)
EXTRA = {
    "Giao": "Set", "Vai": "Role", "Trang": "Page", "Xem": "View", "Trang web": "Web page", "Trong": "During",
    "trong": "during", "Sau": "After", "Slide": "Slides", "File Excel": "Excel files", "1 trang": "1 page",
    "1,5 trang": "1.5 pages", "½ trang": "½ page", "Thang 0–4": "Scale 0–4", "Xem slide": "Review the slides",
    "Tham gia & exit ticket": "Participation & exit tickets", "Tham gia & exit ticket (10%)": "Participation & exit tickets (10%)",
    "Rubric capstone": "Capstone rubric", "Sheet capstone": "Capstone sheet", "Manual Python": "Python manual",
    "⤓ Slide (PDF)": "⤓ Slides (PDF, Vietnamese)", "Exit (0–5)": "Exit (0–5)", "Trang sau": "Next page",
}
TEXT_RX = [(re.compile(r"\bBT(\d)"), r"HW\1"), (re.compile(r"^tr\. (\d+)$"), r"p. \1")]


def translate_toneless(soup):
    for t in soup.find_all(string=True):
        if t.parent is None or t.parent.name in ("script", "style", "code", "pre") or type(t).__name__ != "NavigableString":
            continue
        s = str(t)
        k = norm(s)
        new = EXTRA.get(k, k)
        for rx, rep in TEXT_RX:
            new = rx.sub(rep, new)
        if new != k:
            t.replace_with(s[: len(s) - len(s.lstrip())] + new + s[len(s.rstrip()):])
    for el in soup.find_all(True):
        for a in ATTRS:
            v = el.get(a)
            if isinstance(v, str) and norm(v) in EXTRA:
                el[a] = EXTRA[norm(v)]


def leftovers(soup, page):
    for sc in soup(["script", "style"]):
        sc.extract()
    txt = soup.get_text(" ")
    for a in ATTRS:
        for el in soup.find_all(attrs={a: True}):
            txt += " " + el[a]
    for seg in re.split(r"\s{2,}|\n", txt):
        rest = ALLOWED.sub("", seg)
        if VI_STRICT.search(rest):
            problems.append(f"en/{page}: Vietnamese left: {seg.strip()[:120]!r}")


ROUTER = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ERX Demand Planning</title>
<link rel="alternate" hreflang="vi" href="vi/">
<link rel="alternate" hreflang="en" href="en/">
<script src="config.js"></script>
<script>
/* Language router: the choice is shared by every ERX module through localStorage "erx.lang". */
(function () {
  var lang = "vi";
  try { var s = localStorage.getItem("erx.lang"); if (s === "en" || s === "vi") lang = s; else if (window.ERX_CONFIG && ERX_CONFIG.DEFAULT_LANG) lang = ERX_CONFIG.DEFAULT_LANG; } catch (e) {}
  var q = new URLSearchParams(location.search).get("lang"); if (q === "en" || q === "vi") lang = q;
  location.replace(lang + "/" + location.hash);
})();
</script>
<style>body{font-family:system-ui,sans-serif;margin:0;display:grid;place-items:center;min-height:100vh;background:#fff;color:#1F2421}
a{color:#008A3A;margin:0 .6em;font-weight:600}@media (prefers-color-scheme:dark){body{background:#121614;color:#E8ECE9}a{color:#3CC872}}</style>
</head>
<body><p><a href="vi/">Tiếng Việt</a> · <a href="en/">English</a></p></body>
</html>
"""

NOT_FOUND = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>404 · ERX Demand Planning</title>
<style>body{font-family:system-ui,sans-serif;margin:0;display:grid;place-items:center;min-height:100vh;text-align:center;background:#fff;color:#1F2421}
a{color:#008A3A;font-weight:600}@media (prefers-color-scheme:dark){body{background:#121614;color:#E8ECE9}a{color:#3CC872}}</style></head>
<body><div><h1>404</h1><p>Không tìm thấy trang · Page not found</p><p><a href="/">Trang chủ · Home</a></p></div></body></html>
"""


def write_manifest(pages):
    """module.json — what the ERX central site needs to list, link and mount this module."""
    def title(lang, name):
        t = BeautifulSoup((SITE / lang / name).read_text(encoding="utf-8"), "html.parser").title
        return (t.get_text() if t else name).replace(" · ERX Demand Planning", "")
    man = {
        "id": "demand-planning",
        "title": {"vi": "Demand Planning & Forecasting in Practice", "en": "Demand Planning & Forecasting in Practice"},
        "summary": {"vi": "Khóa 10 buổi: dự báo nhu cầu, Demand Review, tồn kho và S&OP trên case Mekong Bloom Foods.",
                    "en": "10-session course: demand forecasting, Demand Review, inventory and S&OP on the Mekong Bloom Foods case."},
        "owner": {"name": "Thư Nguyễn", "email": "thu.minh090997@gmail.com"},
        "languages": ["vi", "en"],
        "defaultLanguage": "vi",
        "suggestedMountPath": "/demand-planning/",
        "entry": {"router": "index.html", "vi": "vi/index.html", "en": "en/index.html"},
        "sharedFolders": ["assets/", "files/", "config.js"],
        "lab": {"kind": "streamlit", "path": "lab/", "health": "lab/_stcore/health", "languageParam": "lang",
                "overrideWith": "config.js → LAB_URL"},
        "storageKeys": {"language": "erx.lang", "theme": "erx_theme", "progress": "erx_dpf_progress_v1", "games": "erx_games"},
        "links": {"downstream": [
            {"module": "production-planning", "via": "Lab · Session 10 handover file (consensus demand, unconstrained, with error σ and safety stock)"},
            {"module": "procurement", "via": "the same consensus demand → MRP"},
            {"module": "warehouse", "via": "safety stock / ROP and shelf-life (FEFO) alerts from Session 9"}]},
        "pages": [{"file": p.name, "vi": title("vi", p.name), "en": title("en", p.name)} for p in pages if p.name != "404.html"],
    }
    (SITE / "module.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    m = json.loads((ROOT / "i18n" / "html_en.json").read_text(encoding="utf-8"))
    build_games_en()
    pages = sorted(SRC.glob("*.html"))
    for lang in LANGS:
        (SITE / lang).mkdir(exist_ok=True)
        for p in pages:
            soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
            if lang == "en":
                translate(soup, m, p.name)
                translate_toneless(soup)
            rewrite_paths(soup, lang)
            add_chrome(soup, lang, p.name)
            html = str(soup)
            (SITE / lang / p.name).write_text(html, encoding="utf-8")
            if lang == "en":
                leftovers(BeautifulSoup(html, "html.parser"), p.name)
    (SITE / "index.html").write_text(ROUTER, encoding="utf-8")
    (SITE / "404.html").write_text(NOT_FOUND, encoding="utf-8")
    write_manifest(pages)
    print(f"built {len(pages)} pages × {len(LANGS)} languages")
    for x in problems:
        print("!", x)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
