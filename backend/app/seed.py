"""Synthetic demo seed.

Runs only on an empty database. Personas come from the HR data layer; a few
demo campaigns are generated through the shared prompt-template layer (offline,
no LLM/SMTP calls) with varied interaction events so every dashboard chart is
populated on first load.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from .db import SessionLocal
from .models import Employee, Scenario, Campaign, CampaignTarget, InteractionEvent, ScenarioStatus, CampaignStatus
from .services import sync_from_hr, recalc_risk, ensure_context, assess_quality
from .llm.prompts import render_scenario, normalize_language

# email, difficulty, days-ago, [(event_type, minutes-after-delivery)]
DEMO = [
    ("aylin.mammadova@demo.example.com", "medium", 3,
     [("email_opened", 3), ("link_clicked", 7), ("credential_simulation_submitted", 9), ("simulation_reported", 40)]),
    ("kenan.huseynov@demo.example.com", "easy", 3,
     [("email_opened", 2), ("link_clicked", 4), ("credential_simulation_submitted", 6)]),
    ("elvin.guliyev@demo.example.com", "hard", 2,
     [("email_opened", 5), ("simulation_reported", 8)]),
    ("aysel.valiyeva@demo.example.com", "medium", 2,
     [("email_opened", 4), ("link_clicked", 11)]),
    ("daniel.roberts@demo.example.com", "hard", 1,
     [("email_opened", 6)]),
]


def _now():
    return datetime.now(timezone.utc)


def seed():
    db = SessionLocal()
    try:
        if db.scalar(select(Employee).limit(1)):
            return
        # Personas via the HR adapter (same path the running app uses).
        sync_from_hr(db)
        db.flush()

        for i, (email, difficulty, days_ago, events) in enumerate(DEMO):
            e = db.scalar(select(Employee).where(Employee.email == email))
            if not e:
                continue
            rp = recalc_risk(db, e)
            ctx = ensure_context(db, e)
            payload = {
                "employee": {"full_name": e.full_name, "department": e.department, "role": e.role, "preferred_language": e.preferred_language},
                "risk": {"score": rp.score, "level": rp.level},
                "context": [{"kind": x.kind, "title": x.title, "summary": x.summary} for x in ctx],
                "objective": "Recognize contextual social-engineering cues",
                "difficulty": difficulty,
            }
            data = render_scenario(payload)
            q_score, q_notes = assess_quality(data, payload["context"], normalize_language(e.preferred_language))
            _terminal = any(et in ("credential_simulation_submitted", "simulation_reported") for et, _ in events)
            _status = ScenarioStatus.COMPLETED.value if _terminal else ScenarioStatus.ACTIVE.value
            s = Scenario(employee_id=e.id, status=_status, language=e.preferred_language,
                         objective=payload["objective"], difficulty=difficulty,
                         subject=data["subject"], email_body=data["email_body"], pretext=data["pretext"],
                         landing_page_message=data["landing_page_message"], training_objective=data["training_objective"],
                         risk_indicators=data["risk_indicators"], safety_notes=["Synthetic only"],
                         quality_score=q_score, quality_notes=q_notes, approved_at=_now())
            db.add(s); db.flush()
            base = _now() - timedelta(days=days_ago)
            c = Campaign(scenario_id=s.id, name=f"{e.department} awareness baseline", status=CampaignStatus.ACTIVE.value,
                         provider="mock", provider_campaign_id=f"seed-{i}", started_at=base)
            db.add(c); db.flush()
            t = CampaignTarget(campaign_id=c.id, employee_id=e.id, delivered_at=base)
            db.add(t); db.flush()
            for et, minutes in events:
                db.add(InteractionEvent(campaign_id=c.id, employee_id=e.id, session_id=t.session_id, event_type=et,
                                        occurred_at=base + timedelta(minutes=minutes),
                                        safe_metadata={"credential_submitted": True} if et == "credential_simulation_submitted" else {}))
        db.commit()
    finally:
        db.close()


if __name__ == '__main__':
    seed()
