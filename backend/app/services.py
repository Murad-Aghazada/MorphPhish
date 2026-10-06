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
# Compromise funnel (monotonic). "Reported" is a positive outcome, not a funnel
# depth, so it is surfaced separately as a KPI / engagement bar, not here.
FUNNEL_STAGES=[("delivered",None),("opened","email_opened"),("clicked","link_clicked"),
               ("submitted","credential_simulation_submitted")]
RISK_LEVELS=["critical","high","medium","low"]

def _stage_sessions(targets,events):
    """Map each delivered session to the set of stages it reached, so every rate
    counts a session at most ONCE per stage. This makes rates a true share of
    delivered sessions (never >100%), robust to duplicate/historical events."""
    delivered={t.session_id for t in targets if t.delivered_at}
    raw={}  # event_type -> set(session_id), restricted to delivered sessions
    first_hit={}  # session_id -> earliest click/report time (reaction time)
    by_session={t.session_id:t for t in targets}
    for e in events:
        if e.session_id not in delivered: continue
        raw.setdefault(e.event_type,set()).add(e.session_id)
        if e.event_type in {"link_clicked","simulation_reported"}:
            cur=first_hit.get(e.session_id)
            if cur is None or e.occurred_at<cur: first_hit[e.session_id]=e.occurred_at
    # Funnel implication: reaching a deeper stage means the shallower ones were passed
    # (submit/report happen on the landing page, i.e. after a click; a click implies an open).
    submitted=raw.get("credential_simulation_submitted",set()); reported=raw.get("simulation_reported",set())
    clicked=raw.get("link_clicked",set())|submitted|reported
    opened=raw.get("email_opened",set())|clicked
    stages={"email_opened":opened,"link_clicked":clicked,
            "credential_simulation_submitted":submitted,"simulation_reported":reported}
    return delivered,stages,first_hit,by_session

def _rates_block(targets,events):
    """Delivery/open/click/submission/reporting rates (% of delivered sessions)
    plus the average reaction time (seconds from delivery to first click/report).
    Shared by the global view and every dimension; each rate is capped at 100%."""
    delivered,stages,first_hit,by_session=_stage_sessions(targets,events)
    n=len(delivered); pct=lambda et: round(100*len(stages.get(et,set()))/n,1) if n else 0.0
    rts=[(t0-by_session[sid].delivered_at).total_seconds() for sid,t0 in first_hit.items() if by_session[sid].delivered_at]
    return {"targets":len(targets),"delivered":n,
            "delivery_rate":round(100*n/len(targets),1) if targets else 0.0,
            "open_rate":pct("email_opened"),
            "click_rate":pct("link_clicked"),
            "submission_rate":pct("credential_simulation_submitted"),
            "reporting_rate":pct("simulation_reported"),
            "average_response_time_seconds":round(sum(rts)/len(rts),1) if rts else 0.0}

def _funnel(targets,events):
    delivered,stages,_fh,_bs=_stage_sessions(targets,events)
    n=len(delivered); pct=lambda c: round(100*c/n,1) if n else 0.0
    rows=[]
    for stage,etype in FUNNEL_STAGES:
        c=n if etype is None else len(stages.get(etype,set()))
        rows.append({"stage":stage,"count":c,"rate":pct(c)})
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
    for c in db.scalars(select(Campaign)).all(): camps_by_scen.setdefault(c.scenario_id,[]).append(c)
    targets_by_camp={}
    for t in db.scalars(select(CampaignTarget)).all(): targets_by_camp.setdefault(t.campaign_id,[]).append(t)
    types_by_session={}; last_by_session={}
    for ev in db.scalars(select(InteractionEvent)).all():
        types_by_session.setdefault(ev.session_id,set()).add(ev.event_type)
        cur=last_by_session.get(ev.session_id)
        if cur is None or ev.occurred_at>cur: last_by_session[ev.session_id]=ev.occurred_at
    out={}
    for scen_id,camps in camps_by_scen.items():
        tgts=[t for c in camps for t in targets_by_camp.get(c.id,[])]
        reached=set(); recipient=None; recipient_name=None; dept=None; last_event=None
        for t in tgts:
            seen=types_by_session.get(t.session_id,set())
            reached|={stage for stage,et in _STAGE_EVENT.items() if et in seen}
            le=last_by_session.get(t.session_id)
            if le and (last_event is None or le>last_event): last_event=le
            e=emps.get(t.employee_id)
            if e: recipient=e.email; recipient_name=e.full_name; dept=e.department
        launched_at=min((c.started_at for c in camps if c.started_at),default=None)
        out[scen_id]={"launched":bool(tgts),"recipient":recipient,"recipient_name":recipient_name,"department":dept,
                      "opened":"opened" in reached,"clicked":"clicked" in reached,
                      "submitted":"submitted" in reached,"reported":"reported" in reached,
                      "reached":[s for s in _STAGE_EVENT if s in reached],
                      "completed":("submitted" in reached) or ("reported" in reached),
                      "launched_at":launched_at.isoformat() if launched_at else None,
                      "last_event_at":last_event.isoformat() if last_event else None}
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
            "risk_distribution":[{"level":l,"count":dist.get(l,0)} for l in RISK_LEVELS],
            "people_targeted":len({t.employee_id for t in targets}),
            "employees_total":len(emps),
            "high_risk_employees":sum(1 for _id,(_sc,lv) in risk.items() if lv in ("high","critical"))}

