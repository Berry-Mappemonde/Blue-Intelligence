> **Archivé le 22 septembre 2026 — autre hackathon.** Conservé pour la mémoire. Index : [docs/README.md](../README.md).

# Open Agent Hackathon 2026 — synthesis and Blue Intelligence plan

Internal working document. Synthesis of the research on the
GenAI.Works hackathon, of the **official rules** (event page, capture of
13 September 2026) and of the orientations retained for Blue Intelligence /
Berry-Mappemonde.

- Site: https://hackathon.genai.works
- Event page: https://hackathon.genai.works/event/open-agent-hackathon-2026
- Help Center: https://help.genai.works/en/
- Support (ticket): https://genai.works/help
- Last reading of the rules: **13 September 2026**

This document is **not** the submission code. It prepares the hackathon
without violating the build window (rules 4.1–4.2 and 5.2).

---

## 0. Timing decision — start coding

Two times contradict each other **on the same official page**:

| Source | Code start |
|---|---|
| “6 dates that matter” box | 15 October 2026, **00:00 UTC** |
| **Rule 4.1** (Official Rules text) | 15 October 2026, **09:00 UTC** |

**Internal decision until Discord clarification:** we start at
**09:00 UTC on 15 October 2026**.

Why that one: if we code from 00:00 UTC and 09:00 UTC is binding,
those 9 hours of commits are **ineligible** (rule 4.2). If we wait
until 09:00 UTC and 00:00 UTC was binding, we only lose 9 hours, but
we stay eligible.

In Quebec (EDT daylight time, UTC−4 until 1 November 2026):

**Thursday 15 October 2026, 5:00 a.m.**

End of window (rule 4.1 + hard deadline from the table):
**20 October 2026, 23:45 UTC** = **Tuesday 20 October, 7:45 p.m.** in Quebec.

Rule **4.3**: time zones do not extend anything. Everything is in UTC.

### Email of 13 September 2026 — no reply

On 13 September 2026 at 16:51 (time shown in the expedition
mailbox), Clément FILISETTI wrote to
`hackathons@genai.works` to ask which time is binding.

**The message did not arrive.** Google returned *Address not found* /
*The email account that you tried to reach does not exist* (SMTP 5.1.3,
13 Sept. 2026 13:51 PDT). The address published in rule **10.3**
(`hackathons@genai.works`) is therefore **invalid** on that date.

Next action: **ask the same question on the official Discord**
(event room) and, if needed, a ticket on
https://genai.works/help. Keep the written answer.

---

## 1. What this hackathon is

A **100% online** event organised by GenAI Works. Free.
Open from **age 16** at the start of the window (rule 1.1). Teams of
**1 to 5**. One account per person: a double account **disqualifies
the whole team** (1.3).

The brief: build an **agent that does real work** for a
real user, an industry or a community. Not a chatbot.
Not a toy demo.

The agent must:

1. access relevant information;
2. understand context and relationships;
3. reason in several steps;
4. keep a useful memory;
5. produce a concrete result.

The real place of the event is **Discord** (announcements, rooms per
track, Team Finder, mentors, workshops, results). Kickoff, office
hours, judging and results are online. No travel.

Useful organiser history:

- Build with AI 2024 — agents / RAG — 4,511 participants
- #LeadWithAIAgents 2025 — ~3,500 participants, ~200 teams
- World Wide Vibes 2026 — Montgomery civic apps

The page banner says **144 hours**; a marketing footer still says
**72 Hours**. Between 15 Oct. 09:00 and 20 Oct. 23:45 UTC,
count **about 139 hours**, not 72.

---

## 2. Dates, prizes, eligibility

| Item | UTC | Quebec (EDT, UTC−4) |
|---|---|---|
| End of registration | **13 Oct. 2026, 00:00** (hard) | **Monday 12 Oct., 8:00 p.m.** |
| **Code start (rule 4.1)** | **15 Oct. 2026, 09:00** | **Thursday 15 Oct., 5:00 a.m.** |
| Judging opens | 20 Oct. 2026, 00:00 | Monday 19 Oct., 8:00 p.m. |
| **End of submissions** | **20 Oct. 2026, 23:45** (hard) | **Tuesday 20 Oct., 7:45 p.m.** |
| Results | 30 Oct. 2026, 16:00 | Friday 30 Oct., 12:00 p.m. |
| Registered (13 Sept. 2026) | ~1,200 | |
| Format | 100% online | |
| Team size | 1–5 | |
| Prize pool | up to **$20,000** + per-track bounties | |

