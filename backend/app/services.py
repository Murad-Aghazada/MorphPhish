import re
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import *
from .risk import calculate
from .adapters.context import MockContextAdapter
from .adapters.hr import get_hr_adapter, FIELDS as HR_FIELDS
from .llm.providers import get_llm_provider
from .llm.prompts import normalize_language, safe_landing, DEPARTMENT_THEMES, DEFAULT_THEME
from .integrations.campaign import get_campaign_provider
from .integrations.email import get_email_provider, build_email_html
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

def _lang_ok(text,lang):
    has_cyrillic=bool(re.search(r"[а-яА-ЯёЁ]",text or ""))
    return has_cyrillic if lang=="ru" else not has_cyrillic

def assess_quality(data,ctx_localized,lang):
    """Heuristic quality score (0-100) + notes to guide manual review.

    Checks whether the scenario references the operational context, has an
    appropriately sized body, enough risk indicators, a reasonable subject,
    matches the requested language, and carries the safety disclosure.
    """
    subject=(data.get("subject") or ""); body=(data.get("email_body") or "")
    text=(subject+" "+body).lower(); score=0; notes=[]
    anchors=[(c.get("title") or "") for c in (ctx_localized or [])]
    tokens=[t for a in anchors for t in re.split(r"\W+",a.lower()) if len(t)>3]
    if any(t in text for t in tokens): score+=25
    else: notes.append("Does not clearly reference operational context")
    sentences=[s for s in re.split(r"[.!?…]+",body) if s.strip()]
    if 3<=len(sentences)<=5: score+=20
    else: notes.append(f"Body has {len(sentences)} sentences (aim for 3-5)")
    if len(data.get("risk_indicators") or [])>=3: score+=15
    else: notes.append("Fewer than 3 risk indicators")
    if 15<=len(subject)<=90: score+=15
    else: notes.append("Subject length outside the 15-90 character range")
    if _lang_ok(body,lang): score+=15
    else: notes.append(f"Body may not be written in the requested language ({lang})")
    landing=(data.get("landing_page_message") or "").lower()
    if "simulation" in landing and "password" in landing: score+=10
    else: notes.append("Landing page missing the required safety disclosure")
    return score,notes

def _localize_context(ctx,lang):
    out=[]
    for x in ctx:
        meta=x.metadata_json or {}
        title=(meta.get("title_i18n") or {}).get(lang) or x.title
        summary=(meta.get("summary_i18n") or {}).get(lang) or x.summary
        out.append({"kind":x.kind,"title":title,"summary":summary,"anchor":meta.get("anchor",0),
                    "meta":{k:v for k,v in meta.items() if k not in ("title_i18n","summary_i18n")}})
    return out

def _build_scenario_content(db,employee,objective,difficulty,language):
    """Run the model + safety + quality pipeline. Returns (data, notes, q_score, q_notes, lang)."""
    rp=recalc_risk(db,employee); ctx=ensure_context(db,employee)
    target_lang=normalize_language(language or employee.preferred_language)
    payload={"employee":{"full_name":employee.full_name,"department":employee.department,"role":employee.role,"preferred_language":language or employee.preferred_language},"risk":{"score":rp.score,"level":rp.level,"factors":rp.factors},"context":_localize_context(ctx,target_lang),"objective":objective,"difficulty":difficulty}
    data=get_llm_provider().generate(payload)
    data["landing_page_message"]=safe_landing(target_lang)  # safety-critical text is enforced by us, not the LLM
    notes=validate_scenario(data)
    q_score,q_notes=assess_quality(data,payload["context"],target_lang)
    return data,notes,q_score,q_notes

def _apply_content(s,data,notes,q_score,q_notes):
    s.subject=data["subject"]; s.email_body=data["email_body"]; s.pretext=data["pretext"]
    s.landing_page_message=data["landing_page_message"]; s.training_objective=data["training_objective"]
    s.risk_indicators=data["risk_indicators"]; s.safety_notes=notes; s.quality_score=q_score; s.quality_notes=q_notes

def generate_scenario(db,employee,objective,difficulty,language):
    data,notes,q_score,q_notes=_build_scenario_content(db,employee,objective,difficulty,language)
    s=Scenario(employee_id=employee.id,status=ScenarioStatus.REVIEW_REQUIRED.value,language=language or employee.preferred_language,objective=objective,difficulty=difficulty)
    _apply_content(s,data,notes,q_score,q_notes); db.add(s); db.flush()
    audit(db,"scenario_generated","scenario",s.id,{"provider":"configured","quality":q_score}); return s

