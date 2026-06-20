# -*- coding: utf-8 -*-
"""Job Hunter: senior marketing remote jobs -> Telegram.

Collects marketing jobs from many FREE & LEGAL job sources (mostly
aggregators and remote-job boards), applies strict filters, and sends only
NEW matching jobs to a Telegram chat.

Secrets are read from environment variables:
    TELEGRAM_BOT_TOKEN   (required)
    TELEGRAM_CHAT_ID     (required)
    ADZUNA_APP_ID        (optional - enables Adzuna source)
    ADZUNA_APP_KEY       (optional - enables Adzuna source)
    JOOBLE_API_KEY       (optional - enables Jooble source)

No scraping of LinkedIn / Indeed / Glassdoor / Bayt is performed.
"""
import json, time, html, os, sys, re
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import quote_plus

# ----------------------------------------------------------------------------
# Secrets (from environment variables — never hard-code them)
# ----------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
ADZUNA_APP_ID      = os.environ.get("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY     = os.environ.get("ADZUNA_APP_KEY", "").strip()
JOOBLE_API_KEY     = os.environ.get("JOOBLE_API_KEY", "").strip()

# ----------------------------------------------------------------------------
# Filtering rules
# ----------------------------------------------------------------------------
# (1) Whitelist: title (lower-cased) must contain one of these phrases.
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

# (2) Blacklist: reject the job if the title contains any of these.
BLACKLIST = [
    "content creator", "content writer", "customer service", "supervisor",
    "specialist", "coordinator", "assistant", "intern", "internship",
    "junior", "graduate", "trainee", "entry",
]

# (4) Gulf-nationality requirement: reject if title/description contains any.
NATIONALITY_BLOCK = [
    "saudization", "saudi nationals only", "emiratization",
    "emirati nationals only", "qatarization", "qatari nationals only",
    "kuwaitization", "kuwaiti nationals only", "omanization",
    "omani nationals only", "bahrainization", "bahraini nationals only",
    "nationals only", "citizens only",
]

# (5) Foreign-language requirement: reject if a non-English/non-Arabic
# language is required. Each entry maps to the regex tokens that signal it.
FOREIGN_LANGUAGES = {
    "German":     [r"german", r"deutsch"],
    "French":     [r"french", r"fran[cç]ais"],
    "Spanish":    [r"spanish", r"espa[nñ]ol"],
    "Italian":    [r"italian", r"italiano"],
    "Dutch":      [r"dutch", r"nederlands"],
    "Portuguese": [r"portuguese", r"portugu[eê]s"],
    "Russian":    [r"russian"],
    "Polish":     [r"polish"],
    "Turkish":    [r"turkish"],
    "Chinese":    [r"chinese", r"mandarin"],
    "Japanese":   [r"japanese"],
    "Korean":     [r"korean"],
    "Swedish":    [r"swedish"],
    "Danish":     [r"danish"],
    "Norwegian":  [r"norwegian"],
    "Finnish":    [r"finnish"],
    "Greek":      [r"greek"],
    "Hebrew":     [r"hebrew"],
}
# If the language is only "nice to have", do NOT reject.
LANG_SOFT_HINTS = ["a plus", "plus.", "nice to have", "nice-to-have",
                   "is a bonus", "bonus", "preferred but not", "an advantage",
                   "advantageous", "would be a plus", "optional"]

# (6) Location filter -----------------------------------------------------
# STRICT allow-list: accept a job ONLY when its location OR description
# clearly places it in the Gulf, Egypt, or a region that includes them
# (MENA / Middle East / GCC / Gulf / Arab region). Everything else is
# rejected — Europe, the Americas, non-Gulf Asia, and any vague/blank or
# generic "Remote / Worldwide / Anywhere" location with no explicit mention.
# Short/ambiguous tokens use word boundaries to avoid false matches
# (e.g. "oman" inside "Romania", "mena" inside "phenomena").
LOCATION_ALLOW = [
    # --- regions that include Egypt/Gulf ---
    r"\bmena\b", r"middle east", r"\bgcc\b", r"\bgulf\b", r"arab region",
    # --- Saudi Arabia ---
    r"saudi arabia", r"\bsaudi\b", r"\bksa\b", r"riyadh", r"jeddah",
    # --- UAE ---
    r"\buae\b", r"united arab emirates", r"\bemirates\b", r"dubai",
    r"abu dhabi",
    # --- Qatar ---
    r"\bqatar\b", r"\bdoha\b",
    # --- Kuwait ---
    r"\bkuwait\b",
    # --- Oman ---
    r"\boman\b", r"muscat",
    # --- Bahrain ---
    r"bahrain", r"manama",
    # --- Egypt ---
    r"\begypt\b", r"egyptian", r"cairo",
]

# (3) Salary filter: convert to EGP/month; reject if < this threshold.
MIN_EGP_PER_MONTH = 50000

# Approximate FX rates: 1 unit of currency -> EGP. Update these as needed.
FX_TO_EGP = {
    "EGP": 1.0,
    "USD": 50.0,
    "EUR": 54.0,
    "GBP": 63.0,
    "SAR": 13.3,
    "AED": 13.6,
    "QAR": 13.7,
    "KWD": 162.0,
    "OMR": 130.0,
    "BHD": 132.0,
    "CAD": 36.0,
    "AUD": 33.0,
    "CHF": 56.0,
    "INR": 0.60,
    "JOD": 70.0,
    "JPY": 0.33,
}

# Map currency symbols / words -> ISO code used in FX_TO_EGP.
CURRENCY_TOKENS = [
    (r"egp|le\b|ج\.?م|جنيه", "EGP"),
    (r"\$|usd|us\$|dollar", "USD"),
    (r"€|eur|euro", "EUR"),
    (r"£|gbp|pound|sterling", "GBP"),
    (r"sar|﷼|ر\.?س|ريال سعودي|saudi riyal", "SAR"),
    (r"aed|د\.?إ|dirham", "AED"),
    (r"qar|qatari riyal", "QAR"),
    (r"kwd|kuwaiti dinar", "KWD"),
    (r"omr|omani rial", "OMR"),
    (r"bhd|bahraini dinar", "BHD"),
    (r"cad", "CAD"),
    (r"aud", "AUD"),
    (r"chf", "CHF"),
    (r"₹|inr|rupee", "INR"),
    (r"jod|jordanian dinar", "JOD"),
    (r"jpy|¥|yen", "JPY"),
    # generic "ريال" without country -> assume SAR (most common in Gulf ads)
    (r"ريال", "SAR"),
]

CHECK_INTERVAL_SECONDS = 1200  # 20 minutes (used only when looping locally)
SEEN_FILE = "seen_jobs.json"
SEND_EXISTING_ON_FIRST_RUN = True
HEADERS = {"User-Agent": "Mozilla/5.0 (JobHunter)",
           "Accept": "application/json, */*"}
SEARCH_TERMS = ["marketing manager", "digital marketing", "head of marketing",
                "performance marketing", "marketing director"]


# ----------------------------------------------------------------------------
# HTTP helpers
# ----------------------------------------------------------------------------
def _fetch(url, timeout=25, headers=None, data=None, method=None):
    try:
        req = Request(url, headers=headers or HEADERS, data=data, method=method)
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print("  [x]", e)
        return None


def _strip_html(s):
    return re.sub(r"<[^>]+>", " ", s or "")


# ----------------------------------------------------------------------------
# Sources (all free & legal). Each returns a list of normalized job dicts:
#   {id, title, company, location, url, source, description,
#    salary_text, salary_min, salary_max, salary_currency, salary_period}
# ----------------------------------------------------------------------------
def _job(id, title, company, location, url, source, description="",
         salary_text="", salary_min=None, salary_max=None,
         salary_currency=None, salary_period=None):
    return {
        "id": id, "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "Remote").strip(),
        "url": (url or "").strip(), "source": source,
        "description": _strip_html(description or ""),
        "salary_text": salary_text or "", "salary_min": salary_min,
        "salary_max": salary_max, "salary_currency": salary_currency,
        "salary_period": salary_period,
    }


def fetch_remotive():
    jobs = []
    raw = _fetch("https://remotive.com/api/remote-jobs?category=marketing&limit=200")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw).get("jobs", []):
            jobs.append(_job(
                f"remotive-{j.get('id')}", j.get("title"),
                j.get("company_name"), j.get("candidate_required_location") or "Remote",
                j.get("url"), "Remotive",
                description=j.get("description"),
                salary_text=j.get("salary") or ""))
    except json.JSONDecodeError:
        print("  [x] Remotive not JSON")
    return jobs


