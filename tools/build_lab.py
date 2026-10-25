"""Generate the English copy of the Forecasting Lab (Streamlit).

The Vietnamese source stays untouched: lab/home.py, lab/lab_common.py, lab/lab_pages/*.py, lab/dpkit/*.py.
English copies are generated next to it with different module names, so both languages run in the
same Streamlit process without clashing:
    lab/home_en.py, lab/lab_common_en.py, lab/lab_pages_en/*.py, lab/dpkit_en/*.py
lab/app.py chooses the language per session (?lang=en|vi or the sidebar switch).

Maps: i18n/lab/*.tsv  — "vi<TAB>en" fragment pairs; lines "!<TAB>a<TAB>b" are literal replacements;
      i18n/lab/data.tsv — exact translations of Vietnamese values in the CSV data (applied at load time).
Usage: python3 tools/build_lab.py   (exit 1 when Vietnamese is left in the English copy)
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from i18n_common import JS_RUN, VI  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "lab"
MAPS = ROOT / "i18n" / "lab"
VI_STRICT = re.compile(r"[àáâãèéêìíòóôõùúýăđĩũơưÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯẠ-ỹ]")
ALLOWED = re.compile(r"Tết|Thư Nguyễn|Phở|Ngôn ngữ|Tiếng Việt")
problems = []


def read_map(p):
    pairs, lits = {}, []
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        if ln.startswith("!\t"):
            _, a, b = ln.split("\t", 2)
            lits.append((a, b))
        else:
            a, b = ln.split("\t", 1)
            pairs[a] = b
    return pairs, lits


def load_maps():
    code, lits = {}, []
    for p in sorted(MAPS.glob("*.tsv")):
        if p.name == "data.tsv":
            continue
        pairs, l2 = read_map(p)
        lits += l2
        for a, b in pairs.items():
            if a in code and code[a] != b:
                problems.append(f"conflict for {a!r}: {code[a]!r} vs {b!r} ({p.name})")
            code.setdefault(a, b)
    data, _ = read_map(MAPS / "data.tsv")
    for a, b in data.items():           # data values that also appear in code must translate the same way
        if len(a) >= 6:
            if a in code and code[a] != b:
                problems.append(f"data/code conflict for {a!r}: {code[a]!r} vs {b!r}")
            code.setdefault(a, b)
    return code, lits, data


def strip_comments(src):
    src = re.sub(r'"""[\s\S]*?"""', '""""""', src)
    return re.sub(r"(?m)#[^\n'\"]*$", "", src)


def translate(src, code, lits, name):
    for a, b in lits:
        src = src.replace(a, b)
    for k in sorted(code, key=len, reverse=True):
        src = src.replace(k, code[k])
    src = re.sub(r"\bfrom lab_common import", "from lab_common_en import", src)
    src = re.sub(r"\bimport lab_common\b", "import lab_common_en", src)
    src = re.sub(r"\bfrom dpkit\b", "from dpkit_en", src)
    body = strip_comments(src)
    for ln in body.splitlines():
        if VI_STRICT.search(ALLOWED.sub("", ln)):
            problems.append(f"{name}: Vietnamese left: {ln.strip()[:150]}")
    return src


EN_COMMON_TAIL = '''

# ---------------------------------------------------------------- English edition
# (appended by tools/build_lab.py) — translate Vietnamese values in the case data at load time
import json as _json  # noqa: E402

_DATA_EN = _json.loads((HERE / "i18n_data_en.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_all() -> dict[str, pd.DataFrame]:  # noqa: F811
    out = {}
    for k, df in dpdata.load(DATA_DIR).items():
        df = df.copy()
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]):
                df[c] = df[c].map(lambda v: _DATA_EN.get(v, v) if isinstance(v, str) else v)
        out[k] = df
    return out


def fmt_num(x, d=0):  # noqa: F811
    try:
        return f"{x:,.{d}f}"
    except (TypeError, ValueError):
        return str(x)
'''


def main():
    code, lits, data = load_maps()
    # English copies
    (LAB / "lab_pages_en").mkdir(exist_ok=True)
    if (LAB / "dpkit_en").exists():
        shutil.rmtree(LAB / "dpkit_en")
    (LAB / "dpkit_en").mkdir()
    jobs = [(LAB / "home.py", LAB / "home_en.py"), (LAB / "lab_common.py", LAB / "lab_common_en.py")]
    jobs += [(p, LAB / "lab_pages_en" / p.name) for p in sorted((LAB / "lab_pages").glob("*.py"))]
    jobs += [(p, LAB / "dpkit_en" / p.name) for p in sorted((LAB / "dpkit").glob("*.py"))]
    for src, dst in jobs:
        out = translate(src.read_text(encoding="utf-8"), code, lits, str(src.relative_to(LAB)))
        if src.name == "lab_common.py":
            out += EN_COMMON_TAIL
        dst.write_text(out, encoding="utf-8")
    data = {**{k: v for k, v in code.items()}, **data}   # exact-value lookup: data map first, then code fragments
    (LAB / "i18n_data_en.json").write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    # data values without a translation
    import pandas as pd
    for f in sorted((LAB / "data").glob("*.csv")):
        if f.name.startswith("mau_"):
            continue
        df = pd.read_csv(f, encoding="utf-8-sig")
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]):
                for v in df[c].dropna().unique():
                    if isinstance(v, str) and VI.search(v) and v not in data:
                        problems.append(f"data {f.name}.{c}: no translation for {v!r}")
    print(f"English Lab generated: {len(jobs)} files, {len(code)} fragments, {len(data)} data values")
    for p in problems:
        print("!", p)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
