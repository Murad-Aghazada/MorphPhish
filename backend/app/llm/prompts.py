"""Prompt-engineering layer for scenario generation.

A single template system, shared by every LLM provider:
  * `render_scenario(payload)` deterministically renders a scenario from the
    templates (used by the offline MockLLMProvider and by tests);
  * `build_prompt(payload)` assembles the system + user prompts a real model
    (OpenAI / Anthropic) receives, describing the same intent and constraints.

Templates vary by department (theme), difficulty (tone / red-flag density),
and language, so output is driven by the persona's role attributes. All content
is synthetic; no real links, credentials, or payloads are ever produced.
"""

# Supported output languages (extensible — add a code + its templates below).
LANGUAGES = {"az": "Azerbaijani", "en": "English"}


def normalize_language(v):
    v = (v or "en").lower()
    if v.startswith("az"):
        return "az"
    return "en"


# Per-department theme: the team the lure impersonates and the asset it references.
DEPARTMENT_THEMES = {
    "Finance":     {"team": {"en": "Finance Operations", "az": "Maliyyə Əməliyyatları"},   "asset": {"en": "vendor payment records", "az": "təchizatçı ödəniş qeydləri"}},
    "IT":          {"team": {"en": "IT Service Desk", "az": "İT Xidmət Masası"},           "asset": {"en": "mailbox and VPN access", "az": "poçt və VPN girişi"}},
    "Security":    {"team": {"en": "Information Security", "az": "İnformasiya Təhlükəsizliyi"}, "asset": {"en": "recent sign-in activity", "az": "son giriş fəaliyyəti"}},
    "HR":          {"team": {"en": "People & Culture", "az": "İnsan Resursları"},           "asset": {"en": "payroll and benefits profile", "az": "əmək haqqı və benefit profili"}},
    "Management":  {"team": {"en": "Executive Office", "az": "İcraçı Ofis"},                "asset": {"en": "pending approval documents", "az": "təsdiq gözləyən sənədlər"}},
    "Legal":       {"team": {"en": "Legal & Compliance", "az": "Hüquq və Uyğunluq"},       "asset": {"en": "compliance agreement", "az": "uyğunluq sazişi"}},
    "Sales":       {"team": {"en": "Sales Operations", "az": "Satış Əməliyyatları"},        "asset": {"en": "contract and pricing files", "az": "müqavilə və qiymət faylları"}},
    "Marketing":   {"team": {"en": "Brand & Communications", "az": "Brend və Kommunikasiya"}, "asset": {"en": "shared campaign assets", "az": "paylaşılan kampaniya materialları"}},
    "Operations":  {"team": {"en": "Operations Center", "az": "Əməliyyat Mərkəzi"},         "asset": {"en": "workflow access records", "az": "iş axını giriş qeydləri"}},
    "Engineering": {"team": {"en": "Platform Engineering", "az": "Platforma Mühəndisliyi"}, "asset": {"en": "repository and pipeline access", "az": "anbar və pipeline girişi"}},
}
DEFAULT_THEME = {"team": {"en": "IT Service Desk", "az": "İT Xidmət Masası"}, "asset": {"en": "account access", "az": "hesab girişi"}}

DIFFICULTIES = ("easy", "medium", "hard")
DIFFICULTY_GUIDANCE = {
    "easy": "overt urgency and obvious red flags a trained user should easily catch",
    "medium": "a professional, contextual message with moderate time pressure",
    "hard": "a subtle, highly contextual message with very few red flags",
}
_DEFAULT_CTX = {"en": "account review", "az": "hesab yoxlaması"}

_RISK_INDICATORS = {
    "easy": ["account suspension threat", "extreme urgency", "generic greeting", "verify-now link"],
    "medium": ["authority impersonation", "time pressure", "account verification request", "secure-portal link"],
    "hard": ["trusted-context reference", "soft call to action", "plausible sender", "credential re-entry request"],
}

_LANDING = {
    "en": ("This is an authorized security-awareness simulation. Do not enter a real password — "
           "any value you type is discarded immediately and is never stored."),
    "az": ("Bu, icazə verilmiş təhlükəsizlik simulyasiyasıdır (simulation). Həqiqi parolu (password) daxil etməyin — "
           "yazdığınız hər hansı dəyər dərhal silinir və heç vaxt saxlanmır."),
}


def _subject(lang, difficulty, team, asset, ctx_ref):
    if lang == "az":
        return {
            "easy": "TƏCİLİ: hesabınız bu gün dayandırılacaq",
            "medium": f"Tədbir tələb olunur: {asset} təsdiqi",
            "hard": f"Re: {ctx_ref} — qısa təsdiq lazımdır",
        }[difficulty]
    return {
        "easy": "URGENT: your account will be suspended today",
        "medium": f"Action required: {asset} confirmation",
        "hard": f"Re: {ctx_ref} — quick confirmation needed",
    }[difficulty]


