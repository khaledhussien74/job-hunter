# -*- coding: utf-8 -*-
"""CV tailoring for Job Hunter.

For a given job (title + description/snippet) this module produces a tailored,
ATS-friendly PDF CV built from the MASTER CV (cv_master.json):

  1. Picks the best-fit target title (Marketing Manager / Digital Marketing
     Manager / Performance Marketing Manager / Growth Marketing Manager).
  2. Rewrites the Professional Summary and re-orders Core Competencies to mirror
     the job's keywords/requirements — using ONLY facts from the master CV
     (no fabrication). This step uses the Anthropic API when ANTHROPIC_API_KEY
     is available; otherwise a keyword heuristic is used as a fallback.
  3. Renders a clean, single-column, ATS-friendly PDF (selectable text,
     standard section headings, no tables/columns/images).

The job's full work history, employers, dates, numbers, education and skills
are always taken verbatim from the master CV, so the CV stays truthful.
"""
import json, os, re
from urllib.request import Request, urlopen

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
# Default model. Override with the ANTHROPIC_MODEL env var.
# Sonnet gives the best tailoring; Haiku is cheaper (claude-haiku-4-5-20251001).
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip()

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_PATH = os.path.join(HERE, "cv_master.json")


# ---------------------------------------------------------------------------
def load_master(path=MASTER_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Title selection
# ---------------------------------------------------------------------------
# Keyword -> canonical title. Checked against the job title first, then the
# job description. The first allowed title that matches wins.
_TITLE_RULES = [
    ("Performance Marketing Manager",
     [r"performance marketing", r"\bppc\b", r"media buy", r"paid (media|ads|search|social)"]),
    ("Growth Marketing Manager",
     [r"growth marketing", r"\bgrowth\b", r"demand gen", r"user acquisition", r"\bcac\b", r"\bltv\b"]),
    ("Digital Marketing Manager",
     [r"digital marketing", r"\bseo\b", r"\bsem\b", r"\bcro\b", r"google ads", r"social media", r"online marketing"]),
    ("Marketing Manager",
     [r"marketing manager", r"head of marketing", r"marketing director", r"\bbrand\b", r"marketing"]),
]


def heuristic_title(job, allowed):
    """Pick the closest allowed title from the job's text via keywords."""
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    for target, patterns in _TITLE_RULES:
        if target not in allowed:
            continue
        if any(re.search(p, title) for p in patterns):
            return target
    for target, patterns in _TITLE_RULES:
        if target not in allowed:
            continue
        if any(re.search(p, desc) for p in patterns):
            return target
    return allowed[0]


# ---------------------------------------------------------------------------
# FREE local tailoring (no API, no token) — role-specific summary + keyword
# re-ordering of competencies. All wording is derived from the master CV
# facts, so the CV stays truthful.
# ---------------------------------------------------------------------------
# One tailored summary per target title. Every claim here exists in the
# master CV (cv_master.json) — only the emphasis changes per role.
ROLE_SUMMARIES = {
    "Marketing Manager": (
        "Marketing manager with 10+ years driving revenue, demand, and brand "
        "growth across the GCC and MENA. I own the full customer journey "
        "end-to-end — paid media, SEO/CRO, organic social, and brand — and "
        "decide on data, reporting on CAC, LTV, and ROAS rather than vanity "
        "metrics. A hands-on, full-funnel operator and a proven leader who has "
        "built and led teams from 12 to 150+, with a strong GA4/GTM analytics "
        "foundation, deep GCC market knowledge, and native Arabic. Certified by "
        "Google, LinkedIn, and Coursera."
    ),
    "Digital Marketing Manager": (
        "Digital marketing manager with 10+ years driving online growth across "
        "the GCC and MENA. I own digital end-to-end — paid search and paid "
        "social (Google Ads, Meta, TikTok, Snapchat), SEO, CRO, organic social, "
        "and CRM/lifecycle — on a strong analytics foundation in GA4, Google "
        "Tag Manager, and Looker Studio. I make decisions on data, reporting on "
        "CAC, LTV, and ROAS, and use AI tools to automate reporting and "
        "workflows. Native Arabic with deep GCC market knowledge; certified by "
        "Google, LinkedIn, and Coursera."
    ),
    "Performance Marketing Manager": (
        "Performance marketing manager with 10+ years running paid media at "
        "scale across the GCC and MENA. Hands-on across Google Ads and paid "
        "social (Meta, TikTok, Snapchat) with daily spend, pacing, and budget "
        "management, consistently hitting ROAS targets and improving unit "
        "economics (CAC, LTV) — including 5.2x ROAS on $300K+ annual spend and "
        "monthly budgets above $2.5M. Strong CRO and full-funnel optimisation "
        "backed by GA4, Google Tag Manager, and Looker Studio. Native Arabic "
        "with deep GCC market knowledge; certified by Google, LinkedIn, and "
        "Coursera."
    ),
    "Growth Marketing Manager": (
        "Growth marketing manager with 10+ years driving demand, acquisition, "
        "and revenue across the GCC and MENA. I own full-funnel growth "
        "end-to-end — paid media, SEO/CRO, CRM/lifecycle, and A/B "
        "experimentation — and optimise on unit economics (CAC, LTV) and ROAS "
        "rather than vanity metrics, including cutting CAC by up to 28% and "
        "lifting lead generation by 40%. Strong analytics in GA4, Google Tag "
        "Manager, and Looker Studio, and a daily user of AI tools to automate "
        "workflows. Native Arabic with deep GCC market knowledge; certified by "
        "Google, LinkedIn, and Coursera."
    ),
}

_STOP = {"and", "the", "for", "with", "you", "our", "are", "will", "across",
         "have", "this", "that", "from", "your", "they", "all", "who", "has"}


def _job_keywords(job):
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    words = re.findall(r"[a-z0-9]+", text)
    return {w for w in words if len(w) > 2 and w not in _STOP}


def _reorder_competencies(job, competencies):
    """Stable-sort competencies so the ones most relevant to THIS job (by
    keyword overlap) come first. Nothing is added or removed."""
    kws = _job_keywords(job)
    if not kws:
        return list(competencies)

    def score(comp):
        cwords = set(re.findall(r"[a-z0-9]+", comp.lower()))
        return len(cwords & kws)

    ranked = sorted(range(len(competencies)),
                    key=lambda i: (-score(competencies[i]), i))
    return [competencies[i] for i in ranked]


def smart_local_tailor(job, master):
    """Free, deterministic tailoring: heuristic title + role-specific summary
    + job-keyword competency ordering. No API and no token required."""
    allowed = master.get("allowed_titles",
                         [master.get("default_title", "Marketing Manager")])
    title = heuristic_title(job, allowed)
    summary = ROLE_SUMMARIES.get(title) or master.get("summary", "")
    comps = _reorder_competencies(job, master.get("competencies", []))
    return {"target_title": title, "summary": summary, "competencies": comps}


# ---------------------------------------------------------------------------
# Anthropic API tailoring (OPTIONAL — only used if ANTHROPIC_API_KEY is set)
# ---------------------------------------------------------------------------
_SYSTEM = (
    "You are an expert ATS resume writer. You tailor an existing master CV to a "
    "specific job. You MUST NOT invent or change any facts: employers, dates, "
    "numbers, metrics, titles of past roles, education, certifications and tools "
    "are fixed. You only (a) choose the best-fit target headline title from the "
    "allowed list, (b) rewrite the professional summary so it naturally mirrors "
    "the job's real keywords and requirements while staying 100% truthful to the "
    "master CV, and (c) re-order/select the most relevant core competencies "
    "(only items already in the master list). Keep the summary 3-5 sentences, "
    "first person optional, concrete and ATS-friendly (plain words, real "
    "keywords, no buzzword stuffing). Reply with JSON only."
)


def _anthropic_tailor(job, master, api_key, model):
    allowed = master.get("allowed_titles", [master.get("default_title", "Marketing Manager")])
    user = {
        "job": {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "description": (job.get("description", "") or "")[:4000],
        },
        "allowed_titles": allowed,
        "master_summary": master.get("summary", ""),
        "master_competencies": master.get("competencies", []),
    }
    prompt = (
        "Tailor this CV to the job below.\n\n"
        + json.dumps(user, ensure_ascii=False)
        + "\n\nReturn JSON with EXACTLY these keys:\n"
        '{"target_title": "<one of allowed_titles>",\n'
        ' "summary": "<rewritten 3-5 sentence summary, truthful to master_summary>",\n'
        ' "competencies": ["<subset of master_competencies, most relevant first, 12-18 items, verbatim>"]}'
    )
    body = json.dumps({
        "model": model,
        "max_tokens": 1200,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = Request(ANTHROPIC_ENDPOINT, data=body, headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }, method="POST")
    with urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))
    # Concatenate text blocks, then extract the JSON object.
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in model reply")
    out = json.loads(m.group(0))
    if out.get("target_title") not in allowed:
        out["target_title"] = heuristic_title(job, allowed)
    # Keep only competencies that actually exist in the master (no fabrication).
    master_comp = master.get("competencies", [])
    out["competencies"] = [c for c in out.get("competencies", []) if c in master_comp] or master_comp
    if not out.get("summary"):
        out["summary"] = master.get("summary", "")
    return out


