from abc import ABC, abstractmethod
import json, httpx
from app.core.config import settings

class LLMProvider(ABC):
    @abstractmethod
    def generate(self,payload:dict)->dict: ...

# Department-flavoured lure themes for the offline mock generator. Each theme
# drives a realistic 3-4 sentence training email. Content is fully synthetic;
# no real links, credentials, or payloads are ever produced.
_THEME={
 "Finance":{"team":{"en":"Finance Operations","az":"Maliyyə Əməliyyatları"},"subject":{"en":"Action required: quarterly reconciliation confirmation","az":"Təcili: rüblük uzlaşdırmanın təsdiqi"},"noun":{"en":"vendor payment records","az":"təchizatçı ödəniş qeydləri"}},
 "IT":{"team":{"en":"IT Service Desk","az":"İT Xidmət Masası"},"subject":{"en":"Your account password will expire today","az":"Hesab parolunuzun müddəti bu gün bitir"},"noun":{"en":"mailbox and VPN access","az":"poçt və VPN girişi"}},
 "Security":{"team":{"en":"Information Security","az":"İnformasiya Təhlükəsizliyi"},"subject":{"en":"Unusual sign-in detected on your account","az":"Hesabınızda qeyri-adi giriş aşkarlandı"},"noun":{"en":"recent sign-in activity","az":"son giriş fəaliyyəti"}},
 "HR":{"team":{"en":"People & Culture","az":"İnsan Resursları"},"subject":{"en":"Please confirm your updated payroll details","az":"Yenilənmiş əmək haqqı məlumatlarınızı təsdiqləyin"},"noun":{"en":"payroll and benefits profile","az":"əmək haqqı və benefit profili"}},
 "Management":{"team":{"en":"Executive Office","az":"İcraçı Ofis"},"subject":{"en":"Quick approval needed before today's review","az":"Bu günkü baxışdan əvvəl təcili təsdiq lazımdır"},"noun":{"en":"pending approval documents","az":"təsdiq gözləyən sənədlər"}},
 "Legal":{"team":{"en":"Legal & Compliance","az":"Hüquq və Uyğunluq"},"subject":{"en":"Signature required on updated compliance agreement","az":"Yenilənmiş uyğunluq sazişində imza tələb olunur"},"noun":{"en":"compliance agreement","az":"uyğunluq sazişi"}},
 "Sales":{"team":{"en":"Sales Operations","az":"Satış Əməliyyatları"},"subject":{"en":"Client contract awaiting your confirmation","az":"Müştəri müqaviləsi təsdiqinizi gözləyir"},"noun":{"en":"contract and pricing files","az":"müqavilə və qiymət faylları"}},
 "Marketing":{"team":{"en":"Brand & Communications","az":"Brend və Kommunikasiya"},"subject":{"en":"Approve the campaign assets before launch","az":"İşə salmadan əvvəl kampaniya materiallarını təsdiqləyin"},"noun":{"en":"shared campaign assets","az":"paylaşılan kampaniya materialları"}},
 "Operations":{"team":{"en":"Operations Center","az":"Əməliyyat Mərkəzi"},"subject":{"en":"Update required for your workflow access","az":"İş axını girişiniz üçün yeniləmə tələb olunur"},"noun":{"en":"workflow access records","az":"iş axını giriş qeydləri"}},
 "Engineering":{"team":{"en":"Platform Engineering","az":"Platforma Mühəndisliyi"},"subject":{"en":"Re-authenticate to keep your repository access","az":"Anbar girişini saxlamaq üçün yenidən doğrulama"},"noun":{"en":"repository and pipeline access","az":"anbar və pipeline girişi"}},
}
_DEFAULT={"team":{"en":"IT Service Desk","az":"İT Xidmət Masası"},"subject":{"en":"Action required on your account","az":"Hesabınızda tədbir tələb olunur"},"noun":{"en":"account access","az":"hesab girişi"}}

def _lang(v): return "az" if str(v or "").lower().startswith("az") else "en"

