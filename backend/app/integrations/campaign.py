from abc import ABC, abstractmethod
import httpx
from app.core.config import settings
class CampaignProvider(ABC):
    @abstractmethod
    def create_campaign(self,campaign,scenario,target): ...
class MockCampaignProvider(CampaignProvider):
    def create_campaign(self,campaign,scenario,target): return {"id":f"mock-{campaign.id}","status":"active"}
class GophishProvider(CampaignProvider):
    def create_campaign(self,campaign,scenario,target):
        if not settings.gophish_url or not settings.gophish_api_key: raise RuntimeError("GoPhish is not configured")
        # Integration is intentionally limited to pre-created authorized template/page/profile names.
        payload={"name":campaign.name,"template":{"name":"MorphPhish Authorized Simulation"},"url":f"{settings.frontend_url}/simulate/{target.session_id}","page":{"name":"MorphPhish Safe Landing"},"smtp":{"name":"MorphPhish Test SMTP"},"groups":[{"name":"MorphPhish Synthetic Targets"}]}
        with httpx.Client(timeout=15,verify=settings.gophish_verify_tls) as c:
            r=c.post(settings.gophish_url.rstrip('/')+"/api/campaigns/",params={"api_key":settings.gophish_api_key},json=payload); r.raise_for_status(); return r.json()
def get_campaign_provider(): return MockCampaignProvider() if settings.campaign_provider.lower()=="mock" else GophishProvider()
