"""Synthetic demo seed.

Runs only on an empty database. Personas come from the HR data layer; a curated
set of demo simulations is generated through the shared prompt-template layer
(offline, no LLM/SMTP calls) with a balanced spread of outcomes, dates, and
statuses so every tab tells a clear story for a presentation:

  * Archive     — completed runs (reported / submitted) and a rejected draft.
  * Simulations — active runs (clicked / opened, incl. one stale no-response) and
                  a scenario still awaiting review.
  * Analytics   — a populated funnel, risk distribution, and a department/role
                  risk map with real contrast (Management/Finance high, Security low).
  * Training    — a few assigned and completed corrective actions.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from .db import SessionLocal
from .models import Employee, Scenario, Campaign, CampaignTarget, InteractionEvent, ScenarioStatus, CampaignStatus
from .services import sync_from_hr, recalc_risk, ensure_context, assess_quality, derive_topics, assign_training, complete_training
from .llm.prompts import render_scenario, normalize_language

# Outcome shorthand -> interaction events (minutes after delivery). 1.
OUTCOMES = {
    "reported":  [("email_opened", 3), ("link_clicked", 6), ("simulation_reported", 9)],
    "submitted": [("email_opened", 2), ("link_clicked", 5), ("credential_simulation_submitted", 7)],
    "clicked":   [("email_opened", 4), ("link_clicked", 12)],
    "opened":    [("email_opened", 6)],
    "none":      [],
}

# email, difficulty, days-ago, outcome | "review" | "rejected"
DEMO = [
    ("rashad.guliyev@demo.example.com",  "hard",   5,  "submitted"),   # CFO compromised -> critical
    ("leyla.karimova@demo.example.com",  "hard",   6,  "submitted"),   # CEO compromised -> critical
    ("murad.aliyev@demo.example.com",    "hard",   8,  "submitted"),   # SysAdmin compromised
    ("anna.ivanova@demo.example.com",    "medium", 2,  "submitted"),
    ("ramil.jafarov@demo.example.com",   "medium", 11, "submitted"),
    ("viktor.sokolov@demo.example.com",  "hard",   7,  "reported"),    # Security/IT catch it
    ("elvin.guliyev@demo.example.com",   "hard",   1,  "reported"),
    ("narmin.abbasova@demo.example.com", "medium", 3,  "reported"),
    ("aylin.mammadova@demo.example.com", "medium", 5,  "reported"),
    ("sabina.karimli@demo.example.com",  "easy",   9,  "reported"),
    ("tural.ismayilov@demo.example.com", "hard",   6,  "reported"),
    ("gunel.mammadli@demo.example.com",  "easy",   4,  "reported"),
    ("orxan.nabiyev@demo.example.com",   "medium", 4,  "clicked"),     # active, in progress
    ("kenan.huseynov@demo.example.com",  "easy",   3,  "clicked"),
    ("nigar.hasanova@demo.example.com",  "medium", 2,  "clicked"),
    ("aysel.valiyeva@demo.example.com",  "medium", 2,  "clicked"),
    ("kamran.rzayev@demo.example.com",   "medium", 10, "opened"),      # stale: no response in 10 days
    ("daniel.roberts@demo.example.com",  "hard",   2,  "opened"),
    ("farid.baghirov@demo.example.com",  "hard",   1,  "none"),        # delivered, awaiting response
    ("farid.baghirov@demo.example.com",  "medium", 0,  "review"),      # still awaiting human review
    ("aysel.valiyeva@demo.example.com",  "easy",   1,  "rejected"),    # rejected draft -> archive
]

# email, topic, completed?  — populate the Training tab + show the remediation loop
TRAIN = [
    ("murad.aliyev@demo.example.com",   "credential hygiene", True),
    ("kenan.huseynov@demo.example.com", "link inspection",    True),
    ("rashad.guliyev@demo.example.com", "credential hygiene", False),
    ("orxan.nabiyev@demo.example.com",  "link inspection",    False),
]


def _now():
    return datetime.now(timezone.utc)


def seed():
    db = SessionLocal()
    try:
        if db.scalar(select(Employee).limit(1)):
            return
        sync_from_hr(db); db.flush()  # personas via the HR adapter (same path the app uses)

        for i, (email, difficulty, days_ago, kind) in enumerate(DEMO):
            e = db.scalar(select(Employee).where(Employee.email == email))
            if not e:
                continue
            rp = recalc_risk(db, e); ctx = ensure_context(db, e)
            payload = {
                "employee": {"full_name": e.full_name, "department": e.department, "role": e.role, "preferred_language": e.preferred_language},
                "risk": {"score": rp.score, "level": rp.level},
                "context": [{"kind": x.kind, "title": x.title, "summary": x.summary} for x in ctx],
                "objective": "Recognize contextual social-engineering cues",
                "difficulty": difficulty,
            }
            data = render_scenario(payload)
            q_score, q_notes = assess_quality(data, payload["context"], normalize_language(e.preferred_language))
            base = _now() - timedelta(days=days_ago)
            launched = kind in OUTCOMES
            if kind == "rejected":
                status, approved = ScenarioStatus.REJECTED.value, None
            elif kind == "review":
                status, approved = ScenarioStatus.REVIEW_REQUIRED.value, None
            else:
                terminal = any(et in ("credential_simulation_submitted", "simulation_reported") for et, _ in OUTCOMES[kind])
                status, approved = (ScenarioStatus.COMPLETED.value if terminal else ScenarioStatus.ACTIVE.value), base
            s = Scenario(employee_id=e.id, status=status, language=e.preferred_language,
                         objective=payload["objective"], difficulty=difficulty,
                         subject=data["subject"], email_body=data["email_body"], pretext=data["pretext"],
                         landing_page_message=data["landing_page_message"], training_objective=data["training_objective"],
                         risk_indicators=data["risk_indicators"], safety_notes=["Synthetic only"],
                         quality_score=q_score, quality_notes=q_notes, created_at=base, approved_at=approved)
            db.add(s); db.flush()
            if launched:
                c = Campaign(scenario_id=s.id, name=f"{e.department} awareness — {e.full_name.split()[0]}",
                             status=CampaignStatus.ACTIVE.value, provider="mock", provider_campaign_id=f"seed-{i}", started_at=base)
                db.add(c); db.flush()
                t = CampaignTarget(campaign_id=c.id, employee_id=e.id, delivered_at=base)
                db.add(t); db.flush()
                for et, minutes in OUTCOMES[kind]:
                    db.add(InteractionEvent(campaign_id=c.id, employee_id=e.id, session_id=t.session_id, event_type=et,
                                            occurred_at=base + timedelta(minutes=minutes),
                                            safe_metadata={"credential_submitted": True} if et == "credential_simulation_submitted" else {}))
        db.flush()

        for email, topic, done in TRAIN:  # assign (and optionally complete) corrective training
            e = db.scalar(select(Employee).where(Employee.email == email))
            if not e or topic not in derive_topics(db, e):
                continue
            a = assign_training(db, e, topic)
            if done:
                complete_training(db, a)
        db.flush()

        for e in db.scalars(select(Employee)).all():   # reflect seeded outcomes + training in each persona's risk
            recalc_risk(db, e)
        db.commit()
    finally:
        db.close()


if __name__ == '__main__':
    seed()