def tailor(job, master, api_key=None, model=None):
    """Return {target_title, summary, competencies}.

    Default is FREE local tailoring (no API, no token). If an ANTHROPIC_API_KEY
    is explicitly provided, an AI rewrite is used instead; on any failure it
    falls back to the free local tailoring."""
    api_key = (api_key if api_key is not None
               else os.environ.get("ANTHROPIC_API_KEY", "")).strip()
    model = model or DEFAULT_MODEL
    if api_key:
        try:
            return _anthropic_tailor(job, master, api_key, model)
        except Exception as e:
            print("  [x] CV tailor (API) failed, using free local tailoring:", e)
    # Default path: free, deterministic, no token required.
    return smart_local_tailor(job, master)


# ---------------------------------------------------------------------------
# ATS-friendly PDF rendering (single column, plain text, standard headings)
# ---------------------------------------------------------------------------
def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", (s or "").strip()).strip("_") or "CV"


def render_pdf(tailored, master, out_path):
    """Render an ATS-friendly PDF. Requires fpdf2 (pip install fpdf2)."""
    from fpdf import FPDF

    # Normalise unicode punctuation that the core PDF fonts can't encode.
    def s(t):
        if t is None:
            return ""
        repl = {"–": "-", "—": "-", "‘": "'", "’": "'",
                "“": '"', "”": '"', "•": "-", "…": "...",
                " ": " ", "→": "->", "×": "x", "€": "EUR",
                "£": "GBP"}
        for k, v in repl.items():
            t = t.replace(k, v)
        return t.encode("latin-1", "ignore").decode("latin-1")

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 14, 15)
    pdf.add_page()
    W = pdf.w - pdf.l_margin - pdf.r_margin

    def heading(txt):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 6, s(txt.upper()), new_x="LMARGIN", new_y="NEXT")
        y = pdf.get_y()
        pdf.set_draw_color(150, 150, 150)
        pdf.line(pdf.l_margin, y, pdf.l_margin + W, y)
        pdf.ln(1.5)

    def body(txt, size=9.5, style="", gap=4.6):
        pdf.set_font("Helvetica", style, size)
        pdf.set_text_color(35, 35, 35)
        pdf.multi_cell(0, gap, s(txt), new_x="LMARGIN", new_y="NEXT")

    def bullet(txt):
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(35, 35, 35)
        x = pdf.get_x()
        pdf.cell(4, 4.6, "-")
        pdf.set_x(x + 4)
        pdf.multi_cell(W - 4, 4.6, s(txt), new_x="LMARGIN", new_y="NEXT")

    name = master.get("name", "")
    contact = master.get("contact", {})
    title = tailored.get("target_title") or master.get("default_title", "")

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 15, 15)
    pdf.cell(0, 8, s(name), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11.5)
    pdf.set_text_color(70, 70, 70)
    pdf.cell(0, 6, s(title), new_x="LMARGIN", new_y="NEXT")
    cline = "  |  ".join(v for v in [contact.get("email"), contact.get("phone"),
                                     contact.get("location"), contact.get("linkedin")] if v)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 5, s(cline), new_x="LMARGIN", new_y="NEXT")

    # Summary
    heading("Professional Summary")
    body(tailored.get("summary") or master.get("summary", ""))

    # Core competencies (tailored order) — comma-joined for clean ATS parsing
    comps = tailored.get("competencies") or master.get("competencies", [])
    if comps:
        heading("Core Competencies")
        body("  -  ".join(comps))

    # Experience (verbatim from master)
    heading("Professional Experience")
    for e in master.get("experience", []):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 5, s(e.get("title", "")) + "   |   " + s(e.get("dates", "")),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.set_text_color(70, 70, 70)
        comp_loc = s(e.get("company", ""))
        if e.get("location"):
            comp_loc += "  -  " + s(e.get("location"))
        pdf.cell(0, 5, comp_loc, new_x="LMARGIN", new_y="NEXT")
        for b in e.get("bullets", []):
            bullet(b)
        pdf.ln(1)

    # Skills (verbatim). Use markdown bold so the label + value wrap cleanly
    # across the full width without manual cursor juggling.
    skills = master.get("skills", {})
    if skills:
        heading("Technical Skills & Tools")
        pdf.set_text_color(35, 35, 35)
        for k, v in skills.items():
            pdf.set_font("Helvetica", "", 9.5)
            pdf.multi_cell(0, 4.6, "**" + s(k) + ":** " + s(v), markdown=True,
                           new_x="LMARGIN", new_y="NEXT")

    # Education
    edu = master.get("education", [])
    if edu:
        heading("Education")
        for ed in edu:
            line = s(ed.get("degree", ""))
            if ed.get("institution"):
                line += "  -  " + s(ed.get("institution"))
            body(line)

    # Certifications & languages
    heading("Certifications & Languages")
    if master.get("certifications"):
        body("Certifications: " + master["certifications"])
    if master.get("languages"):
        body("Languages: " + master["languages"])

    pdf.output(out_path)
    return out_path


def build_cv_for_job(job, master, out_dir, api_key=None, model=None):
    """Tailor + render. Returns (pdf_path, tailored_dict)."""
    tailored = tailor(job, master, api_key=api_key, model=model)
    fname = "Khaled_Hussien_CV_" + _slug(tailored["target_title"]) + ".pdf"
    out_path = os.path.join(out_dir, fname)
    render_pdf(tailored, master, out_path)
    return out_path, tailored
