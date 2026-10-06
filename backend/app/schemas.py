from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class LoginRequest(BaseModel): username:str=Field(min_length=1,max_length=150); password:str=Field(min_length=1,max_length=512,repr=False)
class TokenOut(BaseModel): access_token:str; token_type:str="bearer"; expires_in:int
class EmployeeCreate(BaseModel):
    full_name:str=Field(min_length=2,max_length=160); email:EmailStr; department:str; role:str; preferred_language:str="az"; privilege_level:int=Field(1,ge=1,le=5); access_sensitivity:int=Field(1,ge=1,le=5); social_exposure:int=Field(1,ge=1,le=5)
class EmployeeUpdate(BaseModel):
    full_name:str|None=None; department:str|None=None; role:str|None=None; preferred_language:str|None=None; privilege_level:int|None=Field(None,ge=1,le=5); access_sensitivity:int|None=Field(None,ge=1,le=5); social_exposure:int|None=Field(None,ge=1,le=5); active:bool|None=None
class EmployeeOut(ORM):
    id:str; full_name:str; email:str; department:str; role:str; preferred_language:str; privilege_level:int; access_sensitivity:int; social_exposure:int; source:str; external_id:str|None; active:bool; created_at:datetime; risk_score:float|None=None; risk_level:str|None=None
class HRRecordOut(BaseModel):
    external_id:str|None=None; full_name:str; email:str; department:str; role:str; preferred_language:str; privilege_level:int; access_sensitivity:int; social_exposure:int
class HRSyncResult(BaseModel): provider:str; created:int; updated:int; total:int
class RiskFactor(BaseModel): key:str; label:str; category:str; weight:int; points:float; detail:str
class RiskOut(ORM): id:str; employee_id:str; score:float; level:str; factors:list[RiskFactor]; calculated_at:datetime
class ContextOut(ORM): id:str; employee_id:str; kind:str; title:str; summary:str; metadata_json:dict; created_at:datetime
class ProfileOut(BaseModel): employee:EmployeeOut; risk:RiskOut; context:list[ContextOut]
class ScenarioRequest(BaseModel): employee_id:str; objective:str="Improve phishing awareness"; difficulty:str=Field("medium",pattern="^(easy|medium|hard)$"); language:str|None=None
class ScenarioOut(ORM):
    id:str; employee_id:str; status:str; language:str; objective:str; difficulty:str; subject:str; email_body:str; pretext:str; landing_page_message:str; training_objective:str; risk_indicators:list; safety_notes:list; quality_score:float|None=None; quality_notes:list=[]; created_at:datetime; approved_at:datetime|None; department:str|None=None; completed:bool=False; outcome:dict|None=None
class ScenarioUpdate(BaseModel):
    subject:str|None=Field(None,min_length=1,max_length=255); email_body:str|None=Field(None,min_length=1); pretext:str|None=Field(None,min_length=1); landing_page_message:str|None=Field(None,min_length=1); training_objective:str|None=None; objective:str|None=Field(None,max_length=160); difficulty:str|None=Field(None,pattern="^(easy|medium|hard)$"); risk_indicators:list|None=None
class ScenarioLaunchRequest(BaseModel): name:str|None=Field(None,max_length=180)
class CampaignCreate(BaseModel): scenario_id:str; name:str|None=Field(None,max_length=180)
class CampaignOut(ORM): id:str; scenario_id:str; name:str; status:str; provider:str; provider_campaign_id:str|None; started_at:datetime|None; completed_at:datetime|None; created_at:datetime
class LaunchOut(BaseModel): campaign_id:str; session_id:str; status:str; simulation_url:str
class SimulationOut(BaseModel): session_id:str; campaign_id:str; sender:str; recipient:str; subject:str; email_body:str; pretext:str; landing_page_message:str; notice:str
class RecommendationOut(BaseModel): employee_id:str; employee:str; topic:str; priority:str; recommendation:str
class TrainingAssignRequest(BaseModel): employee_id:str; topic:str
class EventIn(BaseModel): session_id:str=Field(max_length=64); event_type:str=Field(pattern="^(page_viewed|link_clicked|form_viewed|credential_simulation_submitted|simulation_reported|email_opened)$"); password:str|None=Field(default=None,max_length=512,repr=False)  # discarded; bounded + kept out of reprs/logs
class EventOut(ORM): id:str; campaign_id:str; employee_id:str; session_id:str; event_type:str; occurred_at:datetime; safe_metadata:dict
