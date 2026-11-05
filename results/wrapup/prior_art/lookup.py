"""Logged bibliographic lookups for Study 4 (DECISIONS S4). Every API response is saved verbatim under lookups/ and
one line per request is appended to lookups/LOG.jsonl (UTC time, URL, HTTP status, saved file, SHA-256).
Usage:
  python3 lookup.py doi <DOI> [label]            Crossref /works/<DOI>, then Semantic Scholar DOI:<DOI> (abstract)
  python3 lookup.py arxiv <id> [label]           arXiv API id_list=<id>
  python3 lookup.py search "<bibliographic text>" [label]   Crossref query.bibliographic (top 5)
  python3 lookup.py s2search "<title words>" [label]        Semantic Scholar search (top 5, with abstracts)
  python3 lookup.py url <URL> [label]            any page (datasheet, product page); saved as fetched
Network: through the container's HTTPS proxy (curl). Nothing here is interpreted; reading is done by hand."""
import datetime, hashlib, json, os, pathlib, re, subprocess, sys, time, urllib.parse

L = pathlib.Path(__file__).resolve().parent / "lookups"
L.mkdir(exist_ok=True)
UA = os.environ.get("LOOKUP_UA", "wrapup-lookup/1.0")  # set LOOKUP_UA to add your own mailto contact (Crossref polite pool)


def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:90]


def fetch(url, label, ext, retries=5):
    out = None
    for a in range(retries):
        r = subprocess.run(["curl", "-sS", "-L", "-A", UA, "-w", "\n%{http_code}", "--max-time", "60", url],
                           capture_output=True)
        body, _, code = r.stdout.rpartition(b"\n")
        code = code.decode().strip()
        out = (body, code)
        if code not in ("429", "500", "502", "503", "504", ""):
            break
        time.sleep(3 * 2 ** a)
    body, code = out
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    f = L / f"{ts}_{slug(label)}.{ext}"
    f.write_bytes(body)
    rec = dict(utc=ts, url=url, http=code, file=f.name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), label=label)
    with open(L / "LOG.jsonl", "a") as g:
        g.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))
    return body, code


def show_crossref(body):
    try:
        m = json.loads(body)["message"]
    except Exception:
        print("  (not JSON)"); return
    items = m.get("items", [m])
    for it in items[:5]:
        print("  DOI", it.get("DOI"), "|", (it.get("title") or [""])[0][:150], "|", (it.get("container-title") or [""])[0][:60],
              "|", (it.get("issued", {}).get("date-parts") or [[None]])[0][0], "|",
              ", ".join(f"{a.get('family')}" for a in (it.get("author") or [])[:6]))


if __name__ == "__main__":
    kind, arg = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else arg
    if kind == "doi":
        b, c = fetch(f"https://api.crossref.org/works/{urllib.parse.quote(arg)}", f"crossref_{label}", "json")
        show_crossref(b)
        b2, c2 = fetch(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(arg)}"
                       "?fields=title,year,venue,authors,abstract,externalIds", f"s2_{label}", "json")
        try:
            d = json.loads(b2); print("  S2:", d.get("title"), d.get("year"), "| abstract:", (d.get("abstract") or "")[:600])
        except Exception:
            print("  S2: not JSON", c2)
    elif kind == "arxiv":
        b, c = fetch(f"https://export.arxiv.org/api/query?id_list={arg}", f"arxiv_{label}", "xml")
        t = b.decode(errors="replace")
        print("  ", re.findall(r"<title>(.*?)</title>", t, re.S)[1:2], re.findall(r"<summary>(.*?)</summary>", t, re.S)[:1])
    elif kind == "search":
        b, c = fetch("https://api.crossref.org/works?rows=5&query.bibliographic=" + urllib.parse.quote(arg), f"crossref_search_{label}", "json")
        show_crossref(b)
    elif kind == "s2search":
        b, c = fetch("https://api.semanticscholar.org/graph/v1/paper/search?limit=5&fields=title,year,venue,externalIds,abstract&query="
                     + urllib.parse.quote(arg), f"s2search_{label}", "json")
        try:
            for p in json.loads(b).get("data", []):
                print("  ", p.get("year"), p.get("title"), p.get("externalIds"), "|", (p.get("abstract") or "")[:300])
        except Exception:
            print("  not JSON", c)
    elif kind == "url":
        ext = "pdf" if arg.lower().endswith(".pdf") else "html"
        fetch(arg, f"url_{label}", ext)
