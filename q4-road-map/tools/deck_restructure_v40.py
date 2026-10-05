"""Restructure the Data Platform deck: big picture -> four capabilities -> detail per capability."""
import json
import re
import shutil
from pathlib import Path

SRC = Path("/tmp/claude-0/-home-user-harish/46702d0d-4589-5388-ae89-63d39405c644/scratchpad/artifact-files/8884f25c-a7bc-494e-9d13-063ed9fcfa1d/project")
ROOT = Path("/tmp/claude-0/-home-user-harish/46702d0d-4589-5388-ae89-63d39405c644/scratchpad/deck-root")
OUT = ROOT / "project" / "slides"
if ROOT.exists():
    shutil.rmtree(ROOT)
OUT.mkdir(parents=True)

ORDER = [
    # s1 big picture
    "cover", "lessons", "current", "target", "platform", "onepager", "summary",
    # s2 how they fit
    "sequencing", "dependencies",
    # s3 capability 1
    "cap-ing", "ing-brief", "ing-reuse", "ing-architecture", "ing-ui", "ing-jobstore", "ing-tables",
    "ing-erd", "ing-release", "ing-phases", "ing-onboarding", "ing-kpis",
    # s4 capability 2
    "cap-lap", "lp-brief", "lp-personas", "lp-architecture", "lp-split", "lp-phases", "lp-kpis",
    "acc-brief", "acc-workflow", "acc-phases", "acc-kpis",
    # s5 capability 3
    "cap-pii", "pii-brief", "pii-framework", "pii-tiers", "pii-controls", "pii-masking",
    "pii-detection", "pii-phases", "pii-kpis",
    # s6 capability 4
    "cap-doc", "doc-brief", "doc-workflow", "doc-phases", "doc-kpis",
    # s7 delivery
    "oct", "nov", "dec", "evolution", "capacity",
    # s8 governance
    "risks", "dashboard", "ownership", "asks",
]
NUM = {sid: f"{i + 1:02d}" for i, sid in enumerate(ORDER)}

slides = {p.stem: p.read_text() for p in (SRC / "slides").glob("*.html")}
assert set(slides) | {"platform", "cap-ing", "cap-lap", "cap-pii", "cap-doc"} == set(ORDER), \
    set(ORDER) ^ (set(slides) | {"platform", "cap-ing", "cap-lap", "cap-pii", "cap-doc"})

# ---------------------------------------------------------------- wording
# Old initiative numbers -> new capability numbers (1 ingestion, 2 LAP, 3 PII, 4 docs).
INIT_TO_CAP = {"1": "1", "2": "3", "3": "2", "4": "4"}

EYEBROW_OVERRIDES = {
    "ing-brief": ("Initiative 1 · Data ingestion platform", "Capability 1 · Ingestion Platform"),
    "pii-brief": ("Initiative 2 · PII data governance", "Capability 3 · PII Data Governance"),
    "lp-brief": ("Initiative 3 · Least privilege, service accounts and access",
                 "Capability 2 · Least Access Privilege"),
    "doc-brief": ("Initiative 4 · AI documentation", "Capability 4 · AI Documentation"),
}

LABELS = {  # whole-element text -> new text
    "PII governance": "PII Data Governance",
    "Least privilege and access": "Least Access Privilege",
    "Least privilege &amp; access": "Least Access Privilege",
    "Ingestion platform": "Ingestion Platform",
    "AI documentation": "AI Documentation",
    "Initiative": "Capability",
    "INITIATIVE": "CAPABILITY",
}

VISIBLE = {  # exact visible phrases
    "Cross-initiative dependencies": "Cross-capability dependencies",
    "How the initiatives feed each other": "How the capabilities feed each other",
    "Four initiatives, one quarter": "Four capabilities, one quarter",
    "One owner per initiative, all inside the team": "One owner per capability, all inside the team",
    "Endorse the Q4 scope, four initiatives, and the explicit after-Q4 backlog":
        "Endorse the Q4 scope: one Data Platform, four capabilities, and the explicit after-Q4 backlog",
    "Four initiatives and six cut-overs in one quarter": "Four capabilities and six cut-overs in one quarter",
    "PII governance: protect client data from the file it arrives in":
        "PII Data Governance: protect client data from the file it arrives in",
    "Least privilege: every account has a role, an owner and a reason":
        "Least Access Privilege: every account has a role, an owner and a reason",
    "AI documentation: docs that update when the system changes":
        "AI Documentation: docs that update when the system changes",
    "Least privilege in Q4, month by month": "Least Access Privilege in Q4, month by month",
    "PII governance in Q4, month by month": "PII Data Governance in Q4, month by month",
    "Ingestion: from a working project to a platform feature":
        "Ingestion Platform: from a working project to a platform feature",
}


