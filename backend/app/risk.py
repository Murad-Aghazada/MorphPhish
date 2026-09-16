DEPT={"Finance":18,"Security":15,"IT":14,"Management":16,"HR":12,"Operations":10}
def calculate(employee, prior_events=0):
    factors={
      "department_exposure": DEPT.get(employee.department,8),
      "role_privilege": employee.privilege_level*7,
      "access_sensitivity": employee.access_sensitivity*6,
      "social_engineering_exposure": employee.social_exposure*5,
      "previous_simulation_behavior": min(prior_events*4,12),
    }
    score=min(100.0, round(sum(factors.values())/1.18,1))
    level="low" if score<35 else "medium" if score<65 else "high" if score<85 else "critical"
    return score,level,factors
