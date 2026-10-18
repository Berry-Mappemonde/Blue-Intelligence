# Master plan: GenAI.works Open Agent Hackathon 2026, Blue Intelligence (PoE Reconciler)

Drafted Sat 17 Oct 2026, ~19:30 Toronto (23:30 UTC), by Grok Bot. **Updated 17 Oct 19:45 Toronto: Toloka ASAP decision (D24) and organizer questions sent. Updated 17 Oct ~21:00 Toronto: full rules review of every public official source → new §0.5 "How this hackathon actually works", conflicts C19–C26, tasks P23–P33, CH-16 likely done.** Read-only review: nothing in the repo, on the Mac or on any service was changed. No message was sent. Facts marked **(unverified)** could not be checked from the sources listed in §1.

---

## 0. Résumé exécutif (FR)

1. On présente **uniquement Blue Intelligence** sur le **track 01** avec l'agent **PoE Reconciler**. Le règlement officiel (relu le 17 oct.) confirme : Zetaris + Meterless obligatoires, Cursor obligatoire, code préexistant déclaré, seul le travail fait du 22 au 27 oct. est noté.
2. **Aucun code avant le 22 oct. 00:00 UTC** (21 oct. 20:00 Toronto). D'ici là : préparation des données, des comptes et des textes uniquement.
3. **Bloquant n°1 : Toloka, à lancer le plus vite possible (décision du 17 oct. 19:39).** Le lot est construit **avant le 22** à partir des verdicts existants (aucun code nouveau) et déployé **le 22 oct. à 00:00 UTC pile (21 oct. 20:00 Toronto)**, après ton « oui » sur le coût. Le contrôle Nemotron VL n'est plus un préalable : il tourne en parallèle le 22 et sert de comparaison (démo/évals). L'équipe est encore en essai : la vérification est à faire **ce week-end**, sans attendre l'appel avec Rajesh (**lun. 19 oct. 12:30 Toronto**, en secours).
4. **Organisateurs.** L'adresse hackathons@genai.works (règle 10) a rejeté le mail. Les deux questions (track, grille de notation) sont **parties le 17 oct. à 19:38 Toronto** à support@academy.genai.works (fil « Remove a team member and rename our team »). Réponse attendue ; sinon, les poser sur HackOS (canal « Help desk », que les e-mails des organisateurs désignent comme canal des questions) ou à l'appel d'onboarding du 21 oct. Voir §0.5 pour le fonctionnement complet du hackathon (règles, soumission, jugement, divergences entre sources).
5. **Équipe** : 5 membres, Hamid à remplacer. Le remplaçant doit être inscrit **avant le 22 oct. 23:45 UTC** (19:45 Toronto ; l'e-mail officiel du 12 oct. dit 23:45, la page 23:59 : on retient le plus tôt). Ne créer **aucune soumission** avant, car la première soumission verrouille l'équipe.
6. **Six contradictions** entre le plan Toloka et le plan du dépôt (granularité, nombre de lots, budget, stockage, zones, calendrier) : je propose de les trancher ainsi. Un seul lot Toloka, au niveau des URL (≈ 23 items, ≈ 48 $), lancé le 22 à 00:00 UTC, construit à partir des verdicts existants ; Nemotron VL en parallèle. Les résultats vont dans le Postgres `poe_gold`, pas dans Mongo, et nourrissent la mémoire H-MEM.
7. **Split** : pas encore fait (aucun dépôt NAVIGUIDE n'existe). S'il n'est pas fini au 22 oct. 00:00 UTC, on ouvre une branche `agent-poe` dans le dépôt actuel (décision 12).
8. **Ajouts proposés** : une boucle où Nemotron interroge lui-même Zetaris avec `run_sql` (c'est le modèle du guide officiel, et ça compte pour « Sponsor tech »), un petit écran Gold pour la note « Produit & UX », ainsi que `evals/` et `FAILURES.md`.
9. **Améliorations de l'audit** (ruff, N+1, données lourdes, Vite…) : **après** le hackathon, sauf ce qui sert directement l'agent.
10. Dates clés : onboarding le **21 oct. 08:00–09:30 Toronto**. Gel du code le **27 oct. 08:00 Toronto**. Envoi visé le **27 oct. 16:00 Toronto**, limite **19:45 Toronto**. Résultats le **6 nov. 11:00 Toronto** (heure d'hiver).

### Key dates

| Event | UTC | Toronto |
|---|---|---|
| Now (this plan) | Sat 17 Oct 23:30 | Sat 17 Oct 19:30 (EDT, UTC−4) |
| Toloka call with Rajesh (Google Meet, booked) | Mon 19 Oct 16:30–17:00 | Mon 19 Oct 12:30–13:00 |
| Setup guide: "run the checks at least two days before kickoff" | by Tue 20 Oct 00:00 | by Mon 19 Oct 20:00 |
| Power Day workshop (Meterless + Nemotron, YouTube live; "3:00 PM PST", PT ambiguity) | Mon 19 Oct ~22:00 | Mon 19 Oct ~18:00 |
| Build Day workshop (Cursor + Meterless prompt library, YouTube live; "9:00 PM PST") | Wed 21 Oct ~04:00 | Wed 21 Oct ~00:00 |
| Nebius × NVIDIA judges webinar (NAVIGUIDE hackathon, optional) | Tue 20 Oct 16:00–17:00 | Tue 20 Oct 12:00–13:00 |
| Participant onboarding call (YouTube live, recording afterwards in the Academy lesson; not yet in calendar) | Wed 21 Oct 12:00–13:30 | Wed 21 Oct 08:00–09:30 |
| **Build window opens** | **Thu 22 Oct 00:00** | **Wed 21 Oct 20:00** |
| Registration closes (5th member must be registered; e-mail 12 Oct says 23:45, page 23:59 → use 23:45) | Thu 22 Oct 23:45 | Thu 22 Oct 19:45 |
| Toloka dataset built + uploaded, pipeline Self-check green (no deploy) | by Wed 21 Oct 23:59 at the latest | by Wed 21 Oct 19:59 |
| **Toloka run deployed (D24)** | **Thu 22 Oct 00:00 exactly** | **Wed 21 Oct 20:00** |
| Nebius × NVIDIA "submission update" (NAVIGUIDE) | Fri 23 Oct (time not stated) | Fri 23 Oct |
| Judging opens (submissions still open) | Tue 27 Oct 00:00 | Mon 26 Oct 20:00 |
| Code freeze (plan) | Tue 27 Oct 12:00 | Tue 27 Oct 08:00 |
| Target submission | Tue 27 Oct 20:00 | Tue 27 Oct 16:00 |
| **Submissions close (hard)** | **Tue 27 Oct 23:45** | **Tue 27 Oct 19:45** |
| Nebius × NVIDIA final submission (NAVIGUIDE) | Fri 30 Oct 17:00 | Fri 30 Oct 13:00 (10:00 PT) |
| Toronto leaves daylight saving | Sun 1 Nov | (from then on UTC−5) |
| Toloka promo code validity | until 4 Nov (whether the credit itself expires: **unverified**) | |
| Results announced | Fri 6 Nov 16:00 | Fri 6 Nov 11:00 (EST, UTC−5) |

---

## 0.5 How this hackathon actually works (rules review, 17 Oct 2026 ~21:00 Toronto)

Read-only review of every public official source on 17 Oct 2026 (UTC−4 Toronto). Quotes are verbatim. **(unverified)** = not confirmed by an official source; **(inference)** = my reading.

**Sources.** [E] event page and its rules 01–10 + FAQ (read from the page data), https://hackathon.genai.works/event/open-agent-hackathon-2026 · [A] GenAI Academy course "Open Agent Hackathon 2026", lessons *How the Week Runs*, *Onboarding Call*, *Build/Power Quick Start*, *Build Day / Power Day* (public API of https://academy.genai.works/courses/open-agent-hackathon-2026/details) · [G] Participant Setup Guide, last updated 15 Oct (`/workspace/guide.txt`, Google Doc linked in the organizer e-mail of 15 Oct) · [M1] organizer e-mail 12 Oct "has moved to 22–27 October" · [M2] e-mail 15 Oct "Your Setup Guide Is Here" · [M3] e-mail 13 Oct "Data Day recap" · [Z] https://github.com/zetaris/getting-started (README, organizer checklist, demo template) · [ML] https://github.com/Meterless/Meterless `docs/community/hackathon-guide.md` · [X] @GenAI_Now posts (23 Sep, 9 Oct). Not readable: HackOS pages behind sign-in (team workspace, submission form, task board, `/policy/content`), and the Discord server https://discord.gg/tfwSeqVWmR (announcements) → **unread**.

### 0.5.1 Timeline (all deadlines UTC; "Time zones do not extend the window; all deadlines are UTC." [E 04])
| When (UTC) | Toronto (EDT; EST from 1 Nov) | What | Source / note |
|---|---|---|---|
| 14 Aug 00:00 | — | Registration opens | [E] |
| 12 Oct 22:00 | 12 Oct 18:00 | Data Day workshop (Zetaris), recording on HackOS Resources | [A], [M3] |
| 19 Oct "3:00 PM PST" | 19 Oct 18:00 (if PT = PDT) | Power Day workshop (Meterless + Nemotron), YouTube live | [A]; "PST" in October is ambiguous (PDT = UTC−7 → 22:00 UTC) **(unverified)** |
| 20 Oct "9:00 PM PST" | 21 Oct 00:00 (if PDT) | Build Day workshop (Cursor + Meterless prompt library), YouTube live | [A]; same ambiguity |
| **21 Oct 12:00–13:30** | **21 Oct 08:00–09:30** | Onboarding call, "Streamed live on YouTube. The recording appears in this lesson after the call." | [A], [M1], [M2] |
| **22 Oct 00:00** | **21 Oct 20:00** | Build window opens | [E 04] |
| **22 Oct 23:45** (e-mail) / 23:59 (page) | **22 Oct 19:45** | Registration closes: "Everyone on a team needs to be registered before registration closes." | [M1] says 23:45, [E] says 23:59 → **plan on 23:45** |
| first submission created | — | Team locks: "Team composition locks when your first submission is created" | [E 02] |
| 27 Oct 00:00 | 26 Oct 20:00 | Judging opens (submissions still open) | [E]; judges may start on early submissions **(inference)** |
| **27 Oct 23:45** | **27 Oct 19:45** | Submissions close, "Hard deadline" | [E] |
| 6 Nov 16:00 | 6 Nov 11:00 (EST) | Results announced | [E] |
| ≤ 30 days after results | — | "Cash prizes are paid by bank transfer within 30 days of the results announcement." | [E 08] |

Finalists / live pitch: **no rule describes a finalist round or live pitch.** The event page community block only says "Judge announcements, finalist demos and next-edition dates as they are confirmed" and "the results call"; FAQ: "Kickoff, office hours, judging and results all happen online in Discord and on the platform." The 2025 GenAI.Works #LeadWithAIAgents hackathon (72 h, 3,000+ builders) announced 6 ranked winners on LinkedIn, no pitch round visible **(unverified)**. → Judging is on the submitted artifacts; keep Clément reachable 27 Oct–6 Nov in case finalists are asked for a live demo.

### 0.5.2 What you submit, and where
- **Where**: "Submission done in HackOS Platform: https://hackathon.genai.works/dashboard" [A]; "You may change track any time before the submission deadline from your team workspace." [E 03]. The form itself is behind sign-in → **exact field list unverified**; it will be visible once a submission draft is created (which locks the team, see P31).
- **Required pieces** [E 06], [A]: (1) "A demo video of 1-4 minutes that shows the main workflow, how the agent solves the selected challenge, its key features, and how Zetaris and Meterless are integrated." (2) "A slide deck covering the problem and target users, the solution, the agent workflow or architecture, the technical stack, how Zetaris and Meterless were used, what was unique about your use of the sponsor technologies, product visuals, and future enhancements." (3) "A GitHub repository with all source code and a README covering setup, usage and dependencies. If your agents run in Google Colab, include the Colab links." (4) "A clear explanation of how Zetaris and Meterless were integrated, how Cursor was used during development, where NVIDIA technology contributes, and what was unique about your use of the sponsor technologies." (5) "Pre-existing product code must be declared in the submission form." [E 05]
- **Official checklist** [A]: primary track selected; video 1–4 min end to end; "Video and deck both name Zetaris, Meterless and Cursor and show where each one sits"; deck has an architecture diagram and the stack; README "someone outside your team could run it"; `.env` in `.gitignore`, no secrets; pre-existing code declared; Colab links if any; "Submitted before 27 October 2026, 23:45 UTC".
- **Video hosting**: no platform rule (YouTube is our choice). HackOS has a chunked video-upload endpoint (seen in the platform's front-end code) → the form may accept a direct upload **(unverified)**: keep the MP4 (< 4:00) ready **and** a YouTube link (public or unlisted).
- **Deck format**: not specified → export PDF (and keep the source). **Repo visibility / licence**: not specified; judges must be able to read it → keep the graded repo **public** (today `Berry-Mappemonde/Blue-Intelligence` is public, MIT + Apache-2.0). If the split creates a new repo, it must be public with a LICENSE before submission. `metadata.json`: no rule asks for it (optional).
- **Draft pre-existing declaration** (to paste in the form; adjust after the split):
  > Pre-existing (all commits before 22 Oct 2026 00:00 UTC, tag `pre-hackathon-2026-10-22`): the Blue Intelligence platform — FastAPI backend (`backend/app/`, incl. the PoE pipeline `services/poe_*.py`, text catalogue harvesting in `poe_seed_enrich.py`, `core/extract.py`/`render.py`/`pdf_preview.py`, the NVIDIA client `core/nvidia.py`), the React map and review UI (`frontend/`), embedded data (`backend/data/`), CI workflows and docs. Pre-existing data prepared before the window without new code: the 23-item Toloka dataset built from existing review verdicts, and its screenshots. The NAVIGUIDE simulator (`naviguide-simulator/`, `naviguide/`) shares the repository but is not part of this submission.
  > New during the window (22–27 Oct): `backend/app/agent_poe/` (Zetaris client and source registration, Nemotron VL extraction with mandatory citation, Nemotron reconciler and `run_sql` tool loop, H-MEM memory in Python + TypeScript conformance adapter, versioned `poe_gold` in a Postgres registered in Zetaris, Toloka aggregation), `evals/`, `FAILURES.md`, the Gold card UI, the agent CI job, and hygiene/compliance PRs `conformite/*` on the existing product (declared as such).

### 0.5.3 Judging
- "Scoring out of 100: Impact 30, Technical 20, Innovation 15, Demo 15, Product & UX 10, Sponsor tech 10." · "Each submission is reviewed by at least three judges." · "Ties are resolved on the Impact score, then on submission timestamp." [E 07] · The primary track "determines the judging panel and the prizes it competes for"; "Cross-track relevance is welcome but is not scored twice." [E 03]
- Named judges [E]: Michael Hay (CTO, Zetaris), Michael Armentano (Head of Technical Partnerships, SpaceXAI), Sam Cummings, Shestakov Vladyslav, Remus Ranca (GenAI Works). A further list of ~35 names (mentors or extra judges) follows on the page **(role unverified)**. A Zetaris CTO on the panel → the Zetaris integration must be technically credible, not cosmetic.
- Special prizes ("Best use of NVIDIA Nemotron": DGX Spark, $4,699; "Best use of Cursor-built product": SpaceX Cursor API credits, $2,301) are "in-kind rewards for selected winners" [E 08]; **how they are judged is not published (unverified)**; they are not a separate track.
- Wildcard wording [A]: "Judging is on the extension, not on prior development" — the same treatment as rule 04 for every track → **track 01 stays the choice** (question still pending with support).

### 0.5.4 Teams, eligibility, IP, conduct
- [E 01] "Open worldwide to anyone aged 16 or older at the start of the build window." · "Employees of the organizer and of judging sponsors may participate but are not eligible for cash prizes." · "One account per participant. Duplicate accounts disqualify the whole team."
- [E 02] "Teams of one to five people." · "Team composition locks when your first submission is created; before that you may join, leave or merge freely." · "A participant may belong to exactly one team."
- [E 08] "Cash prizes are split equally among team members unless the team submits a different split in writing." · "Taxes and any local charges are the recipient's responsibility."
- [E 09] "You keep all rights to what you build." · "By submitting you grant the organizer a license to show your demo, screenshots and description in event coverage." · "Sponsor-track submissions grant that sponsor the same non-exclusive promotional license." (No transfer of rights to the association is planned, §3.8.)
- [E 05] "Generated code is allowed and expected, you own the result and are accountable for it." · "Any language, framework, model or cloud, including closed-source APIs and sponsor credits."
- [E 10] "The organizer may adjust the schedule for technical reasons; changes are announced on this page and in Discord." · "Disqualification decisions are final and are communicated with a reason to the team lead."
- **Forbidden / disqualifying** (explicit): undeclared work committed before 22 Oct 00:00 UTC ([E 04]); duplicate accounts ([E 01]); missing Zetaris + Meterless integration or not using Cursor ([E 05]). No separate code of conduct is public (`/policy/content` needs sign-in) **(unverified)**.

### 0.5.5 Required technology — what each source says
| Source | Zetaris | Meterless | Cursor | NVIDIA |
|---|---|---|---|---|
| [E 05] (rules, governs) | required | **required** ("Every submission must integrate Zetaris and Meterless") | required ("teams must use Cursor for development") | "wherever it contributes" |
| [G] setup guide | "Zetaris and meterless must be running on your machine for eligibility" | Option A = Nemotron through a Meterless account/credit; base URL, prompt library, hotspot still "[Organisers: add …]" | required | "The Power rule: your product must run on NVIDIA Nemotron" (Option A Meterless, or Option B NVIDIA free API) |
| [A] *How the Week Runs* | required | required | required | "The setup guide's Power rule is that your product runs on NVIDIA Nemotron through Meterless" |
| [A] *Power Quick Start* | — | Meterless = OpenAI-compatible provider; "Sponsor credits are on the task board on HackOS"; `METERLESS_BASE_URL` still "[ORGANISERS TO ADD …]" | Cursor credit also on the HackOS task board | Nemotron inside Meterless |
| [A] course landing FAQ (updated 8 Oct) | required | not listed ("Nemotron, either connected directly or through the Meterless engine") | required | Nemotron |
| Pavlo (Meterless), 13 Oct (decision 13) | — | no API, no key | — | — |

→ **Our reading**: H-MEM implemented in Python + green official conformance scorecard is an honest "integration of Meterless" under [E 05], and Nemotron via NVIDIA's free API is the guide's explicit Option B. **But** the organizer material increasingly frames Meterless as the model route with credit on the HackOS task board. Cheap hedge: Clément checks the task board now (P29); if a Meterless endpoint/credit exists by 22 Oct, route Nemotron through it as well (3 `.env` settings, no architecture change) and show both in the video; otherwise ask at the onboarding call / HackOS "Help Meterless".

### 0.5.6 Communication channels
| Channel | Status |
|---|---|
| hackathons@genai.works (rule 10, "expect a reply within one working day") | **bounced** 17 Oct 06:13 Toronto ("Address not found") |
| support@academy.genai.works ("usually within one business day") | works; team request 17 Oct 14:16 + 2 rules questions 19:38 Toronto; **no reply yet** |
| HackOS Help desk + "Help Zetaris / Help Meterless / Help Cursor / Help NVIDIA Tools" channels | organizer e-mails: "Questions go on HackOS, the technical and sponsor teams are there and respond quickly." → **preferred channel** for rules questions |
| Discord https://discord.gg/tfwSeqVWmR | announcements and schedule changes ([E 10]); **unread by Grok Bot** |
| Onboarding call 21 Oct (YouTube live) | last chance to ask before the window |

### 0.5.7 Discrepancies and surprises
1. **Registration close**: page 23:59 UTC vs e-mail 12 Oct 23:45 UTC → use **23:45 UTC (19:45 Toronto)** for the 5th member.
2. **Prize split**: page = $13,000 cash + $7,000 in-kind, track 01 $1,600/$1,200/$900; Academy landing = $15,000 + $5,000 and $2,000/$1,350/$1,000 per track; Academy lesson = "$15,000 in cash" but per-track $1,600/$1,200/$900. **The event page (rule 08) governs**; amounts in this plan unchanged.
3. **Meterless** required vs "provider with credit" vs "no API, no key" (§0.5.5).
4. **Dates moved**: Sept posts said 15–20 Oct, registration 13 Oct, "4 tracks"; e-mail 12 Oct moved the event to 22–27 Oct "from bringing new sponsors on board, which means more challenges and more prizes. You'll hear the full details at the onboarding call on 21 October." → **tracks/prizes may still change on 21 Oct**; re-read [E] and [A] right after the call (P30). @GenAI_Now (9 Oct) also lists Bright Data as a sponsor, absent from the page.
5. **Zetaris**: [Z] README says "The event instance is shared; use assigned team names and permissions", while [G] says "everyone runs Zetaris locally in Docker". We stay local (Method A); ask at the call whether a shared instance exists.
6. **Meterless repo grid** ([ML]: Usefulness 30 %, Meterless engine usage 25 %…) is not the event grid; rule 07 governs (question sent).
7. **Build Day** [A] calls the workshop agent "a legitimate starting skeleton for your submission" — organizers tolerate pre-window skeletons, but **our rule stays: no BI code before 22 Oct 00:00 UTC.**
8. **Cursor credit** is on the HackOS task board ([A]) while [G] still has a placeholder → claim it (P29).

---

## 1. Sources reviewed, and conflicts between them

### 1.1 Sources reviewed

| # | Source | What it gave |
|---|---|---|
| S1 | Parent conversation (GenAI.works Hackathon agent), as relayed in the task and its summary | Decisions 16–17 Oct: track 01, Method A then B, H-MEM in Python + TS adapter, Toloka Day 1, 5 members, "keep in mind" items, PR #539 merged, Discord post published |
| S2 | `docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md` on `main` (merged PR #539; identical to `/workspace/plan/PLAN.md`) | Architecture, Zetaris schema, JSON contracts, feasibility tests of 16 Oct, demo set, test plan, schedule, decisions 1–23 |
| S3 | Attachment: Toloka plan (EN, 17 Oct, 7 pm), same as `/workspace/toloka/plan_toloka_hackathon_EN.md` | Option B (overlap 3, no QA), 23 items ≈ $48 on $50, route-priority EEZs, controls, blockers B1–B8, Day-0 timeline, Rajesh draft |
| S4 | Attachment: code audit baseline (16 Oct) | ruff 1,541, 3 broken `deploy_ai.py`, N+1 Mongo, heavy data, phases 0–5 |
| S5 | `/workspace/split/` (Split agent): `PLAN_AVANT_SPLIT.md`, `INVENTAIRE_AVANT_SEPARATION.md`, `IDEES_A_CODER.md`, `REVUE_IDEES_2026-10-17.md` (Clément's verdicts on 56 ideas), `LOTS_AU.md`, `PLAN_FUSION_PR_ET_POINTS_ATTENTION.md`, `SAUVEGARDE_17OCT.md`, `CONTABO_SECURISATION.md` | Split status and order, AU lots, the BI gaps that are already shipped and the ones still missing, OVH backup verified on 17 Oct |
| S6 | `/workspace/genai/` (16 Oct drafts: integration plan, README draft, deck outline, FR submission answers, daily checklist) | Older direction (track 02, "Skipper agent", new repo), plus useful ideas: `evals/`, `FAILURES.md`, daily checklist |
| S7 | `/workspace/hackos/` (published team description and invitation note) | Public pitch: track 01, 3–5 EEZs, "Team full (5/5)" |
| S8 | `/workspace/guide.txt` (official Participant Setup Guide copy) + setup-guide email of 15 Oct | "You're done when" checks; agent loop Nemotron → `run_sql` → Zetaris; Meterless Option A placeholders still unfilled; onboarding 21 Oct 12:00–13:30 UTC |
| S9 | Event page, rules 01–10 (read from page data on 17 Oct) | Rules quoted in §5; prizes; dates; judges (incl. Zetaris CTO) |
| S10 | Gmail (read-only search, last 3 days) and Google Calendar (17–28 Oct) | hackathons@genai.works bounced; resend to support@academy.genai.works 14:16 Toronto, no reply yet; Rajesh call booked for 19 Oct; Clément's email to Rajesh with the plan sent 19:18 Toronto today; onboarding call **not** in the calendar |
| S11 | `/workspace/moisson-*.md` (harvest of the day) | What every agent sent today (HackOS posts, Discord, LinkedIn, support ticket, 30 DMs to candidates, Discord post of the plan) |
| S12 | Cursor IDE agent transcripts on the Mac (`~/.cursor/projects/Users-clement-Blue-Intelligence-Map/agent-transcripts/`, 5 chats modified on 17 Oct; secrets filtered out) | Mostly NAVIGUIDE batch work (PRs #541–#551). BI-relevant: VL review routed through **Nebius Token Factory** (`nvidia/Nemotron-3.5-Super-VL`) for NAVIGUIDE; AMP polygon "pearls" fix PR #542; anti-orphan fix PR #543; Mac local `main` diverged from origin |
| S13 | Public shallow clone of `Berry-Mappemonde/Blue-Intelligence` at `90ab81e` (merge of #559, 17 Oct 18:09 Toronto) in `/workspace/bi-review`, plus GitHub public API (open PRs) | Code facts in §1.3 and §2 |
| S14 | Mac, read-only: `docker ps`, `.env` variable **names** only, `git status` count | Zetaris containers healthy (up 39 h); `.env` has the Zetaris and model names, `POE_GOLD_PG_URL` and `TOLOKA_API_KEY` commented out; `.env` permissions still `-rw-r--r--` |

### 1.2 Conflicts found and proposed resolutions

| # | Conflict | Sources | Proposed resolution |
|---|---|---|---|
| C1 | **Toloka granularity.** S2 §5.3 sends *port candidates* (yes/no/insufficient, "classic API"). S3 sends *1 EEZ + 1 candidate URL* with 6 labels on the new platform (v2-beta pipelines, Quorum node). | S2, S3 | Adopt **S3 (URL level, v2-beta)** for the only batch. It fits the budget and the credited account, and it feeds H-MEM: "this URL is valid evidence for this polygon" is exactly the memory H-MEM stores. Port-level doubtful verdicts (`conflict`, `missing_in_listing`, `new_from_doc`) go to **Clément as operator** in the review screen, shown in the video as the "next Toloka round" (post-hackathon / Bespoke with Rajesh). Rewrite S2 §5.3 accordingly. |
| C2 | **Number of batches and budget.** S2 plans a launch on the 22nd plus "a second small batch on the 25th", with a cap of 30 tasks. S3: 23 items ≈ $48 of a $50 balance, trial = 1 pipeline, and a deployed pipeline is locked. | S2, S3 | **One batch, 23 items** (18 to judge + 5 hidden controls), `itemLimit` = 23. A second batch only if Clément tops up the balance (a purchase, so his explicit decision) or Toloka grants credit after the 19 Oct call. Replace "cap 30" with "itemLimit from budget (23)". |
| C3 | **"Mini test batch prepared beforehand".** On trial, runs return 403, and a run costs money. | S2 §9, S3 B1/B5 | Replace it with **Self-check + "User Interface" check on 5 control items, no Deploy**, on 19 Oct (S3 calendar). |
| C4 | **Toloka "Day 1" vs the Nemotron VL gate.** The batch must not leave before the VL review, which is repo code, so 22 Oct at the earliest. S3 itself expects "late on the 22nd at best, more likely the 23rd". | Parent decision 21, S3 B8 | **RESOLVED by D24 (Clément, 17 Oct 19:39 Toronto): Toloka ASAP, VL is no longer a gate.** The batch (18 priority-1 route URLs + 5 hidden controls, 2 onboarding examples; overlap 3, No QA, ≈ $48 of $50) is built **before 22 Oct** from pre-existing data only: existing Proposer/auto-review verdicts (`review_doc_picker` / `review_suggest`), candidate fiches exported read-only. The "doubtful" selection uses those existing verdicts; if anything is needed it is done by hand/CLI **outside the repo**, no new code. Dataset uploaded beforehand (an upload is not a run). **Deploy at 22 Oct 00:00 UTC exactly (21 Oct 20:00 Toronto), not before** (rule 04: the answers feed graded work), after Clément's explicit "yes" on the Cost breakdown (Expected / Maximum). The Nemotron VL review runs **in parallel** on 22 Oct on the same items; Toloka vs VL vs Proposer becomes an agreement table (video + `evals/`). If verification (B1) is not done by 21 Oct 20:00 Toronto: deploy the moment it is; nothing else changes (F-TOL §3.3 only if no answers by 25 Oct 12:00 UTC). |
| C5 | **Where Toloka results are written.** S3 writes them to Mongo (`review_suggest.toloka` or a new `review_crowd`) and pre-ticks `review_choices`. S2 decision 4: **no Mongo write during the hackathon**; Gold goes to the agent's Postgres. | S2, S3 | Follow decision 4. Toloka answers go to a `toloka_answers` table in the **same gold Postgres**, with `poe_gold.toloka_status` and the H-MEM trust entry updated from them. Mirroring into `review_suggest` / `review_gold` is a post-hackathon task (§7). |
| C6 | **Which zones.** S2 demo = 5 EEZs (5677, 48944, 8429, 8447, 5696). S3 Toloka priority = 18 non-French route EEZs (Spain → Grenada), with Mexico 8429 and Niue 8447 as hidden controls, and France/Mayotte/New Caledonia only as onboarding examples. | S2, S3 | Keep both, with distinct roles. The **reconciler demo** runs on the 5 S2 zones. **Toloka** validates URLs for the route zones (that is Clément's priority). Mexico and Niue tie both together in the video. Optional on the 26th: run the reconciler on 1–2 route zones whose URL Toloka validated unanimously (for example an English-language one such as Saint Lucia 8416 or Barbados 8418). Open question Q2. |
| C7 | **Candidate export source.** S3 has Clément run the local backend on **Atlas** to export fiches. S2 decision 4: the live database is the VPS; Atlas is a frozen copy since 10 Sept, "do not use it for the demo". Also, prod `GET /api/review/*` requires the admin key (`backend/app/main.py`, `_ADMIN_GET_PREFIXES`). | S2, S3, S13 | Export read-only from the **VPS production API** with the admin key (Clément, his credentials, nothing pasted in chat), or through a read-only tunnel. Atlas only if the VPS export fails, and then the README says "frozen stock of 10 Sept". |
| C8 | **Tavily step.** The S3 gate uses `naviguide-simulator/server/tavily_client.py` and `truth_judge.py`. After the split, those files belong to the NAVIGUIDE repository, and Tavily is not a sponsor. | S3, S5 | **Drop Tavily from the BI agent.** Fetch with BI's own `core/extract.py` / `render.py` / `pdf_preview.py`. |
| C9 | **Screenshots before the 22nd.** S3 allows "a local script outside the repo that imports these functions" before the 22nd. Clément's rule: no code before 22 Oct 00:00 UTC. | S3, parent | No script before the 22nd. Captures before the 22nd only with existing CLI tools (`pdftoppm`, a browser screenshot) as data prep, declared in the README. With D24 the screenshots are **required before 21 Oct** (dataset upload), so they are made with these existing tools. |
| C10 | **Organizer contact.** Rule 10 and S2 decision 23 give hackathons@genai.works ("reply within one working day"). That address **bounced** on 17 Oct (06:13 Toronto). The two questions drafted on 17 Oct (track for a pre-existing project; which grid and dates apply) were **not sent** (no such mail in Sent). | S9, S10, S11 | **Update 17 Oct 19:38 Toronto: both questions SENT** to support@academy.genai.works, in the thread "Remove a team member and rename our team". Awaiting reply; if none, ask live at the 21 Oct onboarding call. Fix decision 23. |
| C11 | **Team status.** The HackOS invitation note says "Team full (5/5)", the team name is still "NAVIGUIDE and Blue Intelligence for Berry-Mappemonde", and RH DM'd 30 candidates today. Rule 2: the team locks at the first submission. | S7, S11, S9 | No submission draft is *created* on the platform before the replacement has joined and the removal is done. Replacement registered before **22 Oct 23:59 UTC**. Update the invitation note once a name is chosen. |
| C12 | **VL endpoint.** S2 uses NVIDIA's free API (`integrate.api.nvidia.com`, tested 16 Oct). Clément's verdict on idea #18 (S5) says "Nemotron Super VL via Nebius Token Factory", and today the NAVIGUIDE VL review was moved to Token Factory (S12). | S2, S5, S12 | Recommendation: **NVIDIA free API as primary** for the hackathon. It is the guide's Option B, already tested, free, and it saves Nebius credit for the NAVIGUIDE judges (1–15 Dec). Token Factory is a fallback by switching `MODEL_BASE_URL`/key (same model family). Both count as NVIDIA Nemotron. Open question Q3. |
| C13 | **What is pre-existing.** S2 (line 15, §1.2, §1.6) says §6.3 (reading a whole catalogue page) is unimplemented and counts as new work. S5 shows `judge_one` already calls `harvest_bu_catalog` + `remember_seed_urls` (`poe_seed_enrich.py:647/940`; commit `8b89495e`, 8 Sept, per S5, not re-verified here because the clone is shallow). | S2, S5, S13 | Declaring existing work as new is a disqualification risk (rule 04). Rewrite: **text** catalogue harvesting is **pre-existing**; **new** = VL page reading with mandatory citation, multi-source reconciliation with proofs, H-MEM, Toloka, `poe_gold`, Zetaris integration. |
| C14 | **Repository facts.** S2 says `Blue-Intelligence-Map` with 1,249 commits. The repo is now `Berry-Mappemonde/Blue-Intelligence` (`-Map` redirects to it), `main` has 1,401+ commits (S5), and no NAVIGUIDE repo exists yet. The split plan renames the mono-repo to `-Map` and then creates a new `Blue-Intelligence`. | S2, S5, S13 | Update §1/§2 of S2. Pre-existing declaration = "all commits up to tag `pre-hackathon-2026-10-22` (to create at 22 Oct 00:00 UTC)". |
| C15 | **S6 drafts (16 Oct).** Track 02, a "Skipper agent", a brand-new repo at window opening, a deck with the NAVIGUIDE logo. | S6 vs S1/S2 | Superseded by the 17 Oct decisions (track 01, PoE Reconciler, BI only). Archive `/workspace/genai/` as "superseded"; reuse `evals/` + `FAILURES.md` + the daily checklist. |
| C16 | **S2 schedule internal inconsistency.** Toloka launches on the 22nd, but VL extraction is on the 23rd and the reconciler (which produces port-level doubts) on the 24th. So the 22nd batch could not contain the S2 §5.3 tasks. | S2 §9 | Solved by C1 + C4/D24 (URL-level batch built before the window from existing verdicts). |
| C17 | **`metadata.json`.** S2 plans it, but rule 06 does not require it and no schema is published. | S2, S9 | Keep it optional (2 min of work). Required deliverables = video, slide deck, repo + README, sponsor explanation (rule 06). Slides were not in the S2 checklist as a full item: add them. |
| C18 | **Meterless setup guide placeholders.** The guide still has "[Organisers: add the Meterless base URL / prompt library / AI hotspot]". Pavlo (13 Oct): no API, no key. | S8, S1 | Keep the decision (H-MEM in Python + TS conformance). Check at the onboarding call whether the organizers publish a "Meterless prompt library" or "hotspot" by then. If they do, using one prompt file in Cursor is a cheap extra sponsor proof. |
| C19 | **Registration close time.** Event page 23:59 UTC; organizer e-mail of 12 Oct 23:45 UTC. | §0.5.1 | Use **22 Oct 23:45 UTC (19:45 Toronto)** everywhere (P7, Day 1). |
| C20 | **Meterless as provider vs "no API, no key".** Academy *Power Quick Start* and the setup guide route Nemotron through Meterless with credit on the HackOS task board (base URL still a placeholder); Pavlo said no API, no key; the course FAQ even omits Meterless from the required list, while rule 05 requires it. | §0.5.5 | Keep decision 13 (H-MEM in Python + TS conformance) as the Meterless integration. Hedge: Clément checks the HackOS task board (P29); if a Meterless endpoint/credit exists, also route Nemotron through it (3 `.env` settings). Ask at the 21 Oct call / HackOS "Help Meterless". |
| C21 | **Prize amounts.** Event page $13k cash + $7k in-kind; Academy landing $15k + $5k with $2,000/$1,350/$1,000 per track. | §0.5.7 | Event page (rule 08) governs; no change to the plan's figures. |
| C22 | **Video hosting.** The plan says YouTube; HackOS has a video-upload endpoint, so the form may want a file. | §0.5.2 | Keep the MP4 (< 4:00) **and** a YouTube link ready; decide when the draft form is visible (P31). |
| C23 | **Organizer contact.** Rule 10 address bounced; organizer e-mails say "Questions go on HackOS". | §0.5.6 | HackOS Help desk is the primary channel; support@academy.genai.works second; Discord unread. |
| C24 | **Tracks/prizes may change on 21 Oct** ("more challenges and more prizes … full details at the onboarding call"). | §0.5.7 | Re-read the event page and the *How the Week Runs* lesson right after the call (P30); re-check the track choice. |
| C25 | **NAVIGUIDE content in the graded repo.** If the split is not done, the graded repo also contains NAVIGUIDE. | §0.5.2 | The declaration says NAVIGUIDE is not part of the submission; README points judges to `backend/app/agent_poe/`. |
| C26 | **Freeze language.** Older drafts had a code/PR/video freeze. | Clément 17 Oct | **No freeze** (decision 25 amended, PR #568). Safety margin = target submission 27 Oct 16:00 Toronto, hard 19:45; green CI on every merge. |

---

## 2. Pre-hackathon phase (Sat 17 → Wed 21 Oct 20:00 Toronto)

Rule: **no repo code, no agent code, no commit of hackathon work.** Merging the open pre-window PRs is allowed: they are pre-existing and get declared. Owners: **C** = Clément; **T** = a team member; **GB** = Grok Bot; **CU-plan** = Cursor in plan/test mode only.

| # | Task | Owner | Deadline (Toronto) | Done when |
|---|---|---|---|---|
| P1 | **Toloka team verification (B1)** (trial → no run, 403): look for "Verify" in platform.toloka.ai or the Business Console. **Do it this weekend**, not waiting for Monday. | C | **Sat 17–Sun 18 Oct**; backup: Rajesh call Mon 19 Oct 12:30; hard stop Wed 21 Oct 20:00 | Team no longer "trial"; a `GET /me` (read) shows the verified status, or Toloka confirms in writing |
| P2 | Rajesh call (Mon 19 Oct 12:30–13:00), backup for P1: verification (if still pending), unverified pool on Quorum (B2), Bespoke unit price for the 285 polygons, possible pilot credit. Fill in the [N] figures of the email first. | C (GB prepares notes) | Mon 19 Oct 12:30 | Answers written into the Toloka plan |
| P3 | Toloka UI: create **the** project + **the** pipeline (Start → Quorum, EN audience, $6/h if the unverified pool is allowed, 300 s, overlap 3, No QA, offboarding rule on `label`, per-annotator cap off), instructions, 3–6 step onboarding, demo dataset of 5 controls, Self-check + UI check. **No Deploy.** | C (clicks), GB (copy) | Mon 19 Oct evening (at the latest Tue 20 Oct) | Self-check green; image field renders (B3) |
| P4 | Candidate export for the 18 priority-1 route EEZs + 5 controls + 2 onboarding examples, read-only from the VPS API with the admin key (C7); output `candidates.jsonl` **outside the repo**. Include the existing Proposer/auto-review verdicts (`review_doc_picker` / `review_suggest`) | C | Sun 18–Mon 19 Oct | File exists; 25 polygons covered; no write anywhere |
| P4b | **Build the Toloka dataset (D24)**: pick the 18 priority-1 route URLs (doubtful first, by existing verdicts) + 5 hidden controls + 2 onboarding examples; S3 §3.4 item schema; by hand/CLI **outside the repo**, no new code. Screenshots taken. | C (GB helps with the selection notes) | Tue 20 Oct | 23 items + 2 examples in a TSV/JSON outside the repo |
| P4c | **Upload the dataset** to the pipeline (upload is not a run); Self-check green again; Cost breakdown readable | C | Wed 21 Oct 19:00 | Dataset attached, pipeline ready to deploy |
| P5 | Public HTTPS hosting for screenshots (JPEG < 300 KB), outside the repo | C | Mon 19–Tue 20 Oct | One test image opens in the Toloka UI check |
| P6 | **Organizer questions** (track 01 vs Wildcard for a declared pre-existing project; which grid and dates apply) (C10) | C | ✅ **Sent Sat 17 Oct 19:38 Toronto** to support@academy.genai.works (thread "Remove a team member and rename our team") | Reply logged in the plan. If no reply: ask on the 21 Oct call |
| P6b | **Toloka deploy slot**: Clément available Wed 21 Oct 20:00 Toronto (= 22 Oct 00:00 UTC) to read the Cost breakdown, say "yes" and Deploy | C | Wed 21 Oct 20:00 | Run deployed |
| P7 | Team: removal of Hamid Aziz + team rename to "Blue Intelligence" (support email 17 Oct 14:16 Toronto + ticket + `#general-admin` + Discord, no reply yet); choose and onboard the 5th member | C (+ RH agent drafts) | Replacement registered **before Thu 22 Oct 19:45 Toronto** (23:45 UTC) | HackOS team page shows 5 members and the new name |
| P8 | Roles for the 5 members (proposal: Clément = product/operator/Gold reviewer; Dileep = harbour-master POC + PR #552 knowledge; Nitesh / Hakan = tests, README/slides, H-MEM TS adapter; 5th = video/QA). **(Names known, skills unverified.)** | C | Wed 21 Oct | Roles posted in Blue Intelligence `#général` (after approval) |
| P9 | Repo split (S5 phases 0–4). Graded code then lives in the new BI repo. | C (Split agent prepares) | Ideally Sun 18 Oct; at the latest Wed 21 Oct 19:00 | Both repos exist, BI CI green, VPS repointed. Otherwise fallback: `agent-poe` branch in the current repo after 00:00 UTC (decision 12) |
| P10 | Pre-window PRs: decide on **#557** (deploy_ai fix + F401), **#561** (backend pytest in CI with a local Mongo), **#553/#554/#555** (split docs), **#542/#543/#546/#547/#549/#562**. Either merged **before 22 Oct 00:00 UTC**, or left until after 27 Oct so they are not mixed with graded work. | C | Wed 21 Oct 19:00 | Each PR merged or explicitly deferred |
| P11 | Tag the last pre-window commit: `pre-hackathon-2026-10-22` (at 22 Oct 00:00 UTC, on the repo that will be graded) | C | Wed 21 Oct 20:00 | Tag visible on GitHub |
| P12 | Zetaris setup checks from the guide: `./verify.sh`, `SELECT 1 AS one`, the sample ("Pikachu") query returns two rows, the API key in `.env`. `SELECT 1` already passed on 16 Oct; containers healthy on 17 Oct. | C (GB can run read-only checks) | Mon 19 Oct 20:00 (guide: two days before kickoff) | All three checks green |
| P13 | Separate Postgres for `poe_gold`: start a plain Postgres container (not the Zetaris one on 55000). Check that the Zetaris containers reach it via `host.docker.internal`. **Infra only, no schema in the repo.** Put the URL in `.env` as `POE_GOLD_PG_URL` (Clément types it himself). | C | Wed 21 Oct | `psql` connects from the host; reachability from the Zetaris container is noted, or left as the first test on the 22nd |
| P14 | Nemotron smoke tests (guide "Verify your setup"): Super and VL with `reasoning_effort: "none"`. Already passed on 16 Oct. Re-run once on 20 Oct. | GB/CU-plan (read-only calls, keys stay in `.env`) | Tue 20 Oct | Both reply; VL returns JSON |
| P15 | H-MEM homework: read `engines/hmem` (AGENTS.md, conformance runner, the `HMEM` interface) and write the **Python type map** in the plan (no code) | CU-plan | Wed 21 Oct | A table of interface methods → Python functions → tests |
| P16 | Write the test cases as **notes** (≈ 20 eval cases from the 11 stable polygons, expected vs actual) for `evals/` | CU-plan / GB | Wed 21 Oct | List in the plan |
| P17 | Shot list and storyboard of the video (1–4 min, English, YouTube); slide outline aligned with rule 06 | GB | Wed 21 Oct | Storyboard file on the box |
| P18 | Onboarding call (Wed 21 Oct 08:00–09:30 Toronto, YouTube live): ask the open questions (track, grid, Meterless provider/credit vs H-MEM, shared Zetaris instance or local, can a submission be edited after it is submitted and does that change its timestamp, video upload vs link, Zetaris write path B). Live questions may only be possible in the YouTube chat or HackOS: post them on HackOS Help desk beforehand (P33). **Add it to the calendar** (offer still open). | C attends, GB prepares questions | Wed 21 Oct 08:00 | Answers noted |
| P19 | `.env` hygiene: `chmod 600 ~/Blue-Intelligence-Map/.env`; check `.gitignore`; add `TOLOKA_API_KEY` himself | C | Sun 18 Oct | `ls -l` shows `-rw-------` |
| P20 | HackOS / LinkedIn polish (optional): role location, headline; invitation note once the 5th member is known | C / GB with approval | Wed 21 Oct | — |
| P21 | Mac local repo after the batch: delete the untracked plan copy, `git pull`, `git remote set-url` to the right repo (only after the split decision) | C | After his batch | Local `main` = origin |
| P22 | NAVIGUIDE time budget (Clément's choice, **to be confirmed**): the Nebius "submission update" on 23 Oct and the final submission on 30 Oct (editable until then) overlap the window. No Nebius rule freezes NAVIGUIDE; how much NAVIGUIDE work to do during 22–27 Oct is purely a time-budget decision for Clément. | C | Wed 21 Oct | Decision written |
| P23 | **Submission-form pack** (docs, not code): title, one-line pitch, track 01, team, repo URL, video (MP4 + YouTube link), deck (PDF), sponsor explanation (Zetaris / Meterless / Cursor / NVIDIA / "what was unique"), pre-existing declaration (§0.5.2 draft), Colab = none. | GB drafts, C validates | Wed 21 Oct | One text file ready to paste |
| P24 | **Duplicate-account check** (rule 01: duplicates disqualify the whole team): each of the 5 members has exactly one HackOS account. | C | Wed 21 Oct | Confirmed by each member |
| P25 | **Repo visibility and licence**: the graded repo must stay public with a LICENSE (today public, MIT + Apache-2.0). If the split creates a new BI repo, make it public and add LICENSE before 22 Oct 00:00 UTC. | C | Wed 21 Oct 19:00 | `gh repo view` shows public + licence |
| P26 | **Prize split** (rule 08: equal split unless the team submits another split in writing): decide whether any cash goes to the association, and get the members' written agreement if so. | C | Before 27 Oct | Decision noted (no message sent without approval) |
| P27 | Power Day (Mon 19 Oct ~18:00 Toronto) and Build Day (Wed 21 Oct ~00:00 Toronto) workshops: watch live or the recording, only to catch Meterless provider details or new rules. Optional. | C / T | 19–21 Oct | Notes added to §0.5 |
| P28 | Daily watch of the event page and Discord announcements (schedule changes are announced there, rule 10). | GB (page) / C (Discord) | daily to 27 Oct | Changes logged |
| P29 | **HackOS task board** (read-only look, then claim): Cursor credit, and whether a Meterless credit / base URL exists (C20). | C | Sun 18 Oct | Cursor credit active; Meterless status noted |
| P30 | **Right after the onboarding call** (21 Oct 13:30 UTC): re-read the event page + *How the Week Runs* lesson; update §0.5 and the track choice if tracks/prizes changed (C24). | GB | Wed 21 Oct 10:00 Toronto | §0.5 updated |
| P33 | Post the open rules questions on **HackOS Help desk** (same text as §6.4, plus: edit-after-submit, video upload vs link, Meterless provider). Needs Clément's approval to post. | C (GB drafts) | Sun 18 Oct | Question posted / answered |

**Code-audit items before the 22nd: no.** No new code from Cursor before 22 Oct 00:00 UTC (Clément's rule). The only code allowed to land before is what already sits in open PRs (#557, #561…), if Clément merges them himself, and it is then declared as pre-existing.

---

## 3. Build window, day by day (22–27 Oct)

Toronto = UTC−4 for the whole window. Blocks are targets; every gate decides what happens next.

### 3.0 Principles
- New code lives **only** in `backend/app/agent_poe/`, `backend/tests/test_agent_poe_*.py`, `hmem_adapter/`, `evals/`, the README / `FAILURES.md`, one small UI view, and one CI job. Pre-existing modules are **called, not edited**. If one must change, it is a minimal, separate commit, declared.
- Every model call: an explicit Nemotron model + `reasoning_effort: "none"`. Today `core/nvidia.py::generation_extras()` returns `{}` for Nemotron models, so the agent must pass it itself; a test checks it.
- No Mongo writes. Only reads, from the VPS export.
- Each day ends with: push, CI green, a 30-second screen capture, README "what runs today" updated (S6 checklist).

### 3.1 Day 1: Thu 22 Oct (UTC) / Wed 21 Oct 20:00 → Thu 22 Oct 20:00 Toronto
| UTC | Toronto | Work | Owner |
|---|---|---|---|
| 00:00–00:15 | Wed 20:00–20:15 | **Gate G1 (Toloka, D24)**: verification done? Dataset (23 items, uploaded before) frozen; read the Cost breakdown (Expected / Maximum); **explicit "yes" from Clément** → **Deploy the Toloka run** (UI). If not verified: deploy the moment it is. | C |
| 00:15–00:45 | Wed 20:15–20:45 | G0 gate: which repo (split done or fallback branch); tag `pre-hackathon-2026-10-22`; first commit = `agent_poe/` skeleton + `config.py` (`TabConfig`, `CONFIGS["poe"]`) | C + Cursor |
| 00:45–03:00 | 20:45–23:00 | `zetaris_client.py` (SELECT-only) + tests; **VL URL review** (`vl_extractor.check_url`: is this page a PoE list for this polygon? JSON with quote), **no longer a gate**; `toloka_task.py` reader for the already-built items (schema S3 §3.4) + tests | Cursor, reviewed by C |
| 03:00–14:00 | 23:00–10:00 | Run the VL review **in parallel** on the same 23 Toloka items (+ the rest of `candidates.jsonl`), SHA-256 cache; store verdicts for the Toloka vs VL vs Proposer agreement table. Toloka: read-only GET monitoring. | Script unattended; C |
| 14:00–18:00 | 10:00–14:00 | Zetaris: generate the CSVs of the 5 zones (`load_sources.py`), register them, control SELECT + one join; gold Postgres: DDL for `poe_gold` / `toloka_answers` (in `gold.py` migrations), `CREATE DATASOURCE` + `REGISTER DATASOURCE TABLES` via `host.docker.internal`; **Method B test** (`INSERT INTO`) in a separate setup script | Cursor + C |
| 18:00–20:00 | 14:00–16:00 | **Gate G2 (Zetaris)**: `poe_gold` (empty) readable through Zetaris? B works or not, noted in the README | C |
| 20:00–24:00 | 16:00–20:00 | Registration closes **23:45 UTC** (19:45 Toronto, C19): check the 5th member is in before. Start `memory.py` (types + `MemoryStore`), seeded from `poe_exceptions.json` | C / Cursor |

### 3.2 Day 2: Fri 23 Oct
| UTC | Toronto | Work |
|---|---|---|
| 12:00–16:00 | 08:00–12:00 | `vl_extractor.extract_document` on the France PDF (1 page) then Mexico; enforce "no quote → doubtful"; text fallback through `pdf_worker` + `extract_structured_ports`; `docs_cache` |
| 16:00–20:00 | 12:00–16:00 | Decision 8: Mayotte or New Caledonia (2nd French polygon). Niue + UK pages. Toloka: read-only monitoring, first answers |
| 20:00–02:00 | 16:00–22:00 | `memory.py`: `MemoryRetrieval`, layers working → long_term, trust from Toloka; start `hmem_adapter/index.ts` |
| — | — | Clément: Nebius "submission update" for NAVIGUIDE (time-box ≤ 2 h) |
| 12:00–13:00 | 08:00–09:00 | **P31: create the submission draft on HackOS** (only once Hamid's removal is done and the 5th member has joined: the first submission locks the team). Select track 01, read the real form fields, save; adjust the P23 pack. |

**Gate G3 (end of 23 Oct)**: VL gives cited rows for France. If VL fails twice (502/429): text fallback, and the README says VL was shown on the cached page (S2 plan B).

### 3.3 Day 3: Sat 24 Oct
| UTC | Toronto | Work |
|---|---|---|
| 12:00–17:00 | 08:00–13:00 | `reconciler.py` with Nemotron Super on the 5 zones, statuses of S2 §5.2, proofs JSON; Mayotte vs mainland test |
| 17:00–21:00 | 13:00–17:00 | **Agentic step (new, recommended):** Nemotron Super gets a `run_sql` tool and issues the §4.2 reconciliation queries to Zetaris itself (bounded loop, max N calls, SELECT-only). This is the guide's reference loop and the strongest "Sponsor tech" proof. |
| 21:00–01:00 | 17:00–21:00 | Toloka export (`POST /datasets/{id}/exports`, with Clément's agreement) + aggregation (3/3, 2/3, 1/1/1 rules) into `toloka_answers`; controls pass rate; **agreement table Toloka vs Nemotron VL vs Proposer** → `evals/toloka_vl_proposer.md` + a video shot |

**Fallback F-TOL** (Toloka not verified, or no answers by 25 Oct 12:00 UTC): the video shows the submitted task and the pipeline; aggregation runs on Clément's **operator** answers, clearly labelled "operator, not the Toloka pool" (S2 §9 risk table). No fake crowd data.

### 3.4 Day 4: Sun 25 Oct
| UTC | Toronto | Work |
|---|---|---|
| 12:00–16:00 | 08:00–12:00 | `gold.publish` v1 (INSERT-only, `parent_version`, fingerprint) for rows with complete proofs; read back through Zetaris; latest-version query |
| 16:00–19:00 | 12:00–15:00 | H-MEM: recall a French URL for a second polygon (Mayotte sees it and filters by geometry); Toloka-validated URLs promoted to long_term with trust |
| 19:00–23:00 | 15:00–19:00 | **Gate G4 (harbour-master POC)**: only if France PoE is in Gold. One directory page, one office (Calais or La Rochelle), `TabConfig["capitainerie"]`, one verdict in the README. Otherwise skip. |
| — | — | `TabConfig` for marinas and AMP (design only, no execution) + `test_agent_poe_tabs.py` |

### 3.5 Day 5: Mon 26 Oct
| UTC | Toronto | Work |
|---|---|---|
| 12:00–15:00 | 08:00–12:00 | Metrics (S2 §8: listing coverage, precision after Toloka, complete proofs, WPI conflicts); `evals/` (~20 cases, expected vs actual); `FAILURES.md` |
| 15:00–18:00 | 11:00–14:00 | **H-MEM conformance scorecard green** through the TS adapter (`HMEM_IMPL=… npx tsx conformance/runner.ts`); CI job `agent-poe` (pytest of the agent tests; only if #561 is not already on `main`) |
| 18:00–22:00 | 14:00–18:00 | **Minimal UI** (Product & UX 10): a read-only "Gold" card in the existing Formalities/Review screen: version, statuses, proofs (URL/page/quote), Toloka agreement. Feature freeze at 22:00 UTC. |
| 22:00–03:00 | 18:00–23:00 | README (setup, usage, dependencies, pre-existing vs new, sponsor section), slide deck draft, final video script; record the shots from the live run (`docs_cache` + `poe_gold` replay if a call fails) |

Note: judging opens at 27 Oct 00:00 UTC (26 Oct 20:00 Toronto). Submissions stay open until 23:45 UTC, but an early, complete submission is safer (ties: Impact, then timestamp).

### 3.6 Day 6: Tue 27 Oct
| UTC | Toronto | Work |
|---|---|---|
| 10:00–12:00 | 06:00–08:00 | Replay on 5677 and 8429; fix blocking bugs only. **Code freeze 12:00 UTC.** |
| 12:00–16:00 | 08:00–12:00 | Video edit (GB), upload to YouTube (Clément's account; public or unlisted, to confirm); slides exported to PDF |
| 16:00–19:00 | 12:00–15:00 | Submission form: track 01, links, **pre-existing declaration** (tag + list of modules), sponsor explanation, team. Clément says "publish". |
| **by 20:00** | **by 16:00** | **Submit.** Margin to 23:45 UTC (19:45 Toronto). |

**P32, submission protocol (no freeze; safety margin only).** The official checklist ([A], §0.5.2) is ticked item by item: track 01 selected; video 1–4 min (check the exact length) naming Zetaris, Meterless and Cursor; deck PDF with architecture diagram + stack; README runnable by an outsider; `.env` ignored, secret scan clean; pre-existing declaration pasted; Colab = none. Links opened from a private browser window (repo public, video plays). If edits after submit are allowed (to confirm, P18/P33), submit a complete version **before 27 Oct 00:00 UTC** (judging opens; ties go to the earlier timestamp) and update it later; otherwise submit once at 16:00 Toronto. Merges may continue after submission with green CI; the video stays the one recorded on `main` that day.

### 3.7 Scope per tab (unchanged from S2 §11.5)
| Tab | Scope | Deliverable |
|---|---|---|
| Ports of entry | Full demo | Video + `poe_gold` on the 5 zones (minimum 5677 + 8429) + Toloka URL batch |
| Harbour masters | POC if G4 passes | One sheet, one document, one verdict in the README |
| Marinas | Design | `TabConfig` + S2 §11.2 |
| AMP | Design: a verification tool on top of ProtectedSeas (CC BY 4.0, public FeatureServer, no bulk download) | `TabConfig` + S2 §11.3 |
| Climatology | Out of scope | Nothing |


### 3.8 Conformité et confiance (approved by Clément, 17 Oct ~20:15 Toronto)

Source: `conformite-hackathon.md` (agent « Actif technologique », 17 Oct 20:15 Toronto), adapted to this plan. **Scope €0 only**: free GitHub settings, in-house files, open-source workflows (CodeQL, Syft, Scorecard, pytest-cov, promptfoo, garak), the free NVIDIA API already used here. Paid items stay out (`plan-si-prix.md`). **No transfer of rights from Clément to the association** is part of this plan (rule 09: teams keep all rights).

**Rules.**
- All CH work is done **inside the window (22–27 Oct)** on separate `conformite/*` branches/PRs. Product-side items (`.github/`, `infra/`, `docs/`) are declared in the form as **"hygiene and compliance of the pre-existing product, done during the window"** (rule 04, §3.0). Agent-side items (CH-10…CH-15) live in the agent perimeter and count as new work.
- **It must never delay the submission**: last `conformite/*` PR merged by **Tue 27 Oct 08:00 Toronto** (code freeze); submission before **16:00 Toronto**. If a CH task slips, it is dropped, not the critical path (PoE Reconciler, Toloka deploy 22 Oct 00:00 UTC, video, submission).
- Clément merges each `conformite/*` PR (~5 min each); CH work runs in a separate Cursor cloud agent, only short review slots for Clément. Human time ≈ 1 h 30–2 h 30 [estimate].
- **CH-16**: the AI Act notice "vous échangez avec une IA" goes into the **NAVIGUIDE simulator**, separate PR, **not presented to GenAI judges**. **Timing to be confirmed by Clément** (open question §6.3 #11).
- CodeQL/Scorecard findings outside `agent_poe/` are listed and fixed after 27 Oct.

**Tasks** (S < 2 h, M = half-day; 🤖 Cursor cloud agent, ⚙️ GitHub admin, 👤 human):

| Id | Tâche | Branche / PR | Fichiers touchés | Critère de fin | Effort | Qui | Présentation aux juges (critère) |
|---|---|---|---|---|---|---|---|
| **CH-1** | **Activer** la détection de secrets, le blocage à l'envoi (*push protection*), les alertes et mises à jour de sécurité Dependabot, le signalement privé des vulnérabilités, et la configuration CodeQL par défaut (*default setup*) si on ne fait pas le workflow de CH-8 | Aucune (réglage) | *Settings → Code security* | L'API `GET /repos/{owner}/{repo}` affiche `secret_scanning`, `secret_scanning_push_protection` et `dependabot_security_updates` à `enabled` (ils sont à `disabled` le 17/10) | S (10 min) | ⚙️ Clément (ou un agent avec droits admin, **sur son accord explicite**) | Capture dans la slide « Trust ». « Aucun secret ne peut être poussé » (Technical) |
| **CH-2** | **Traiter les alertes de secrets** de l'historique : GitHub scanne tout l'historique dès l'activation | Aucune | Consoles des fournisseurs | Chaque alerte est classée « révoquée et régénérée » ou « faux positif », sans afficher aucune valeur | S à M | 👤 Clément (rotation des clés). 🤖 tri des alertes en lecture | Non montré (hygiène) |
| **CH-3** | **Dependabot pip pour `backend/`** (absent aujourd'hui) | `conformite/dependabot-backend` | `.github/dependabot.yml` (une entrée `pip`, `directory: /backend`, hebdomadaire) | La PR est fusionnée et la page Dependabot montre `backend/requirements.txt`. **Aucune PR Dependabot non critique fusionnée pendant la fenêtre** | S | 🤖 | Ligne dans le README (Technical) |
| **CH-4** | `SECURITY.md` (périmètre, comment signaler via le formulaire privé de CH-1, délai visé, versions supportées) | `conformite/security-policy` | `SECURITY.md` à la racine | Le fichier est visible dans l'onglet *Security → Policy* | S | 🤖 · 👤 validation du délai de réponse | README, section « Security » (Technical) |
| **CH-5** | `security.txt` (RFC 9116) sur blueintelligence.online | `conformite/security-txt` | `infra/vps/nginx/…` (bloc `location = /.well-known/security.txt`) et le fichier texte | `curl https://blueintelligence.online/.well-known/security.txt` renvoie 200 avec `Contact:` et `Expires:` | S en code, S en déploiement | 🤖 (PR) · 👤 **Clément déploie sur le VPS** (accès SSH) | Non montré (hygiène) |
| **CH-6** | `DATA_SOURCES.md` : registre des sources (URL, licence, attribution, date, cessible oui/non) pour **toutes les sources que l'agent fédère via Zetaris** et pour la base existante. Sources visées : ZEE Marine Regions, WPI, OSM (ODbL), ProtectedSeas (CC BY 4.0), pages gouvernementales, Toloka | `conformite/data-sources` (produit) ; la partie « sources de l'agent » est reprise dans le README de l'agent | `DATA_SOURCES.md`, plus un lien dans le README | Chaque table enregistrée dans Zetaris a une ligne. Chaque licence a une URL. L'ambiguïté Marine Regions (CC-BY 4.0 ou CC-BY-NC-SA) est signalée | M | 🤖 · 👤 envoi éventuel d'une question à Marine Regions (pas pendant la fenêtre) | **Piste 01 « Fragmented Intelligence »** : « chaque source fédérée est identifiée, licenciée et citée » (Impact, Technical) |
| **CH-7** | **SBOM** CycloneDX à chaque push sur la branche notée et à la release | `conformite/sbom` | `.github/workflows/sbom.yml` (anchore/sbom-action ou Syft) | Artefact `sbom.cdx.json` téléchargeable sur le dernier run. Le pilote Postgres ajouté par AP-dep y apparaît | S | 🤖 | Lien dans le README (Technical) |
| **CH-8** | **CodeQL** (Python et JavaScript), non bloquant | `conformite/codeql` (ou *default setup* via CH-1) | `.github/workflows/codeql.yml` | Premier scan terminé. **0 alerte « high » ou « critical » ouverte sur `backend/app/agent_poe/`** au gel du code. Les autres alertes sont listées | S, plus M de tri | 🤖 · 👤 décision sur les alertes du code existant (corriger après le hackathon) | Badge et phrase dans le README (Technical) |
| **CH-9** | **OpenSSF Scorecard** et son badge | `conformite/scorecard` | `.github/workflows/scorecard.yml` (ossf/scorecard-action, `publish_results: true`), badge dans le README | Score publié sur scorecard.dev. Les corrections rapides (permissions en lecture seule, actions épinglées) sont faites si elles ne touchent pas le chemin critique | S, plus S de corrections | 🤖 · ⚙️ protection de la branche par défaut (Clément) | Badge (Technical) |
| **CH-10** | **Couverture des tests de l'agent** | Intégrée à **AP-ci** du plan maître (job CI de l'agent) | `backend/requirements-dev.txt` ou l'équivalent (`pytest-cov`), et le job CI : `pytest backend/tests/test_agent_poe_*.py --cov=backend/app/agent_poe --cov-report=term --cov-report=xml` avec un résumé dans `$GITHUB_STEP_SUMMARY` | Pourcentage affiché dans le résumé CI et recopié dans le README (**mesuré, pas promis**) | S | 🤖 | Technical (« reliability ») |
| **CH-11** | **Fiche de gouvernance IA de l'agent** `docs/AI_GOVERNANCE.md` : modèles et endpoints exacts, `reasoning_effort: "none"`, règle « pas de citation, pas d'entrée », contrôles humains (Toloka, opérateur), journalisation, données envoyées aux modèles, classification AI Act (pas de haut risque visé, **transparence de l'art. 50**), limites (lien vers `FAILURES.md`) | Avec **AP-readme** (périmètre de l'agent) | `docs/AI_GOVERNANCE.md` (ou `backend/app/agent_poe/AI_GOVERNANCE.md`), lien depuis le README | Chaque affirmation renvoie à un fichier ou à un test du dépôt | M | 🤖 · 👤 validation | **Track 01 ou 02 (« explain why »)**, Impact, Product & UX : l'agent dit d'où vient chaque fait et qui l'a vérifié |
| **CH-12** | **Marquage AI Act des sorties de l'agent** (art. 50.2 et 50.4) : champs lisibles par machine dans `poe_gold` et dans l'export JSON (`ai_generated`, `model_id`, `generated_at`, `human_verified` avec un rôle et non un nom, `evidence_quote` déjà prévu). Un test vérifie qu'aucune ligne Gold n'est publiée sans ces champs | Dans **AP-gold** et **AP-rec** (périmètre de l'agent) | `backend/app/agent_poe/gold.py` (schéma), `reconciler.py`, `backend/tests/test_agent_poe_ai_marking.py` | Test vert. Un export JSON montre les champs. Le dossier texte de plus de 200 jetons est documenté : le code de bonnes pratiques de la Commission prévoit un filigrane, que l'association ne peut pas apposer seule (question au fournisseur à poser **après** la fenêtre). L'exemption art. 50(4) liée à la revue humaine est documentée dans CH-11 | M | 🤖 · 👤 validation du schéma par Clément (décision 9 « pas de Gold sans citation » inchangée) | **Innovation** et Impact : « Généré par IA, prouvé par une citation, vérifié par un humain », lisible par machine |
| **CH-13** | **Badge IA sur la carte Gold** (la vue UI du plan maître, AP-ui) : « Généré par IA (NVIDIA Nemotron) · vérifié par : opérateur / Toloka 3/3 », en FR et en EN, avec un lien vers la citation | Dans **AP-ui** | Le composant de la carte Gold, les fichiers i18n BI | Visible sur la carte. Test Playwright ou test unitaire de rendu | S | 🤖 | **Product & UX** et **Demo** : environ 10 s dans la vidéo |
| **CH-14** | **Tests adverses de l'agent** : injection de prompt *indirecte* dans les pages et PDF lus par le VL (« ignore previous instructions… »), invention de chiffres, fuite de consignes, boucle `run_sql` qui tenterait autre chose qu'un SELECT. **promptfoo** pour les cas ciblés de l'agent, **garak (NVIDIA)** pour quelques sondes génériques sur l'endpoint Nemotron. Ces deux outils sont open source et gratuits. **Seulement sur l'API NVIDIA gratuite** (`integrate.api.nvidia.com`, endpoint principal du plan maître), avec un nombre d'appels plafonné. **Pas de repli payant** (Token Factory ou autre) : si le quota gratuit est épuisé, on s'arrête et on consigne ce qui a tourné | Avec **AP-evals** | `evals/redteam/promptfooconfig.yaml`, `evals/redteam/cases/*.html|pdf` (pages piégées locales), `evals/redteam/README.md`, résultats dans `FAILURES.md` | Au moins 10 cas exécutés, avec le résultat réel consigné (réussi ou échoué) **sans maquillage**. Le garde-fou SELECT-only est prouvé par un test. Le nombre d'appels est noté, à 0 € (API gratuite) | M | 🤖 · 👤 accord sur le plafond d'appels (API NVIDIA gratuite uniquement) | **Technical** (fiabilité), **Sponsor tech** (garak est un outil NVIDIA), lien avec la piste 02 |
| **CH-15** | **Section README « Responsible AI & Security »**, **une slide « Trust »** et **une ligne dans le formulaire** (« hygiène et conformité du produit préexistant, faites pendant la fenêtre, PR `conformite/*` » d'un côté, « marquage et tests adverses de l'agent, nouveau travail » de l'autre) | Avec **AP-readme** | `README.md`, deck, formulaire | Chaque élément renvoie à une preuve (un lien vers un run, un fichier, un test) | S | 🤖 rédaction · 👤 validation et soumission (Clément) | Toutes les catégories. Honnêteté sur ce qui préexiste (règle 04) |
| **CH-16** *(NAVIGUIDE, hors notation GenAI)* — **probablement fait / à vérifier** (PR #566 « EU AI Act art. 50 transparency (NAVIGUIDE) » ouverte le 17 oct. ; Clément pense que c'est fait ou en cours) | **Simulateur** : phrase visible « Vous échangez avec un assistant d'IA (NVIDIA Nemotron)… Ne convient pas à la navigation », étiquette « Texte généré par IA », champs JSON `ai_generated`/`model`/`generated_at` dans les réponses du serveur, et test Playwright | `conformite/naviguide-ai-act-art50` (dépôt NAVIGUIDE si la séparation est faite, sinon le mono-dépôt) | `naviguide-simulator/src/i18n/fr.js`, `en.js`, le composant du chat ou du briefing, `naviguide-simulator/server/main.py` (réponses), un spec e2e | Phrase et étiquette visibles dans les modes Suivre et Simulation. Spec vert. Champs présents dans le JSON | M | 🤖 · 👤 Clément vérifie la PR #566 (phrase visible, spec vert) et la fusionne ; plus de créneau planifié | **À ne pas présenter aux juges GenAI.** Utile pour les juges Nebius (du 1er au 15 déc.) et pour l'échéance AI Act |

**Schedule (Toronto), adjusted to the critical path:**

| When | CH tasks | Conflict check / adjustment |
|---|---|---|
| Wed 21 Oct **20:45** (after Toloka deploy 20:00–20:15 and G0/tag 20:15–20:45) | CH-1 GitHub settings (10 min, Clément) | **Moved** from 20:05 in the source doc: it collided with the Toloka cost "yes" + deploy (D24) and the G0 tag. |
| Wed 21:00 → Thu 08:00 | 🤖 opens CH-3, CH-4; read-only triage of CH-1 alerts | No conflict (parallel agent). |
| Thu 22, 14:00–16:00 | Clément merges CH-3/CH-4; **CH-2** key rotation if alerts appeared | **Constraint**: do not rotate the NVIDIA or Zetaris keys while the VL review (until ~10:00) or Zetaris G2 (14:00–16:00) needs them; rotate after 16:00, update `.env` himself. Toloka item: the source doc's "Toloka Thu 7–10" slot is obsolete (D24). |
| Fri 23, 08:00–16:00 | CH-6 `DATA_SOURCES.md`, CH-11 first draft | No conflict. |
| — | **CH-16** (NAVIGUIDE simulator): **likely done / to verify** (PR #566 open) | Not scheduled; Clément checks and merges #566 when convenient; outside the GenAI critical path. |
| Fri 23 evening | CH-5 `security.txt` PR + Clément deploys nginx (5 min) | No conflict. |
| Sat 24, 08:00–13:00 | CH-7 SBOM, CH-8 CodeQL, CH-9 Scorecard (non-blocking) | Watch CI minutes: the pytest job already takes 30+ min; keep these workflows non-required. |
| Sat 24, 13:00–17:00 | CH-12 schema **designed** + validated by Clément (15 min) | Overlaps AP-agentic; design only, 15 min of Clément. |
| Sun 25, 08:00–12:00 | CH-12 coded with `gold.publish` v1 + `test_agent_poe_ai_marking.py` | Same block as AP-gold: if gold v1 slips, CH-12 slips with it (never the reverse). |
| Sun 25, 12:00–19:00 | CH-14 promptfoo + garak, free NVIDIA API only, capped calls | No overlap with the H-MEM block (08:00–11:00 Toronto); stop if the free quota is hit (no paid fallback). |
| Mon 26, 08:00–18:00 | CH-14 results → `FAILURES.md`; CH-10 coverage (with AP-ci); CH-13 AI badge (with AP-ui) | Feature freeze 18:00 Toronto applies to CH too. |
| Mon 26, 18:00–23:00 | CH-15 README "Responsible AI & Security", "Trust" slide, form line; CH-11 final | Docs only, after freeze: OK. |
| Tue 27, 06:00–08:00 | Verification only; **no new CH PR after 08:00** | — |
| Tue 27, 08:00–15:00 | ~10 s of video (Gold card + AI badge), Trust slide, form | Video time goes first to Zetaris + Meterless. Submit before 16:00. |


---

## 4. All planned BI improvements (consolidated)

Effort: S < ½ day, M ½–2 days, L > 2 days. Criterion = the judging criterion helped (I Impact, T Technical, N Innovation, D Demo, U Product & UX, S Sponsor tech), or "—" for hygiene.

### 4.1 Agent (new work, in-hackathon)
| Id | Item | When | Effort | Criterion |
|---|---|---|---|---|
| AP-skel | `agent_poe/` skeleton + `TabConfig` | 22 Oct | S | T |
| AP-zetaris | SELECT-only client + CSV of 5 zones + datasource registration | 22 Oct | M | S, T |
| AP-gold | Gold Postgres, `poe_gold` INSERT-only versioned (Method A); Method B test | 22, 25 Oct | M | S, T |
| AP-vlgate | VL URL review run in parallel to Toloka (not a gate, D24); feeds the agreement table | 22 Oct | S | T, S (NVIDIA) |
| AP-toloka | v2-beta URL batch (23 items), aggregation, controls, `toloka_answers` | 22–24 Oct | M | I, T |
| AP-vl | VL extraction of official PDFs with mandatory quote + text fallback | 23 Oct | M | T, N, NVIDIA prize |
| AP-hmem | H-MEM contract in Python (store, retrieval, layers, trust) | 22–25 Oct | M | S, N |
| AP-hmem-ts | TS adapter + official conformance scorecard | 25–26 Oct | S–M | S, T |
| AP-rec | Nemotron Super reconciler with proofs | 24 Oct | M | I, T, N |
| AP-agentic | Nemotron tool-calling loop over `run_sql` (new proposal) | 24 Oct | S–M | S, N, Track 01 fit |
| AP-tests | `test_agent_poe_*.py` (S2 §8 + reasoning_effort check + no-Mongo-write check) | daily | M | T |
| AP-ci | CI job running the agent tests | 26 Oct | S | T |
| AP-ui | Read-only Gold card (proofs, version, Toloka agreement) | 26 Oct | S–M | U, D |
| AP-evals | `evals/` (~20 cases from the stable polygons) + `FAILURES.md` | 26 Oct | S | T, D |
| AP-tabs | `TabConfig` marinas / AMP / harbour masters (design) | 25 Oct | S | N |
| AP-hm-poc | Harbour-master POC (one document) | 25 Oct if G4 | M | I |
| AP-readme | README, slides, video, optional `metadata.json`, pre-existing declaration | 26–27 Oct | M | D, S, all |
| AP-hmem-bonus | Dreaming / SleepCycle; Markovian / World Model cited only | 26 Oct if time | M | N |
| AP-route | Reconciler on 1–2 route zones validated by Toloka | 26 Oct if time | S | I |
| AP-dep | Add a Postgres driver to `backend/requirements.txt` (none today) | 22 Oct | S | T |

### 4.2 BI product (from S5 inventory and Clément's verdicts, ideas 14–44)
| Item | Status on `main` | When | Effort | Criterion |
|---|---|---|---|---|
| Protect harbour-master data, never wipe or overwrite with empty values (PR #552, Dileep), extend to all tabs | not done (PR closed: conflict markers) | post | M | — |
| Report a port of entry button + API + moderation (PR #146) | UI only, not wired | post | M | — |
| Verify fiche links (PR #227; 20/194 broken on 21 Sept) | not done | post (could feed AP-vlgate later) | M | — |
| Parallel TD ∥ BU search per `mrgid` | not done | post | M | — |
| Auto-refresh of fiches, non-blocking then re-enabled (off since #221; cap 10 vs CDC 60) | partial | post | M | — |
| UN/LOCODE as a signal (WPI snapshot has no LOCODE) | partial | post | S–M | — |
| Query translation with opus-mt (today a static matrix) | not done | post | M | — |
| OSM reliability filter or score on the map | not done | post | S | — |
| Projects ↔ formalities cross-link (Clément: "bof") | not done | post, low priority | M | — |
| One Formalities queue (remove the API `poe` kind, orphan `PoeFiche.js`) | partial | post | S | — |
| Science / Climatology review tabs (Clément says done; S5 says placeholders) | **to verify** | post | — | — |
| Seamark objects: lights, rocks, wrecks, restricted areas | candidates only | post | M–L | — |
| NOAA lights/buoys beyond level 1 | partial | post | M | — |
| Projects: several sites, HQ vs visitable site, multi-point, manual publish (route returns 501) | not done / partial | post | L | — |
| Real user accounts | **rejected by Clément** | never | — | — |
| Backend pytest in CI | PR #561 open | before 22 Oct or post | S | T (if pre-existing) |
| Update stale docs (CDC PoE §9.3, ETAT, CDC Review §18, plan §1) | not done | the plan's §1 now; others post | S | — |

### 4.3 Hygiene and performance (audit S4 + AU lots S5)
| Item | Status | When | Effort |
|---|---|---|---|
| AU1: fix the 3 `deploy_ai.py` (NAVIGUIDE side) | PR #557 open; still broken on `main` | before 22 Oct or post | S |
| AU2: ruff F401 on `backend/app` (check whether "unused" imports are meant for later, per Clément) | PR #557 | before 22 Oct or post | S |
| AU3: one `route.geojson` (the duplicate is still identical on `main`) | not done | post (after the split, choose the right file) | S |
| AU4: recette captures to WebP | **done** (#559, 291 WebP, 0 JPG in `docs/recette`) | — | — |
| AU5: wind files in float16 (85 MB today on `main`) with a tolerance test | not done | post | S |
| Group the `import_*_geojson` functions | not done | post | M |
| spaCy census before any removal | not done | post | S |
| Pin versions in the 7 requirements files | not done | post | S |
| Parametrise repetitive tests | not done | post | M |
| Audit phase 0 (baseline: pytest, Playwright, p50/p95, bundle) | not done | post | M |
| Phase 1 (`ruff --fix`, no logic change) | not done | post | S |
| Phase 2 (dead code: vulture, knip, depcheck) | not done | post | M |
| Phase 3 (heavy data: EEZ GeoJSON 2 × 18 MB → PMTiles/FlatGeobuf, npz external/LFS, history rewrite **only with explicit approval**) | not done | post | L |
| Phase 4 (N+1 Mongo → `$in`/bulk: `review_queue.py:216` and others; one map engine; CRA → Vite) | not done | post | L |
| Phase 5 (docs: archive dated plans, English, MkDocs, docstrings 42 % → 70 %) | not done | post | M–L |

### 4.4 Shared / both projects
Split + VPS repoint (P9), doc sorting (D0), Contabo for NAVIGUIDE, OVH Ubuntu 25.04 → LTS, AU lots after the split, the "big jobs" (one map engine, Vite, a single source of NAVIGUIDE agents, climatology on demand, a docs site), which Clément now thinks can be done "with a well-designed batch". **All post-hackathon.** NAVIGUIDE items (Globe 3D G0–G7, voice, VL around the boat, RJ1/RJ2, weather chain…) are out of this plan.

---

## 5. Scoring map and sponsor-tech evidence

### 5.1 Rules that shape the deliverables (event page, 17 Oct)
- Rule 04: work committed before 22 Oct 00:00 UTC is not eligible, except clearly declared pre-existing components.
- Rule 05: integrate Zetaris **and** Meterless; use Cursor for development; NVIDIA wherever it contributes; declare pre-existing product code in the form.
- Rule 06: video 1–4 min (main workflow, how the agent solves the challenge, key features, **how Zetaris and Meterless are integrated**); slide deck (problem and users, solution, workflow/architecture, stack, Zetaris and Meterless use, what is unique, product visuals, future enhancements); GitHub repo + README (setup, usage, dependencies); explanation of Zetaris/Meterless/Cursor/NVIDIA.
- Rule 07: Impact 30, Technical 20, Innovation 15, Demo 15, Product & UX 10, Sponsor tech 10; at least 3 judges; ties → Impact, then submission time.
- Rule 03: one primary track, changeable until the deadline; cross-track relevance is not scored twice.
- Rule 01: 16+, one account per participant (duplicates disqualify the whole team); organizer/judging-sponsor employees not eligible for cash.
- Rule 02: 1–5 members; the team locks when the first submission is created; one team per participant.
- Rule 08: cash split equally unless the team submits another split in writing; paid by bank transfer within 30 days.
- Rule 09: teams keep all rights; licence to the organizer (and the sponsor for sponsor-track submissions) to show demo, screenshots and description.
- Rule 10: schedule changes announced on the page and in Discord; disqualification final, reason sent to the team lead.
- Full brief with quotes, sources and discrepancies: §0.5.

### 5.2 Deliverable → points
| Criterion (pts) | What earns it |
|---|---|
| Impact 30 | A named user (the Berry-Mappemonde skipper and operator), the real voyage route (Toloka on route EEZs), a before/after story (fragmented gazettes → one cited sheet; the before/after time is **to be measured**, not claimed), metrics on 5 zones |
| Technical 20 | Tests + CI green, hermetic mocks, INSERT-only versioned Gold, H-MEM conformance scorecard, fallbacks (VL → text, replay from cache), `FAILURES.md` |
| Innovation 15 | "No quote, no entry", a crowd check on *evidence URLs*, memory of good sources with trust from humans, Nemotron writing its own Zetaris SQL, one chain configured for 4 tabs |
| Demo 15 | 1–4 min video following the shot list: Zetaris sources → VL quote → reconcile (one confirmed, one conflict) → Toloka task + agreement → `poe_gold` version → H-MEM recall + scorecard |
| Product & UX 10 | Gold card in the existing map UI; plain-language statuses; FR/EN labels (i18n exists) |
| Sponsor tech 10 | §5.3 checklist |

### 5.3 Sponsor-tech evidence checklist (video + slides + README)
- **Zetaris**: the five source tables registered; the gold Postgres registered as a datasource; one federated join live; `run_sql` tool calls by Nemotron; Method B result (works or not, said honestly).
- **Meterless**: H-MEM in Python, citing `github.com/Meterless/Meterless` `engines/hmem` (Apache 2.0); recall on screen; **green conformance scorecard**; Markovian / World Model cited as not used on the filmed path. If the HackOS task board provides a Meterless model endpoint (C20), Nemotron calls also go through Meterless and the video shows it.
- **Cursor** (also for "Best use of Cursor-built product"): all new code written in Cursor; commit trailers or branch names showing Cursor agents; the `.cursor/rules` used; one screenshot of an agent session (no secrets visible).
- **NVIDIA** (also for "Best use of NVIDIA Nemotron"): exact model ids (`nvidia/nemotron-3.5-super-vl-120b-a12b`, `nvidia/nemotron-3-super-120b-a12b`), the endpoint, `reasoning_effort: "none"` and why, token counts per zone, VL on a real scanned or PDF page.
- **Toloka** (not a sponsor): overlap 3, controls, agreement rule, cost forecast vs actual.

---

## 6. Risks, decision log, open questions

### 6.1 Risks and mitigations
| Risk | Likelihood | Mitigation / fallback |
|---|---|---|
| Toloka still on trial on 22 Oct 00:00 UTC | Medium-high | P1 this weekend, P2 Monday as backup; deploy the moment verification lands; F-TOL only if no answers by 25 Oct 12:00 UTC |
| Batch built from pre-existing data seen as graded work done early (rule 04) | Low | Build/upload only before; **deploy not before 22 Oct 00:00 UTC**; declare the dataset and its source verdicts as pre-existing in the form |
| Clément not available at 21 Oct 20:00 Toronto | Low | P6b; deploy as soon as he is |
| Toloka answers slow (processing time undocumented) | Medium | Deploy at 22 Oct 00:00 UTC (D24); small batch; the video can show the task + partial answers |
| Unverified pool refused on Quorum (B2) → $12/h | Medium | 11 items (6 + 5 controls) instead of 23 |
| VL 502/429 or empty content | Medium | `reasoning_effort: "none"`; SHA-256 cache; text fallback; Token Factory as a backup endpoint |
| Zetaris cannot reach the gold Postgres (Docker networking) | Medium | `host.docker.internal`; else Option C (versioned CSV registered as a table) |
| Split not finished | Medium | Fallback branch `agent-poe` (decision 12) |
| Mac overloaded (NAVIGUIDE batch + Zetaris in Docker with 8 GB) | Medium | Pause the night batch during the window (S5 phase 0.1) |
| Pre-existing work presented as new (C13) | Low if fixed | Tag + explicit module list in the form |
| Team change not processed before the first submission | Medium | No submission before the change; ask on the 21 Oct call |
| Nebius/NAVIGUIDE deadlines eat the week | Medium | P22 time budget |
| Secrets leak in video or screenshots | Low | `.env` 600; screenshots checked before upload; no terminal with `env` on screen |
| Writing to Atlas or VPS Mongo by mistake | Low | Read-only client + a test forbidding insert/update/delete |
| Judges read "integrate Meterless" as "Nemotron through Meterless" (C20) | Medium | P29 task-board check; ask at the call; H-MEM + green scorecard shown clearly; switch the model route if an endpoint appears |
| Tracks/prizes changed at the 21 Oct call (C24) | Low-medium | P30 re-read; track can change until the deadline |
| Submission draft created too early locks the team without the 5th member | Medium | P31 only after the team change is confirmed |
| Duplicate HackOS account in the team (rule 01) | Low | P24 |
| Form wants a video file, not a link | Low | MP4 kept ready (C22) |

### 6.2 Decision log (16–17 Oct, from S1/S2)
16 Oct: (1) two repos, split by Clément; (2) Zetaris `source = "SqlEditor"`; (3) Toloka EN + translations, overlap 3; (4) no Mongo writes, Atlas frozen, VPS live; (5) track 01; (6) video on YouTube, English, made by Grok Bot; (8) Mayotte then New Caledonia; (9) no Gold row without a quote; (10) H-MEM in Python; (11) AMP through the existing FeatureServer, no bulk download; (12) fallback branch.
17 Oct: (13) Meterless: no API, no key, no credit; (14) TS conformance adapter: we do it; (15) Method A main, B test on the 22nd, C fallback; separate Postgres via `host.docker.internal`; (16) video, slides and README show Zetaris + Meterless integration, Cursor use and the NVIDIA contribution; (17) official grid, ignore the Meterless repo grid (confirmation pending); (18) prizes verified; (19) track 01 preferred (confirmation pending); (20) 5 members, Hamid being replaced; (21) Toloka launched on Day 1, Clément handles it; (22) split after his batch, no code before 22 Oct; (23) organizer contact: hackathons@genai.works bounced; questions **sent 17 Oct 19:38 Toronto** to support@academy.genai.works (thread "Remove a team member and rename our team"), awaiting reply. From S3 (Toloka plan): option B (overlap 3, no LLM review), route-priority EEZs, 23 items.
**17 Oct ~20:15 Toronto, (25) Conformité et confiance (Clément):** §3.8 adopted: CH-1…CH-16, €0, 22–27 Oct on `conformite/*` branches, declared as hygiene of the pre-existing product; never delays submission (PR freeze 27 Oct 08:00, submit before 16:00 Toronto); CH-16 in the NAVIGUIDE simulator (timing to be confirmed by Clément), not shown to GenAI judges; no transfer of rights.
**17 Oct 19:39 Toronto, (24) Toloka ASAP (Clément):** the Nemotron VL check is no longer a gate. The batch (~23 items: 18 priority-1 route URLs + 5 hidden controls, 2 onboarding examples; overlap 3, No QA, ≈ $48 of $50) is built before 22 Oct from pre-existing data only (existing Proposer/auto-review verdicts, read-only candidate export), no new code. Deploy at **22 Oct 00:00 UTC exactly** (21 Oct 20:00 Toronto), after Clément's explicit "yes" on the Cost breakdown. VL runs in parallel on 22 Oct; Toloka vs VL vs Proposer agreement table goes into the video and `evals/`. If verification is late: deploy the moment it lands.
**Proposed today (pending Clément):** C1–C18 resolutions above (C4 and C10 now settled).
**17 Oct ~21:00 Toronto, (26) Rules review (Clément's request):** §0.5 added; registration close taken as 23:45 UTC; HackOS Help desk as the primary question channel; no code on BI before 22 Oct 00:00 UTC (confirmed again); no freeze (see PR #568); CH-16 marked likely done / to verify (PR #566); Clément available 21 Oct 20:00 Toronto for the Toloka cost approval and deploy at 22 Oct 00:00 UTC.

### 6.3 Open questions for Clément (genuinely open)
1. **Toloka**: OK for a single URL-level batch (23 items), with port-level doubts reviewed by you as operator? Or will you top up the balance for a second, port-level batch?
2. **Zones**: Toloka on the route EEZs (+ Mexico/Niue controls) while the reconciler demo stays on the 5 zones. Agreed? Add 1–2 route zones to the reconciler if time allows?
3. **VL endpoint**: NVIDIA free API as primary and Token Factory as backup (recommended), or Token Factory first?
4. **Candidate export (P4)**: from the VPS with your admin key (recommended), or from Atlas (frozen stock of 10 Sept)?
5. **Pre-window PRs** (#557, #561, split docs, NAVIGUIDE fixes): merge before 22 Oct 00:00 UTC, or after 27 Oct?
6. **Split**: will it be done before 22 Oct 00:00 UTC, or do we plan directly on the fallback branch?
7. **5th member**: who, and with which role? (They must register before 22 Oct 23:59 UTC.)
8. **Product & UX**: is a small "Gold" card in the existing Formalities/Review screen the right surface, or do you want a separate agent page?
9. **Screenshot hosting** for Toloka (public HTTPS outside the repo): where?
10. **Are the 11 "stable" polygons certified Gold** in `review_gold` on the VPS? (Their exact URLs serve as controls.)
11. **CH-16**: is the AI notice in the NAVIGUIDE simulator done? PR #566 is open; verify and merge it, then CH-16 is closed.
12. **Meterless route (C20)**: if the HackOS task board offers a Meterless credit/endpoint, do we also route Nemotron through Meterless (recommended as a hedge), or stay on NVIDIA's free API only?
13. **Prize split (rule 08)**: equal split among the 5 members (default), or a written split (e.g. to the association)?
14. **Submission timing**: if the form can be edited after submitting, submit a complete version before 27 Oct 00:00 UTC (judging opens) and update later?

### 6.4 Organizer questions (✅ SENT 17 Oct 19:38 Toronto, text below for the record)
**To:** support@academy.genai.works (thread "Open Agent Hackathon 2026 – Remove a team member and rename our team"), and/or the same text in HackOS `#general-admin`.
**Subject:** Re: Open Agent Hackathon 2026 – two rules questions (track for a declared pre-existing project; judging grid)
> Hello GenAI.works team,
>
> Two short questions in addition to our team request. hackathons@genai.works, listed in rule 10, bounced on 17 October, so I'm writing here.
>
> 1. Our project, Blue Intelligence, has a pre-existing platform that we will declare in the submission form (rules 04–05). Is it fine to submit under Track 01 "Solving Fragmented Intelligence", with only the new agent work scored? Or should a declared pre-existing project go to the Wildcard [Tinkerer] track?
> 2. The Meterless repository (docs/community/hackathon-guide.md) and meterless.ai show a different judging grid and older dates. We assume the event page applies (rule 07: Impact 30, Technical 20, Innovation 15, Demo 15, Product & UX 10, Sponsor tech 10; window 22–27 October). Can you confirm?
>
> Thank you,
> Clément Filisetti, President, Association Berry-Mappemonde (team lead)

---

## 7. After the hackathon (from 28 Oct)

| When | Item |
|---|---|
| 28–31 Oct | Toloka: final export, controls report, spend vs forecast; check whether the promo credit expires on 4 Nov |
| 28 Oct → | Mirror Toloka signals and Gold rows into the product (`review_suggest` / `review_gold` → `poe_ports` through the existing human Gold flow: "no live without Gold, no silent Gold") |
| Nov | Rajesh / Bespoke: quote for the full referential (285 polygons, wave 1 EN/FR/ES), compared with self-service |
| 30 Oct | NAVIGUIDE final submission (Nebius × NVIDIA) |
| 6 Nov 11:00 Toronto | Results; post a recap to the team (with approval) |
| Nov | Finish the split if it used the fallback branch; archive the old repo once the 8 tests are green |
| Nov–Dec | Audit phases 0–5 and the AU lots, in order, one branch per phase, CI green, tag `baseline-…` first; history rewrite only with explicit approval |
| Nov–Dec | BI product backlog of §4.2: #552 data protection (all tabs), #146 PoE report + moderation, #227 link checker, auto-refresh, TD ∥ BU, LOCODE, opus-mt, seamark objects |
| Dec | Generalise the agent to harbour masters (full), then marinas, then AMP verification; climatology stays separate |

---

## 8. Diff list for `docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md` (proposed, not applied)

1. **Header and §1 (line 23)**: replace "`Blue-Intelligence-Map` (1,249 commits)" with "`Berry-Mappemonde/Blue-Intelligence` (`-Map` redirects to it), 1,401+ commits on 17 Oct; the split creates the BI repo". Pre-existing = everything up to tag `pre-hackathon-2026-10-22`.
2. **Line 15, §1.2 `poe_seed_enrich.py` row, §1.6**: the full-catalogue text reading (§6.3) is **pre-existing** (`judge_one` → `harvest_bu_catalog` + `remember_seed_urls`). New = VL page reading with mandatory quote, cited reconciliation, H-MEM, Toloka, `poe_gold`, Zetaris.
3. **§1 line 21**: "`review_gold` holds 0 documents" → "0 on Atlas on 16 Oct; live VPS count unverified".
4. **§3.1 table**: add `vl_extractor.check_url()` (VL URL review, parallel to Toloka, not a gate: D24); `toloka_task.py` → "Toloka platform v2-beta (pipelines, Quorum node), URL-level items, `itemLimit` from budget (23)" instead of "classic API, cap 30"; add an `agent.py` tool loop (`run_sql` called by Nemotron, SELECT-only, bounded); note the Postgres driver dependency to add.
5. **§3.2**: add "`core/nvidia.py::generation_extras()` returns `{}` for Nemotron: the agent passes `reasoning_effort: "none"` explicitly; a test checks it." Add the endpoint choice (NVIDIA free API primary, Token Factory backup) once Q3 is answered.
6. **§4.1**: add the table `toloka_answers` (gold Postgres): `item_id, mrgid, url, labels[], annotator_ids[], agreement, consensus, escalate, run_id, is_control, control_pass`. `poe_gold.toloka_status` values → `not_sent`, `url_validated`, `url_rejected`, `operator_review`.
7. **§5.3**: replace the port-level task with the S3 URL-level item schema (visible vs hidden fields, 6 labels, `evidence_quote`, `applies_to_polygon`) and the 3/3 / 2/3 / 1/1/1 rule; port-level doubts → operator review.
8. **§7**: add "Toloka set": 18 priority-1 route EEZs (S3 §3.1) + 5 hidden controls (Venezuela 8433, Sint-Maarten 21803, Mexico 8429, Niue 8447 with the NZ 8455 page, Western Sahara 8368) + 2 onboarding examples (Mayotte, New Caledonia). The reconciler demo stays on the 5 zones.
9. **§8**: add tests for the VL URL review, `toloka_answers` aggregation (arrays shorter than 3), the explicit `reasoning_effort`, and "no Mongo write" for Toloka results.
10. **§9 schedule**: replace Day 22 with the hour blocks of §3.1 (cost gate + deploy at 00:00 UTC, D24; VL review in parallel; Zetaris afterwards); remove "mini test batch" (→ Self-check on 19 Oct) and "second small batch on the 25th" (→ only if the balance is topped up); add gates G0–G4, the agentic step on the 24th, the UI card on the 26th, and code freeze 12:00 UTC / submit 20:00 UTC on the 27th.
11. **§9 risk table**: drop the Tavily dependency; add the Toloka trial (B1), unverified-pool pricing (B2), registration close 22 Oct 23:59 UTC for the 5th member, the team lock on the first submission, and the overlap with the Nebius deadlines.
12. **§10 checklist**: add the **slide deck** as a required item with the rule-06 contents; mark `metadata.json` as optional (no schema published); add `evals/` and `FAILURES.md`; sponsor evidence checklist (§5.3 here) including Cursor and NVIDIA prize proofs.
13. **Decision 21** (applied 17 Oct via D24): "Toloka batch on Day 1" → "URL-level batch built before the window from existing verdicts, deployed 22 Oct 00:00 UTC, VL in parallel, 23 items ≈ $48 (forecast), results stored in the gold Postgres (no Mongo write), single batch unless topped up".
14. **Decision 23**: hackathons@genai.works bounced on 17 Oct → contact support@academy.genai.works / HackOS `#general-admin` / Discord `#hackathon-help`; questions sent 17 Oct 19:38 Toronto; ask them at the 21 Oct onboarding call if no reply.
15. **Decision 20**: add "the replacement must register before 22 Oct 23:59 UTC; do not create a submission before the team change is done (rule 2)".
16. **New decision rows** for C1–C9 and C12 once Clément confirms Q1–Q4.
17. **§2**: the split status on 17 Oct (not done; no NAVIGUIDE repo yet), and the fallback branch name `agent-poe`.
18. **`docs/HACKATHON_PLAN.md`**: its link text still says "the `Blue-Intelligence-Map` mono-repo"; update after the split.
