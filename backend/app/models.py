import enum, uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)
class ScenarioStatus(str, enum.Enum):
    DRAFT="DRAFT"; GENERATED="GENERATED"; REVIEW_REQUIRED="REVIEW_REQUIRED"; APPROVED="APPROVED"; ACTIVE="ACTIVE"; COMPLETED="COMPLETED"; REJECTED="REJECTED"; CLOSED="CLOSED"
class CampaignStatus(str, enum.Enum):
    DRAFT="DRAFT"; ACTIVE="ACTIVE"; COMPLETED="COMPLETED"; FAILED="FAILED"
class Employee(Base):
    __tablename__="employees"
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    full_name:Mapped[str]=mapped_column(String(160)); email:Mapped[str]=mapped_column(String(255),unique=True,index=True)
    department:Mapped[str]=mapped_column(String(80),index=True); role:Mapped[str]=mapped_column(String(120),index=True); preferred_language:Mapped[str]=mapped_column(String(10),default="az")
    privilege_level:Mapped[int]=mapped_column(Integer,default=1); access_sensitivity:Mapped[int]=mapped_column(Integer,default=1); social_exposure:Mapped[int]=mapped_column(Integer,default=1)
    source:Mapped[str]=mapped_column(String(40),default="manual",index=True); external_id:Mapped[str|None]=mapped_column(String(64),nullable=True,index=True)
    active:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class RiskProfile(Base):
    __tablename__="risk_profiles"; __table_args__=(UniqueConstraint("employee_id",name="uq_risk_employee"),)
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); employee_id:Mapped[str]=mapped_column(ForeignKey("employees.id",ondelete="CASCADE"),index=True)
    score:Mapped[float]=mapped_column(Float); level:Mapped[str]=mapped_column(String(16)); factors:Mapped[dict]=mapped_column(JSON,default=dict); calculated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class OperationalContext(Base):
    __tablename__="operational_context"
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); employee_id:Mapped[str]=mapped_column(ForeignKey("employees.id",ondelete="CASCADE"),index=True)
    kind:Mapped[str]=mapped_column(String(40),index=True); title:Mapped[str]=mapped_column(String(200)); summary:Mapped[str]=mapped_column(Text); metadata_json:Mapped[dict]=mapped_column(JSON,default=dict); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Scenario(Base):
    __tablename__="scenarios"
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); employee_id:Mapped[str]=mapped_column(ForeignKey("employees.id",ondelete="CASCADE"),index=True)
    status:Mapped[str]=mapped_column(String(30),default=ScenarioStatus.DRAFT.value,index=True); language:Mapped[str]=mapped_column(String(10)); objective:Mapped[str]=mapped_column(String(160)); difficulty:Mapped[str]=mapped_column(String(20))
    subject:Mapped[str]=mapped_column(String(255)); email_body:Mapped[str]=mapped_column(Text); pretext:Mapped[str]=mapped_column(Text); landing_page_message:Mapped[str]=mapped_column(Text); training_objective:Mapped[str]=mapped_column(Text); risk_indicators:Mapped[list]=mapped_column(JSON,default=list)
    safety_notes:Mapped[list]=mapped_column(JSON,default=list); quality_score:Mapped[float|None]=mapped_column(Float,nullable=True); quality_notes:Mapped[list]=mapped_column(JSON,default=list); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); approved_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class Campaign(Base):
    __tablename__="campaigns"
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); scenario_id:Mapped[str]=mapped_column(ForeignKey("scenarios.id",ondelete="CASCADE"),index=True); name:Mapped[str]=mapped_column(String(180)); status:Mapped[str]=mapped_column(String(30),default=CampaignStatus.DRAFT.value,index=True)
    provider:Mapped[str]=mapped_column(String(30),default="mock"); provider_campaign_id:Mapped[str|None]=mapped_column(String(120),nullable=True); started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class CampaignTarget(Base):
    __tablename__="campaign_targets"; __table_args__=(UniqueConstraint("campaign_id","employee_id",name="uq_campaign_target"),)
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); campaign_id:Mapped[str]=mapped_column(ForeignKey("campaigns.id",ondelete="CASCADE"),index=True); employee_id:Mapped[str]=mapped_column(ForeignKey("employees.id",ondelete="CASCADE"),index=True); session_id:Mapped[str]=mapped_column(String(64),unique=True,index=True,default=uid); delivered_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class InteractionEvent(Base):
    __tablename__="interaction_events"
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); campaign_id:Mapped[str]=mapped_column(ForeignKey("campaigns.id",ondelete="CASCADE"),index=True); employee_id:Mapped[str]=mapped_column(ForeignKey("employees.id",ondelete="CASCADE"),index=True); session_id:Mapped[str]=mapped_column(String(64),index=True); event_type:Mapped[str]=mapped_column(String(50),index=True); occurred_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); safe_metadata:Mapped[dict]=mapped_column(JSON,default=dict)
class TrainingRecommendation(Base):
    __tablename__="training_recommendations"
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); employee_id:Mapped[str|None]=mapped_column(ForeignKey("employees.id",ondelete="CASCADE"),nullable=True,index=True); campaign_id:Mapped[str|None]=mapped_column(ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=True,index=True); topic:Mapped[str]=mapped_column(String(80)); recommendation:Mapped[str]=mapped_column(Text); priority:Mapped[str]=mapped_column(String(20)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class TrainingAssignment(Base):
    __tablename__="training_assignments"; __table_args__=(UniqueConstraint("employee_id","topic",name="uq_training_assignment"),)
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); employee_id:Mapped[str]=mapped_column(ForeignKey("employees.id",ondelete="CASCADE"),index=True); topic:Mapped[str]=mapped_column(String(80)); priority:Mapped[str]=mapped_column(String(20)); recommendation:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(20),default="assigned",index=True); assigned_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class AuditEvent(Base):
    __tablename__="audit_events"
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid); action:Mapped[str]=mapped_column(String(80),index=True); entity_type:Mapped[str]=mapped_column(String(60)); entity_id:Mapped[str|None]=mapped_column(String(64),nullable=True); details:Mapped[dict]=mapped_column(JSON,default=dict); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
