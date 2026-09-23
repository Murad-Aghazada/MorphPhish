from sqlalchemy import select
from .db import SessionLocal
from .models import Employee, Scenario, Campaign, CampaignTarget, InteractionEvent, ScenarioStatus, CampaignStatus
from .services import sync_from_hr
from datetime import datetime, timezone, timedelta

def seed():
  db=SessionLocal()
  try:
    if db.scalar(select(Employee).limit(1)): return
    # Personas come from the HR data layer (adapter pattern), same path the app uses.
    sync_from_hr(db); db.flush()
    e=db.scalar(select(Employee).where(Employee.email=="aylin.mammadova@demo.example.com"))
    sc=Scenario(employee_id=e.id,status=ScenarioStatus.APPROVED.value,language="az",objective="Recognize contextual social-engineering cues",difficulty="medium",
      subject="Təcili: rüblük uzlaşdırmanın təsdiqi",
      email_body=("Salam Aylin, Maliyyə Əməliyyatları komandası «Finance access review» prosesini yekunlaşdırır və sizin təsdiqiniz hələ də gözlənilir. "
                  "Zəhmət olmasa yenilənmiş təchizatçı ödəniş qeydlərini nəzərdən keçirin və günün sonuna qədər aşağıdakı təhlükəsiz portal linki vasitəsilə hesabınızı təsdiqləyin. "
                  "Sessiyanız bitibsə, davam etmək üçün yenidən daxil olmağınız istənə bilər. "
                  "Cədvələ riayət etməyə kömək etdiyiniz üçün əvvəlcədən təşəkkür edirik."),
      pretext="Maliyyə Əməliyyatları adından, real görünən Finance iş axınına istinad edərək vaxt təzyiqi yaradan ssenari.",
      landing_page_message="Bu, icazə verilmiş təhlükəsizlik simulyasiyasıdır (simulation). Həqiqi parolu (password) daxil etməyin — yazdığınız hər hansı dəyər dərhal silinir və heç vaxt saxlanmır.",
      training_objective="Recognize contextual social-engineering cues",risk_indicators=["authority impersonation","time pressure","account verification request","secure-portal link"],safety_notes=["Synthetic only"],approved_at=datetime.now(timezone.utc)); db.add(sc); db.flush()
    c=Campaign(scenario_id=sc.id,name="Synthetic Finance Baseline",status=CampaignStatus.ACTIVE.value,provider="mock",provider_campaign_id="seed-demo",started_at=datetime.now(timezone.utc)-timedelta(hours=1)); db.add(c); db.flush()
    t=CampaignTarget(campaign_id=c.id,employee_id=e.id,delivered_at=datetime.now(timezone.utc)-timedelta(minutes=50)); db.add(t); db.flush()
    for et,minu in [("email_opened",45),("link_clicked",40),("credential_simulation_submitted",38),("simulation_reported",30)]: db.add(InteractionEvent(campaign_id=c.id,employee_id=e.id,session_id=t.session_id,event_type=et,occurred_at=datetime.now(timezone.utc)-timedelta(minutes=minu),safe_metadata={"credential_submitted":True} if et=="credential_simulation_submitted" else {}))
    db.commit()
  finally: db.close()
if __name__=='__main__': seed()