def fetch_jobicy():
    jobs = []
    raw = _fetch("https://jobicy.com/api/v2/remote-jobs?count=100&industry=marketing")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw).get("jobs", []):
            jobs.append(_job(
                f"jobicy-{j.get('id')}", j.get("jobTitle"),
                j.get("companyName"), j.get("jobGeo") or "Remote",
                j.get("url"), "Jobicy",
                description=j.get("jobExcerpt") or j.get("jobDescription"),
                salary_min=j.get("annualSalaryMin"),
                salary_max=j.get("annualSalaryMax"),
                salary_currency=j.get("salaryCurrency"),
                salary_period="year"))
    except json.JSONDecodeError:
        print("  [x] Jobicy not JSON")
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
            tags = " ".join(j.get("tags") or [])
            jobs.append(_job(
                f"remoteok-{j.get('id')}", j.get("position"),
                j.get("company"), j.get("location") or "Remote",
                j.get("url"), "RemoteOK",
                description=(j.get("description") or "") + " " + tags,
                salary_min=j.get("salary_min"),
                salary_max=j.get("salary_max"),
                salary_currency="USD", salary_period="year"))
    except json.JSONDecodeError:
        print("  [x] RemoteOK not JSON")
    return jobs


def fetch_arbeitnow():
    jobs = []
    raw = _fetch("https://www.arbeitnow.com/api/job-board-api")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw).get("data", []):
            jobs.append(_job(
                f"arbeitnow-{j.get('slug')}", j.get("title"),
                j.get("company_name"), j.get("location") or "Remote",
                j.get("url"), "Arbeitnow",
                description=j.get("description")))
    except json.JSONDecodeError:
        print("  [x] Arbeitnow not JSON")
    return jobs


