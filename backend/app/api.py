import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Form, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .db import get_db
from .models import *
from .schemas import *
from .services import *
from .core.config import settings
router=APIRouter(prefix="/api/v1")
_basic=HTTPBasic(auto_error=True)

def require_admin(credentials:HTTPBasicCredentials=Depends(_basic)):
    ok=secrets.compare_digest(credentials.username,settings.admin_username) and secrets.compare_digest(credentials.password,settings.admin_password)
    if not ok: raise HTTPException(401,"Invalid admin credentials",headers={"WWW-Authenticate":"Basic"})
    return credentials.username

def one(db,model,id):
    x=db.get(model,id)
    if not x: raise HTTPException(404,f"{model.__name__} not found")
    return x
@router.get('/health')
def health(): return {"status":"ok","app":settings.app_name,"mode":{"llm":settings.llm_provider,"campaign":settings.campaign_provider,"email":settings.email_provider}}
@router.get('/employees',response_model=list[EmployeeOut])
def employees(db:Session=Depends(get_db)): return db.scalars(select(Employee).order_by(Employee.department,Employee.full_name)).all()
@router.get('/hr/source',response_model=list[HRRecordOut])
def hr_source():
    try: return get_hr_adapter().list_employees()
    except RuntimeError as e: raise HTTPException(503,str(e))
@router.post('/hr/sync',response_model=HRSyncResult)
def hr_sync(db:Session=Depends(get_db)):
    try: res=sync_from_hr(db); db.commit(); return res
    except RuntimeError as e: db.rollback(); raise HTTPException(503,str(e))
@router.post('/employees',response_model=EmployeeOut,status_code=201)
def create_employee(body:EmployeeCreate,db:Session=Depends(get_db)):
    if db.scalar(select(Employee).where(Employee.email==str(body.email))): raise HTTPException(409,"Email already exists")
    e=Employee(**body.model_dump()); db.add(e); db.flush(); recalc_risk(db,e); ensure_context(db,e); audit(db,"employee_created","employee",e.id); db.commit(); return e
@router.get('/employees/{id}',response_model=EmployeeOut)
def employee(id:str,db:Session=Depends(get_db)): return one(db,Employee,id)
@router.patch('/employees/{id}',response_model=EmployeeOut)
def update_employee(id:str,body:EmployeeUpdate,db:Session=Depends(get_db)):
    e=one(db,Employee,id)
    for k,v in body.model_dump(exclude_unset=True).items(): setattr(e,k,v)
    recalc_risk(db,e); audit(db,"employee_updated","employee",e.id); db.commit(); return e
@router.delete('/employees/{id}',status_code=204)
def delete_employee(id:str,db:Session=Depends(get_db)):
    e=one(db,Employee,id); db.delete(e); audit(db,"employee_deleted","employee",id); db.commit()
@router.post('/employees/{id}/risk',response_model=RiskOut)
def risk(id:str,db:Session=Depends(get_db)):
    rp=recalc_risk(db,one(db,Employee,id)); db.commit(); return rp
@router.get('/employees/{id}/risk',response_model=RiskOut)
def get_risk(id:str,db:Session=Depends(get_db)):
    one(db,Employee,id); rp=db.scalar(select(RiskProfile).where(RiskProfile.employee_id==id));
    if not rp: raise HTTPException(404,"Risk profile not found")
    return rp
@router.get('/employees/{id}/context',response_model=list[ContextOut])
def context(id:str,db:Session=Depends(get_db)):
    items=ensure_context(db,one(db,Employee,id)); db.commit(); return items
@router.get('/employees/{id}/profile',response_model=ProfileOut)
def profile(id:str,db:Session=Depends(get_db)):
    e=one(db,Employee,id); rp=recalc_risk(db,e); items=ensure_context(db,e); db.commit()
    return ProfileOut(employee=e,risk=rp,context=items)
@router.get('/scenarios',response_model=list[ScenarioOut])
def scenarios(db:Session=Depends(get_db)):
    rows=db.scalars(select(Scenario).order_by(Scenario.created_at.desc())).all()
    oc=scenario_outcomes(db); emp_dept={e.id:e.department for e in db.scalars(select(Employee)).all()}
    items=[]
    for s in rows:
        item=ScenarioOut.model_validate(s); item.department=emp_dept.get(s.employee_id)
        o=oc.get(s.id)
        if o: item.completed=o["completed"]; item.outcome=o
        items.append(item)
    return items