def regenerate_scenario(db,scenario):
    """Regenerate content for an EXISTING scenario in place (no new row)."""
    employee=db.get(Employee,scenario.employee_id)
    if not employee: raise ValueError("Scenario employee no longer exists")
    data,notes,q_score,q_notes=_build_scenario_content(db,employee,scenario.objective,scenario.difficulty,scenario.language)
    _apply_content(scenario,data,notes,q_score,q_notes)
    scenario.status=ScenarioStatus.REVIEW_REQUIRED.value; scenario.approved_at=None
    db.flush(); audit(db,"scenario_regenerated","scenario",scenario.id,{"quality":q_score}); return scenario

def score_scenario(db,scenario):
    emp=db.get(Employee,scenario.employee_id); lang=normalize_language(scenario.language)
    ctx=_localize_context(ensure_context(db,emp),lang) if emp else []
    data={"subject":scenario.subject,"email_body":scenario.email_body,"risk_indicators":scenario.risk_indicators,"landing_page_message":scenario.landing_page_message}
    scenario.quality_score,scenario.quality_notes=assess_quality(data,ctx,lang)
    return scenario.quality_score,scenario.quality_notes

def launch_campaign(db,campaign,scenario,employee):
    if scenario.status!=ScenarioStatus.APPROVED.value: raise ValueError("Scenario must be approved before campaign launch")
    target=CampaignTarget(campaign_id=campaign.id,employee_id=employee.id); db.add(target); db.flush()
    url=simulation_url(target.session_id); lang=normalize_language(scenario.language)
    team=(DEPARTMENT_THEMES.get(employee.department,DEFAULT_THEME))["team"][lang]
    cta={"az":"Hesaba daxil ol","ru":"Войти в аккаунт"}.get(lang,"Sign in to continue")
    text=f"{scenario.email_body}\n\n{cta}: {url}"
    pixel=settings.backend_url.rstrip('/')+f"/api/v1/simulation/{target.session_id}/pixel.gif"
    html_body=build_email_html(team,scenario.subject,scenario.email_body,url,cta,pixel_url=pixel)
    result=get_campaign_provider().create_campaign(campaign,scenario,target)
    get_email_provider().send(employee.email,scenario.subject,text,html_body=html_body,from_name=team)
    campaign.status=CampaignStatus.ACTIVE.value; campaign.started_at=datetime.now(timezone.utc); campaign.provider_campaign_id=str(result.get("id","")); target.delivered_at=datetime.now(timezone.utc); scenario.status=ScenarioStatus.ACTIVE.value; audit(db,"campaign_started","campaign",campaign.id,{"provider":campaign.provider}); return target

# ---------------------------------------------------------------- analytics (Week 4)
# The engagement funnel stage -> the interaction event that marks it reached.
FUNNEL_STAGES=[("delivered",None),("opened","email_opened"),("clicked","link_clicked"),
               ("submitted","credential_simulation_submitted"),("reported","simulation_reported")]
RISK_LEVELS=["critical","high","medium","low"]

def _event_counts(events):
    c={}
    for e in events: c[e.event_type]=c.get(e.event_type,0)+1
    return c

def _rates_block(targets,events):
    """Delivery/open/click/submission/reporting rates (% of delivered) plus the
    average reaction time (seconds from delivery to click/report) for one slice
    of targets and their events. Shared by the global view and every dimension."""
    delivered=sum(1 for t in targets if t.delivered_at)
    c=_event_counts(events); pct=lambda n,d: round(100*n/d,1) if d else 0.0
    by_session={t.session_id:t for t in targets}; rts=[]
    for e in events:
        t=by_session.get(e.session_id)
        if t and t.delivered_at and e.event_type in {"link_clicked","simulation_reported"}:
            rts.append((e.occurred_at-t.delivered_at).total_seconds())
    return {"targets":len(targets),"delivered":delivered,
            "delivery_rate":pct(delivered,len(targets)),
            "open_rate":pct(c.get("email_opened",0),delivered),
            "click_rate":pct(c.get("link_clicked",0),delivered),
            "submission_rate":pct(c.get("credential_simulation_submitted",0),delivered),
            "reporting_rate":pct(c.get("simulation_reported",0),delivered),
            "average_response_time_seconds":round(sum(rts)/len(rts),1) if rts else 0.0}