def fetch_himalayas():
    jobs = []
    raw = _fetch("https://himalayas.app/jobs/api?limit=100")
    if not raw:
        return jobs
    try:
        for j in json.loads(raw).get("jobs", []):
            loc = j.get("locationRestrictions") or []
            jobs.append(_job(
                f"himalayas-{j.get('guid') or j.get('title')}", j.get("title"),
                j.get("companyName"), ", ".join(loc) if loc else "Remote",
                j.get("applicationLink") or j.get("guid"), "Himalayas",
                description=j.get("description") or j.get("excerpt"),
                salary_min=j.get("minSalary"), salary_max=j.get("maxSalary"),
                salary_currency=j.get("salaryCurrency") or "USD",
                salary_period="year"))
    except json.JSONDecodeError:
        print("  [x] Himalayas not JSON")
    return jobs


def fetch_weworkremotely():
    """We Work Remotely – marketing RSS feed (legal, public feed)."""
    jobs = []
    raw = _fetch("https://weworkremotely.com/categories/remote-marketing-jobs.rss")
    if not raw:
        return jobs
    items = re.findall(r"<item>(.*?)</item>", raw, re.S)
    for it in items:
        def grab(tag):
            m = re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S)
            if not m:
                return ""
            val = m.group(1)
            val = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", val, flags=re.S)
            return html.unescape(val).strip()
        link = grab("link")
        title = grab("title")  # often "Company: Job Title"
        company = ""
        if ":" in title:
            company, title = title.split(":", 1)
        jobs.append(_job(
            f"wwr-{link}", title.strip(), company.strip(),
            grab("region") or "Remote", link, "WeWorkRemotely",
            description=grab("description")))
    return jobs


def fetch_themuse():
    jobs = []
    for page in range(0, 3):
        raw = _fetch(f"https://www.themuse.com/api/public/jobs?category=Marketing&page={page}")
        if not raw:
            break
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("  [x] TheMuse not JSON")
            break
        for j in data.get("results", []):
            locs = [l.get("name") for l in (j.get("locations") or [])]
            comp = (j.get("company") or {}).get("name")
            refs = (j.get("refs") or {}).get("landing_page")
            jobs.append(_job(
                f"themuse-{j.get('id')}", j.get("name"), comp,
                ", ".join(locs) if locs else "Remote", refs, "TheMuse",
                description=j.get("contents")))
        time.sleep(1)
    return jobs


def fetch_findwork():
    """Findwork.dev public job search (no key needed for basic search)."""
    jobs = []
    raw = _fetch("https://findwork.dev/api/jobs/?search=marketing&remote=true")
    if not raw:
        return jobs
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("  [x] Findwork not JSON")
        return jobs
    for j in data.get("results", []):
        jobs.append(_job(
            f"findwork-{j.get('id')}", j.get("role"), j.get("company_name"),
            j.get("location") or "Remote", j.get("url"), "Findwork",
            description=j.get("text"),
            salary_text=j.get("keywords") and "" or ""))
    return jobs


