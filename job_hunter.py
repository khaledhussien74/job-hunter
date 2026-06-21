# -*- coding: utf-8 -*-
"""Job Hunter v2: remote marketing jobs -> Telegram."""
import json, time, html, os, re, sys
from datetime import datetime
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

# ── Credentials (environment variables only) ──────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
ADZUNA_APP_ID      = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_API_KEY     = os.environ.get("ADZUNA_API_KEY", "")
JOOBLE_API_KEY     = os.environ.get("JOOBLE_API_KEY", "")
FINDWORK_API_KEY   = os.environ.get("FINDWORK_API_KEY", "")

SEEN_FILE = "seen_jobs.json"
SEND_EXISTING_ON_FIRST_RUN = False
HEADERS = {"User-Agent": "Mozilla/5.0 (JobHunter/2.0)", "Accept": "application/json, */*"}

# ── Whitelist: title must contain at least one phrase ─────────────────────────
WHITELIST = [
    "marketing manager",
    "digital marketing manager",
    "performance marketing manager",
    "marketing director",
    "head of marketing",
    "head of digital",
    "senior marketing manager",
    "senior marketing director",
    "senior digital marketing",
]

# ── Blacklist: title must NOT contain any of these ────────────────────────────
BLACKLIST = [
    "content creator", "content writer", "customer service",
    "supervisor", "specialist", "coordinator", "assistant",
    "intern", "internship", "junior", "graduate", "trainee", "entry",
]

# ── Nationality restriction keywords ─────────────────────────────────────────
NATIONALITY_KEYWORDS = [
    "saudization", "saudi nationals only",
    "emiratization", "emirati nationals only",
    "qatarization", "qatari nationals only",
    "kuwaitization", "kuwaiti nationals only",
    "omanization", "omani nationals only",
    "bahrainization", "bahraini nationals only",
    "nationals only", "citizens only",
]

# ── Foreign languages that are a hard disqualifier ────────────────────────────
FOREIGN_LANGUAGES = [
    "german", "deutsch",
    "french", "français", "francais",
    "spanish", "español", "espanol",
    "italian", "italiano",
    "dutch", "nederlands",
    "portuguese", "português", "portugues",
    "russian", "polish", "turkish",
    "chinese", "mandarin", "cantonese",
    "japanese", "korean",
    "swedish", "danish", "norwegian", "finnish",
    "greek", "hebrew",
]

# Context phrases that mean the language is optional (not required)
NICE_TO_HAVE = [
    "a plus", "a+", "nice to have", "advantage", "advantageous",
    "bonus", "preferred", "not required", "optional", "desirable",
    "would be", "asset", "beneficial", "ideally", "is a plus",
]

# ── Salary: approximate EGP exchange rates (mid-2025) ─────────────────────────
_RATES = {
    "usd": 48.5, "eur": 52.8, "gbp": 62.1,
    "sar": 12.9, "aed": 13.2, "qar": 13.3,
    "kwd": 157.5, "bhd": 128.6, "omr": 126.0,
    "cad": 35.6, "aud": 31.2, "sgd": 36.1,
    "chf": 55.0, "try": 1.43, "pln": 12.5,
    "inr": 0.58, "jpy": 0.32,
}
_SYM_MAP = {"$": "usd", "€": "eur", "£": "gbp"}
_CODE_PAT = r"USD|EUR|GBP|SAR|AED|QAR|KWD|BHD|OMR|CAD|AUD|SGD|CHF|TRY|PLN|INR|JPY"
MIN_MONTHLY_EGP = 50_000

# ── HTTP helper ───────────────────────────────────────────────────────────────
def _fetch(url, timeout=25, post_data=None, extra_headers=None):
    try:
        hdrs = dict(HEADERS)
        if extra_headers:
            hdrs.update(extra_headers)
        req = Request(url, data=post_data, headers=hdrs)
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [x] {url[:70]}: {e}")
        return None

def _strip_html(s):
    return re.sub(r"<[^>]+>", " ", s or "").strip()