# ---------------------------------------------------------------- training (Week 4)
# Corrective-training catalog: topic -> (priority, guidance). Derivation + assignment
# both read from here so recommendation text stays consistent.
TRAINING_TOPICS={
    "credential hygiene":("high","Use simulation-only values and verify identity prompts before entering credentials."),
    "link inspection":("medium","Inspect link destinations and validate the sender/context before following links."),
    "reporting procedure":("medium","Practice using the organization-approved reporting channel for suspicious messages."),
    "sender validation":("low","Continue validating sender identity and unexpected requests."),
}
_PRIORITY_RANK={"high":0,"medium":1,"low":2}

def derive_topics(db,employee):
    """Which corrective topics a persona needs, from how they handled simulations."""
    def cnt(et): return db.scalar(select(func.count()).select_from(InteractionEvent).where(InteractionEvent.employee_id==employee.id,InteractionEvent.event_type==et)) or 0
    submitted=cnt("credential_simulation_submitted"); clicked=cnt("link_clicked"); reported=cnt("simulation_reported")
    topics=[]
    if submitted: topics.append("credential hygiene")
    if clicked: topics.append("link inspection")
    if not reported: topics.append("reporting procedure")
    if not topics: topics.append("sender validation")
    return topics

def training_overview(db):
    """Per-persona training view: derived topics merged with assignment status,
    employee context and risk, sorted by most urgent topic then risk."""
    emps=db.scalars(select(Employee)).all()
    risk={rp.employee_id:(rp.score,rp.level) for rp in db.scalars(select(RiskProfile)).all()}
    assigns={(a.employee_id,a.topic):a for a in db.scalars(select(TrainingAssignment)).all()}
    out=[]
    for e in emps:
        items=[]
        for tp in derive_topics(db,e):
            pr,rec=TRAINING_TOPICS[tp]; a=assigns.get((e.id,tp))
            items.append({"topic":tp,"priority":pr,"recommendation":rec,
                          "status":(a.status if a else "none"),"assignment_id":(a.id if a else None),
                          "assigned_at":(a.assigned_at.isoformat() if a else None),
                          "completed_at":(a.completed_at.isoformat() if a and a.completed_at else None)})
        sc,lv=risk.get(e.id,(None,None))
        out.append({"employee_id":e.id,"employee":e.full_name,"department":e.department,"role":e.role,
                    "risk_score":sc,"risk_level":lv,"items":items})
    out.sort(key=lambda r:(min((_PRIORITY_RANK.get(i["priority"],3) for i in r["items"]),default=3),-(r["risk_score"] or 0)))
    return out

def assign_training(db,employee,topic):
    if topic not in TRAINING_TOPICS: raise ValueError("Unknown training topic")
    pr,rec=TRAINING_TOPICS[topic]
    a=db.scalar(select(TrainingAssignment).where(TrainingAssignment.employee_id==employee.id,TrainingAssignment.topic==topic))
    if a: a.status="assigned"; a.completed_at=None; a.priority=pr; a.recommendation=rec
    else: a=TrainingAssignment(employee_id=employee.id,topic=topic,priority=pr,recommendation=rec,status="assigned"); db.add(a)
    db.flush(); audit(db,"training_assigned","employee",employee.id,{"topic":topic}); return a

def complete_training(db,assignment):
    assignment.status="completed"; assignment.completed_at=datetime.now(timezone.utc)
    audit(db,"training_completed","training",assignment.id,{"topic":assignment.topic}); return assignment