def fetch_adzuna():
    """Adzuna aggregator (needs free APP_ID + APP_KEY)."""
    jobs = []
    if not (ADZUNA_APP_ID and ADZUNA_APP_KEY):
        print("  [i] Adzuna skipped (no ADZUNA_APP_ID / ADZUNA_APP_KEY)")
        return jobs
    countries = ["gb", "us", "ae"]  # aggregator coverage across boards
    for c in countries:
        for term in ["marketing manager", "head of marketing"]:
            url = (f"https://api.adzuna.com/v1/api/jobs/{c}/search/1"
                   f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
                   f"&results_per_page=50&what={quote_plus(term)}"
                   f"&content-type=application/json")
            raw = _fetch(url)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                print("  [x] Adzuna not JSON")
                continue
            cur = {"gb": "GBP", "us": "USD", "ae": "AED"}.get(c, "USD")
            for j in data.get("results", []):
                jobs.append(_job(
                    f"adzuna-{j.get('id')}", j.get("title"),
                    (j.get("company") or {}).get("display_name"),
                    (j.get("location") or {}).get("display_name") or "Remote",
                    j.get("redirect_url"), "Adzuna",
                    description=j.get("description"),
                    salary_min=j.get("salary_min"),
                    salary_max=j.get("salary_max"),
                    salary_currency=cur, salary_period="year"))
            time.sleep(1)
    return jobs


def fetch_jooble():
    """Jooble aggregator (needs free API key)."""
    jobs = []
    if not JOOBLE_API_KEY:
        print("  [i] Jooble skipped (no JOOBLE_API_KEY)")
        return jobs
    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    for term in ["marketing manager", "head of marketing", "marketing director"]:
        body = json.dumps({"keywords": term, "location": "remote"}).encode("utf-8")
        raw = _fetch(url, headers={"Content-Type": "application/json"},
                     data=body, method="POST")
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("  [x] Jooble not JSON")
            continue
        for j in data.get("jobs", []):
            jobs.append(_job(
                f"jooble-{j.get('id')}", j.get("title"), j.get("company"),
                j.get("location") or "Remote", j.get("link"), "Jooble",
                description=j.get("snippet"),
                salary_text=j.get("salary") or ""))
        time.sleep(1)
    return jobs


SOURCES = [
    fetch_remotive, fetch_jobicy, fetch_remoteok, fetch_arbeitnow,
    fetch_himalayas, fetch_weworkremotely, fetch_themuse, fetch_findwork,
    fetch_adzuna, fetch_jooble,
]


# ----------------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------------
def title_passes(title):
    t = (title or "").lower()
    if not t:
        return False
    if any(b in t for b in BLACKLIST):       # (2) blacklist
        return False
    return any(w in t for w in WHITELIST)     # (1) whitelist


def nationality_passes(text):
    """(4) Reject Gulf-nationality-only postings."""
    t = (text or "").lower()
    return not any(p in t for p in NATIONALITY_BLOCK)


def language_passes(text):
    """(5) Reject if a non-EN/AR language is *required* (not 'a plus')."""
    t = (text or "").lower()
    for lang, tokens in FOREIGN_LANGUAGES.items():
        for tok in tokens:
            for m in re.finditer(tok, t):
                # Look at a small window after the mention to see if it's soft.
                window = t[m.start(): m.end() + 80]
                if any(h in window for h in LANG_SOFT_HINTS):
                    continue  # mentioned only as "a plus" -> ignore
                return False
    return True


def _to_egp_month(amount, currency, period):
    rate = FX_TO_EGP.get((currency or "USD").upper(), FX_TO_EGP["USD"])
    egp = amount * rate
    p = (period or "year").lower()
    if "year" in p or "annum" in p or "yr" in p or "annual" in p:
        egp /= 12.0
    elif "week" in p:
        egp *= 4.33
    elif "day" in p:
        egp *= 22.0
    elif "hour" in p or "hr" in p:
        egp *= 160.0
    # "month" -> as-is
    return egp


def _parse_salary_text(text):
    """Return (amount, currency, period) parsed from free text, or None."""
    if not text:
        return None
    t = text.lower().replace(",", "")
    currency = None
    for pat, code in CURRENCY_TOKENS:
        if re.search(pat, t):
            currency = code
            break
    if not currency:
        return None
    # Find numbers, supporting 50k / 50,000 / 5.5k style.
    nums = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([km])?", t):
        val = float(m.group(1))
        suf = m.group(2)
        if suf == "k":
            val *= 1_000
        elif suf == "m":
            val *= 1_000_000
        if val >= 100:  # ignore tiny stray numbers
            nums.append(val)
    if not nums:
        return None
    amount = sum(nums) / len(nums)  # midpoint of any range found
    period = "year"
    if re.search(r"month|/mo|per month|monthly|شهر", t):
        period = "month"
    elif re.search(r"hour|/hr|hourly|per hour|/hour", t):
        period = "hour"
    elif re.search(r"week|weekly", t):
        period = "week"
    return amount, currency, period


