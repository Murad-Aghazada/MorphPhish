from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import *
from .risk import calculate
from .adapters.context import MockContextAdapter
from .adapters.hr import get_hr_adapter, FIELDS as HR_FIELDS
from .llm.providers import get_llm_provider
from .integrations.campaign import get_campaign_provider
from .integrations.email import get_email_provider
from .core.config import settings

def simulation_url(session_id): return settings.frontend_url.rstrip('/')+f"/simulate/{session_id}"
def audit(db,action,etype,eid=None,details=None): db.add(AuditEvent(action=action,entity_type=etype,entity_id=eid,details=details or {}))
def recalc_risk(db,employee):
    prior=db.scalar(select(func.count()).select_from(InteractionEvent).where(InteractionEvent.employee_id==employee.id, InteractionEvent.event_type.in_(["link_clicked","credential_simulation_submitted"]))) or 0
    score,level,factors=calculate(employee,prior)
    rp=db.scalar(select(RiskProfile).where(RiskProfile.employee_id==employee.id))
    if rp: rp.score=score; rp.level=level; rp.factors=factors; rp.calculated_at=datetime.now(timezone.utc)
    else: rp=RiskProfile(employee_id=employee.id,score=score,level=level,factors=factors); db.add(rp)
    db.flush(); return rp

def ensure_context(db,employee):
    existing=db.scalars(select(OperationalContext).where(OperationalContext.employee_id==employee.id)).all()
    if existing: return existing
    for kind,title,summary,meta in MockContextAdapter().generate(employee): db.add(OperationalContext(employee_id=employee.id,kind=kind,title=title,summary=summary,metadata_json=meta))
    db.flush(); return db.scalars(select(OperationalContext).where(OperationalContext.employee_id==employee.id)).all()

def sync_from_hr(db, provider_label=None):
    """Import/update employees from the configured HR adapter (idempotent).

    Matches existing employees by external_id, then email. Recalculates risk
    and ensures operational context for every synced persona.
    """
    adapter=get_hr_adapter(); label=provider_label or f"{settings.hr_provider}-hr"
    created=updated=0
    for rec in adapter.list_employees():
        rec={k:rec.get(k) for k in HR_FIELDS}
        e=None
        if rec.get("external_id"): e=db.scalar(select(Employee).where(Employee.external_id==rec["external_id"]))
        if not e and rec.get("email"): e=db.scalar(select(Employee).where(Employee.email==rec["email"]))
        if e:
            for k in ("full_name","email","department","role","preferred_language","privilege_level","access_sensitivity","social_exposure"):
                if rec.get(k) is not None: setattr(e,k,rec[k])
            e.external_id=rec.get("external_id"); e.source=label; updated+=1
        else:
            e=Employee(source=label,**{k:rec[k] for k in HR_FIELDS if rec.get(k) is not None}); db.add(e); created+=1
        db.flush(); recalc_risk(db,e); ensure_context(db,e)
    audit(db,"hr_sync","employee",None,{"provider":label,"created":created,"updated":updated})
    return {"provider":label,"created":created,"updated":updated,"total":created+updated}

def validate_scenario(data):
    text=" ".join(str(data.get(k,"")) for k in ["subject","email_body","pretext","landing_page_message"]).lower()
    forbidden=["powershell -enc","mimikatz","disable antivirus","steal password","send credentials to","http://bit.ly","https://bit.ly"]
    hits=[x for x in forbidden if x in text]
    if hits: raise ValueError("Scenario failed safety validation")
    landing=data.get("landing_page_message","").lower()
    if "simulation" not in landing or "password" not in landing: raise ValueError("Landing page must clearly identify the simulation and password safety rule")
    return ["Synthetic data only","No real credential storage","Administrative approval required"]

def revalidate_scenario(scenario):
    return validate_scenario({"subject":scenario.subject,"email_body":scenario.email_body,"pretext":scenario.pretext,"landing_page_message":scenario.landing_page_message})

def generate_scenario(db,employee,objective,difficulty,language):
    rp=recalc_risk(db,employee); ctx=ensure_context(db,employee)
    payload={"employee":{"full_name":employee.full_name,"department":employee.department,"role":employee.role,"preferred_language":language or employee.preferred_language},"risk":{"score":rp.score,"level":rp.level,"factors":rp.factors},"context":[{"kind":x.kind,"title":x.title,"summary":x.summary} for x in ctx],"objective":objective,"difficulty":difficulty}
    data=get_llm_provider().generate(payload); notes=validate_scenario(data)
    s=Scenario(employee_id=employee.id,status=ScenarioStatus.REVIEW_REQUIRED.value,language=language or employee.preferred_language,objective=objective,difficulty=difficulty,subject=data["subject"],email_body=data["email_body"],pretext=data["pretext"],landing_page_message=data["landing_page_message"],training_objective=data["training_objective"],risk_indicators=data["risk_indicators"],safety_notes=notes); db.add(s); db.flush(); audit(db,"scenario_generated","scenario",s.id,{"provider":"configured"}); return s

def launch_campaign(db,campaign,scenario,employee):
    if scenario.status!=ScenarioStatus.APPROVED.value: raise ValueError("Scenario must be approved before campaign launch")
    target=CampaignTarget(campaign_id=campaign.id,employee_id=employee.id); db.add(target); db.flush()
    result=get_campaign_provider().create_campaign(campaign,scenario,target); get_email_provider().send(employee.email,scenario.subject,scenario.email_body+f"\n\nSimulation link: {simulation_url(target.session_id)}")
    campaign.status=CampaignStatus.ACTIVE.value; campaign.started_at=datetime.now(timezone.utc); campaign.provider_campaign_id=str(result.get("id","")); target.delivered_at=datetime.now(timezone.utc); scenario.status=ScenarioStatus.ACTIVE.value; audit(db,"campaign_started","campaign",campaign.id,{"provider":campaign.provider}); return target

def analytics(db,campaign_id=None):
    cq=select(Campaign); eq=select(InteractionEvent); tq=select(CampaignTarget)
    if campaign_id: cq=cq.where(Campaign.id==campaign_id); eq=eq.where(InteractionEvent.campaign_id==campaign_id); tq=tq.where(CampaignTarget.campaign_id==campaign_id)
    campaigns=db.scalars(cq).all(); events=db.scalars(eq).all(); targets=db.scalars(tq).all(); delivered=sum(1 for t in targets if t.delivered_at)
    types=[e.event_type for e in events]; count=lambda x:types.count(x); safe=lambda n,d: round(100*n/d,1) if d else 0.0
    response_times=[]
    by_session={t.session_id:t for t in targets}
    for e in events:
        t=by_session.get(e.session_id)
        if t and t.delivered_at and e.event_type in {"link_clicked","simulation_reported"}: response_times.append((e.occurred_at-t.delivered_at).total_seconds())
    avg=round(sum(response_times)/len(response_times),1) if response_times else 0.0
    return {"campaigns":len(campaigns),"targets":len(targets),"delivery_rate":safe(delivered,len(targets)),"open_rate":safe(count("email_opened"),delivered),"click_rate":safe(count("link_clicked"),delivered),"submission_rate":safe(count("credential_simulation_submitted"),delivered),"reporting_rate":safe(count("simulation_reported"),delivered),"average_response_time_seconds":avg}