# ── Salary filter ─────────────────────────────────────────────────────────────
def _salary_passes(text: str) -> bool:
    """Return True if salary is acceptable or not mentioned at all."""
    if not text:
        return True
    s = text[:5000]
    is_annual  = bool(re.search(r"\b(?:per year|p\.?a\.?|annual|annum|/yr(?:ear)?|yearly)\b", s, re.I))
    is_monthly = bool(re.search(r"\b(?:per month|/month|/mo\.?|monthly|pcm)\b", s, re.I))

    pairs = []

    # Pattern A: symbol + number  e.g. $50,000  £60k
    for m in re.finditer(r"([$€£])\s*([\d,]+(?:\.\d+)?)\s*(k)?", s):
        cur = _SYM_MAP.get(m.group(1))
        if not cur:
            continue
        val = float(m.group(2).replace(",", "")) * (1000 if m.group(3) else 1)
        pairs.append((cur, val))

    # Pattern B: currency code + number  e.g. USD 50,000  SAR 15k
    for m in re.finditer(rf"\b({_CODE_PAT})\s+([\d,]+(?:\.\d+)?)\s*(k)?", s, re.I):
        val = float(m.group(2).replace(",", "")) * (1000 if m.group(3) else 1)
        pairs.append((m.group(1).lower(), val))

    # Pattern C: number + currency code  e.g. 50000 USD
    for m in re.finditer(rf"([\d,]+(?:\.\d+)?)\s*(k)?\s*\b({_CODE_PAT})\b", s, re.I):
        val = float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
        pairs.append((m.group(3).lower(), val))

    if not pairs:
        return True  # no salary info → let through

    best = 0.0
    for cur, val in pairs:
        rate = _RATES.get(cur)
        if not rate:
            continue
        egp = val * rate
        if is_annual:
            egp /= 12
        elif not is_monthly and cur not in ("kwd", "bhd", "omr") and val > 10_000:
            # Large raw number without period label → assume annual
            egp /= 12
        if egp > best:
            best = egp

    return best >= MIN_MONTHLY_EGP if best > 0 else True

# ── Foreign language filter ───────────────────────────────────────────────────
def _no_foreign_lang(title: str, desc: str) -> bool:
    """Return True (OK to send) when no hard foreign language requirement found."""
    combined = f"{title} {desc}"[:5000].lower()
    for lang in FOREIGN_LANGUAGES:
        idx = combined.find(lang)
        if idx == -1:
            continue
        # Check surrounding context for "nice to have" signals
        window = combined[max(0, idx - 80): idx + len(lang) + 100]
        if any(p in window for p in NICE_TO_HAVE):
            continue  # optional → not a disqualifier
        return False
    return True

# ── Master filter ─────────────────────────────────────────────────────────────
def passes_filter(job: dict) -> bool:
    title = (job.get("title") or "").strip()
    desc  = (job.get("description") or "")
    tl    = title.lower()

    # 1. Whitelist (title must match)
    if not any(w in tl for w in WHITELIST):
        return False

    # 2. Blacklist (title must NOT match)
    if any(b in tl for b in BLACKLIST):
        return False

    # 3. Gulf nationality restrictions (title + description)
    combined_l = f"{tl} {desc.lower()}"
    if any(n in combined_l for n in NATIONALITY_KEYWORDS):
        return False

    # 4. Foreign language requirement
    if not _no_foreign_lang(title, desc):
        return False

    # 5. Salary floor
    if not _salary_passes(desc):
        return False

    return True

# ── Job dict factory ──────────────────────────────────────────────────────────
def _job(source, uid, title, company, location, url, desc=""):
    return {
        "id": f"{source}-{uid}",
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "Remote").strip(),
        "url": (url or "").strip(),
        "source": source,
        "description": desc,
    }

# ── Source fetchers ───────────────────────────────────────────────────────────

def fetch_remotive():
    jobs = []
    raw = _fetch("https://remotive.com/api/remote-jobs?category=marketing&limit=100")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw).get("jobs", []):
            jobs.append(_job("Remotive", j.get("id"), j.get("title", ""),
                j.get("company_name", ""), j.get("candidate_required_location", "Remote"),
                j.get("url", ""), _strip_html(j.get("description", ""))[:3000]))
    except Exception as e:
        print(f"  [x] Remotive: {e}")
    return jobs


def fetch_remoteok():
    jobs = []
    raw = _fetch("https://remoteok.com/api")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw):
            if not isinstance(j, dict) or "id" not in j:
                continue
            jobs.append(_job("RemoteOK", j.get("id"), j.get("position", ""),
                j.get("company", ""), j.get("location", "Remote"),
                j.get("url", ""), _strip_html(j.get("description", ""))[:3000]))
    except Exception as e:
        print(f"  [x] RemoteOK: {e}")
    return jobs


