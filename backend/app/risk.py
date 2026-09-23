"""Explainable, role- and department-aware risk profiling.

Score (0-100) is a weighted sum of transparent factors so the profile can be
justified per employee. Attributes come from the HR data layer; language drives
content generation rather than the score, and is recorded on the employee.
"""

# Department attack-surface exposure.
DEPT = {"Finance": 18, "Security": 15, "IT": 14, "Management": 16, "Legal": 13,
        "HR": 12, "Engineering": 12, "Sales": 11, "Operations": 10, "Marketing": 9}

# Role-title seniority/targeting weight (first keyword match wins).
ROLE_SIGNALS = [
    (("chief", "ceo", "cfo", "cto", "president", "director", "head"), 16),
    (("administrator", "admin", "sysadmin", "devops"), 14),
    (("manager", "lead"), 12),
    (("counsel", "accountant", "controller"), 10),
    (("engineer", "developer"), 9),
    (("specialist", "analyst", "officer", "coordinator", "executive"), 7),
    (("intern", "assistant", "technician", "desk"), 5),
]


def role_weight(role):
    r = (role or "").lower()
    for keywords, weight in ROLE_SIGNALS:
        if any(k in r for k in keywords):
            return weight
    return 6


def calculate(employee, prior_events=0):
    factors = {
        "department_exposure": DEPT.get(employee.department, 8),
        "role_seniority": role_weight(employee.role),
        "access_privilege": employee.privilege_level * 5,
        "data_sensitivity": employee.access_sensitivity * 6,
        "social_exposure": employee.social_exposure * 5,
        "prior_behavior": min(prior_events * 4, 12),
    }
    # Max attainable ~126; divide so a maximal profile lands near 100.
    score = min(100.0, round(sum(factors.values()) / 1.26, 1))
    level = "low" if score < 35 else "medium" if score < 65 else "high" if score < 85 else "critical"
    return score, level, factors