@router.post('/scenarios/generate',response_model=ScenarioOut,status_code=201)
def gen(body:ScenarioRequest,db:Session=Depends(get_db)):
    try: s=generate_scenario(db,one(db,Employee,body.employee_id),body.objective,body.difficulty,body.language); db.commit(); return s
    except ValueError as e: db.rollback(); raise HTTPException(422,str(e))
    except RuntimeError as e: db.rollback(); raise HTTPException(503,str(e))
@router.post('/scenarios/{id}/approve',response_model=ScenarioOut)
def approve(id:str,db:Session=Depends(get_db)):
    s=one(db,Scenario,id)
    if s.status not in {ScenarioStatus.REVIEW_REQUIRED.value,ScenarioStatus.GENERATED.value}: raise HTTPException(409,"Scenario is not awaiting approval")
    s.status=ScenarioStatus.APPROVED.value; s.approved_at=datetime.now(timezone.utc); audit(db,"scenario_approved","scenario",s.id); db.commit(); return s
@router.post('/scenarios/{id}/reject',response_model=ScenarioOut)
def reject(id:str,db:Session=Depends(get_db)):
    s=one(db,Scenario,id); s.status=ScenarioStatus.REJECTED.value; audit(db,"scenario_rejected","scenario",s.id); db.commit(); return s
@router.post('/scenarios/{id}/close',response_model=ScenarioOut)
def close_scenario(id:str,db:Session=Depends(get_db)):
    """Close a launched simulation that never got a terminal response (no-response).
    Retires the link and moves the scenario to the archive."""
    s=one(db,Scenario,id)
    if s.status!=ScenarioStatus.ACTIVE.value: raise HTTPException(409,"Only a launched (active) simulation can be closed")
    s.status=ScenarioStatus.CLOSED.value; audit(db,"scenario_closed","scenario",s.id,{"reason":"no_response"}); db.commit(); return s
EDITABLE={ScenarioStatus.REVIEW_REQUIRED.value,ScenarioStatus.GENERATED.value,ScenarioStatus.DRAFT.value}
@router.patch('/scenarios/{id}',response_model=ScenarioOut)
def edit_scenario(id:str,body:ScenarioUpdate,db:Session=Depends(get_db)):
    s=one(db,Scenario,id)
    if s.status not in EDITABLE: raise HTTPException(409,"Only unapproved scenarios can be edited")
    for k,v in body.model_dump(exclude_unset=True).items(): setattr(s,k,v)
    try: s.safety_notes=revalidate_scenario(s)
    except ValueError as e: db.rollback(); raise HTTPException(422,str(e))
    score_scenario(db,s); audit(db,"scenario_edited","scenario",s.id); db.commit(); return s
@router.post('/scenarios/{id}/regenerate',response_model=ScenarioOut)
def regenerate(id:str,db:Session=Depends(get_db)):
    s=one(db,Scenario,id)
    if s.status not in EDITABLE: raise HTTPException(409,"Only unapproved scenarios can be regenerated")
    try: regenerate_scenario(db,s); db.commit(); return s
    except ValueError as e: db.rollback(); raise HTTPException(422,str(e))
    except RuntimeError as e: db.rollback(); raise HTTPException(503,str(e))
async def _optional_name(request:Request):
    """Read an optional campaign name from the request body WITHOUT a typed body
    param, so any body shape (object, array, string, empty, or malformed) is
    accepted instead of 422ing. The name is used only if the body is an object."""
    try:
        payload=await request.json()
    except Exception: return None
    return (payload.get("name") or None) if isinstance(payload,dict) else None

@router.post('/scenarios/{id}/launch',response_model=LaunchOut)
async def launch_scenario(id:str,request:Request,admin:str=Depends(require_admin),db:Session=Depends(get_db)):
    s=one(db,Scenario,id)
    if s.status!=ScenarioStatus.APPROVED.value: raise HTTPException(409,"Scenario must be approved before launch")
    e=one(db,Employee,s.employee_id)
    name=(await _optional_name(request)) or f"{s.subject[:60]} — {datetime.now(timezone.utc):%Y-%m-%d %H:%M}"
    c=Campaign(scenario_id=s.id,name=name,provider=settings.campaign_provider); db.add(c); db.flush(); audit(db,"campaign_created","campaign",c.id)
    try: t=launch_campaign(db,c,s,e); db.commit()
    except (ValueError,RuntimeError) as ex: db.rollback(); raise HTTPException(503 if isinstance(ex,RuntimeError) else 409,str(ex))
    return LaunchOut(campaign_id=c.id,session_id=t.session_id,status=c.status,simulation_url=simulation_url(t.session_id))