def fetch_jobicy():
    jobs = []
    raw = _fetch("https://jobicy.com/api/v2/remote-jobs?count=50&industry=marketing")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw).get("jobs", []):
            jobs.append(_job("Jobicy", j.get("id"), j.get("jobTitle", ""),
                j.get("companyName", ""), j.get("jobGeo", "Remote"),
                j.get("url", ""), _strip_html(j.get("jobDescription", ""))[:3000]))
    except Exception as e:
        print(f"  [x] Jobicy: {e}")
    return jobs


def fetch_arbeitnow():
    jobs = []
    raw = _fetch("https://arbeitnow.com/api/job-board-api")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw).get("data", []):
            jobs.append(_job("Arbeitnow", j.get("slug", ""), j.get("title", ""),
                j.get("company_name", ""), j.get("location", "Remote"),
                j.get("url", ""), _strip_html(j.get("description", ""))[:3000]))
    except Exception as e:
        print(f"  [x] Arbeitnow: {e}")
    return jobs


def fetch_himalayas():
    jobs = []
    for q in ["marketing+manager", "head+of+marketing", "marketing+director"]:
        raw = _fetch(f"https://himalayas.app/jobs/api?q={q}&limit=50")
        if not raw:
            continue
        try:
            for j in json.loads(raw).get("jobs", []):
                jid = j.get("id") or j.get("slug", "")
                url = j.get("applicationLink") or j.get("url", "")
                jobs.append(_job("Himalayas", jid, j.get("title", ""),
                    j.get("companyName", ""), j.get("location", "Remote"),
                    url, _strip_html(j.get("description", ""))[:3000]))
        except Exception as e:
            print(f"  [x] Himalayas ({q}): {e}")
        time.sleep(1)
    return jobs


def fetch_weworkremotely():
    jobs = []
    raw = _fetch("https://weworkremotely.com/categories/remote-marketing-jobs.rss",
                 extra_headers={"Accept": "application/rss+xml, */*"})
    if not raw:
        return jobs
    try:
        root = ET.fromstring(raw)
        for item in root.iter("item"):
            title   = (item.findtext("title") or "").strip()
            link    = (item.findtext("link") or "").strip()
            guid    = (item.findtext("guid") or link).strip()
            desc    = _strip_html(item.findtext("description") or "")
            company = ""
            # WWR titles are often "CompanyName: Job Title"
            if ": " in title:
                company, title = title.split(": ", 1)
            jobs.append(_job("WeWorkRemotely", guid[-80:], title.strip(),
                company.strip(), "Remote", link, desc[:3000]))
    except Exception as e:
        print(f"  [x] WeWorkRemotely: {e}")
    return jobs


def fetch_themuse():
    jobs = []
    for page in range(3):
        raw = _fetch(
            f"https://www.themuse.com/api/public/jobs"
            f"?category=Marketing&level=Senior%20Level&page={page}&descending=true"
        )
        if not raw:
            break
        try:
            data = json.loads(raw)
            results = data.get("results", [])
            if not results:
                break
            for j in results:
                loc = ", ".join(l.get("name", "") for l in j.get("locations", []) if l.get("name"))
                jobs.append(_job("TheMuse", j.get("id", ""), j.get("name", ""),
                    j.get("company", {}).get("name", ""), loc or "Remote",
                    j.get("refs", {}).get("landing_page", ""),
                    _strip_html(j.get("body", ""))[:3000]))
        except Exception as e:
            print(f"  [x] TheMuse page {page}: {e}")
            break
        time.sleep(1)
    return jobs


def fetch_findwork():
    if not FINDWORK_API_KEY:
        print("  [!] FINDWORK_API_KEY not set, skipping Findwork")
        return []
    jobs = []
    auth = {"Authorization": f"Token {FINDWORK_API_KEY}"}
    for q in ["marketing+manager", "head+of+marketing", "marketing+director"]:
        raw = _fetch(
            f"https://findwork.dev/api/jobs/?search={q}&remote=true&order_by=-date",
            extra_headers=auth
        )
        if not raw:
            continue
        try:
            for j in json.loads(raw).get("results", []):
                jobs.append(_job("Findwork", j.get("id", ""), j.get("role", ""),
                    j.get("company_name", ""), "Remote", j.get("url", ""),
                    (j.get("text") or "")[:3000]))
        except Exception as e:
            print(f"  [x] Findwork ({q}): {e}")
        time.sleep(1)
    return jobs