def _funnel(targets,events):
    delivered=sum(1 for t in targets if t.delivered_at); c=_event_counts(events)
    pct=lambda n: round(100*n/delivered,1) if delivered else 0.0
    rows=[]
    for stage,etype in FUNNEL_STAGES:
        n=delivered if etype is None else c.get(etype,0)
        rows.append({"stage":stage,"count":n,"rate":pct(n)})
    return rows

def analytics(db,campaign_id=None):
    cq=select(Campaign); eq=select(InteractionEvent); tq=select(CampaignTarget)
    if campaign_id: cq=cq.where(Campaign.id==campaign_id); eq=eq.where(InteractionEvent.campaign_id==campaign_id); tq=tq.where(CampaignTarget.campaign_id==campaign_id)
    campaigns=db.scalars(cq).all(); events=db.scalars(eq).all(); targets=db.scalars(tq).all()
    return {"campaigns":len(campaigns),**_rates_block(targets,events),"funnel":_funnel(targets,events)}

_STAGE_EVENT={"opened":"email_opened","clicked":"link_clicked","submitted":"credential_simulation_submitted","reported":"simulation_reported"}
def scenario_outcomes(db):
    """Per-scenario launch outcome, computed in a few bulk queries (no N+1), so the
    scenario list can be split into active vs archived and filtered. A scenario is
    `completed` once any of its targets submitted or reported (the link is retired)."""
    emps={e.id:e for e in db.scalars(select(Employee)).all()}
    camps_by_scen={}
    for c in db.scalars(select(Campaign)).all(): camps_by_scen.setdefault(c.scenario_id,[]).append(c.id)
    targets_by_camp={}
    for t in db.scalars(select(CampaignTarget)).all(): targets_by_camp.setdefault(t.campaign_id,[]).append(t)
    types_by_session={}
    for ev in db.scalars(select(InteractionEvent)).all(): types_by_session.setdefault(ev.session_id,set()).add(ev.event_type)
    out={}
    for scen_id,cids in camps_by_scen.items():
        tgts=[t for cid in cids for t in targets_by_camp.get(cid,[])]
        reached=set(); recipient=None; dept=None
        for t in tgts:
            seen=types_by_session.get(t.session_id,set())
            reached|={stage for stage,et in _STAGE_EVENT.items() if et in seen}
            e=emps.get(t.employee_id)
            if e: recipient=e.email; dept=e.department
        out[scen_id]={"launched":bool(tgts),"recipient":recipient,"department":dept,
                      "opened":"opened" in reached,"clicked":"clicked" in reached,
                      "submitted":"submitted" in reached,"reported":"reported" in reached,
                      "reached":[s for s in _STAGE_EVENT if s in reached],
                      "completed":("submitted" in reached) or ("reported" in reached)}
    return out

def risk_map(db):
    """Human-risk map: every engagement metric aggregated by department and by
    role, plus the organization's risk-level distribution. This is the Week 4
    diagnostic surface — it turns raw events into a role/department risk picture."""
    emps=db.scalars(select(Employee)).all()
    targets=db.scalars(select(CampaignTarget)).all()
    events=db.scalars(select(InteractionEvent)).all()
    risk={rp.employee_id:(rp.score,rp.level) for rp in db.scalars(select(RiskProfile)).all()}
    def block_for(group):
        ids={e.id for e in group}
        ts=[t for t in targets if t.employee_id in ids]; es=[ev for ev in events if ev.employee_id in ids]
        scores=[risk[e.id][0] for e in group if e.id in risk]
        return {"employees":len(group),"average_risk":round(sum(scores)/len(scores),1) if scores else 0.0,**_rates_block(ts,es)}
    def group_by(attr):
        buckets={}
        for e in emps: buckets.setdefault(getattr(e,attr),[]).append(e)
        return sorted([{"key":k,**block_for(v)} for k,v in buckets.items()],key=lambda r:r["average_risk"],reverse=True)
    dist={l:0 for l in RISK_LEVELS}
    for _id,(_sc,lv) in risk.items(): dist[lv]=dist.get(lv,0)+1
    return {"by_department":group_by("department"),"by_role":group_by("role"),
            "risk_distribution":[{"level":l,"count":dist.get(l,0)} for l in RISK_LEVELS]}
