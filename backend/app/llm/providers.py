from abc import ABC, abstractmethod
import json, httpx
from app.core.config import settings
class LLMProvider(ABC):
    @abstractmethod
    def generate(self,payload:dict)->dict: ...
class MockLLMProvider(LLMProvider):
    def generate(self,payload):
        e=payload["employee"]; objective=payload["objective"]; difficulty=payload["difficulty"]
        return {"subject":f"[SIMULATION] {e['department']} workflow review","email_body":f"Authorized awareness simulation for {e['full_name']}. Please review the synthetic {e['department']} workflow notice and use only the simulation link provided by the platform.","pretext":f"Synthetic internal workflow update tailored to the {e['role']} role.","landing_page_message":"This is an authorized security-awareness simulation. Do not enter a real password.","training_objective":objective,"risk_indicators":["unexpected request","urgency cue","link destination verification"],"difficulty":difficulty}
class OpenAIProvider(LLMProvider):
    def generate(self,payload):
        if not settings.llm_api_key: raise RuntimeError("LLM_API_KEY is not configured")
        instruction=("Return JSON only with keys subject,email_body,pretext,landing_page_message,training_objective,risk_indicators,difficulty. "
          "Create an authorized phishing-awareness simulation using ONLY the synthetic context provided. Never request real credentials, external links, malware, scripts, executable payloads, or instructions for evasion. The landing page must explicitly say it is an authorized simulation and must tell the user not to enter a real password.")
        body={"model":settings.llm_model,"input":[{"role":"system","content":instruction},{"role":"user","content":json.dumps(payload)}],"text":{"format":{"type":"json_schema","name":"scenario","strict":True,"schema":{"type":"object","properties":{"subject":{"type":"string"},"email_body":{"type":"string"},"pretext":{"type":"string"},"landing_page_message":{"type":"string"},"training_objective":{"type":"string"},"risk_indicators":{"type":"array","items":{"type":"string"}},"difficulty":{"type":"string"}},"required":["subject","email_body","pretext","landing_page_message","training_objective","risk_indicators","difficulty"],"additionalProperties":False}}}}
        with httpx.Client(timeout=30) as c:
            r=c.post(settings.openai_base_url.rstrip('/')+"/responses",headers={"Authorization":f"Bearer {settings.llm_api_key}","Content-Type":"application/json"},json=body); r.raise_for_status(); data=r.json()
        text="".join(x.get("text","") for item in data.get("output",[]) for x in item.get("content",[]) if x.get("type")=="output_text")
        return json.loads(text)
def get_llm_provider(): return MockLLMProvider() if settings.llm_provider.lower()=="mock" else OpenAIProvider()