def fetch_adzuna():
    if not ADZUNA_APP_ID or not ADZUNA_API_KEY:
        print("  [!] Adzuna credentials not set, skipping Adzuna")
        return []
    jobs = []
    for country in ["gb", "us", "ca", "au"]:
        for q in ["marketing+manager", "head+of+marketing", "marketing+director"]:
            url = (
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
                f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_API_KEY}"
                f"&what={q}&what_and=remote&results_per_page=50&content-type=application/json"
            )
            raw = _fetch(url)
            if not raw:
                continue
            try:
                for j in json.loads(raw).get("results", []):
                    jobs.append(_job(f"Adzuna-{country.upper()}", j.get("id", ""),
                        j.get("title", ""), j.get("company", {}).get("display_name", ""),
                        j.get("location", {}).get("display_name", "Remote"),
                        j.get("redirect_url", ""),
                        (j.get("description") or "")[:3000]))
            except Exception as e:
                print(f"  [x] Adzuna {country}/{q}: {e}")
            time.sleep(1)
    return jobs


def fetch_jooble():
    if not JOOBLE_API_KEY:
        print("  [!] JOOBLE_API_KEY not set, skipping Jooble")
        return []
    jobs = []
    for q in ["marketing manager", "head of marketing", "marketing director",
              "digital marketing manager", "performance marketing manager"]:
        payload = json.dumps({"keywords": q, "location": "remote", "page": "1"}).encode()
        raw = _fetch(
            f"https://jooble.org/api/{JOOBLE_API_KEY}",
            post_data=payload,
            extra_headers={"Content-Type": "application/json"},
        )
        if not raw:
            continue
        try:
            for j in json.loads(raw).get("jobs", []):
                jobs.append(_job("Jooble", j.get("id", ""), j.get("title", ""),
                    j.get("company", ""), j.get("location", "Remote"),
                    j.get("link", ""), _strip_html(j.get("snippet", ""))[:3000]))
        except Exception as e:
            print(f"  [x] Jooble ({q}): {e}")
        time.sleep(1)
    return jobs


SOURCES = [
    fetch_remotive,
    fetch_remoteok,
    fetch_jobicy,
    fetch_arbeitnow,
    fetch_himalayas,
    fetch_weworkremotely,
    fetch_themuse,
    fetch_findwork,
    fetch_adzuna,
    fetch_jooble,
]

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(job: dict) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [x] Telegram credentials not set.")
        return False
    text = (
        "New job: <b>" + html.escape(job["title"]) + "</b>\n"
        + html.escape(job["company"]) + "\n"
        + html.escape(job["location"]) + "\n"
        + html.escape(job["source"]) + "\n"
        + html.escape(job["url"])
    )
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": False,
    }).encode()
    try:
        with urlopen(Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"},
        ), timeout=20) as r:
            return bool(json.loads(r.read().decode()).get("ok"))
    except Exception as e:
        print(f"  [x] Telegram: {e}")
        return False

# ── State persistence ─────────────────────────────────────────────────────────
def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=1)

# ── Run ───────────────────────────────────────────────────────────────────────
def run_once(seen: set, first_run: bool = False):
    all_jobs = []
    for src in SOURCES:
        print(f"  -> {src.__name__.replace('fetch_', '')}")
        all_jobs.extend(src())
        time.sleep(2)

    # Deduplicate by URL across sources
    seen_urls: set = set()
    unique = []
    for j in all_jobs:
        key = j["url"] or j["id"]
        if key and key not in seen_urls:
            seen_urls.add(key)
            unique.append(j)

    matched = [j for j in unique if passes_filter(j)]
    new     = [j for j in matched if j["id"] not in seen]
    print(f"  total {len(unique)} | matched {len(matched)} | new {len(new)}")

    sent = 0
    for job in new:
        if first_run and not SEND_EXISTING_ON_FIRST_RUN:
            seen.add(job["id"])
            continue
        if send_telegram(job):
            sent += 1
        time.sleep(1)
        seen.add(job["id"])

    save_seen(seen)
    if first_run and not SEND_EXISTING_ON_FIRST_RUN:
        print(f"  first run: {len(matched)} saved, new jobs will be sent next run.")
    else:
        print(f"  sent {sent} new.")
    return sent


def main():
    print("=" * 40)
    print("  Job Hunter v2")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 40)
    seen  = load_seen()
    first = len(seen) == 0
    run_once(seen, first_run=first)
    if "--once" in sys.argv:
        print("done (--once).")
        return
    interval = 1200  # 20 minutes
    print(f"running every {interval // 60} min. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(interval)
            print("--- recheck", datetime.now().strftime("%H:%M"))
            run_once(seen)
    except KeyboardInterrupt:
        print("stopped.")


if __name__ == "__main__":
    main()
