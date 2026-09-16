# Rules of Engagement (RoE) — DRAFT

**Project:** RiskIntern PhishSim — AI-assisted, role-oriented phishing-awareness simulation
**Status:** Draft v0.1 (Week 1 deliverable) — requires sign-off before any non-synthetic execution
**Document owner:** _TBD_  ·  **Approver(s):** _TBD_  ·  **Date:** _TBD_

> This is an academic prototype. By default it runs entirely on **synthetic data** in **mock mode** and sends no
> real email. This RoE governs the conditions under which any real recipients could ever be involved. Until every
> section below is completed and signed, the project remains synthetic-only.

## 1. Purpose and scope
- **Purpose:** Measure and improve organizational resilience to targeted phishing through authorized, non-punitive simulation.
- **In scope:** Synthetic personas and context; scenario generation; a fully isolated landing/simulation sandbox; aggregated analytics.
- **Out of scope:** Real malware or payloads; credential capture/storage; exploitation of any live system; targeting individuals for evaluation or discipline; any channel or recipient not explicitly authorized here.

## 2. Authorization
- Every campaign runs **only** under a signed authorization referencing this RoE.
- Named authorizing party (role/title): _TBD_.
- Authorized target population (department/role/group): _TBD_ — **synthetic dataset only** for the prototype.
- Authorized time window: _TBD_.
- Authorized sending domain(s): must be listed in `AUTHORIZED_EMAIL_DOMAINS`; the SMTP provider rejects all others.

## 3. Rules and constraints
- **Data minimization:** only attributes required for the simulation (role, department, language, coarse risk signals) are processed; PII is pseudonymized where possible.
- **No harm:** no real payloads; all interaction stays inside the isolated sandbox landing page.
- **No credential handling:** the simulation never needs a real password. Any value submitted to the event endpoint is **discarded immediately** — never stored, hashed, logged, forwarded, or placed in metadata. Only a binary "interaction occurred" event is recorded.
- **Human approval gate:** a generated scenario must be explicitly **approved** before a campaign can launch.
- **Auditability:** all state changes are written to an append-only audit log that excludes secrets.
- **Provider safety:** LLM output passes a safety validator; external SMTP is domain allow-listed; GoPhish is limited to pre-created, authorized resources.

## 4. Prohibited actions
- Using real employee data without written authorization and a completed data-handling review.
- Sending to any recipient/domain not in the authorized list.
- Storing, transmitting, or attempting to recover submitted credential values.
- Using results to identify, rank, or penalize named individuals.
- Enabling any real-delivery provider (`EMAIL_PROVIDER`/`CAMPAIGN_PROVIDER`) before sign-off.

## 5. Communication and escalation
- Primary point of contact: _TBD_.
- Escalation path for incidents or accidental real-recipient contact: _TBD_.
- Stop condition: any participant distress, scope breach, or safety-control failure → **halt immediately** and notify the owner.

## 6. Participant care (non-punitive principle)
- Results are used for **systemic awareness**, never individual blame.
- Participants receive a **debrief** after the campaign explaining the purpose and the safe design.

## 7. Data handling and retention
- Storage: PostgreSQL (synthetic data for the prototype).
- Retained: personas, risk factors, interaction **events** (type + timestamp only), aggregate analytics, audit log.
- Never retained: credential values, message content beyond the generated scenario, real PII beyond authorized minimum.
- Retention period / disposal method: _TBD_.

## 8. Reference frameworks
MITRE ATT&CK T1566 (Phishing); OWASP awareness guidance; standard penetration-testing Rules of Engagement methodology.

## 9. Sign-off
| Role | Name | Signature | Date |
|---|---|---|---|
| Project owner | | | |
| Authorizing party | | | |
| Data/privacy reviewer | | | |

_This draft was produced in Week 1. Fields marked TBD must be completed and the table signed before any execution beyond synthetic mock mode._