def _body(lang, difficulty, first, team, asset, ctx_ref):
    if lang == "az":
        return {
            "easy": (f"Hörmətli istifadəçi, hesabınızda problem aşkarlandı və bir neçə saat ərzində dayandırılacaq. "
                     f"Girişi itirməmək üçün aşağıdakı təhlükəsiz portal linki ilə {asset} məlumatlarınızı dərhal təsdiqləyin. "
                     f"Bu gün təsdiqləməsəniz, uzun manual bərpa prosesi tələb olunacaq. "
                     f"Hesabınızı aktiv saxlamaq üçün indi hərəkət edin."),
            "medium": (f"Salam {first}, {team} komandası «{ctx_ref}» prosesini yekunlaşdırır və sizin təsdiqiniz hələ də gözlənilir. "
                       f"Zəhmət olmasa yenilənmiş {asset} məlumatlarını nəzərdən keçirin və günün sonuna qədər aşağıdakı təhlükəsiz portal linki ilə hesabınızı təsdiqləyin. "
                       f"Sessiyanız bitibsə, davam etmək üçün yenidən daxil olmağınız istənə bilər. "
                       f"Kömək etdiyiniz üçün əvvəlcədən təşəkkür edirik."),
            "hard": (f"Salam {first}, danışdığımız «{ctx_ref}» ilə bağlı davam edirəm — yenilənmiş {asset} sənədini nəzərdən keçirməyiniz üçün paylaşdım. "
                     f"İmkanınız olanda, aşağıdakı təhlükəsiz portal linki vasitəsilə detalları təsdiqləyə bilərsinizmi ki, məsələni bağlayaq? "
                     f"Tələsmirik, amma komanda görüşündən əvvəl təsdiqiniz faydalı olardı. "
                     f"Çox sağ olun."),
        }[difficulty]
    return {
        "easy": (f"Dear user, we detected a problem with your account and it will be suspended within a few hours. "
                 f"You must verify your {asset} immediately using the secure portal link below to avoid losing access. "
                 f"Failure to confirm today will require a lengthy manual reactivation. "
                 f"Act now to keep your account active."),
        "medium": (f"Hi {first}, {team} is finalizing the {ctx_ref} and your confirmation is still outstanding. "
                   f"Please review the updated {asset} and verify your account through the secure portal link below before the end of the day. "
                   f"If your session has expired, you may be asked to sign in again to continue. "
                   f"Thanks in advance for helping us keep everything on schedule."),
        "hard": (f"Hi {first}, following up on the {ctx_ref} we discussed — I've shared the updated {asset} for your review. "
                 f"When you have a moment, could you confirm the details through the secure portal link below so we can close this out? "
                 f"No rush, but it would help to have your sign-off before the team sync. "
                 f"Thanks so much."),
    }[difficulty]


def _parts(payload):
    """Resolve the template inputs from a generation payload."""
    persona = payload.get("employee", {})
    lang = normalize_language(persona.get("preferred_language"))
    difficulty = payload.get("difficulty") if payload.get("difficulty") in DIFFICULTIES else "medium"
    dept = persona.get("department", "")
    first = (persona.get("full_name") or "").split()[0] or ("istifadəçi" if lang == "az" else "there")
    theme = DEPARTMENT_THEMES.get(dept, DEFAULT_THEME)
    team = theme["team"][lang]
    asset = theme["asset"][lang]
    ctx = payload.get("context") or []
    ctx_ref = (ctx[0].get("title") if ctx else None) or _DEFAULT_CTX[lang]
    objective = payload.get("objective") or ("Recognize contextual social-engineering cues")
    return lang, difficulty, dept, first, team, asset, ctx_ref, objective


def render_scenario(payload):
    """Deterministically render a full scenario dict from the templates."""
    lang, difficulty, dept, first, team, asset, ctx_ref, objective = _parts(payload)
    pretext = (f"{difficulty} çətinlikdə {team} adından, real {dept} iş axınına ({ctx_ref}) istinad edən ssenari."
               if lang == "az" else
               f"Impersonates {team} at {difficulty} difficulty, referencing a realistic {dept} workflow ({ctx_ref}).")
    return {
        "subject": _subject(lang, difficulty, team, asset, ctx_ref),
        "email_body": _body(lang, difficulty, first, team, asset, ctx_ref),
        "pretext": pretext,
        "landing_page_message": _LANDING[lang],
        "training_objective": objective,
        "risk_indicators": list(_RISK_INDICATORS[difficulty]),
        "difficulty": difficulty,
    }


def build_prompt(payload):
    """Assemble (system, user) prompts for a real LLM, mirroring the templates."""
    lang, difficulty, dept, first, team, asset, ctx_ref, objective = _parts(payload)
    system = (
        "You generate a single authorized phishing-awareness SIMULATION email for a training platform. "
        f"Write everything in {LANGUAGES[lang]}. "
        f"Impersonate the '{team}' team and reference the operational context titled '{ctx_ref}', "
        f"targeting a {dept} employee. Difficulty is {difficulty}: {DIFFICULTY_GUIDANCE[difficulty]}. "
        "The email_body must be 3-4 sentences and end with a call to action to use a secure portal link. "
        "SAFETY: use only the synthetic context provided; never include real URLs, malware, scripts, "
        "executable payloads, credential-harvesting instructions, or evasion guidance. "
        "landing_page_message MUST state it is an authorized simulation and tell the user not to enter a real password. "
        "Return ONLY a JSON object with keys: subject, email_body, pretext, landing_page_message, "
        "training_objective, risk_indicators (array of strings), difficulty."
    )
    user = {
        "employee": payload.get("employee", {}),
        "risk": payload.get("risk", {}),
        "operational_context": payload.get("context", []),
        "objective": objective,
        "difficulty": difficulty,
        "language": lang,
    }
    return system, user


# JSON schema shared by structured-output providers.
SCENARIO_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "email_body": {"type": "string"},
        "pretext": {"type": "string"},
        "landing_page_message": {"type": "string"},
        "training_objective": {"type": "string"},
        "risk_indicators": {"type": "array", "items": {"type": "string"}},
        "difficulty": {"type": "string"},
    },
    "required": ["subject", "email_body", "pretext", "landing_page_message", "training_objective", "risk_indicators", "difficulty"],
    "additionalProperties": False,
}