def renumber_initiatives(text: str) -> str:
    return re.sub(r"Initiative ([1-4])", lambda m: "Capability \x00" + INIT_TO_CAP[m.group(1)], text) \
        .replace("\x00", "")


def notes_wording(note: str) -> str:
    note = renumber_initiatives(note)
    note = note.replace("an initiative", "a capability").replace("An initiative", "A capability")
    note = note.replace("initiatives", "capabilities").replace("Initiatives", "Capabilities")
    note = note.replace("initiative", "capability")
    note = note.replace("least privilege and access requests are now one capability",
                        "Least Access Privilege covers service accounts and access requests together")
    note = note.replace("Least privilege and access requests are now one capability",
                        "Least Access Privilege covers service accounts and access requests together")
    note = note.replace("Least privilege and access is one capability now",
                        "Least Access Privilege covers accounts and requests")
    note = note.replace("Least Access Privilege covers accounts and requests, so it has two columns: accounts and requests.",
                        "Least Access Privilege covers accounts and requests, so it has two columns.")
    return note


def rewrite(sid: str, html: str) -> str:
    if sid in EYEBROW_OVERRIDES:
        old, new = EYEBROW_OVERRIDES[sid]
        assert old in html, (sid, old)
        html = html.replace(old, new)
    # split notes from body
    m = re.search(r"<aside>(.*?)</aside>", html, re.S)
    note = m.group(1) if m else None
    body = html[: m.start()] + "\x01" + html[m.end():] if m else html
    for old, new in VISIBLE.items():
        body = body.replace(old, new)
    body = renumber_initiatives(body)
    body = re.sub(r">(\s*)([^<]+?)(\s*)<",
                  lambda mm: ">" + mm.group(1) + LABELS.get(mm.group(2), mm.group(2)) + mm.group(3) + "<",
                  body)
    if note is not None:
        body = body.replace("\x01", "<aside>" + notes_wording(note) + "</aside>")
    return body


for sid in list(slides):
    slides[sid] = rewrite(sid, slides[sid])

# lessons: arrows point at the new capability numbers
s = slides["lessons"]
for old, new in [("→ 2 PII registry", "→ 3 PII registry"), ("→ 3 AD groups", "→ 2 AD groups")]:
    assert old in s, old
    s = s.replace(old, new)
s = s.replace("every capability in this roadmap answers it",
              "every capability of the Data Platform answers it")
slides["lessons"] = s

# onepager: rows in capability order (Ingestion, LAP, PII, AI Documentation)
s = slides["onepager"]
lines = s.split("\n")
label_idx = {}
for i, ln in enumerate(lines):
    for name in ("Ingestion Platform", "PII Data Governance", "Least Access Privilege", "AI Documentation"):
        if f">{name}</p></div>" in ln and "justify-content:center\"><p" in ln:
            label_idx[name] = i
assert len(label_idx) == 4, label_idx
rows = {n: lines[i:i + 5] for n, i in label_idx.items()}
first = min(label_idx.values())
new_rows = sum((rows[n] for n in ("Ingestion Platform", "Least Access Privilege",
                                   "PII Data Governance", "AI Documentation")), [])
lines[first:first + 20] = new_rows
s = "\n".join(lines)
old_note = re.search(r"<aside>(.*?)</aside>", s, re.S).group(1)
s = s.replace(old_note, (
    "This is the whole quarter on one page, one row per capability of the Data Platform. Each month has "
    "one outcome: in October we find out what we have, in November we build the controls and the "
    "platform path, and in December all six clients and the controls go into daily use. The last column "
    "matters as much as the first three: it's the backlog we are deliberately not doing this quarter, so "
    "nobody mistakes it for slippage. Three points to make. Least Access Privilege covers service accounts "
    "and access requests together, because the access workflow automates the role model the least-privilege "
    "work builds. PII Data Governance and Least Access Privilege start in week one, because everything else "
    "depends on them. And all six clients cut over in three waves of two, finishing by 18 December."))
slides["onepager"] = s

# ------------------------------------------------------------- new slides
DARK = ("background:#16222F; color:#F4F1EA; font-family:'IBM Plex Sans', sans-serif; "
        "padding:128px 128px 160px; display:flex; flex-direction:column; justify-content:space-between; gap:40px")
MONO = "font-family:'IBM Plex Mono', monospace"