@router.get('/campaigns',response_model=list[CampaignOut])
def campaigns(db:Session=Depends(get_db)): return db.scalars(select(Campaign).order_by(Campaign.created_at.desc())).all()
@router.post('/campaigns',response_model=CampaignOut,status_code=201)
def create_campaign(body:CampaignCreate,db:Session=Depends(get_db)):
    s=one(db,Scenario,body.scenario_id)
    if s.status!=ScenarioStatus.APPROVED.value: raise HTTPException(409,"Scenario must be approved")
    name=body.name or f"{s.subject[:60]} — {datetime.now(timezone.utc):%Y-%m-%d %H:%M}"
    c=Campaign(scenario_id=s.id,name=name,provider=settings.campaign_provider); db.add(c); db.flush(); audit(db,"campaign_created","campaign",c.id); db.commit(); return c
@router.post('/campaigns/{id}/launch',response_model=LaunchOut)
def launch(id:str,admin:str=Depends(require_admin),db:Session=Depends(get_db)):
    c=one(db,Campaign,id); s=one(db,Scenario,c.scenario_id); e=one(db,Employee,s.employee_id)
    if c.status!=CampaignStatus.DRAFT.value: raise HTTPException(409,"Campaign is not in DRAFT state")
    try: t=launch_campaign(db,c,s,e); db.commit()
    except (ValueError,RuntimeError) as ex: db.rollback(); raise HTTPException(503 if isinstance(ex,RuntimeError) else 409,str(ex))
    return LaunchOut(campaign_id=c.id,session_id=t.session_id,status=c.status,simulation_url=simulation_url(t.session_id))
SENDER_TEAM={"Finance":"Finance Operations","IT":"IT Service Desk","Security":"Information Security","HR":"People & Culture","Management":"Executive Office","Legal":"Legal & Compliance","Sales":"Sales Operations","Marketing":"Brand & Communications","Operations":"Operations Center","Engineering":"Platform Engineering"}
def _sender(dept):
    team=SENDER_TEAM.get(dept,"IT Service Desk")
    slug=team.lower().replace(" & ","-").replace(" ","-")
    return f"{team} <{slug}@corp-portal.example>"  # lookalike, reserved .example domain — never a real sender
TERMINAL_EVENTS={"credential_simulation_submitted","simulation_reported"}
_PIXEL=b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
def _session_completed(db,session_id):
    return db.scalar(select(InteractionEvent).where(InteractionEvent.session_id==session_id,InteractionEvent.event_type.in_(TERMINAL_EVENTS))) is not None
def _record_event(db,t,etype,meta=None):
    """Upsert one interaction event per (session, event_type) — idempotent so the
    stage is recorded once no matter how often the landing page fires it."""
    ev=db.scalar(select(InteractionEvent).where(InteractionEvent.session_id==t.session_id,InteractionEvent.event_type==etype))
    if ev: ev.occurred_at=datetime.now(timezone.utc); ev.safe_metadata=meta or {}
    else: ev=InteractionEvent(campaign_id=t.campaign_id,employee_id=t.employee_id,session_id=t.session_id,event_type=etype,safe_metadata=meta or {}); db.add(ev)
    return ev
@router.get('/simulation/{session_id}/pixel.gif')
def open_pixel(session_id:str,db:Session=Depends(get_db)):
    # Email-open tracking pixel: viewing the message records email_opened. Always
    # returns the 1x1 GIF so the mail client never shows a broken image.
    t=db.scalar(select(CampaignTarget).where(CampaignTarget.session_id==session_id))
    if t: _record_event(db,t,"email_opened"); db.commit()
    return Response(content=_PIXEL,media_type="image/gif",headers={"Cache-Control":"no-store, no-cache, must-revalidate"})
@router.get('/simulation/{session_id}',response_model=SimulationOut)
def simulation(session_id:str,db:Session=Depends(get_db)):
    t=db.scalar(select(CampaignTarget).where(CampaignTarget.session_id==session_id))
    if not t: raise HTTPException(404,"Simulation session not found")
    # One-shot: once the recipient has submitted or reported, the simulation is complete
    # and the link is retired — reopening it no longer serves the lure.
    if _session_completed(db,session_id): raise HTTPException(410,"This simulation has ended")
    c=one(db,Campaign,t.campaign_id); s=one(db,Scenario,c.scenario_id); e=one(db,Employee,s.employee_id)
    if s.status==ScenarioStatus.CLOSED.value: raise HTTPException(410,"This simulation has ended")
    return SimulationOut(session_id=session_id,campaign_id=c.id,sender=_sender(e.department),recipient=f"{e.full_name} <{e.email}>",subject=s.subject,email_body=s.email_body,pretext=s.pretext,landing_page_message=s.landing_page_message,notice="AUTHORIZED SIMULATION — never enter a real password.")
