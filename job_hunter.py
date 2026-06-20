# -*- coding: utf-8 -*-
"""Job Hunter: marketing-manager remote jobs -> Telegram."""
import json, time, html, os, sys
from datetime import datetime
from urllib.request import Request, urlopen

TELEGRAM_BOT_TOKEN = "8518591008:AAFf24I38qtsj40KCSAkx5JYiEUh1hKGIQA"
TELEGRAM_CHAT_ID   = "5936947558"

SENIOR  = ["manager", "director", "head", "senior"]
EXCLUDE = ["assistant","intern","internship","junior","coordinator","specialist","trainee","graduate","entry"]
CHECK_INTERVAL_SECONDS = 900
SEEN_FILE = "seen_jobs.json"
SEND_EXISTING_ON_FIRST_RUN = True
HEADERS = {"User-Agent":"Mozilla/5.0 (JobHunter)","Accept":"application/json, */*"}

def _fetch(url, timeout=25):
    try:
        with urlopen(Request(url, headers=HEADERS), timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print("  [x]", e); return None

def fetch_remotive():
    jobs=[]; raw=_fetch("https://remotive.com/api/remote-jobs?category=marketing&limit=100")
    if not raw: return jobs
    try:
        for j in json.loads(raw).get("jobs", []):
            jobs.append({"id":f"remotive-{j.get('id')}","title":(j.get("title") or "").strip(),
                "company":(j.get("company_name") or "").strip(),
                "location":(j.get("candidate_required_location") or "Remote").strip(),
                "url":(j.get("url") or "").strip(),"source":"Remotive"})
    except json.JSONDecodeError: print("  [x] Remotive not JSON")
    return jobs

def fetch_jobicy():
    jobs=[]; raw=_fetch("https://jobicy.com/api/v2/remote-jobs?count=50&industry=marketing")
    if not raw: return jobs
    try:
        for j in json.loads(raw).get("jobs", []):
            jobs.append({"id":f"jobicy-{j.get('id')}","title":(j.get("jobTitle") or "").strip(),
                "company":(j.get("companyName") or "").strip(),
                "location":(j.get("jobGeo") or "Remote").strip(),
                "url":(j.get("url") or "").strip(),"source":"Jobicy"})
    except json.JSONDecodeError: print("  [x] Jobicy not JSON")
    return jobs

def fetch_remoteok():
    jobs=[]; raw=_fetch("https://remoteok.com/api")
    if not raw: return jobs
    try:
        for j in json.loads(raw):
            if not isinstance(j, dict) or "id" not in j: continue
            jobs.append({"id":f"remoteok-{j.get('id')}","title":(j.get("position") or "").strip(),
                "company":(j.get("company") or "").strip(),
                "location":(j.get("location") or "Remote").strip(),
                "url":(j.get("url") or "").strip(),"source":"RemoteOK"})
    except json.JSONDecodeError: print("  [x] RemoteOK not JSON")
    return jobs

SOURCES=[fetch_remotive, fetch_jobicy, fetch_remoteok]

def passes_filter(job):
    t=(job.get("title") or "").lower()
    if not t or any(b in t for b in EXCLUDE): return False
    if "head of digital" in t: return True
    return ("marketing" in t) and any(s in t for s in SENIOR)

def send_telegram(job):
    if "PUT_YOUR" in TELEGRAM_BOT_TOKEN or "PUT_YOUR" in TELEGRAM_CHAT_ID:
        print("  [x] Telegram token not set."); return False
    text=("New: <b>"+html.escape(job["title"])+"</b>\n"+html.escape(job["company"])+"\n"
        +html.escape(job["location"])+"\n"+html.escape(job["source"])+"\n"+html.escape(job["url"]))
    payload=json.dumps({"chat_id":TELEGRAM_CHAT_ID,"text":text,"parse_mode":"HTML",
        "disable_web_page_preview":False}).encode("utf-8")
    try:
        with urlopen(Request("https://api.telegram.org/bot"+TELEGRAM_BOT_TOKEN+"/sendMessage",
            data=payload, headers={"Content-Type":"application/json"}), timeout=20) as r:
            return bool(json.loads(r.read().decode()).get("ok"))
    except Exception as e:
        print("  [x] telegram:", e); return False

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, encoding="utf-8") as f: return set(json.load(f))
        except Exception: return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=1)

def run_once(seen, first_run=False):
    all_jobs=[]
    for src in SOURCES:
        print("  -> checking", src.__name__.replace("fetch_",""))
        all_jobs.extend(src()); time.sleep(2)
    matched=[j for j in all_jobs if passes_filter(j)]
    new=[j for j in matched if j["id"] not in seen]
    print("  total", len(all_jobs), "matched", len(matched), "new", len(new))
    for j in matched: print("   *", j["title"], "-", j["company"], "(", j["source"], ")")
    sent=0
    for job in new:
        if first_run and not SEND_EXISTING_ON_FIRST_RUN:
            seen.add(job["id"]); continue
        if send_telegram(job): sent+=1; time.sleep(1)
        seen.add(job["id"])
    save_seen(seen)
    print("  first run: saved, will send new next time." if (first_run and not SEND_EXISTING_ON_FIRST_RUN)
        else "  sent "+str(sent)+" new.")
    return sent

def main():
    print("="*40); print("  Job Hunter"); print("  "+datetime.now().strftime("%Y-%m-%d %H:%M")); print("="*40)
    loop="--once" not in sys.argv
    seen=load_seen(); first=len(seen)==0
    run_once(seen, first_run=first)
    if not loop: print("done (--once)."); return
    print("running every", CHECK_INTERVAL_SECONDS//60, "min. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)
            print("--- recheck", datetime.now().strftime("%H:%M")); run_once(seen)
    except KeyboardInterrupt: print("stopped.")

if __name__ == "__main__":
    main()
