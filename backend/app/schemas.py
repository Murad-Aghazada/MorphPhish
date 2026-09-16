from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class EmployeeCreate(BaseModel):
    full_name:str=Field(min_length=2,max_length=160); email:EmailStr; department:str; role:str; preferred_language:str="az"; privilege_level:int=Field(1,ge=1,le=5); access_sensitivity:int=Field(1,ge=1,le=5); social_exposure:int=Field(1,ge=1,le=5)
class EmployeeUpdate(BaseModel):
    full_name:str|None=None; department:str|None=None; role:str|None=None; preferred_language:str|None=None; privilege_level:int|None=Field(None,ge=1,le=5); access_sensitivity:int|None=Field(None,ge=1,le=5); social_exposure:int|None=Field(None,ge=1,le=5); active:bool|None=None
class EmployeeOut(ORM):
    id:str; full_name:str; email:str; department:str; role:str; preferred_language:str; privilege_level:int; access_sensitivity:int; social_exposure:int; active:bool; created_at:datetime
class RiskOut(ORM): id:str; employee_id:str; score:float; level:str; factors:dict; calculated_at:datetime
class ContextOut(ORM): id:str; employee_id:str; kind:str; title:str; summary:str; metadata_json:dict; created_at:datetime
class ScenarioRequest(BaseModel): employee_id:str; objective:str="Improve phishing awareness"; difficulty:str=Field("medium",pattern="^(easy|medium|hard)$"); language:str|None=None
class ScenarioOut(ORM):
    id:str; employee_id:str; status:str; language:str; objective:str; difficulty:str; subject:str; email_body:str; pretext:str; landing_page_message:str; training_objective:str; risk_indicators:list; safety_notes:list; created_at:datetime; approved_at:datetime|None
class CampaignCreate(BaseModel): scenario_id:str; name:str=Field(min_length=3,max_length=180)
class CampaignOut(ORM): id:str; scenario_id:str; name:str; status:str; provider:str; provider_campaign_id:str|None; started_at:datetime|None; completed_at:datetime|None; created_at:datetime
class EventIn(BaseModel): session_id:str; event_type:str=Field(pattern="^(page_viewed|link_clicked|form_viewed|credential_simulation_submitted|simulation_reported|email_opened)$"); password:str|None=None
class EventOut(ORM): id:str; campaign_id:str; employee_id:str; session_id:str; event_type:str; occurred_at:datetime; safe_metadata:dict