Judging **opens before** the submission deadline. On an Impact
tie, it is the **submission time** that breaks it (rule 7.3):
submit early, not at 7:44 p.m.

Old calendar still visible on Google / NCSA Illinois article
(7–9 October, 72 h): **do not rely on it anymore**.

### Global prizes (rule 08)

| Place | Amount | Note |
|---|---|---|
| 1st | $8,000 | best score across all tracks + community showcase |
| 2nd | $4,000 | split equally among members by default |
| 3rd | $2,000 | on a tie, break by Impact then timestamp |

- Employees of the organiser or of a judging sponsor: participation OK,
  **no money** (1.2).
- Transfer within **30 days** after the results announcement (8.1) —
  shorter than the old April 2025 T&Cs (~3 months).
- Equal split, unless written team agreement (8.2).
- Taxes and local fees at the winner’s charge (8.3).
- France is not a US-embargoed country. Still verify
  personal eligibility.

### Intellectual property (rule 09 — more protective than the 2025 T&Cs)

- **9.1** You **keep all rights** on what you build. Nothing
  transfers ownership to the organiser or the sponsors.
- **9.2** By submitting, you give the organiser a licence to
  show **demo, captures and description** in the event
  coverage.
- **9.3** Submissions of a sponsor track give the sponsor the
  same promotional, non-exclusive licence.