@router.post('/simulation/{session_id}/event',response_model=EventOut,status_code=201)
def event(session_id:str,body:EventIn,db:Session=Depends(get_db)):
    if body.session_id!=session_id: raise HTTPException(422,"Session mismatch")
    t=db.scalar(select(CampaignTarget).where(CampaignTarget.session_id==session_id))
    if not t: raise HTTPException(404,"Simulation session not found")
    # Deliberately discard body.password. It is never stored, hashed, logged, forwarded, or included in metadata.
    meta={"credential_submitted":True,"credential_stored":False} if body.event_type=="credential_simulation_submitted" else {}
    ev=_record_event(db,t,body.event_type,meta)
    if body.event_type=="link_clicked": _record_event(db,t,"email_opened")  # reaching the page implies the email was opened
    # A terminal response completes the run: move the scenario to COMPLETED so its
    # status is correct everywhere (badge + Simulations/Archive split).
    if body.event_type in TERMINAL_EVENTS:
        sc=db.get(Scenario,db.get(Campaign,t.campaign_id).scenario_id)
        if sc and sc.status==ScenarioStatus.ACTIVE.value: sc.status=ScenarioStatus.COMPLETED.value
    db.flush(); audit(db,"simulation_event","campaign",t.campaign_id,{"event_type":body.event_type}); db.commit(); return ev
STAGE_EVENT={"opened":"email_opened","clicked":"link_clicked","submitted":"credential_simulation_submitted","reported":"simulation_reported"}
@router.get('/scenarios/{id}/result')
def scenario_result(id:str,db:Session=Depends(get_db)):
    """Per-target outcome for a launched scenario: which funnel stages each
    recipient reached, so the Simulations tab can show the result after it ends."""
    s=one(db,Scenario,id)
    camps=db.scalars(select(Campaign).where(Campaign.scenario_id==id)).all()
    targets=[]
    for c in camps:
        for t in db.scalars(select(CampaignTarget).where(CampaignTarget.campaign_id==c.id)).all():
            evs=db.scalars(select(InteractionEvent).where(InteractionEvent.session_id==t.session_id)).all()
            types={e.event_type for e in evs}
            reached=[stage for stage,et in STAGE_EVENT.items() if et in types]
            emp=db.get(Employee,t.employee_id); last=max((e.occurred_at for e in evs),default=None)
            targets.append({"session_id":t.session_id,"recipient":emp.email if emp else None,
                            "delivered":bool(t.delivered_at),"reached":reached,
                            "opened":"opened" in reached,"clicked":"clicked" in reached,
                            "submitted":"submitted" in reached,"reported":"reported" in reached,
                            "last_event_at":last.isoformat() if last else None})
    return {"scenario_id":id,"status":s.status,"launched":bool(camps),"targets":targets}
@router.get('/analytics')
def analytics_all(db:Session=Depends(get_db)):
    return {**analytics(db),**risk_map(db)}
@router.get('/campaigns/{id}/analytics')
def campaign_analytics(id:str,db:Session=Depends(get_db)): one(db,Campaign,id); return analytics(db,id)
@router.get('/recommendations',response_model=list[RecommendationOut])
def recommendations(db:Session=Depends(get_db)):
    rows=[]
    for e in db.scalars(select(Employee)).all():
        clicked=db.scalar(select(func.count()).select_from(InteractionEvent).where(InteractionEvent.employee_id==e.id,InteractionEvent.event_type=="link_clicked")) or 0
        submitted=db.scalar(select(func.count()).select_from(InteractionEvent).where(InteractionEvent.employee_id==e.id,InteractionEvent.event_type=="credential_simulation_submitted")) or 0
        reported=db.scalar(select(func.count()).select_from(InteractionEvent).where(InteractionEvent.employee_id==e.id,InteractionEvent.event_type=="simulation_reported")) or 0
        topics=[]
        if submitted: topics.append(("credential hygiene","high","Use simulation-only values and verify identity prompts before entering credentials."))
        if clicked: topics.append(("link inspection","medium","Inspect link destinations and validate the sender/context before following links."))
        if not reported: topics.append(("reporting procedure","medium","Practice using the organization-approved reporting channel for suspicious messages."))
        if not topics: topics.append(("sender validation","low","Continue validating sender identity and unexpected requests."))
        rows.extend({"employee_id":e.id,"employee":e.full_name,"topic":a,"priority":b,"recommendation":c} for a,b,c in topics)
    return rows
@router.get('/audit')
def audit_events(db:Session=Depends(get_db)): return [{"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"details":x.details,"created_at":x.created_at} for x in db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100)).all()]
