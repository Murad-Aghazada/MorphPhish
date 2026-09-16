from sqlalchemy import select
from .db import SessionLocal
from .models import Employee, Scenario, Campaign, CampaignTarget, InteractionEvent, ScenarioStatus, CampaignStatus
from .services import recalc_risk, ensure_context
from datetime import datetime, timezone, timedelta
# Synthetic personas (clearly non-real, demo.example.com domain).
# Columns: full_name, email, department, role, preferred_language,
#          privilege_level, access_sensitivity, social_exposure (each 1-5).
DATA=[
("Aylin Məmmədova","aylin.mammadova@demo.example.com","Finance","Senior Accountant","az",3,4,4),
("Rəşad Quliyev","rashad.guliyev@demo.example.com","Finance","Chief Financial Officer","az",5,5,4),
("Murad Əliyev","murad.aliyev@demo.example.com","IT","Systems Administrator","az",5,5,3),
("Kənan Hüseynov","kenan.huseynov@demo.example.com","IT","Help Desk Technician","az",2,2,5),
("Elvin Quliyev","elvin.guliyev@demo.example.com","Security","Security Engineer","en",5,5,2),
("Nərmin Abbasova","narmin.abbasova@demo.example.com","Security","SOC Analyst","az",3,4,2),
("Nigar Həsənova","nigar.hasanova@demo.example.com","HR","HR Specialist","az",2,4,5),
("Səbinə Kərimli","sabina.karimli@demo.example.com","HR","HR Manager","az",3,5,4),
("Leyla Kərimova","leyla.karimova@demo.example.com","Management","Chief Executive Officer","en",5,5,5),
("Orxan Nəbiyev","orxan.nabiyev@demo.example.com","Management","Operations Director","az",5,5,4),
("Kamran Rzayev","kamran.rzayev@demo.example.com","Operations","Operations Analyst","az",2,3,4),
("Tural İsmayılov","tural.ismayilov@demo.example.com","Legal","Corporate Counsel","az",3,5,3),
("Aysel Vəliyeva","aysel.valiyeva@demo.example.com","Sales","Account Executive","az",2,3,5),
("Ramil Cəfərov","ramil.jafarov@demo.example.com","Sales","Sales Manager","az",3,4,5),
("Günel Məmmədli","gunel.mammadli@demo.example.com","Marketing","Marketing Specialist","az",2,2,5),
("Daniel Roberts","daniel.roberts@demo.example.com","Engineering","DevOps Engineer","en",5,5,2),
("Fərid Bağırov","farid.baghirov@demo.example.com","Engineering","Software Engineer","az",3,3,2),]
def seed():
  db=SessionLocal()
  try:
    if db.scalar(select(Employee).limit(1)): return
    emps=[]
    for n,email,d,r,l,p,a,s in DATA:
      e=Employee(full_name=n,email=email,department=d,role=r,preferred_language=l,privilege_level=p,access_sensitivity=a,social_exposure=s); db.add(e); db.flush(); recalc_risk(db,e); ensure_context(db,e); emps.append(e)
    e=emps[0]; sc=Scenario(employee_id=e.id,status=ScenarioStatus.APPROVED.value,language="az",objective="Link inspection awareness",difficulty="medium",subject="[SIMULATION] Finance sənəd yoxlaması",email_body="Authorized simulation message.",pretext="Synthetic finance workflow",landing_page_message="This is an authorized simulation. Do not enter a real password.",training_objective="Link inspection",risk_indicators=["urgency","link validation"],safety_notes=["Synthetic only"],approved_at=datetime.now(timezone.utc)); db.add(sc); db.flush()
    c=Campaign(scenario_id=sc.id,name="Synthetic Finance Baseline",status=CampaignStatus.ACTIVE.value,provider="mock",provider_campaign_id="seed-demo",started_at=datetime.now(timezone.utc)-timedelta(hours=1)); db.add(c); db.flush()
    t=CampaignTarget(campaign_id=c.id,employee_id=e.id,delivered_at=datetime.now(timezone.utc)-timedelta(minutes=50)); db.add(t); db.flush()
    for et,minu in [("email_opened",45),("link_clicked",40),("credential_simulation_submitted",38),("simulation_reported",30)]: db.add(InteractionEvent(campaign_id=c.id,employee_id=e.id,session_id=t.session_id,event_type=et,occurred_at=datetime.now(timezone.utc)-timedelta(minutes=minu),safe_metadata={"credential_submitted":True} if et=="credential_simulation_submitted" else {}))
    db.commit()
  finally: db.close()
if __name__=='__main__': seed()
