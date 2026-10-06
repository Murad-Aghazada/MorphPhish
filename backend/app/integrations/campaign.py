"""Campaign (delivery) providers behind one interface.

MockCampaignProvider  — built-in one-click launch (default); MorphPhish itself
                        delivers the email and tracks events on its landing page.
GophishProvider       — delegates delivery to a real GoPhish instance. It ensures
                        the required GoPhish resources exist (sending profile →
                        Mailpit, email template, landing page, a per-launch group
                        with the single synthetic target) and then creates a GoPhish
                        campaign. GoPhish sends the mail and tracks open/click in its
                        own dashboard; MorphPhish stays the orchestration/analytics layer.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import html
import httpx
from app.core.config import settings

# Shared, reusable GoPhish resource names (created once, looked up by name).
SMTP_NAME = "MorphPhish Mailpit"
TEMPLATE_NAME = "MorphPhish Authorized Simulation"
PAGE_NAME = "MorphPhish Safe Landing"


class CampaignProvider(ABC):
    @abstractmethod
    def create_campaign(self, campaign, scenario, target): ...


class MockCampaignProvider(CampaignProvider):
    def create_campaign(self, campaign, scenario, target):
        return {"id": f"mock-{campaign.id}", "status": "active"}


class GophishProvider(CampaignProvider):
    def _client(self):
        if not settings.gophish_url or not settings.gophish_api_key:
            raise RuntimeError("GoPhish is not configured (set GOPHISH_URL and GOPHISH_API_KEY)")
        return httpx.Client(base_url=settings.gophish_url.rstrip("/"), timeout=20,
                            verify=settings.gophish_verify_tls,
                            headers={"Authorization": settings.gophish_api_key, "Content-Type": "application/json"})

    def _ensure(self, c, path, name, payload):
        """Create a named resource if one with that name doesn't already exist."""
        r = c.get(path); r.raise_for_status()
        for item in r.json():
            if item.get("name") == name:
                return item
        r = c.post(path, json=payload); r.raise_for_status()
        return r.json()

    def create_campaign(self, campaign, scenario, target, employee=None):
        first, _, last = (getattr(employee, "full_name", "") or " ").partition(" ")
        body_html = "".join(f"<p>{html.escape(p)}</p>" for p in (scenario.email_body or "").split("\n") if p.strip())
        template_html = (f"{body_html}<p><a href=\"{{{{.URL}}}}\">Sign in to continue</a></p>{{{{.Tracker}}}}")
        try:
            with self._client() as c:
                self._ensure(c, "/api/smtp/", SMTP_NAME, {
                    "name": SMTP_NAME, "interface_type": "SMTP",
                    "host": f"{settings.smtp_host}:{settings.smtp_port}",
                    "from_address": settings.smtp_from, "ignore_cert_errors": True})
                self._ensure(c, "/api/templates/", TEMPLATE_NAME, {
                    "name": TEMPLATE_NAME, "subject": scenario.subject,
                    "html": template_html, "text": scenario.email_body})
                self._ensure(c, "/api/pages/", PAGE_NAME, {
                    "name": PAGE_NAME,
                    "html": "<html><body><h2>Authorized security-awareness simulation</h2>"
                            "<p>This was a training exercise. Never enter a real password.</p></body></html>",
                    "capture_credentials": False, "capture_passwords": False,
                    "redirect_url": settings.frontend_url})
                # One fresh group per launch (targets differ per simulation).
                group_name = f"MorphPhish {campaign.id[:8]}"
                self._ensure(c, "/api/groups/", group_name, {
                    "name": group_name,
                    "targets": [{"email": getattr(employee, "email", "target@demo.example.com"),
                                 "first_name": first or "Team", "last_name": last or "Member",
                                 "position": getattr(employee, "role", "")}]})
                payload = {
                    "name": f"{campaign.name} [{campaign.id[:8]}]",
                    "template": {"name": TEMPLATE_NAME}, "page": {"name": PAGE_NAME},
                    "smtp": {"name": SMTP_NAME}, "groups": [{"name": group_name}],
                    "url": settings.gophish_phish_url.rstrip("/"),
                    "launch_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")}
                r = c.post("/api/campaigns/", json=payload); r.raise_for_status()
                return r.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"GoPhish request failed: {e}")


def get_campaign_provider():
    return MockCampaignProvider() if settings.campaign_provider.lower() == "mock" else GophishProvider()
