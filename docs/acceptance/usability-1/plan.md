# Usability session 1 · plan (template)

Card: IMP-611 (US-142, NFR-027). Lead: Junaid. Findings: Krrish ([findings.md](findings.md)).

Status: **template, not yet run.** Nothing in this file is a result. Results are entered by the members after the real sessions, in `findings.md` only.

## Goal

Check first-use success (NFR-027: at least 4 of 5 participants finish the core journey within 10 minutes) and find the problems that stop or slow a first-time traveller. Record what participants did (task completion, errors, time), not only what they said.

## Set-up

| Item | Value |
| --- | --- |
| Environment | Staging (Gemini provider), during a staging window |
| Participants | 5, coded P1 to P5 |
| Accounts | Team-made test accounts, one per participant; never the participant's own e-mail |
| Data | SAMPLE or curated destinations only |
| Roles | One moderator (reads the script, does not help), one note-taker (fills the observation sheet) |
| Length | About 20 minutes per participant |
| Device | Laptop browser; note the browser and screen size per session |

## Privacy (IMD-185)

- Participants are identified only by their code P1 to P5. No names, contacts, photos, recordings or other identifying details are written here, in `findings.md`, in issues or in commits.
- No screen or audio recording unless the team agrees a separate decision first.
- Test accounts are deleted after the session (or reset with the account-deletion flow).

## Consent wording (read aloud before starting)

> Thank you for helping. We are testing the app, not you; there are no wrong answers. We will watch how you use it and take notes on what happens. We will not write down your name or anything that identifies you; you will only be called by a code such as P1. The account you use is a test account made by us. You can stop at any time without giving a reason. Is it all right to start?

Record only "consent given: yes / no" against the code. If no, do not run the session.

## Script

Read each task exactly as written. Do not explain the interface. If the participant is stuck for 2 minutes, mark the task "not completed" and move on.

| Task | Instruction read to the participant | Success means |
| --- | --- | --- |
| T1 | "Sign in with the account on this card." | Dashboard visible |
| T2 | "Plan a 3-day trip to <destination> for two people with a medium budget." | Trip created and generation started |
| T3 | "Wait for your plan, then tell me what you will do on day 2 in the afternoon." | Participant finds and reads day 2 items |
| T4 | "Move one activity from day 1 to day 2." | Edit saved (plan revision changes) |
| T5 | "Find out how much the whole trip is estimated to cost and what is not included." | Costs page found; participant names a label or exclusion |
| T6 | "Find a place you would like to add and look at its details." | Explore page and place details opened |
| T7 | "Save the current plan as a version, then find the trip summary you could print." | Version saved; summary page opened |

## Observation sheet (one per participant, copy for P1 to P5)

| Field | Entry |
| --- | --- |
| Participant code | |
| Consent given | |
| Browser and screen size | |
| Start time / end time | |

| Task | Completed (yes / no / with hint) | Time (mm:ss) | Errors or wrong paths observed | Quote or behaviour (no identifying details) |
| --- | --- | --- | --- | --- |
| T1 | | | | |
| T2 | | | | |
| T3 | | | | |
| T4 | | | | |
| T5 | | | | |
| T6 | | | | |
| T7 | | | | |

## After the sessions

1. Copy each observed problem into the finding table in `findings.md` with its participant code(s) and severity.
2. Triage: create one GitHub issue per finding of severity 1 or 2, with a label and an owner; link it from `findings.md`.
3. Feed the top issues into IMP-704 (usability session 2).
4. No result is reported that was not observed.