def _mock_scenario(payload):
    e=payload["employee"]; objective=payload.get("objective") or ""; difficulty=payload.get("difficulty","medium")
    lang=_lang(e.get("preferred_language")); dept=e["department"]; first=(e["full_name"] or "").split()[0] or "there"
    t=_THEME.get(dept,_DEFAULT); team=t["team"][lang]; noun=t["noun"][lang]
    ctx=payload.get("context") or []
    ctx_ref=ctx[0]["title"] if ctx else ("account review" if lang=="en" else "hesab yoxlaması")
    if lang=="az":
        subject=t["subject"]["az"]
        email_body=(f"Salam {first}, {team} komandası «{ctx_ref}» prosesini yekunlaşdırır və sizin təsdiqiniz hələ də gözlənilir. "
                    f"Zəhmət olmasa yenilənmiş {noun} məlumatlarını nəzərdən keçirin və günün sonuna qədər aşağıdakı təhlükəsiz portal linki vasitəsilə hesabınızı təsdiqləyin. "
                    f"Sessiyanız bitibsə, davam etmək üçün yenidən daxil olmağınız istənə bilər. "
                    f"Cədvələ riayət etməyə kömək etdiyiniz üçün əvvəlcədən təşəkkür edirik.")
        pretext=f"{team} adından, real görünən {dept} iş axınına istinad edərək vaxt təzyiqi yaradan ssenari."
        landing=("Bu, icazə verilmiş təhlükəsizlik simulyasiyasıdır (simulation). Həqiqi parolu (password) daxil etməyin — "
                 "yazdığınız hər hansı dəyər dərhal silinir və heç vaxt saxlanmır.")
    else:
        subject=t["subject"]["en"]
        email_body=(f"Hi {first}, {team} is finalizing the {ctx_ref} and your confirmation is still outstanding. "
                    f"Please review the updated {noun} and verify your account through the secure portal link below before the end of the day. "
                    f"If your session has expired, you may be asked to sign in again to continue. "
                    f"Thanks in advance for helping us keep everything on schedule.")
        pretext=f"Impersonates {team}, referencing a realistic {dept} workflow to create time pressure."
        landing=("This is an authorized security-awareness simulation. Do not enter a real password — "
                 "any value you type is discarded immediately and is never stored.")
    return {"subject":subject,"email_body":email_body,"pretext":pretext,"landing_page_message":landing,
            "training_objective":objective or "Recognize contextual social-engineering cues",
            "risk_indicators":["authority impersonation","time pressure","account verification request","secure-portal link"],
            "difficulty":difficulty}

class MockLLMProvider(LLMProvider):
    def generate(self,payload): return _mock_scenario(payload)

class OpenAIProvider(LLMProvider):
    def generate(self,payload):
        if not settings.llm_api_key: raise RuntimeError("LLM_API_KEY is not configured")
        instruction=("Return JSON only with keys subject,email_body,pretext,landing_page_message,training_objective,risk_indicators,difficulty. "
          "Create an authorized phishing-awareness simulation email using ONLY the synthetic context provided, written in the employee's preferred_language. "
          "email_body must be a realistic 3-4 sentence message that references the role/department context and ends with a call to action to use a secure portal link. "
          "Never request real credentials, external links, malware, scripts, executable payloads, or instructions for evasion. "
          "The landing_page_message must explicitly say it is an authorized simulation and must tell the user not to enter a real password.")
        body={"model":settings.llm_model,"input":[{"role":"system","content":instruction},{"role":"user","content":json.dumps(payload)}],"text":{"format":{"type":"json_schema","name":"scenario","strict":True,"schema":{"type":"object","properties":{"subject":{"type":"string"},"email_body":{"type":"string"},"pretext":{"type":"string"},"landing_page_message":{"type":"string"},"training_objective":{"type":"string"},"risk_indicators":{"type":"array","items":{"type":"string"}},"difficulty":{"type":"string"}},"required":["subject","email_body","pretext","landing_page_message","training_objective","risk_indicators","difficulty"],"additionalProperties":False}}}}
        with httpx.Client(timeout=30) as c:
            r=c.post(settings.openai_base_url.rstrip('/')+"/responses",headers={"Authorization":f"Bearer {settings.llm_api_key}","Content-Type":"application/json"},json=body); r.raise_for_status(); data=r.json()
        text="".join(x.get("text","") for item in data.get("output",[]) for x in item.get("content",[]) if x.get("type")=="output_text")
        return json.loads(text)

def get_llm_provider(): return MockLLMProvider() if settings.llm_provider.lower()=="mock" else OpenAIProvider()
