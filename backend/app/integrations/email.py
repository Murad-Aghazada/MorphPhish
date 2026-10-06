from abc import ABC, abstractmethod
from email.message import EmailMessage
from email.utils import formataddr
import html
import smtplib
from app.core.config import settings


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to, subject, body, html_body=None, from_name=None): ...


class MockEmailProvider(EmailProvider):
    def send(self, to, subject, body, html_body=None, from_name=None):
        return {"accepted": True, "mode": "mock"}


class SMTPProvider(EmailProvider):
    def send(self, to, subject, body, html_body=None, from_name=None):
        domain = to.rsplit('@', 1)[-1].lower()
        if domain not in settings.allowed_domains:
            raise ValueError("Recipient domain is outside AUTHORIZED_EMAIL_DOMAINS")
        msg = EmailMessage()
        # A realistic display name (the impersonated team) over the authorized,
        # allow-listed address — the address itself is never spoofed.
        msg['From'] = formataddr((from_name, settings.smtp_from)) if from_name else settings.smtp_from
        msg['To'] = to
        msg['Subject'] = subject
        msg.set_content(body)                       # text/plain fallback
        if html_body:
            msg.add_alternative(html_body, subtype='html')  # multipart/alternative
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            if settings.smtp_username:
                s.starttls(); s.login(settings.smtp_username, settings.smtp_password)
            s.send_message(msg)
        return {"accepted": True, "mode": "smtp"}


def build_email_html(team, subject, body_text, cta_url, cta_label, pixel_url=None):
    """Render a realistic, self-contained HTML simulation email with a branded
    header and a styled call-to-action button. Inline styles only, so it renders
    the same in Mailpit and any mail client. All content is synthetic; the link
    points at the isolated lab landing page, never a real site. An optional 1x1
    tracking pixel records email-open when the client loads remote images."""
    esc = html.escape
    pixel = (f'<img src="{esc(pixel_url)}" width="1" height="1" alt="" '
             f'style="display:block;width:1px;height:1px;border:0;">') if pixel_url else ""
    paragraphs = "".join(
        f'<p style="margin:0 0 16px;line-height:1.6;color:#2b2f36;font-size:15px;">{esc(p)}</p>'
        for p in (body_text or "").split("\n") if p.strip()
    )
    return f"""\
<!doctype html><html><body style="margin:0;padding:0;background:#eef1f5;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef1f5;padding:28px 12px;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e2e5ec;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <tr><td style="background:#1f3a8a;padding:18px 28px;">
    <span style="color:#ffffff;font-size:17px;font-weight:700;letter-spacing:.2px;">{esc(team)}</span>
  </td></tr>
  <tr><td style="padding:28px 28px 8px;">
    <h1 style="margin:0 0 18px;font-size:19px;color:#11151c;font-weight:700;">{esc(subject)}</h1>
    {paragraphs}
  </td></tr>
  <tr><td style="padding:6px 28px 28px;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="border-radius:8px;background:#2a66d6;">
      <a href="{esc(cta_url)}" style="display:inline-block;padding:13px 30px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;">{esc(cta_label)} &rarr;</a>
    </td></tr></table>
    <p style="margin:18px 0 0;font-size:12px;color:#8a909b;line-height:1.5;">
      If the button does not work, copy and paste this address into your browser:<br>
      <span style="color:#2a66d6;word-break:break-all;">{esc(cta_url)}</span>
    </p>
  </td></tr>
  <tr><td style="background:#f6f8fb;padding:16px 28px;border-top:1px solid #e2e5ec;">
    <p style="margin:0;font-size:11px;color:#9aa0ab;line-height:1.5;">This message was sent to you by {esc(team)}. Please do not share your account details with anyone.</p>
  </td></tr>
</table>
{pixel}
</td></tr></table>
</body></html>"""


def get_email_provider():
    return MockEmailProvider() if settings.email_provider.lower() == "mock" else SMTPProvider()
