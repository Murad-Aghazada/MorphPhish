from abc import ABC, abstractmethod
from email.message import EmailMessage
import smtplib
from app.core.config import settings
class EmailProvider(ABC):
    @abstractmethod
    def send(self,to,subject,body): ...
class MockEmailProvider(EmailProvider):
    def send(self,to,subject,body): return {"accepted":True,"mode":"mock"}
class SMTPProvider(EmailProvider):
    def send(self,to,subject,body):
        domain=to.rsplit('@',1)[-1].lower()
        if domain not in settings.allowed_domains: raise ValueError("Recipient domain is outside AUTHORIZED_EMAIL_DOMAINS")
        msg=EmailMessage(); msg['From']=settings.smtp_from; msg['To']=to; msg['Subject']=subject; msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=15) as s:
            if settings.smtp_username:
                s.starttls(); s.login(settings.smtp_username,settings.smtp_password)
            s.send_message(msg)
        return {"accepted":True,"mode":"smtp"}
def get_email_provider(): return MockEmailProvider() if settings.email_provider.lower()=="mock" else SMTPProvider()