def salary_passes(job):
    """(3) If salary present, require >= MIN_EGP_PER_MONTH. No salary -> pass."""
    # Prefer structured numeric salary.
    smin, smax = job.get("salary_min"), job.get("salary_max")
    amount = None
    if smin or smax:
        vals = [v for v in (smin, smax) if v]
        try:
            amount = sum(float(v) for v in vals) / len(vals)
        except (TypeError, ValueError):
            amount = None
    if amount is not None:
        egp = _to_egp_month(amount, job.get("salary_currency"),
                            job.get("salary_period"))
        return egp >= MIN_EGP_PER_MONTH

    # Otherwise parse free-text salary, then fall back to scanning description.
    for src in (job.get("salary_text"), job.get("description")):
        parsed = _parse_salary_text(src)
        if parsed:
            amount, currency, period = parsed
            egp = _to_egp_month(amount, currency, period)
            return egp >= MIN_EGP_PER_MONTH

    return True  # no salary mentioned -> let it pass


def location_passes(location, description=""):
    """(6) STRICT: accept ONLY when the location OR description explicitly
    names the Gulf, Egypt, or a region that includes them (MENA / Middle
    East / GCC / Gulf / Arab region). Everything else is rejected, including
    vague/blank locations and generic 'Remote / Worldwide / Anywhere' with
    no explicit Gulf/Egypt/MENA mention."""
    combined = ((location or "") + " " + (description or "")).lower()
    return any(re.search(p, combined) for p in LOCATION_ALLOW)


def passes_filter(job):
    blob = (job.get("title", "") + " " + job.get("description", ""))
    if not title_passes(job.get("title")):
        return False
    if not location_passes(job.get("location"), job.get("description")):
        return False
    if not nationality_passes(blob):
        return False
    if not language_passes(blob):
        return False
    if not salary_passes(job):
        return False
    return True


# ----------------------------------------------------------------------------
# Telegram + state
# ----------------------------------------------------------------------------
def send_telegram(job):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [x] Telegram secrets not set (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).")
        return False
    text = ("New: <b>" + html.escape(job["title"]) + "</b>\n"
            + html.escape(job["company"]) + "\n"
            + html.escape(job["location"]) + "\n"
            + html.escape(job["source"]) + "\n"
            + html.escape(job["url"]))
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text,
                          "parse_mode": "HTML",
                          "disable_web_page_preview": False}).encode("utf-8")
    try:
        with urlopen(Request("https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN
                             + "/sendMessage", data=payload,
                             headers={"Content-Type": "application/json"}),
                     timeout=20) as r:
            return bool(json.loads(r.read().decode()).get("ok"))
    except Exception as e:
        print("  [x] telegram:", e)
        return False


def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=1)


def run_once(seen, first_run=False):
    all_jobs = []
    for src in SOURCES:
        print("  -> checking", src.__name__.replace("fetch_", ""))
        try:
            all_jobs.extend(src())
        except Exception as e:
            print("  [x] source error:", e)
        time.sleep(1)
    matched = [j for j in all_jobs if passes_filter(j)]
    new = [j for j in matched if j["id"] not in seen]
    print("  total", len(all_jobs), "matched", len(matched), "new", len(new))
    for j in matched:
        print("   *", j["title"], "-", j["company"], "(", j["source"], ")")
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
    print("  first run: saved, will send new next time."
          if (first_run and not SEND_EXISTING_ON_FIRST_RUN)
          else "  sent " + str(sent) + " new.")
    return sent


def main():
    print("=" * 40)
    print("  Job Hunter")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 40)
    loop = "--once" not in sys.argv
    seen = load_seen()
    first = len(seen) == 0
    run_once(seen, first_run=first)
    if not loop:
        print("done (--once).")
        return
    print("running every", CHECK_INTERVAL_SECONDS // 60, "min. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)
            print("--- recheck", datetime.now().strftime("%H:%M"))
            run_once(seen)
    except KeyboardInterrupt:
        print("stopped.")


if __name__ == "__main__":
    main()
