"""Tiện ích dùng chung cho bản song ngữ: tách khối văn bản HTML và mảnh chuỗi trong JS/Python."""
import re

VI = re.compile(r"[À-ỹĐđ]")
BLOCK = {"html", "body", "head", "div", "p", "ul", "ol", "li", "table", "thead", "tbody", "tfoot", "tr", "td", "th",
         "h1", "h2", "h3", "h4", "h5", "h6", "section", "header", "footer", "nav", "main", "article", "aside",
         "details", "summary", "figure", "figcaption", "dl", "dt", "dd", "form", "blockquote", "pre", "caption",
         "select", "option", "button", "label", "title", "noscript", "svg"}
SKIP = {"script", "style", "code", "pre", "svg"}
ATTRS = ("title", "alt", "aria-label", "placeholder", "content", "data-label", "data-fallback", "data-prefix", "data-titles")


def norm(s: str) -> str:
    return " ".join(s.split())


def has_block_child(el) -> bool:
    for d in el.descendants:
        if getattr(d, "name", None) in BLOCK:
            return True
    return False


def leaf_blocks(soup):
    """Phần tử chứa chữ tiếng Việt và chỉ có con inline → dịch nguyên innerHTML."""
    out = []
    for el in soup.find_all(True):
        if el.name in SKIP or any(p.name in SKIP for p in el.parents):
            continue
        if el.name not in BLOCK and el.name not in ("a", "span", "strong", "em", "b", "i"):
            continue
        if has_block_child(el):
            continue
        # tránh chọn trùng: bỏ nếu cha cũng là leaf block
        par = el.parent
        if par is not None and par.name not in SKIP and not has_block_child(par) and (par.name in BLOCK or par.name in ("a", "span", "strong", "em", "b", "i")):
            continue
        inner = el.decode_contents()
        if VI.search(el.get_text()):
            out.append((el, inner))
    return out


def orphan_texts(soup, blocks):
    """Đoạn chữ nằm trực tiếp trong phần tử có con block (không thuộc leaf block nào)."""
    inside = set()
    for el, _ in blocks:
        inside.add(id(el))
    res = []
    for t in soup.find_all(string=True):
        p = t.parent
        if p is None or p.name in SKIP or any(x.name in SKIP for x in t.parents):
            continue
        if any(id(x) in inside for x in t.parents):
            continue
        if type(t).__name__ != "NavigableString":
            continue
        if VI.search(t):
            res.append(t)
    return res


JS_RUN = re.compile(r"[^`'\"<>{}$\n\\]*[À-ỹĐđ][^`'\"<>{}$\n\\]*")


def strip_js_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$|(?<=[;,{}()\s])//[^\n'\"`]*$", "", src)


def js_runs(src: str):
    runs = set()
    for m in JS_RUN.finditer(strip_js_comments(src)):
        r = m.group(0).strip(" ,;:()=+?|&")
        if VI.search(r):
            runs.add(r)
    return runs


def replace_runs(src: str, mapping: dict) -> str:
    for k in sorted(mapping, key=len, reverse=True):
        v = mapping[k]
        if v:
            src = src.replace(k, v)
    return src