slides["cover"] = f"""<section id="cover" data-transition="fade" style="background:#16222F; color:#F4F1EA; font-family:'IBM Plex Sans', sans-serif; padding:128px; display:flex; flex-direction:column; justify-content:space-between; gap:48px">
  <p style="{MONO}; font-size:24px; font-weight:500; color:#5FC2B0; letter-spacing:3px; text-transform:uppercase">Q4 2026 roadmap · October to December</p>
  <div style="display:flex; flex-direction:column; gap:32px">
    <h1 style="font-size:120px; font-weight:600; line-height:1.05; color:#F4F1EA">Data Platform</h1>
    <p style="font-size:40px; line-height:1.3; color:#A9B3BD; max-width:1500px">One platform, four capabilities: Ingestion Platform, Least Access Privilege, PII Data Governance and AI Documentation</p>
  </div>
  <aside>Opening. The project is the Data Platform: one governed platform that holds and serves every client's data. It is delivered through four capabilities, each a part of the platform rather than a separate project. The Ingestion Platform loads every client's data by configuration. Least Access Privilege makes sure every person and service has only the access its role needs. PII Data Governance classifies and masks personal data from the moment it lands. AI Documentation keeps the documentation current as the platform changes. We have one quarter, thirteen weeks, so this plan builds the foundations of each capability, puts all six existing clients onto the platform by 18 December, and says clearly what moves to the backlog after Q4. The deck follows the same shape: first the big picture, then the four capabilities and how they fit, then each capability in detail, and finally the plan, capacity, risks and the decisions I need.</aside>
</section>
"""

CAPS = [
    ("1", "Ingestion Platform", "Ingestion Platform",
     "Moves every client's data from any source to any destination by configuration, with PII masked on the way.",
     "Onboarding a client becomes configuration, not a new build.",
     "All six clients live by 18 Dec; scheduling, retries and alerts on."),
    ("2", "Least Access Privilege", "Least Access Privilege",
     "Every person and service has only the access its role needs, with an owner, a reason and a record.",
     "We can show who can read client data, and why.",
     "Accounts inventoried; ≥ 80% of service accounts scoped; every grant via a request."),
    ("3", "PII Data Governance", "PII Data Governance",
     "Client personal data is classified when it lands and masked in every store, from one registry.",
     "PII is masked and audited wherever it is stored.",
     "Every column classified; Restricted columns masked; audit on."),
    ("4", "AI Documentation", "AI Documentation",
     "Every change to a client database produces reviewed documentation, drafted by AI and approved by people.",
     "Documentation stays current without manual upkeep.",
     "Approved docs on every change; metadata for all six client databases."),
]

cards = []
for num, name, _, _, gives, q4 in CAPS:
    cards.append(f"""    <div style="flex:1; display:flex; flex-direction:column; gap:14px; background:#FBFAF6; padding:28px 30px; border:1px solid #DAD4C8; border-top:6px solid #0E7466; border-radius:14px">
      <p style="{MONO}; font-size:40px; font-weight:500; color:#0E7466">0{num}</p>
      <h3 style="font-size:32px; font-weight:600; line-height:1.15; color:#16222F">{name}</h3>
      <p style="{MONO}; font-size:24px; color:#9A4F16">WHAT IT GIVES US</p>
      <p style="font-size:24px; line-height:1.35; color:#16222F">{gives}</p>
      <p style="{MONO}; font-size:24px; color:#0E7466">BY 31 DECEMBER</p>
      <p style="font-size:24px; line-height:1.35; color:#16222F">{q4}</p>
    </div>""")

slides["platform"] = f"""<section id="platform" data-transition="fade" style="background:#F4F1EA; color:#16222F; font-family:'IBM Plex Sans', sans-serif; padding:128px 128px 160px; display:flex; flex-direction:column; gap:28px">
  <div style="display:flex; flex-direction:column; gap:16px">
    <p style="{MONO}; font-size:24px; font-weight:500; color:#0E7466; letter-spacing:2px; text-transform:uppercase">The big picture</p>
    <h2 style="font-size:64px; font-weight:600; line-height:1.1; color:#16222F">One project, four capabilities</h2>
  </div>
  <div style="display:flex; align-items:center; gap:32px; background:#16222F; padding:26px 32px; border-radius:14px">
    <p style="{MONO}; font-size:28px; font-weight:500; color:#5FC2B0; letter-spacing:2px">DATA PLATFORM</p>
    <p style="flex:1; font-size:26px; line-height:1.35; color:#F4F1EA">One governed platform for every client's data: loaded reliably, accessed by role, protected at entry and documented as it changes.</p>
  </div>
  <div style="display:flex; gap:24px; align-items:stretch">
{chr(10).join(cards)}
  </div>
  <p style="position:absolute; left:128px; bottom:64px; width:1664px; font-size:24px; color:#56606B">Data Platform Roadmap · {NUM['platform']}</p>
  <aside>This is the one slide to remember. The Data Platform is the project: one governed platform for every client's data. It is built from four capabilities, and each is a part of the platform, not a project of its own. They share one plan, one team of four and one scorecard. The Ingestion Platform is how data gets in: a new client becomes configuration instead of a new build, and all six existing clients move onto it by 18 December. Least Access Privilege is who can get at the data: by the end of the quarter every account is inventoried, most service accounts are scoped to what they need, and every new grant goes through a recorded request. PII Data Governance is how personal data is protected: every column is classified as it lands and Restricted columns are masked in every store. AI Documentation is how we keep knowing what we have: every change produces reviewed documentation. The next slides show the quarter for all four on one page and how they depend on each other, and then each capability in detail, in this order.</aside>
</section>
"""