The generic April 2025 T&Cs
(https://help.genai.works/en/articles/11051932-hackathon-terms-and-conditions)
still spoke of a broader licence and of Oracle DevRel. **For
this event, it is section 09 of the 2026 page that prevails.** We
still submit a **dedicated repo**, not the production monorepo
(secrets, VPS infra, history).

---

## 3. Tracks

Each submission chooses **exactly one** main track (3.1).
We can **change track** until the deadline (3.2). A project
can touch several tracks, but **it is not scored twice**
(3.3). The track determines the judging panel and any sponsor
bounty.

| # | Track | Brief |
|---|---|---|
| 01 | Enterprise Intelligence | Fragmented company info → insights, decisions, reports |
| 02 | Autonomous Investigation | Multi-source investigation, answers **with evidence** |
| 04 | Persistent Memory Agents | Memory, state, work that continues over time |
| 05 | Real-World Industry Agents | A trade / a community, a real operational problem |
| 06 | Connected Data Agents | Discovery and query across APIs, bases, disconnected systems |

(There is no track 03 on the page of 13 September 2026.)

---

## 4. Scoring grid — rule 7.1

**100 points** + **up to 30 bonus points**.

| Criterion | Points | What judges want to see |
|---|---|---|
| **Impact** | 30 | Real problem, named user, useful result |
| **Technique** | 20 | Multi-step agent + tools, not a GPT wrapper |
| **Innovation** | 15 | Non-obvious angle |
| **Demo** | 15 | Video ≤ 3 min: the agent *does* the work |
| **Product & UX** | 10 | A non-dev could use it tomorrow |
| **Sponsor tech** | **10** | Partner stack really wired |
| **Bonus** | ≤ 30 | Open source + evals + failure modes others can learn from |

Without bonus we play to 100. With bonus we play to 130. The 30
bonus points can invert the ranking.

- At least **three judges** per submission (7.2).
- Sponsor bounties are decided by the sponsor panel (7.2).
- Tie: Impact score, then **submission timestamp** (7.3).

What very often loses:

- generic RAG chatbot;
- 12 features at 40%, zero complete path;
- health / HR / Jira with neither user nor real data;
- demo that crashes, or slides without an agent;
- large model, zero eval, zero citation;
- submitting the existing Blue Intelligence app without a new agent;
- two accounts, or copied code without declaring it.

---

## 5. Official rules (the 10 sections)

### 01 Eligibility

- 1.1 Open worldwide to anyone 16 or older at
  the start of the window.
- 1.2 Organiser / judging-sponsor employees: no cash prize.
- 1.3 One account per participant. Duplicate = whole team out.

### 02 Teams

- 2.1 One to five. Solo plays in the **same** ranking.
- 2.2 The team **freezes at the first submission send**; before,
  you can join, leave or merge freely.
- 2.3 One participant = **one** team only. A mentor may advise
  several teams.

### 03 Tracks

See section 3 above.

### 04 Build window

- 4.1 Build: **15 October 2026, 09:00 UTC** → **20 October
  2026, 23:45 UTC**.
- 4.2 Work committed **before** opening: **ineligible**, except
  preexisting components **clearly declared**.
- 4.3 No extension for time zone. Everything is UTC.

### 05 What you can use

- 5.1 Any language, framework, model or cloud, including
  closed APIs and sponsor credits.
- 5.2 Preexisting open-source libraries: OK. **Preexisting product
  code must be declared in the submission form.**
- 5.3 Generated (AI) code is **allowed and expected**. We own
  it and are **responsible**.

Official FAQ: “Just declare anything pre-existing in your
submission so judges can see what you built during the window.”

### 06 Submission requirements — all three are mandatory

1. A **public** repo, **or** a private repo with jury access.
2. A **running deployment**, **or** a container image +
   instructions in **one command**.
3. A **video of 3 minutes maximum**, **and** a **written
   description of the failure modes** found.

`FAILURES.md` is no longer only a bonus: it is **required**. The
bonus (≤ 30) additionally rewards open source, evals, and the
quality of that failure doc.

### 07 Judging

See section 4.

### 08 Prizes

See section 2.

### 09 Intellectual property

See section 2.

### 10 Schedule & changes

- 10.1 The organiser may adjust the calendar; announcements on the
  page and on Discord.
- 10.2 Disqualifications are final, with a reason to the
  team lead.
- 10.3 The page indicates `hackathons@genai.works` (reply within one
  working day). **This address rejected the email of 13 Sept. 2026.**
  Use Discord + https://genai.works/help.

---

## 6. What has already won at GenAI.Works

**#LeadWithAIAgents 2025** hackathon:

1. **Minizica** — won **twice**. Not a chat: a team
   of agents that automates a real business flow
   (Jira → GitHub → Confluence), wired to **GenAI AgentOS**
   (organiser runtime), open source.
   Repo: https://github.com/param-kasana/Minizica-genai-agentos
2. **2nd** — anonymous matching of patient file ↔ clinical trials, with
   recommendation of the closest trials if no match.
3. Pattern of placed projects: **several agents + real tools +
   a precise trade**, not “ChatGPT with a UI”.

GenAI.Works product talk goes the same way: persistent
memory, audit traces, evals, permissions in the *harness*
(the frame around the model), not only a prompt.

---

## 7. Orientations retained for Blue Intelligence

### 7.1 Idea to build (during the window only)

**A new skipper agent**, not the current application copied.

- Main track: **05 Real-World Industry Agents** (maritime /
  pleasure craft).
- Foot in **02 Autonomous Investigation** (cited answers) and
  **06 Connected Data** (APIs / bases already in prod) — **without**
  double score (3.3).
- One user, one deliverable.
- Track changeable until the deadline if a sponsor bounty fits
  better (3.2).

Judge-proof scenario (video ≤ 3 min, aim for ~90 s of real demo):

> A skipper prepares a passage. The agent: (1) takes the route,
> (2) crosses EEZs and official ports of entry, (3) flags MPAs and
> visit rules, (4) proposes marinas / harbour offices with
> sources, (5) outputs a **formalities dossier with citations**
> (URL, date, OSM confidence). It **remembers** the route from
> one day to the next. It clearly says what it **does not know**.

Single sentence to lock before 15 October:

*For whom? What work? What deliverable?*

### 7.2 What the agent is not

- Not a wrapper around `blueintelligence.online`.
- Not NAVIGUIDE glued back on. NAVIGUIDE is an asset (proof of a real
  user: Berry-Mappemonde expedition, 36,000+ miles, 45+
  stops) **and** a risk: it already does multi-agent briefing.
  The hackathon project must do work that is **visibly different**
  (customs / formalities / MPA investigation, cited dossier, voyage
  memory — what NAVIGUIDE does not do).

### 7.3 Where the hackathon code lives

**New dedicated repo, created on 15 October 2026 at 09:00 UTC
(5 a.m. Quebec). Not a branch of `blue-intelligence`.**

Reasons:

1. Public submission (or private with jury access). The current
   monorepo contains operations information (VPS,
   internal architecture). We do not make public “just a
   branch”.
2. Git history is evidence. A first commit **after**
   09:00 UTC on 15 October shows the project was built
   in the window (4.2).
3. MIT/Apache licence + GenAI promo licence: that must cover the
   small hackathon repo, **not** production.
4. A judge has a few minutes. A repo of ~50 files is readable;
   the monorepo is not.

Schema:

```
blue-intelligence (private, prod)
        │
        │  exposes APIs declared “preexisting” (5.2)
        ▼
new repo (created 15/10 at 09:00 UTC)
        │
        └── agent + evals + FAILURES.md + video + (deployment or Docker)
```

The hackathon repo **does not exist before 15 October 09:00 UTC**.
Until then, it exists only in notes outside the submission git.

### 7.4 Red line: what counts as “working”

**Forbidden before 15 October 2026, 09:00 UTC** (ineligible commits
except declared components, rule 4.2):

- write the agent code, even a skeleton;
- create the hackathon repo, even “empty”;
- code the eval harness;
- write the final prompts in files destined for
  submission.

**Allowed** (preparation, not submission):

- research, sketches, learning the tools / sponsor stack;
- preparation of our own existing data and services on
  `main` (Blue Intelligence product, useful even without hackathon);
- notes outside the repo (scenario, eval cases, video storyboard).

**Mandatory declaration on the day (5.2 + FAQ):** in the
form **and** the README: *Blue Intelligence APIs / data =
preexisting; agent + evals + demo + FAILURES.md = window.*

The question “can we use our prod APIs as tools, by
declaring them?” is already settled by **5.2**: yes, if declared.
The question still open is only **the exact start time**.
Ask it on Discord, not at `hackathons@genai.works`.

### 7.5 How to stick to the grid

**Impact (30)**
Named user (expedition skipper or third-party pleasure-craft sailor).
Measurable before / after: “4 hours of customs research →
4 minutes + sources”. Ideally 2 testimonial sentences in the
video.

**Technique (20)**
Plan → tools (Blue Intelligence APIs, OSM, Ifremer, ProtectedSeas,
etc.) → aggregation → **citations** → action (PDF, GeoJSON,
checklist). Loop if a source fails. Not a single prompt.

**Innovation (15)**
Crossing **route × right of entry × MPA × science**, with
provenance. Not “five agents talking to each other”.

**Demo (15)**
Video **≤ 3 min** (rule 6.3), real screen, zero slides in the middle:

1. the problem (15 s);
2. the agent **does** the work (60–90 s);
3. a proof (citation, trace, eval);
4. an assumed failure + the follow-up.

**UX (10)**
A screen a non-dev understands. Button, map, dossier. Not a
terminal.

**Sponsor (10)**
As soon as the Discord announcement: wire the partner stack **for real**,
even for a single tool. This is no longer 5 points: it is **10**.

**Bonus (≤ 30) + deliverable 6.3**

1. MIT or Apache licence, clean README;
2. `evals/` folder: ~20 cases, expected vs obtained
   (e.g. “is this harbour a PoE?”);
3. `FAILURES.md` **mandatory**: what the agent invents, dead
   sources, hallucinations, guardrails.

Plus: live deployment **or** Docker + one command (6.2).

### 7.6 Team

2 to 4 people, ideally:

- 1 product / domain profile (the skipper in the head);
- 1–2 build profiles (agent + tools);
- 1 demo + README + video + `FAILURES.md` profile (15 + 10 UX,
  often neglected).

Register solo if needed (FAQ: Team Finder; most teams
form the first evening). One account per person. The team
freezes at the **first** submission click (2.2): do not “submit
to test” too early if the team is not closed.

---

## 8. Preparation until 14 October

### 8.1 On `main` (legitimate product work)

This is **not** the submission code. It is Blue Intelligence becoming
a better *external tool* for the agent.

**Data — Impact and demo**

- Advance the backlog already listed in `docs/PRD.md`: re-import of
  the ~695 ungeocoded PoE, OSM validation on the new ones, weekly
  exports up to date.
- Check that API responses carry **provenance** everywhere
  (`source_url`, date, `osm_confidence`): that is what turns
  an agent answer into a proven answer.
- Make sure the immutable-release workflow
  `data-YYYY-MM-DD` runs without error by October.

**API — Technique**

- The OpenAPI doc already exists (`backend/app/main.py`, `/api/docs`).
  Re-read the endpoints the agent will call (PoE by EEZ, marinas,
  MPAs, harbour offices, depth): clear descriptions, clean
  schemas.
- Decide (and if needed put in place) a **read-only access**
  usable from outside: subset of endpoints, API key,
  rate-limit, CORS. During judging (20–30 October), a live
  demo may be opened: the VPS must hold without exposing admin.
- Inventory document on `main` (e.g. `docs/HACKATHON_OUTILS.md`):
  list of APIs / data available as external tools, with
  call examples. Product documentation, not submission code.

**Infra**

- Check the rotation of daily VPS MongoDB backups
  (`~/backups/mongodb/`, 14 days) and do a restore
  test before October. **Never** run `infra/vps/sync-from-atlas.sh`.
- No heavy batch (swarm, worldwide OSM validation) during the
  demo / judging window.

### 8.2 Outside the repo

1. Register **before Monday 12 October 8:00 p.m. Quebec**
   (13 Oct. 00:00 UTC).
2. Join Discord (button on the event page).
3. **Ask the timing question again on Discord** (the email to
   `hackathons@genai.works` failed).
4. Assemble the team (Team Finder).
5. Lock the scenario in one sentence, then the minute-by-minute
   storyboard (which real expedition passage, with interesting EEZ / PoE /
   MPA).
6. Prepare the Impact story (skipper / pleasure-craft sailor testimonial).
7. Learn the sponsor stack as soon as it is announced (tutorials, credits).
   Learn ≠ build.
8. List ~20 eval cases **in notes** (not in code), expected
   answers drawn from Gold data.
9. Video kit: OBS, mic, clean screen resolution.
10. Prepare the typical 5.2 declaration text (form + README).

### 8.3 Calendar

| When | What |
|---|---|
| Now → end of September | Registration, Discord, timing question, team |
| End of September → 10 October | On `main`: PoE data, provenance, read-only access, inventory doc, light load test |
| 10–14 October | Scenario locked, eval cases in notes, sponsor stack learned, video setup, **freeze `main`** |
| **15 October 09:00 UTC (5 a.m. Quebec)** | Repo creation, first commit, build |
| 15–19 October | Heart of the agent (evidence, memory, multi-source) |
| Penultimate day | Freeze features; evals + `FAILURES.md` + Docker or live URL |
| Last 8 h | Video ≤ 3 min, README, submit **before** 20 Oct. 7:45 p.m. Quebec |

---

## 9. During the window — reminder

Day 1: scenario + first tool that works end to end.
Following days: heart (evidence, memory, multi-source).
Penultimate day: no more features; evals + `FAILURES.md` +
deployment or Docker.
Last 8 h: video and submission, **not** the last minute
(timestamp breaks ties).

In one sentence: **win Impact + a working demo + the 10
sponsor points + the 30 bonus**, with a skipper agent that investigates
formalities / MPAs / marinas **with sources**, voyage memory,
evals and a mandatory `FAILURES.md`.

---

## 10. Sources

- Event page / Official Rules (capture 13 Sept. 2026):
  https://hackathon.genai.works/event/open-agent-hackathon-2026
- Email of 13 Sept. 2026, Clément FILISETTI → `hackathons@genai.works`
  (not delivered, address does not exist)
- https://hackathon.genai.works
- https://help.genai.works/en/
- https://genai.works/help
- Generic T&Cs (context, not rule 09 of this event):
  https://help.genai.works/en/articles/11051932-hackathon-terms-and-conditions
- https://github.com/param-kasana/Minizica-genai-agentos
- LinkedIn posts #LeadWithAIAgents (Minizica 1st; clinical-trial
  matching 2nd)
- Internal repo: `README.md`, `docs/PRD.md`, `naviguide/README.md`,
  `backend/app/main.py`
