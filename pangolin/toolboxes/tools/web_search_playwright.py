import base64
import threading
from urllib.parse import quote_plus, urlparse, parse_qs

SCHEMA = {
    "name": "web_search_playwright",
    "description": (
        "Search the web using a real headless browser (Playwright/Chromium). Uses Brave Search, falling back to Bing. "
        "Returns clean, separate title/url/snippet results. Slower than web_search; use when web_search returns "
        "nothing or merged/garbled results."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "1-10, default 5"},
        },
        "required": ["query"],
    },
}

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _text(el, sel):
    e = el.query_selector(sel)
    return e.inner_text().strip() if e else ""


def _brave(page, query, n):
    page.goto(f"https://search.brave.com/search?q={quote_plus(query)}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("div.snippet[data-type='web']", timeout=10000)
    out = []
    for r in page.query_selector_all("div.snippet[data-type='web']"):
        a = r.query_selector("a[href^='http']")
        title = _text(r, ".search-snippet-title") or _text(r, ".title")
        if not a or not title:
            continue
        out.append({"title": title, "url": a.get_attribute("href"),
                    "snippet": _text(r, ".generic-snippet") or _text(r, ".content")})
        if len(out) >= n:
            break
    return out


def _bing_url(href):
    # Bing wraps links as /ck/a?...&u=a1<base64url of real url>
    try:
        u = parse_qs(urlparse(href).query).get("u", [""])[0]
        if u.startswith("a1"):
            b = u[2:]
            return base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode()
    except Exception:
        pass
    return href


def _bing(page, query, n):
    page.goto(f"https://www.bing.com/search?q={quote_plus(query)}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("li.b_algo", timeout=10000)
    out = []
    for r in page.query_selector_all("li.b_algo"):
        a = r.query_selector("h2 a")
        if not a:
            continue
        out.append({"title": a.inner_text().strip(), "url": _bing_url(a.get_attribute("href")),
                    "snippet": _text(r, ".b_caption p") or _text(r, "p")})
        if len(out) >= n:
            break
    return out


def _search(query, n):
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for name, fn in (("brave", _brave), ("bing", _bing)):
                page = browser.new_page(user_agent=UA)
                try:
                    res = fn(page, query, n)
                    if res:
                        return {"engine": name, "results": res}
                    errors.append(f"{name}: no results parsed")
                except Exception as e:
                    errors.append(f"{name}: {type(e).__name__}: {str(e)[:150]}")
                finally:
                    page.close()
        finally:
            browser.close()
    return {"error": "all engines failed", "details": errors}


def run(query, max_results=5):
    n = max(1, min(int(max_results or 5), 10))
    out = {}

    # Separate thread: the sync Playwright API refuses to run inside an active asyncio loop.
    def worker():
        try:
            out["value"] = _search(query, n)
        except ImportError:
            out["value"] = {"error": "playwright not installed: pip install playwright && playwright install chromium"}
        except Exception as e:
            out["value"] = {"error": f"{type(e).__name__}: {e}"}

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=90)
    if t.is_alive():
        return {"error": "search timed out after 90s"}
    return out["value"]
