"""Explainable risk-profiling model.

The profile score (0-100) is a weighted sum of transparent dimensions so every
result can be justified per employee. Five base dimensions — driven by the
plan's role / department / language attributes plus data access and social
exposure — carry fixed weights that sum to 100. Prior risky behaviour is an
additive adaptive modifier on top (capped), which later weeks extend.

`calculate` returns (score, level, factors) where `factors` is an ordered list
of contribution records: {key, label, category, weight, points, detail}.
"""

# Department attack-surface exposure (raw points; normalized against the max).
DEPT = {"Finance": 18, "Security": 15, "IT": 14, "Management": 16, "Legal": 13,
        "HR": 12, "Engineering": 12, "Sales": 11, "Operations": 10, "Marketing": 9}
_DEPT_MAX = max(DEPT.values())
_DEPT_DEFAULT = 8

# Role-title seniority/targeting weight, 0-16 (first keyword match wins).
ROLE_SIGNALS = [
    (("chief", "ceo", "cfo", "cto", "president", "director", "head"), 16),
    (("administrator", "admin", "sysadmin", "devops"), 14),
    (("manager", "lead"), 12),
    (("counsel", "accountant", "controller"), 10),
    (("engineer", "developer"), 9),
    (("specialist", "analyst", "officer", "coordinator", "executive"), 7),
    (("intern", "assistant", "technician", "desk"), 5),
]
_ROLE_MAX = 16

# Language exposure, 0-1. English-operating staff face a larger volume of
# cross-border phishing; the primary local language faces fewer but more
# targeted lures. Modest weight — a documented, defensible academic heuristic.
LANG_EXPOSURE = {"az": 0.45, "en": 0.80, "ru": 0.60, "tr": 0.55}
_LANG_DEFAULT = 0.60

# Base-dimension weights (sum = 100).
WEIGHTS = {"role_privilege": 30, "department_exposure": 22, "data_sensitivity": 20,
           "social_exposure": 18, "language_exposure": 10}
BEHAVIOR_CAP = 12  # additive modifier ceiling


def role_weight(role):
    r = (role or "").lower()
    for keywords, weight in ROLE_SIGNALS:
        if any(k in r for k in keywords):
            return weight
    return 6


def language_exposure(language):
    return LANG_EXPOSURE.get((language or "en").lower()[:2], _LANG_DEFAULT)


def _clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def calculate(employee, prior_events=0):
    priv = employee.privilege_level or 1
    # Each dimension: (key, label, category, weight, normalized 0-1 value, detail)
    dims = [
        ("role_privilege", "Role & privilege", "role", WEIGHTS["role_privilege"],
         _clamp01(0.6 * role_weight(employee.role) / _ROLE_MAX + 0.4 * priv / 5),
         f"{employee.role} · privilege {priv}/5"),
        ("department_exposure", "Department exposure", "department", WEIGHTS["department_exposure"],
         _clamp01(DEPT.get(employee.department, _DEPT_DEFAULT) / _DEPT_MAX),
         employee.department),
        ("data_sensitivity", "Data sensitivity", "access", WEIGHTS["data_sensitivity"],
         _clamp01((employee.access_sensitivity or 1) / 5),
         f"access {employee.access_sensitivity}/5"),
        ("social_exposure", "Social exposure", "social", WEIGHTS["social_exposure"],
         _clamp01((employee.social_exposure or 1) / 5),
         f"exposure {employee.social_exposure}/5"),
        ("language_exposure", "Language exposure", "language", WEIGHTS["language_exposure"],
         language_exposure(employee.preferred_language),
         f"operates in {employee.preferred_language}"),
    ]
    factors = [{"key": k, "label": l, "category": c, "weight": w, "points": round(w * v, 1), "detail": d}
               for (k, l, c, w, v, d) in dims]
    base = sum(f["points"] for f in factors)

    behavior = min((prior_events or 0) * 4, BEHAVIOR_CAP)
    if behavior:
        factors.append({"key": "prior_behavior", "label": "Prior risky behaviour", "category": "behavior",
                        "weight": BEHAVIOR_CAP, "points": float(behavior),
                        "detail": f"{prior_events} prior risky interaction(s)"})

    score = min(100.0, round(base + behavior, 1))
    level = "low" if score < 35 else "medium" if score < 65 else "high" if score < 85 else "critical"
    return score, level, factors