SECTIONS = {
    "1": "Why, current to target, architecture, UI, job store, release, plan, onboarding, measures",
    "2": "Why, scope, architecture, two tracks, plan, access requests, measures",
    "3": "Why, framework, classification, controls, masking, detection, plan, measures",
    "4": "Why, workflow, plan, measures",
}
OWNERS = {
    "1": "Vatsal · waves with Suma and Bhargavi",
    "2": "Suma · Bhargavi runs access requests",
    "3": "Suma · Bhargavi on masking rollout",
    "4": "Bhargavi · Harish on AI policy and review",
}
for (num, name, _, what, _, q4), sid in zip(CAPS, ["cap-ing", "cap-lap", "cap-pii", "cap-doc"]):
    blocks = [("BY 31 DECEMBER", q4), ("OWNER", OWNERS[num]), ("IN THIS SECTION", SECTIONS[num])]
    block_html = "\n".join(
        f"""    <div style="flex:1; display:flex; flex-direction:column; gap:10px; border-top:2px solid #5FC2B0; padding:20px 0px 0px">
      <p style="{MONO}; font-size:24px; color:#5FC2B0">{k}</p>
      <p style="font-size:26px; line-height:1.35; color:#F4F1EA">{v}</p>
    </div>""" for k, v in blocks)
    slides[sid] = f"""<section id="{sid}" data-transition="fade" style="{DARK}">
  <p style="{MONO}; font-size:24px; font-weight:500; color:#5FC2B0; letter-spacing:3px; text-transform:uppercase">Data Platform · Capability {num} of 4</p>
  <div style="display:flex; flex-direction:column; gap:28px">
    <h1 style="font-size:104px; font-weight:600; line-height:1.05; color:#F4F1EA">{name}</h1>
    <p style="font-size:40px; line-height:1.3; color:#A9B3BD; max-width:1500px">{what}</p>
  </div>
  <div style="display:flex; gap:48px; align-items:stretch">
{block_html}
  </div>
  <p style="position:absolute; left:128px; bottom:64px; width:1664px; font-size:24px; color:#8A97A3">Data Platform Roadmap · {NUM[sid]}</p>
  <aside>Capability {num} of 4: {name}. {what} By 31 December: {q4} The owner is {OWNERS[num].split(' · ')[0]}. The next slides cover, in order: {SECTIONS[num].lower()}.</aside>
</section>
"""

# ------------------------------------------------------------- footers
for sid, html in slides.items():
    html = re.sub(r"Data Platform Roadmap · [0-9]+[a-z]?", f"Data Platform Roadmap · {NUM[sid]}", html)
    slides[sid] = html
slides["ing-architecture"] = slides["ing-architecture"].replace(
    "built (slide 10c)", f"built (slide {NUM['ing-jobstore']})")

# ------------------------------------------------------------- write
for sid in ORDER:
    (OUT / f"{sid}.html").write_text(slides[sid])

deck = json.loads((SRC / "deck.json").read_text())
deck["order"] = ORDER
deck["title"] = "Data Platform Roadmap — Q4 2026"
deck["sections"] = {
    "s1": {"description": "The big picture: the Data Platform is the project, delivered through four capabilities",
           "start": "cover"},
    "s2": {"description": "How the four capabilities are sequenced and depend on each other", "start": "sequencing"},
    "s3": {"description": "Capability 1: Ingestion Platform", "start": "cap-ing"},
    "s4": {"description": "Capability 2: Least Access Privilege (service accounts and access requests)",
           "start": "cap-lap"},
    "s5": {"description": "Capability 3: PII Data Governance", "start": "cap-pii"},
    "s6": {"description": "Capability 4: AI Documentation", "start": "cap-doc"},
    "s7": {"description": "Month-by-month plan, where Q4 takes us and capacity", "start": "oct"},
    "s8": {"description": "Risks, scorecard, ownership and decisions needed", "start": "risks"},
}
(ROOT / "project" / "deck.json").write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n")

# report leftovers
for sid in ORDER:
    for m in re.finditer(r"[Ii]nitiative", slides[sid]):
        print("LEFTOVER", sid, slides[sid][max(0, m.start() - 60): m.end() + 40].replace("\n", " "))
print(len(ORDER), "slides; platform =", NUM["platform"], "jobstore =", NUM["ing-jobstore"])
